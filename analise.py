"""
analise.py
----------
Aqui fica o cálculo dos indicadores financeiros (margem, peso do custo,
liquidez, endividamento) — isso é matemática pura, sem IA, e é a base que
alimenta tanto a IA quanto o plano B.

A classificação "de verdade" (saudável/atenção/risco) é feita pela IA, em
ia_analise.py, que recebe estes indicadores já calculados e analisa o mês.

Este arquivo também guarda `classificar_saude_regra`, que é só o PLANO B:
uma classificação por regras simples (if/else comparando com valores de
referência do setor), usada apenas se a API de IA não estiver disponível.
Não treinamos nenhum modelo de machine learning neste projeto.
"""

# Valores de referência por setor (números de exemplo, ajustáveis).
# margem_min: lucro mínimo saudável sobre a receita
# peso_custo_max: quanto dos custos pode "comer" da receita
# liquidez_min: quantos meses de custo o caixa consegue cobrir
# endividamento_max: dívida em relação à receita
BENCHMARKS = {
    "comercio": {
        "margem_min": 0.10,
        "peso_custo_max": 0.70,
        "liquidez_min": 1.0,
        "endividamento_max": 0.40,
    },
    "servicos": {
        "margem_min": 0.15,
        "peso_custo_max": 0.60,
        "liquidez_min": 1.2,
        "endividamento_max": 0.35,
    },
    "industria": {
        "margem_min": 0.08,
        "peso_custo_max": 0.75,
        "liquidez_min": 0.8,
        "endividamento_max": 0.50,
    },
}


def calcular_indicadores(mes):
    """
    Recebe um dicionário de um mês (receita, custos, caixa, divida)
    e devolve um dicionário com os 4 indicadores calculados.
    """
    receita = mes["receita"]

    # Proteção simples contra divisão por zero (receita = 0)
    if receita == 0:
        return {"margem": 0, "peso_custo": 0, "liquidez": 0, "endividamento": 0}

    margem = (receita - mes["custos"]) / receita
    peso_custo = mes["custos"] / receita
    endividamento = mes["divida"] / receita

    # liquidez: quantos meses de custo o caixa atual cobre.
    # Se não há custo nenhum, consideramos liquidez "alta" (999).
    liquidez = mes["caixa"] / mes["custos"] if mes["custos"] > 0 else 999

    return {
        "margem": margem,
        "peso_custo": peso_custo,
        "liquidez": liquidez,
        "endividamento": endividamento,
    }


def classificar_saude_regra(indicadores, setor):
    """
    PLANO B (reserva): compara os indicadores com o benchmark do setor e
    decide "saudável", "atenção" ou "risco" usando regras simples.

    A classificação "de verdade" do projeto é feita pela IA (ver
    ia_analise.py), que recebe estes mesmos indicadores e analisa o mês.
    Esta função só entra em ação se a API de IA não estiver disponível
    (sem internet, sem chave configurada, etc.), pra o programa não travar.

    Regra usada (simples de explicar):
      - conta quantos indicadores estão FORA da faixa saudável
      - 0 fora  -> saudável
      - 1 fora  -> atenção
      - 2+ fora -> risco
    """
    referencia = BENCHMARKS.get(setor, BENCHMARKS["comercio"])

    problemas = {}  # guarda, pra cada indicador ruim, o quanto ele passou do limite

    if indicadores["margem"] < referencia["margem_min"]:
        problemas["margem"] = referencia["margem_min"] - indicadores["margem"]

    if indicadores["peso_custo"] > referencia["peso_custo_max"]:
        problemas["peso_custo"] = indicadores["peso_custo"] - referencia["peso_custo_max"]

    if indicadores["liquidez"] < referencia["liquidez_min"]:
        problemas["liquidez"] = referencia["liquidez_min"] - indicadores["liquidez"]

    if indicadores["endividamento"] > referencia["endividamento_max"]:
        problemas["endividamento"] = indicadores["endividamento"] - referencia["endividamento_max"]

    quantidade_problemas = len(problemas)

    if quantidade_problemas == 0:
        classificacao = "saudável"
    elif quantidade_problemas == 1:
        classificacao = "atenção"
    else:
        classificacao = "risco"

    # O fator crítico é o indicador problemático com o maior desvio.
    if problemas:
        fator_critico = max(problemas, key=problemas.get)
    else:
        fator_critico = None

    return classificacao, fator_critico


def analisar_tendencia(historico_indicadores):
    """
    DIFERENCIAL simples (regra dos 2 meses), sem IA:
    compara a margem do último mês com a do mês anterior
    e diz se a tendência é de melhora, piora ou estabilidade.

    Só funciona se houver pelo menos 2 meses no histórico.
    """
    if len(historico_indicadores) < 2:
        return "Dados insuficientes para prever tendência (é preciso 2+ meses)."

    margem_anterior = historico_indicadores[-2]["margem"]
    margem_atual = historico_indicadores[-1]["margem"]
    diferenca = margem_atual - margem_anterior

    if diferenca > 0.01:
        return "Tendência de melhora: a margem está subindo."
    elif diferenca < -0.01:
        return "Tendência de piora: a margem está caindo."
    else:
        return "Tendência estável: a margem não mudou muito."
