"""
relatorio.py
------------
Gera o RELATÓRIO PDF (seção 3.7 da especificação): capa com score e
classe, gráficos de evolução, tabela de indicadores com semáforo,
previsão com cenários e a lista de alertas/recomendações.

Ferramentas:
  - matplotlib desenha os gráficos e salva como imagem PNG em memória;
  - reportlab (platypus) monta o PDF empilhando blocos: título,
    parágrafos, tabelas e as imagens dos gráficos.
"""

import datetime
import io

import matplotlib

matplotlib.use("Agg")  # backend sem janela: só gera a imagem (necessário em servidor)
import matplotlib.pyplot as plt

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from analise import INFO_INDICADORES

# Cores de cada classe do semáforo (mesma paleta das telas)
CORES_CLASSE = {
    "saudavel": colors.HexColor("#157A5B"),
    "atencao": colors.HexColor("#B0791A"),
    "alerta": colors.HexColor("#C2601D"),
    "critico": colors.HexColor("#C0453B"),
}


def formatar_valor(valor, formato):
    """Formata um número para exibição: percentual, meses, R$ ou número puro."""
    if valor is None:
        return "—"
    if formato == "pct":
        return f"{valor * 100:.1f}%".replace(".", ",")
    if formato == "meses":
        return f"{valor:.1f} meses".replace(".", ",")
    if formato == "reais":
        return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{valor:.2f}".replace(".", ",")


def _grafico_para_imagem(figura, largura_cm=16, altura_cm=6):
    """Salva uma figura do matplotlib como PNG em memória e devolve o bloco Image."""
    memoria = io.BytesIO()
    figura.savefig(memoria, format="png", dpi=150, bbox_inches="tight")
    plt.close(figura)
    memoria.seek(0)
    return Image(memoria, width=largura_cm * cm, height=altura_cm * cm)


def _grafico_evolucao(lancamentos, scores_por_mes):
    """Gráfico 1: receita, despesas e caixa mês a mês + score no eixo direito."""
    meses = [item["mes"] for item in lancamentos]
    receitas = [item["receita_total"] for item in lancamentos]
    despesas = [item["despesas_fixas"] + item["despesas_variaveis"] for item in lancamentos]
    caixas = [item["saldo_caixa_final"] for item in lancamentos]
    scores = [resultado["score"] for resultado in scores_por_mes]

    figura, eixo = plt.subplots(figsize=(9, 3.4))
    eixo.plot(meses, receitas, marker="o", label="Receita", color="#157A5B")
    eixo.plot(meses, despesas, marker="o", label="Despesas", color="#C0453B")
    eixo.plot(meses, caixas, marker="o", label="Caixa", color="#4472C4")
    eixo.set_ylabel("R$")
    eixo.tick_params(axis="x", rotation=45, labelsize=7)
    eixo.legend(loc="upper left", fontsize=8)
    eixo.grid(alpha=0.3)

    eixo_score = eixo.twinx()
    eixo_score.plot(meses, scores, linestyle="--", color="#8A897F", label="Score")
    eixo_score.set_ylabel("Score (0–100)")
    eixo_score.set_ylim(0, 100)
    return _grafico_para_imagem(figura)


def _grafico_previsao(previsao):
    """Gráfico 2: receita projetada com a faixa pessimista–otimista sombreada."""
    meses = previsao["meses"]
    figura, eixo = plt.subplots(figsize=(9, 3.2))
    eixo.fill_between(meses, previsao["receita"]["pessimista"], previsao["receita"]["otimista"],
                      alpha=0.25, color="#157A5B", label="Faixa pessimista–otimista")
    eixo.plot(meses, previsao["receita"]["base"], marker="o", color="#157A5B", label="Cenário base")
    eixo.set_ylabel("Receita prevista (R$)")
    eixo.tick_params(axis="x", rotation=45, labelsize=8)
    eixo.legend(fontsize=8)
    eixo.grid(alpha=0.3)
    return _grafico_para_imagem(figura, altura_cm=5.5)


def gerar_pdf(perfil, lancamentos, indicadores_por_mes, scores_por_mes,
              alertas_ativos, previsao, classificacao_ml):
    """
    Monta o relatório completo e devolve um BytesIO pronto para download.
    Recebe tudo já calculado (app.py calcula uma vez e repassa) — este
    módulo só cuida da apresentação.
    """
    memoria = io.BytesIO()
    documento = SimpleDocTemplate(memoria, pagesize=A4,
                                  topMargin=1.5 * cm, bottomMargin=1.5 * cm)
    estilos = getSampleStyleSheet()
    estilo_titulo = ParagraphStyle("titulo", parent=estilos["Title"], fontSize=22, spaceAfter=6)
    estilo_secao = ParagraphStyle("secao", parent=estilos["Heading2"], spaceBefore=14)
    estilo_texto = estilos["BodyText"]

    resultado_atual = scores_por_mes[-1]
    indicadores_atuais = indicadores_por_mes[-1]
    cor_classe = CORES_CLASSE[resultado_atual["nivel"]]

    blocos = []

    # --- Capa / cabeçalho ----------------------------------------------------
    blocos.append(Paragraph("Saúde MEI — Diagnóstico do Negócio", estilo_titulo))
    hoje = datetime.date.today().strftime("%d/%m/%Y")
    nome_negocio = perfil["nome"] if perfil else "Negócio sem cadastro"
    blocos.append(Paragraph(f"{nome_negocio} · gerado em {hoje} · "
                            f"último mês lançado: {lancamentos[-1]['mes']}", estilo_texto))
    blocos.append(Spacer(1, 12))

    estilo_score = ParagraphStyle("score", parent=estilos["Title"],
                                  fontSize=34, textColor=cor_classe, spaceAfter=2)
    blocos.append(Paragraph(f"Score de Saúde: {resultado_atual['score']:.0f} / 100", estilo_score))
    blocos.append(Paragraph(
        f"<b>Classe: {resultado_atual['classe']}</b> (score por regras) · "
        f"classificação do modelo de IA: <b>{classificacao_ml['classe']}</b>", estilo_texto))
    blocos.append(Spacer(1, 10))

    # --- Evolução -------------------------------------------------------------
    blocos.append(Paragraph("Evolução do negócio", estilo_secao))
    blocos.append(_grafico_evolucao(lancamentos, scores_por_mes))

    # --- Tabela de indicadores com semáforo ------------------------------------
    blocos.append(Paragraph(f"Indicadores de {indicadores_atuais['mes']}", estilo_secao))
    linhas_tabela = [["Indicador", "Valor", "Referência", "Situação"]]
    estilos_tabela = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#ECEBE6")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D8D7D0")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#FAFAF8")]),
    ]

    from score import classificar  # importa aqui para evitar import circular na leitura

    for info in INFO_INDICADORES:
        valor = indicadores_atuais.get(info["chave"])
        nota = resultado_atual["notas"].get(info["chave"])
        if nota is None:
            situacao = "—"  # indicador informativo (sem peso) ou sem dado
        else:
            situacao = classificar(nota)["classe"]
            numero_linha = len(linhas_tabela)
            estilos_tabela.append(
                ("TEXTCOLOR", (3, numero_linha), (3, numero_linha),
                 CORES_CLASSE[classificar(nota)["nivel"]]))
            estilos_tabela.append(("FONTNAME", (3, numero_linha), (3, numero_linha), "Helvetica-Bold"))
        linhas_tabela.append([info["nome"], formatar_valor(valor, info["formato"]),
                              info["referencia"], situacao])

    tabela = Table(linhas_tabela, colWidths=[6.5 * cm, 3.5 * cm, 3.5 * cm, 3 * cm])
    tabela.setStyle(TableStyle(estilos_tabela))
    blocos.append(tabela)

    # --- Alertas ---------------------------------------------------------------
    blocos.append(Paragraph("Alertas e recomendações", estilo_secao))
    if alertas_ativos:
        for alerta in alertas_ativos:
            blocos.append(Paragraph(f"<b>• {alerta['titulo']}:</b> {alerta['mensagem']}", estilo_texto))
    else:
        blocos.append(Paragraph("Nenhum alerta ativo neste mês. Continue acompanhando!", estilo_texto))

    # --- Previsão ----------------------------------------------------------------
    blocos.append(Paragraph("Previsão dos próximos meses", estilo_secao))
    if previsao.get("disponivel"):
        blocos.append(_grafico_previsao(previsao))
        blocos.append(Paragraph(
            f"Modelo: {previsao['modelo']}. Erro típico da receita: "
            f"± R$ {previsao['erro_receita']:,.0f}. Score projetado (cenário base) daqui a "
            f"{len(previsao['meses'])} meses: <b>{previsao['score']['base'][-1]:.0f}</b> "
            f"(hoje: {previsao['score_atual']:.0f}).", estilo_texto))
    else:
        blocos.append(Paragraph(previsao.get("motivo", "Previsão indisponível."), estilo_texto))

    # --- Rodapé metodológico -------------------------------------------------------
    blocos.append(Spacer(1, 14))
    blocos.append(Paragraph(
        "<i>Como este relatório é feito: os indicadores são calculados pelas fórmulas "
        "clássicas de análise financeira; o score é uma média ponderada das notas de cada "
        "indicador (pesos no config.yaml); a classificação usa um modelo Random Forest "
        "treinado localmente com scikit-learn; a previsão usa regressão linear de tendência "
        "sobre o próprio histórico. Detalhes na página Metodologia do aplicativo.</i>",
        ParagraphStyle("rodape", parent=estilo_texto, fontSize=8,
                       textColor=colors.HexColor("#6B6B63"))))

    documento.build(blocos)
    memoria.seek(0)
    return memoria
