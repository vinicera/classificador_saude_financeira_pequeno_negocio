"""
app.py
------
O aplicativo web (Flask). Este arquivo é de propósito "fino": ele só
recebe cliques/formulários, chama os módulos que fazem o trabalho de
verdade e entrega os resultados para os templates HTML mostrarem.

Divisão de responsabilidades (cada módulo é explicável separadamente):
    dados.py       -> banco SQLite (perfil + lançamentos)
    analise.py     -> cálculo dos 10 indicadores
    score.py       -> score 0–100 + classe do semáforo
    alertas.py     -> regras de alerta
    ia_analise.py  -> IA local: classificador Random Forest + previsão
    io_excel.py    -> importação validada, template e exportação Excel
    relatorio.py   -> relatório PDF

Como rodar:
    pip install -r requirements.txt
    python treinar.py        (uma vez, para criar o modelo de IA)
    python app.py            -> abre http://127.0.0.1:5000
"""

import json
import os

from flask import Flask, flash, redirect, render_template, request, send_file, url_for

import dados
from alertas import gerar_alertas
from analise import INFO_INDICADORES, calcular_indicadores
from configuracao import carregar_config
from gerar_sintetico import gerar_negocio_demo
from ia_analise import classificar_mes, prever_meses
from io_excel import exportar_excel, gerar_template, importar_arquivo, validar_linha
from relatorio import formatar_valor, gerar_pdf
from score import calcular_score, classificar

app = Flask(__name__)
# Chave usada pelo Flask só para assinar as mensagens de aviso (flash).
# Em um site de verdade isso seria um segredo; aqui pode ser fixo.
app.secret_key = "saude-mei-projeto-academico"


# ---------------------------------------------------------------------------
# Filtros do Jinja: formatação brasileira de números nos templates
# ---------------------------------------------------------------------------

@app.template_filter("dinheiro")
def filtro_dinheiro(valor):
    """1234.5 -> 'R$ 1.234,50' (ou '—' se não houver valor)."""
    return formatar_valor(valor, "reais")


@app.template_filter("indicador")
def filtro_indicador(valor, formato):
    """Formata um indicador conforme sua ficha (pct, meses, reais...)."""
    return formatar_valor(valor, formato)


# ---------------------------------------------------------------------------
# Contexto comum: tudo que várias telas precisam, calculado num lugar só
# ---------------------------------------------------------------------------

def montar_contexto():
    """
    Carrega os dados e roda a esteira completa de análise:
    lançamentos -> indicadores -> score -> previsão -> alertas -> IA.
    Devolve um dicionário pronto para entregar aos templates.
    """
    lancamentos = dados.carregar_lancamentos()
    perfil = dados.carregar_perfil()

    if not lancamentos:
        return {"lancamentos": [], "perfil": perfil}

    indicadores_por_mes = calcular_indicadores(lancamentos, perfil)
    scores_por_mes = [calcular_score(indicadores) for indicadores in indicadores_por_mes]
    previsao = prever_meses(lancamentos, perfil)

    # O alerta nº 7 ("modelo projeta piora") depende da previsão
    queda_prevista = previsao["queda_score"] if previsao.get("disponivel") else None
    alertas_ativos = gerar_alertas(lancamentos, indicadores_por_mes, queda_prevista)

    return {
        "lancamentos": lancamentos,
        "perfil": perfil,
        "indicadores_por_mes": indicadores_por_mes,
        "scores_por_mes": scores_por_mes,
        "indicadores": indicadores_por_mes[-1],   # mês mais recente
        "resultado_score": scores_por_mes[-1],
        "previsao": previsao,
        "alertas": alertas_ativos,
        "classificacao_ml": classificar_mes(indicadores_por_mes),
    }


# ---------------------------------------------------------------------------
# Telas
# ---------------------------------------------------------------------------

@app.route("/")
def diagnostico():
    """Tela 1 — Diagnóstico: gauge do score, classe, resumo do mês, alertas."""
    contexto = montar_contexto()
    if not contexto["lancamentos"]:
        return render_template("diagnostico.html", **contexto)

    # Resumo do mês atual (e comparação com o mês anterior, se existir)
    atual = contexto["lancamentos"][-1]
    anterior = contexto["lancamentos"][-2] if len(contexto["lancamentos"]) > 1 else None
    despesas = atual["despesas_fixas"] + atual["despesas_variaveis"]
    contexto["resumo"] = {
        "receita": atual["receita_total"],
        "despesas": despesas,
        "lucro": atual["receita_total"] - despesas,
        "caixa": atual["saldo_caixa_final"],
        "variacao_receita": (atual["receita_total"] - anterior["receita_total"])
                            if anterior else None,
    }
    return render_template("diagnostico.html", **contexto)


@app.route("/indicadores")
def indicadores():
    """Tela 2 — Indicadores: cartões com valor, nota e evolução de cada KPI."""
    contexto = montar_contexto()
    if not contexto["lancamentos"]:
        return redirect(url_for("lancamentos"))

    # Série histórica de cada indicador, para os gráficos de linha
    series = {}
    for info in INFO_INDICADORES:
        series[info["chave"]] = {
            "meses": [item["mes"] for item in contexto["indicadores_por_mes"]],
            "valores": [item.get(info["chave"]) for item in contexto["indicadores_por_mes"]],
        }
    # Situação (classe do semáforo) da NOTA de cada indicador no mês atual
    situacoes = {}
    for chave, nota in contexto["resultado_score"]["notas"].items():
        situacoes[chave] = classificar(nota)

    contexto["info_indicadores"] = INFO_INDICADORES
    contexto["series"] = series
    contexto["situacoes"] = situacoes
    return render_template("indicadores.html", **contexto)


@app.route("/previsao")
def previsao():
    """Tela 3 — Previsão: receita, caixa e score projetados com cenários."""
    contexto = montar_contexto()
    if not contexto["lancamentos"]:
        return redirect(url_for("lancamentos"))
    return render_template("previsao.html", **contexto)


@app.route("/lancamentos", methods=["GET", "POST"])
def lancamentos():
    """
    Tela 4 — Lançamentos: tabela dos meses + formulário de novo mês +
    botões de importação/exportação. O POST é o envio do formulário.
    """
    if request.method == "POST":
        # O formulário chega como textos; validamos com as MESMAS regras
        # da importação de planilha (io_excel.validar_linha)
        lancamento, erros = validar_linha(request.form.to_dict())
        if erros:
            for erro in erros:
                flash(f"Erro no formulário: {erro}", "erro")
        else:
            dados.salvar_lancamento(lancamento)
            flash(f"Mês {lancamento['mes']} salvo com sucesso!", "ok")
        return redirect(url_for("lancamentos"))

    contexto = montar_contexto()
    contexto["campos"] = dados.CAMPOS_LANCAMENTO
    return render_template("lancamentos.html", **contexto)


@app.route("/lancamentos/excluir", methods=["POST"])
def excluir_lancamento():
    """Apaga um mês da tabela (botão de lixeira na lista de lançamentos)."""
    mes = request.form.get("mes", "")
    dados.excluir_lancamento(mes)
    flash(f"Lançamento de {mes} excluído.", "ok")
    return redirect(url_for("lancamentos"))


@app.route("/importar", methods=["POST"])
def importar():
    """
    Importação de planilha (.csv ou .xlsx). Regra da especificação:
    se QUALQUER linha tiver erro, nada é gravado — mostramos o relatório
    de erros linha a linha para a pessoa corrigir o arquivo e reenviar.
    """
    arquivo = request.files.get("arquivo")
    if not arquivo or not arquivo.filename:
        flash("Nenhum arquivo selecionado.", "erro")
        return redirect(url_for("lancamentos"))

    lancamentos_validos, relatorio_erros = importar_arquivo(arquivo.read(), arquivo.filename)

    if relatorio_erros:
        contexto = montar_contexto()
        contexto["campos"] = dados.CAMPOS_LANCAMENTO
        contexto["erros_importacao"] = relatorio_erros
        contexto["nome_arquivo_erro"] = arquivo.filename
        return render_template("lancamentos.html", **contexto)

    for lancamento in lancamentos_validos:
        dados.salvar_lancamento(lancamento)
    flash(f"{len(lancamentos_validos)} meses importados de {arquivo.filename}!", "ok")
    return redirect(url_for("lancamentos"))


@app.route("/metodologia")
def metodologia():
    """Tela 5 — Metodologia: como tudo é calculado, em linguagem simples."""
    config = carregar_config()

    # Métricas reais do último treino (se o modelo já foi treinado)
    metricas = None
    caminho_metricas = os.path.join("modelos", "metricas.json")
    if os.path.exists(caminho_metricas):
        with open(caminho_metricas, encoding="utf-8") as arquivo:
            metricas = json.load(arquivo)

    return render_template(
        "metodologia.html",
        info_indicadores=INFO_INDICADORES,
        pesos=config["pesos"],
        faixas=config["faixas"],
        classes=config["classes"],
        mei=config["mei"],
        metricas=metricas,
        perfil=dados.carregar_perfil(),
    )


@app.route("/configuracoes", methods=["GET", "POST"])
def configuracoes():
    """Tela 6 — Configurações: perfil do negócio + parâmetros do config.yaml."""
    if request.method == "POST":
        formulario = request.form
        if not formulario.get("nome", "").strip():
            flash("O nome do negócio é obrigatório.", "erro")
        elif not formulario.get("data_abertura", ""):
            flash("Informe a data de abertura.", "erro")
        else:
            meta = formulario.get("meta_anual", "").strip()
            dados.salvar_perfil({
                "nome": formulario["nome"].strip(),
                "cnpj": formulario.get("cnpj", "").strip() or None,
                "atividade": formulario.get("atividade", "comercio"),
                "data_abertura": formulario["data_abertura"],
                "meta_anual": float(meta.replace(",", ".")) if meta else None,
            })
            flash("Perfil salvo!", "ok")
        return redirect(url_for("configuracoes"))

    config = carregar_config()
    return render_template(
        "configuracoes.html",
        perfil=dados.carregar_perfil(),
        pesos=config["pesos"],
        faixas=config["faixas"],
        mei=config["mei"],
        info_indicadores=INFO_INDICADORES,
    )


# ---------------------------------------------------------------------------
# Downloads e modo demo
# ---------------------------------------------------------------------------

@app.route("/baixar-template")
def baixar_template():
    """Download do template oficial de lançamentos (.xlsx)."""
    return send_file(gerar_template(), as_attachment=True,
                     download_name="template_lancamentos.xlsx")


@app.route("/baixar-exemplo")
def baixar_exemplo():
    """
    Download do CSV da empresa de exemplo (12 meses de um comércio fictício).
    Serve para a pessoa experimentar o fluxo completo: baixar o arquivo e
    importá-lo na tela Lançamentos, como faria com os dados dela.
    """
    return send_file(os.path.abspath("dados_exemplo_mei.csv"), as_attachment=True,
                     download_name="dados_exemplo_mei.csv")


@app.route("/exportar-excel")
def exportar_para_excel():
    """Download do Excel com 3 abas: Dados, Indicadores e Previsão."""
    contexto = montar_contexto()
    if not contexto["lancamentos"]:
        flash("Lance pelo menos um mês antes de exportar.", "erro")
        return redirect(url_for("lancamentos"))
    memoria = exportar_excel(contexto["lancamentos"], contexto["indicadores_por_mes"],
                             contexto["scores_por_mes"], contexto["previsao"])
    return send_file(memoria, as_attachment=True, download_name="saude_mei_export.xlsx")


@app.route("/relatorio-pdf")
def relatorio_pdf():
    """Download do relatório PDF completo do diagnóstico."""
    contexto = montar_contexto()
    if not contexto["lancamentos"]:
        flash("Lance pelo menos um mês antes de gerar o relatório.", "erro")
        return redirect(url_for("lancamentos"))
    memoria = gerar_pdf(contexto["perfil"], contexto["lancamentos"],
                        contexto["indicadores_por_mes"], contexto["scores_por_mes"],
                        contexto["alertas"], contexto["previsao"],
                        contexto["classificacao_ml"])
    return send_file(memoria, as_attachment=True, download_name="saude_mei_relatorio.pdf")


@app.route("/demo", methods=["POST"])
def carregar_demo():
    """
    Modo demo: substitui os lançamentos por 18 meses de um negócio
    sintético (gerar_sintetico.py) — ótimo para apresentar o app sem
    precisar digitar dados.
    """
    dados.apagar_todos_lancamentos()
    for lancamento in gerar_negocio_demo():
        dados.salvar_lancamento(lancamento)
    if not dados.carregar_perfil():
        dados.salvar_perfil({
            "nome": "Doceria da Ana (demo)", "cnpj": None, "atividade": "comercio",
            "data_abertura": "2023-03", "meta_anual": 75000.0,
        })
    flash("Dados de demonstração carregados (18 meses de um negócio fictício).", "ok")
    return redirect(url_for("diagnostico"))


if __name__ == "__main__":
    # host="0.0.0.0" faz o servidor aceitar conexões de outros computadores
    # da MESMA rede (wifi): eles acessam pelo IP desta máquina, por exemplo
    # http://192.168.0.10:5000 (o IP aparece no terminal ao iniciar).
    # No seu próprio computador continua sendo http://127.0.0.1:5000.
    app.run(debug=True, host="0.0.0.0", port=5000)
