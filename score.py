"""
score.py
--------
Transforma os indicadores de um mês (calculados em analise.py) no
SCORE DE SAÚDE (0 a 100) e na classe do semáforo:

    🟢 Saudável (>= 75) · 🟡 Atenção (50–74) · 🟠 Alerta (25–49) · 🔴 Crítico (< 25)

Como funciona (seção 3.4 da especificação):
  1. Cada indicador vira uma NOTA de 0 a 100 por interpolação linear,
     usando as faixas "pessimo"/"otimo" do config.yaml.
  2. O score é a MÉDIA PONDERADA das notas, com os pesos do config.yaml.
  3. Indicador sem dado (None) fica de fora e o peso dele é
     redistribuído entre os que existem.

Este score por regras também é usado para ROTULAR o dataset sintético
que treina o modelo de machine learning (é a "resposta certa" que o
modelo aprende a imitar) — ver gerar_sintetico.py.
"""

from configuracao import carregar_config


def normalizar_indicador(valor, faixa):
    """
    Converte o valor de um indicador em uma nota de 0 a 100.

    Regra de três entre os limites da faixa:
        valor == faixa["pessimo"] -> nota 0
        valor == faixa["otimo"]   -> nota 100
        no meio                   -> proporcional
    Valores fora da faixa são "presos" em 0 ou 100 (não existe nota 130).

    A mesma fórmula funciona quando "menor é melhor" (ex.: dívidas),
    porque nesse caso o config define pessimo=0.50 e otimo=0.0 — a
    interpolação simplesmente anda no sentido contrário.
    """
    pessimo = faixa["pessimo"]
    otimo = faixa["otimo"]

    # Posição do valor entre o pior (0.0) e o melhor (1.0) cenário
    posicao = (valor - pessimo) / (otimo - pessimo)

    # Prende entre 0 e 1, depois converte para a escala 0–100
    posicao = max(0.0, min(1.0, posicao))
    return posicao * 100


def calcular_score(indicadores_do_mes):
    """
    Recebe o dicionário de indicadores de UM mês (saída de
    analise.calcular_indicadores) e devolve:

        {
          "score": 62.4,             # nota final 0–100
          "classe": "Atenção",       # nome da classe
          "nivel": "atencao",        # versão sem acento (útil pro CSS)
          "emoji": "🟡",
          "notas": {"margem_liquida": 80.0, ...}  # nota de cada indicador
        }

    Só entram no score os 8 indicadores que têm peso no config.yaml
    (ticket médio e compras/receita são informativos e geram alertas,
    mas não pontuam). Indicadores None são pulados e o peso deles é
    redistribuído — por isso dividimos pela soma dos pesos USADOS.
    """
    config = carregar_config()
    pesos = config["pesos"]
    faixas = config["faixas"]

    soma_ponderada = 0.0
    soma_dos_pesos_usados = 0.0
    notas = {}

    for nome_indicador, peso in pesos.items():
        valor = indicadores_do_mes.get(nome_indicador)
        if valor is None:
            continue  # sem dado -> fica fora da média (peso redistribuído)

        nota = normalizar_indicador(valor, faixas[nome_indicador])
        notas[nome_indicador] = nota
        soma_ponderada += nota * peso
        soma_dos_pesos_usados += peso

    # Caso extremo: nenhum indicador calculável (não deve acontecer com os
    # campos obrigatórios preenchidos, mas protege contra divisão por zero)
    if soma_dos_pesos_usados == 0:
        score = 0.0
    else:
        score = soma_ponderada / soma_dos_pesos_usados

    resultado = {"score": round(score, 1), "notas": notas}
    resultado.update(classificar(score))
    return resultado


def classificar(score):
    """
    Aplica os cortes do semáforo (config.yaml, seção "classes") sobre um
    score 0–100 e devolve nome, nível (para CSS) e emoji da classe.
    """
    cortes = carregar_config()["classes"]

    if score >= cortes["saudavel"]:
        return {"classe": "Saudável", "nivel": "saudavel", "emoji": "🟢"}
    if score >= cortes["atencao"]:
        return {"classe": "Atenção", "nivel": "atencao", "emoji": "🟡"}
    if score >= cortes["alerta"]:
        return {"classe": "Alerta", "nivel": "alerta", "emoji": "🟠"}
    return {"classe": "Crítico", "nivel": "critico", "emoji": "🔴"}
