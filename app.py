"""
app.py
------
Versão web do programa, usando Flask. Substitui o menu de terminal
(main.py) por duas páginas: uma de entrada de dados e uma de resultado.

IMPORTANTE: a lógica de cálculo e diagnóstico não mudou nada — continua
em dados.py, analise.py e ia_analise.py, exatamente como já estava. Este
arquivo só recebe o que a pessoa preenche no formulário da página e chama
essas mesmas funções, depois manda o resultado pra página HTML mostrar.

Como rodar:
    pip install flask
    python app.py
Depois abre http://127.0.0.1:5000 no navegador.
"""

import os

from flask import Flask, render_template, request

from dados import carregar_csv, carregar_historico, salvar_historico
from analise import calcular_indicadores, analisar_tendencia
from ia_analise import diagnosticar

app = Flask(__name__)

SETORES_VALIDOS = ["comercio", "servicos", "industria"]
PASTA_UPLOADS = "uploads"


@app.route("/", methods=["GET"])
def index():
    """Página inicial: formulário para escolher setor e informar os dados."""
    return render_template("index.html", setores=SETORES_VALIDOS)


@app.route("/analisar", methods=["POST"])
def analisar():
    """
    Recebe o formulário (setor + CSV ou dados digitados), calcula os
    indicadores, pede o diagnóstico pra IA (ou plano B) e mostra o
    resultado na página resultado.html.
    """
    setor = request.form.get("setor", "comercio")
    modo = request.form.get("modo")  # "csv" ou "manual"

    meses_novos = []

    if modo == "csv":
        arquivo = request.files.get("arquivo_csv")
        if arquivo and arquivo.filename:
            os.makedirs(PASTA_UPLOADS, exist_ok=True)
            caminho = os.path.join(PASTA_UPLOADS, arquivo.filename)
            arquivo.save(caminho)
            meses_novos = carregar_csv(caminho)
    else:
        mes = {
            "mes": request.form.get("mes", "Mês"),
            "receita": float(request.form.get("receita") or 0),
            "custos": float(request.form.get("custos") or 0),
            "caixa": float(request.form.get("caixa") or 0),
            "divida": float(request.form.get("divida") or 0),
        }
        meses_novos = [mes]

    # Carrega o histórico já salvo, pra tendência funcionar mesmo entre
    # diferentes execuções do site (igual já fazia a versão de terminal).
    historico = carregar_historico()
    historico_indicadores = [calcular_indicadores(m) for m in historico]

    resultados = []
    for mes in meses_novos:
        indicadores = calcular_indicadores(mes)
        historico_indicadores.append(indicadores)

        resultado = diagnosticar(mes, indicadores, setor)
        resultado["mes"] = mes["mes"]
        resultado["indicadores"] = indicadores
        resultado["tendencia"] = analisar_tendencia(historico_indicadores)
        resultados.append(resultado)

        historico.append(mes)

    salvar_historico(historico)

    return render_template("resultado.html", resultados=resultados, setor=setor)


if __name__ == "__main__":
    app.run(debug=True)
