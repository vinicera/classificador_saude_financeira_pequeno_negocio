"""
analise.py
----------
Cálculo dos 10 INDICADORES (KPIs) da especificação, seção 3.3.
Isso aqui é matemática pura (razões e médias) — sem IA nenhuma.
Os indicadores calculados alimentam:
  - o score por regras (score.py),
  - os alertas (alertas.py),
  - e o modelo de machine learning (ia_analise.py).

Convenção importante deste módulo:
  Quando um indicador NÃO pode ser calculado (dado opcional não preenchido
  ou divisão por zero sem sentido), devolvemos None — e quem usa decide o
  que fazer (o score, por exemplo, redistribui o peso desse indicador).
"""

from configuracao import carregar_config

# ---------------------------------------------------------------------------
# Ficha de cada indicador: nome, fórmula, referência saudável e por que
# importa. Usada pelas telas (expander "como calculamos?"), pela página
# Metodologia e pelo relatório PDF — definida UMA vez, aqui, junto do cálculo.
# "formato" diz como exibir o número: pct (%), meses, reais (R$) ou vezes.
# ---------------------------------------------------------------------------
INFO_INDICADORES = [
    {"chave": "margem_liquida", "nome": "Margem líquida", "formato": "pct",
     "referencia": "≥ 15%",
     "formula": "(receita − despesas totais) ÷ receita",
     "porque": "Mostra quanto de cada R$ 1,00 vendido vira lucro. Margem negativa = prejuízo."},
    {"chave": "crescimento_receita", "nome": "Crescimento da receita", "formato": "pct",
     "referencia": "≥ 0%",
     "formula": "variação da média móvel de 3 meses da receita",
     "porque": "Usa a média de 3 meses para não confundir um pico isolado com crescimento real."},
    {"chave": "runway_meses", "nome": "Fôlego de caixa (runway)", "formato": "meses",
     "referencia": "≥ 3 meses",
     "formula": "saldo de caixa ÷ despesa média mensal (últimos 3 meses)",
     "porque": "Se a receita zerar hoje, por quantos meses o caixa paga as contas?"},
    {"chave": "comprometimento_dividas", "nome": "Comprometimento com dívidas", "formato": "pct",
     "referencia": "≤ 20%",
     "formula": "parcelas de dívidas do mês ÷ receita",
     "porque": "Parcelas altas 'comem' o lucro antes de ele chegar ao dono."},
    {"chave": "uso_limite_mei", "nome": "Uso do limite MEI", "formato": "pct",
     "referencia": "≤ 80%",
     "formula": "receita acumulada no ano ÷ limite anual (proporcional no ano de abertura)",
     "porque": "Estourar o limite de faturamento desenquadra o MEI — com impostos retroativos no pior caso."},
    {"chave": "inadimplencia", "nome": "Inadimplência de clientes", "formato": "pct",
     "referencia": "≤ 5%",
     "formula": "recebíveis atrasados (fiado) ÷ receita",
     "porque": "Fiado atrasado é venda que virou risco: o dinheiro pode nunca entrar."},
    {"chave": "concentracao_clientes", "nome": "Concentração de clientes", "formato": "pct",
     "referencia": "≤ 40%",
     "formula": "receita do maior cliente ÷ receita",
     "porque": "Depender demais de um cliente é frágil: se ele sair, a receita despenca."},
    {"chave": "compras_receita", "nome": "Compras ÷ receita", "formato": "pct",
     "referencia": "≤ 80%",
     "formula": "compras de mercadorias ÷ receita bruta",
     "porque": "Compras acima de 80% da receita levantam suspeita fiscal (regra dos 80%)."},
    {"chave": "ticket_medio", "nome": "Ticket médio", "formato": "reais",
     "referencia": "estável ou subindo",
     "formula": "receita ÷ nº de vendas",
     "porque": "Quanto cada venda rende, em média. Queda constante sugere desconto demais ou mix pior."},
    {"chave": "regularidade_das", "nome": "Regularidade do DAS", "formato": "pct",
     "referencia": "100%",
     "formula": "meses com DAS pago em dia ÷ meses lançados",
     "porque": "Atraso gera multa diária; 12 meses em débito podem excluir o MEI do regime."},
]


def dividir(numerador, denominador):
    """
    Divisão "segura": devolve numerador/denominador, ou None quando algum
    dos dois está faltando (None) ou o denominador é zero.
    Quase todos os indicadores são uma razão, então esse ajudante evita
    repetir o mesmo if em dez lugares.
    """
    if numerador is None or denominador is None or denominador == 0:
        return None
    return numerador / denominador


def despesas_totais(lancamento):
    """Despesas do mês = despesas fixas + despesas variáveis."""
    return lancamento["despesas_fixas"] + lancamento["despesas_variaveis"]


def calcular_margem_liquida(lancamento):
    """
    Margem líquida = (receita − despesas totais) / receita.
    Mostra quanto de cada R$ 1,00 vendido vira lucro. Referência: ≥ 15%.
    """
    receita = lancamento["receita_total"]
    return dividir(receita - despesas_totais(lancamento), receita)


def calcular_crescimento_receita(receitas_ate_o_mes):
    """
    Crescimento da receita = variação da MÉDIA MÓVEL de 3 meses.
    Comparamos a média dos 3 últimos meses com a média dos 3 meses
    anteriores a ela. Usar média móvel (e não o mês isolado) suaviza
    picos: um mês bom não vira "crescimento" sozinho.

    Recebe a lista de receitas em ordem cronológica ATÉ o mês analisado.
    Precisa de pelo menos 4 meses (3 para a média atual + 1 deslocado).
    """
    if len(receitas_ate_o_mes) < 4:
        return None
    media_atual = sum(receitas_ate_o_mes[-3:]) / 3
    media_anterior = sum(receitas_ate_o_mes[-4:-1]) / 3
    return dividir(media_atual - media_anterior, media_anterior)


def calcular_runway(lancamento, despesa_media_mensal):
    """
    Fôlego de caixa (runway) = saldo de caixa / despesa média mensal.
    Responde: "se a receita zerar hoje, quantos meses eu aguento pagar
    as contas?". Referência: ≥ 3 meses.

    Se a despesa média é zero (negócio sem custo registrado), o fôlego é
    "infinito" na prática — devolvemos 99 para não dividir por zero.
    """
    if despesa_media_mensal == 0:
        return 99.0
    return lancamento["saldo_caixa_final"] / despesa_media_mensal


def calcular_uso_limite_mei(lancamentos_ate_o_mes, perfil):
    """
    Uso do limite MEI = receita acumulada no ano / limite anual.
    Referência: ≤ 80% (a partir de 80% acende o alerta de desenquadramento).

    Detalhe da regra: no ANO DE ABERTURA o limite é proporcional:
        (limite anual ÷ 12) × meses ativos até dezembro.
    O limite anual vem do config.yaml (hoje R$ 81.000, parametrizado
    porque há proposta de aumento em tramitação).
    """
    config = carregar_config()
    limite_anual = config["mei"]["limite_anual"]

    # Ano do mês analisado (formato "AAAA-MM" -> pegamos os 4 primeiros caracteres)
    ano_atual = lancamentos_ate_o_mes[-1]["mes"][:4]

    # Soma a receita de todos os meses lançados DESTE ano
    receita_no_ano = sum(
        item["receita_total"]
        for item in lancamentos_ate_o_mes
        if item["mes"][:4] == ano_atual
    )

    # Limite proporcional se o negócio abriu neste mesmo ano
    limite = limite_anual
    if perfil and perfil.get("data_abertura", "")[:4] == ano_atual:
        mes_abertura = int(perfil["data_abertura"][5:7])
        meses_ativos = 12 - mes_abertura + 1  # da abertura até dezembro
        limite = (limite_anual / 12) * meses_ativos

    return dividir(receita_no_ano, limite)


def calcular_regularidade_das(lancamentos_ate_o_mes):
    """
    Regularidade do DAS = meses com DAS pago em dia / meses lançados.
    Referência: 100%. O DAS vence todo dia 20; atraso gera multa de
    0,33%/dia e 12 meses seguidos em débito podem excluir o MEI do regime.
    """
    pagos_em_dia = sum(1 for item in lancamentos_ate_o_mes if item["das_pago_em_dia"] == 1)
    return pagos_em_dia / len(lancamentos_ate_o_mes)


def calcular_indicadores(lancamentos, perfil=None):
    """
    Função principal do módulo: recebe TODOS os lançamentos em ordem
    cronológica (lista de dicionários, como vem de dados.py) e devolve
    uma lista com os 10 indicadores de CADA mês.

    Vários indicadores dependem do histórico (média móvel, acumulado no
    ano, regularidade do DAS), por isso percorremos os meses do primeiro
    ao último, sempre olhando "do início até o mês atual".
    """
    resultado = []

    for posicao, lancamento in enumerate(lancamentos):
        # Fatia do histórico do primeiro mês até o mês atual (inclusive)
        historico = lancamentos[: posicao + 1]
        receitas = [item["receita_total"] for item in historico]

        # Despesa média dos últimos 3 meses (ou menos, se o histórico é curto).
        # É a base do runway: representa o "custo de manter as portas abertas".
        ultimos_3 = historico[-3:]
        despesa_media = sum(despesas_totais(item) for item in ultimos_3) / len(ultimos_3)

        receita = lancamento["receita_total"]

        indicadores = {
            "mes": lancamento["mes"],
            "margem_liquida": calcular_margem_liquida(lancamento),
            "crescimento_receita": calcular_crescimento_receita(receitas),
            "runway_meses": calcular_runway(lancamento, despesa_media),
            # Comprometimento com dívidas = parcelas do mês / receita (≤ 20%)
            "comprometimento_dividas": dividir(lancamento.get("parcelas_dividas_mes"), receita),
            "uso_limite_mei": calcular_uso_limite_mei(historico, perfil),
            # Inadimplência de clientes = fiado atrasado / receita (≤ 5%)
            "inadimplencia": dividir(lancamento.get("recebiveis_atrasados"), receita),
            # Concentração de clientes = receita do maior cliente / receita (≤ 40%)
            "concentracao_clientes": dividir(lancamento.get("receita_maior_cliente"), receita),
            # Compras / receita (≤ 80% — acima disso levanta suspeita fiscal)
            "compras_receita": dividir(lancamento.get("compras_mercadorias"), receita),
            # Ticket médio = receita / nº de vendas (acompanhamos a tendência)
            "ticket_medio": dividir(receita, lancamento.get("num_vendas")),
            "regularidade_das": calcular_regularidade_das(historico),
        }
        resultado.append(indicadores)

    return resultado
