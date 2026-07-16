"""
ia_analise.py
-------------
Aqui mora a INTELIGÊNCIA ARTIFICIAL do projeto — 100% local, com
scikit-learn, sem nenhuma API externa (requisito da especificação).

Duas responsabilidades:

  1. classificar_mes()  -> usa o Random Forest treinado por treinar.py
     (salvo em modelos/classificador.joblib) para classificar o estado
     atual do negócio e dizer QUAIS indicadores mais pesaram (feature
     importance = "o que mais derruba a sua nota").

  2. prever_meses()     -> Regressão Linear sobre o próprio histórico do
     usuário para projetar receita e caixa dos próximos meses, recalcular
     os indicadores projetados e obter o SCORE FUTURO, com três cenários
     (pessimista / base / otimista) baseados no erro do modelo.

PLANO B: se o modelo ainda não foi treinado (modelos/ vazio), o app não
quebra — a classificação cai para o score por regras (score.py) e a tela
avisa. Mesma filosofia do checkpoint anterior: a apresentação nunca trava.
"""

import math
import os

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression

from analise import calcular_indicadores
from configuracao import carregar_config
from gerar_sintetico import proximo_mes
from score import calcular_score

ARQUIVO_MODELO = os.path.join("modelos", "classificador.joblib")

# ---------------------------------------------------------------------------
# Features do classificador (usadas AQUI e em treinar.py — definidas 1 vez)
# ---------------------------------------------------------------------------
# São os indicadores do mês + a variação de 3 meses de margem e caixa
# ("vetor de indicadores + variação dos últimos 3 meses", seção 4.1).
# Todas são razões/percentuais, então valem para negócios de qualquer
# tamanho — um MEI de R$ 3 mil/mês e um de R$ 6 mil/mês são comparáveis.
FEATURES = [
    "margem_liquida",
    "crescimento_receita",
    "runway_meses",
    "comprometimento_dividas",
    "uso_limite_mei",
    "inadimplencia",
    "concentracao_clientes",
    "compras_receita",
    "regularidade_das",
    "variacao_margem_3m",
    "variacao_runway_3m",
]

# Nome bonito de cada classe prevista pelo modelo (o rótulo interno é o
# "nivel" sem acento, que também é usado nas cores do CSS).
CLASSES_EXIBICAO = {
    "saudavel": {"classe": "Saudável", "emoji": "🟢"},
    "atencao": {"classe": "Atenção", "emoji": "🟡"},
    "alerta": {"classe": "Alerta", "emoji": "🟠"},
    "critico": {"classe": "Crítico", "emoji": "🔴"},
}

# Nomes amigáveis das features para mostrar no dashboard
NOMES_FEATURES = {
    "margem_liquida": "Margem líquida",
    "crescimento_receita": "Crescimento da receita",
    "runway_meses": "Fôlego de caixa",
    "comprometimento_dividas": "Comprometimento com dívidas",
    "uso_limite_mei": "Uso do limite MEI",
    "inadimplencia": "Inadimplência de clientes",
    "concentracao_clientes": "Concentração de clientes",
    "compras_receita": "Compras / receita",
    "regularidade_das": "Regularidade do DAS",
    "variacao_margem_3m": "Variação da margem (3 meses)",
    "variacao_runway_3m": "Variação do caixa (3 meses)",
}


def montar_linha_de_features(indicadores_por_mes, posicao):
    """
    Monta o vetor de features do mês na posição `posicao`, olhando o
    histórico de indicadores para calcular as variações de 3 meses.
    Valores que não existem ficam como None — o pipeline treinado tem um
    SimpleImputer que preenche com a mediana vista no treino.
    """
    atual = indicadores_por_mes[posicao]
    linha = {nome: atual.get(nome) for nome in FEATURES if nome in atual}

    # Variação de 3 meses = valor de hoje − valor de 3 meses atrás.
    # Mostra a DIREÇÃO do negócio, não só a foto do mês.
    if posicao >= 3:
        antigo = indicadores_por_mes[posicao - 3]
        for nome_base in ("margem_liquida", "runway_meses"):
            agora, antes = atual.get(nome_base), antigo.get(nome_base)
            valor = (agora - antes) if (agora is not None and antes is not None) else None
            linha[f"variacao_{'margem' if nome_base == 'margem_liquida' else 'runway'}_3m"] = valor
    else:
        linha["variacao_margem_3m"] = None
        linha["variacao_runway_3m"] = None

    return linha


# ---------------------------------------------------------------------------
# 1) Classificador do estado atual (Random Forest)
# ---------------------------------------------------------------------------

# O modelo é carregado do disco uma única vez e guardado aqui (cache)
_modelo_em_memoria = None


def carregar_modelo():
    """Carrega o pacote salvo por treinar.py, ou devolve None se não existe."""
    global _modelo_em_memoria
    if _modelo_em_memoria is None and os.path.exists(ARQUIVO_MODELO):
        _modelo_em_memoria = joblib.load(ARQUIVO_MODELO)
    return _modelo_em_memoria


def classificar_mes(indicadores_por_mes):
    """
    Classifica o mês MAIS RECENTE do histórico usando o Random Forest.

    Devolve um dicionário:
      {
        "nivel": "atencao", "classe": "Atenção", "emoji": "🟡",
        "probabilidades": [("Atenção", 0.72), ("Saudável", 0.18), ...],
        "importancias": [("Fôlego de caixa", 0.23), ...],  # top 5
        "fonte": "ml"  # ou "regra (plano B)" se o modelo não existe
      }
    """
    pacote = carregar_modelo()

    # PLANO B: sem modelo treinado, usamos a classe do score por regras.
    if pacote is None:
        resultado = calcular_score(indicadores_por_mes[-1])
        return {
            "nivel": resultado["nivel"],
            "classe": resultado["classe"],
            "emoji": resultado["emoji"],
            "probabilidades": None,
            "importancias": None,
            "fonte": "regra (plano B — rode 'python treinar.py' para ativar o modelo)",
        }

    linha = montar_linha_de_features(indicadores_por_mes, len(indicadores_por_mes) - 1)
    # DataFrame de 1 linha com as colunas na MESMA ordem do treino
    entrada = pd.DataFrame([linha])[pacote["features"]]

    pipeline = pacote["pipeline"]
    nivel_previsto = pipeline.predict(entrada)[0]

    # predict_proba dá a "confiança" do modelo em cada classe
    probabilidades = sorted(
        zip(pipeline.classes_, pipeline.predict_proba(entrada)[0]),
        key=lambda par: par[1],
        reverse=True,
    )

    return {
        "nivel": nivel_previsto,
        "classe": CLASSES_EXIBICAO[nivel_previsto]["classe"],
        "emoji": CLASSES_EXIBICAO[nivel_previsto]["emoji"],
        "probabilidades": [
            (CLASSES_EXIBICAO[nivel]["classe"], float(prob)) for nivel, prob in probabilidades
        ],
        "importancias": [
            (NOMES_FEATURES.get(nome, nome), peso)
            for nome, peso in pacote["importancias"][:5]
        ],
        "fonte": "ml",
    }


# ---------------------------------------------------------------------------
# 2) Previsão dos próximos meses ("vai piorar?")
# ---------------------------------------------------------------------------

def _prever_serie(valores, horizonte):
    """
    Projeta uma série numérica (receita ou caixa) `horizonte` meses à
    frente e devolve (previsões, erro_padrao, descricao).

    O modelo é uma REGRESSÃO LINEAR DE TENDÊNCIA: ajustamos a reta
    "valor = a × tempo + b" ao histórico e prolongamos essa reta para os
    meses futuros. É o modelo mais simples possível de explicar — e
    estável: testamos a alternativa de regressão sobre lags (prevendo o
    mês seguinte a partir dos 3 anteriores, de forma recursiva) e ela
    amplia demais qualquer aceleração recente, projetando crescimentos
    irreais; a reta de tendência é mais honesta com pouco histórico.

    O erro padrão é o RMSE dos resíduos (a distância típica entre a reta
    e os pontos reais) — é ele que abre a faixa entre os cenários
    pessimista e otimista.
    """
    quantidade = len(valores)

    # X = número do mês (0, 1, 2, ...); y = valor observado nesse mês
    X = [[t] for t in range(quantidade)]
    modelo = LinearRegression()
    modelo.fit(X, valores)

    # Resíduo = valor real − valor na reta; RMSE = "erro típico" do modelo
    residuos = np.array(valores) - modelo.predict(X)
    erro_padrao = float(np.sqrt(np.mean(residuos ** 2)))

    # Prolonga a reta para os próximos meses (nunca abaixo de zero:
    # receita e caixa negativos não fazem sentido aqui)
    previsoes = [
        max(0.0, float(modelo.predict([[quantidade + passo]])[0]))
        for passo in range(horizonte)
    ]

    return previsoes, erro_padrao, "regressão linear de tendência (reta valor × tempo)"


def prever_meses(lancamentos, perfil=None):
    """
    Função principal da previsão. Recebe o histórico real do usuário e
    devolve as projeções de receita, caixa e SCORE para os próximos meses,
    nos três cenários. Exige o mínimo de meses definido no config.yaml
    (4); com menos, devolve {"disponivel": False, "motivo": ...}.

    Como o score futuro é calculado: para cada mês projetado montamos um
    "lançamento fictício" (receita e caixa previstos; os demais campos
    repetem a média dos últimos 3 meses reais), juntamos ao histórico e
    recalculamos os indicadores e o score — exatamente as mesmas funções
    usadas nos meses reais.
    """
    config = carregar_config()["previsao"]
    horizonte = config["meses_a_frente"]
    minimo = config["minimo_meses"]

    if len(lancamentos) < minimo:
        return {
            "disponivel": False,
            "motivo": (
                f"Dados insuficientes para previsão: são necessários pelo menos "
                f"{minimo} meses lançados (você tem {len(lancamentos)})."
            ),
        }

    receitas = [item["receita_total"] for item in lancamentos]
    caixas = [item["saldo_caixa_final"] for item in lancamentos]

    previsao_receita, erro_receita, descricao_modelo = _prever_serie(receitas, horizonte)
    previsao_caixa, erro_caixa, _ = _prever_serie(caixas, horizonte)

    # Meses futuros no formato AAAA-MM, a partir do último mês real
    meses_futuros = []
    mes = lancamentos[-1]["mes"]
    for _ in range(horizonte):
        mes = proximo_mes(mes)
        meses_futuros.append(mes)

    # Média dos últimos 3 meses para os campos que NÃO estamos prevendo
    # (despesas, parcelas etc.) — ignorando os que estão em branco (None)
    def media_3_meses(campo):
        valores = [item.get(campo) for item in lancamentos[-3:] if item.get(campo) is not None]
        return sum(valores) / len(valores) if valores else None

    campos_repetidos = {
        campo: media_3_meses(campo)
        for campo in ["despesas_fixas", "despesas_variaveis", "compras_mercadorias",
                      "parcelas_dividas_mes", "divida_total", "num_vendas",
                      "num_clientes", "recebiveis_atrasados", "receita_maior_cliente"]
    }

    # Monta os três cenários: pessimista = base − erro, otimista = base + erro.
    # O erro cresce com a raiz da distância (sqrt), porque quanto mais longe
    # no futuro, mais incerta é a previsão.
    resultado = {
        "disponivel": True,
        "meses": meses_futuros,
        "receita": {}, "caixa": {}, "score": {},
        "erro_receita": erro_receita,
        "erro_caixa": erro_caixa,
        "modelo": descricao_modelo,
    }

    indicadores_reais = calcular_indicadores(lancamentos, perfil)
    score_atual = calcular_score(indicadores_reais[-1])["score"]
    resultado["score_atual"] = score_atual

    for nome_cenario, sinal in [("pessimista", -1), ("base", 0), ("otimista", +1)]:
        receitas_cenario = []
        caixas_cenario = []
        for passo in range(horizonte):
            abertura = math.sqrt(passo + 1)
            receitas_cenario.append(max(0.0, previsao_receita[passo] + sinal * erro_receita * abertura))
            caixas_cenario.append(max(0.0, previsao_caixa[passo] + sinal * erro_caixa * abertura))

        # Histórico estendido = meses reais + meses fictícios do cenário
        historico_estendido = list(lancamentos)
        for passo in range(horizonte):
            mes_ficticio = dict(campos_repetidos)
            mes_ficticio["mes"] = meses_futuros[passo]
            mes_ficticio["receita_total"] = receitas_cenario[passo]
            mes_ficticio["saldo_caixa_final"] = caixas_cenario[passo]
            mes_ficticio["das_pago_em_dia"] = 1  # supomos DAS em dia no futuro
            historico_estendido.append(mes_ficticio)

        indicadores_estendidos = calcular_indicadores(historico_estendido, perfil)
        scores_futuros = [
            calcular_score(indicadores_estendidos[len(lancamentos) + passo])["score"]
            for passo in range(horizonte)
        ]

        resultado["receita"][nome_cenario] = [round(v, 2) for v in receitas_cenario]
        resultado["caixa"][nome_cenario] = [round(v, 2) for v in caixas_cenario]
        resultado["score"][nome_cenario] = scores_futuros

    # Quantos pontos o score pode cair no cenário base (alimenta o alerta 7)
    resultado["queda_score"] = max(0.0, score_atual - min(resultado["score"]["base"]))

    return resultado
