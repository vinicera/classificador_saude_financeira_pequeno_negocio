"""
alertas.py
----------
As regras de ALERTA da especificação (seção 3.5). São "if"s de negócio,
avaliados sobre o mês mais recente: cada regra que dispara vira um
cartão no dashboard com um conselho prático.

Os gatilhos numéricos (80% do limite, 2 meses de caixa, etc.) vêm do
config.yaml para poderem ser ajustados sem mexer aqui.
"""

from configuracao import carregar_config


def gerar_alertas(lancamentos, indicadores_por_mes, queda_score_prevista=None):
    """
    Avalia as 7 regras da especificação e devolve a lista de alertas ativos.

    Recebe:
      - lancamentos: lista de meses em ordem cronológica (de dados.py)
      - indicadores_por_mes: saída de analise.calcular_indicadores
      - queda_score_prevista: quantos pontos o modelo prevê que o score
        vai cair (None quando ainda não há previsão disponível)

    Devolve: lista de dicionários {"titulo", "mensagem", "nivel"},
    onde nivel é "critico" (vermelho) ou "atencao" (amarelo) — usado
    só para colorir o cartão na tela.
    """
    if not lancamentos:
        return []

    gatilhos = carregar_config()["alertas"]
    mes_atual = lancamentos[-1]
    indicadores = indicadores_por_mes[-1]
    alertas = []

    # 1) Uso do limite MEI >= 80% -> risco de desenquadramento
    uso_limite = indicadores["uso_limite_mei"]
    if uso_limite is not None and uso_limite >= gatilhos["uso_limite_maximo"]:
        alertas.append({
            "titulo": "Risco de desenquadramento do MEI",
            "mensagem": (
                f"Você já usou {uso_limite:.0%} do limite anual de faturamento. "
                "Planeje o faturamento dos próximos meses: passando de 100% há DAS "
                "complementar, e acima de 120% o desenquadramento é retroativo."
            ),
            "nivel": "critico",
        })

    # 2) Fôlego de caixa < 2 meses -> caixa crítico
    runway = indicadores["runway_meses"]
    if runway is not None and runway < gatilhos["runway_minimo"]:
        alertas.append({
            "titulo": "Caixa crítico",
            "mensagem": (
                f"Seu caixa cobre só {runway:.1f} mês(es) de despesas. "
                "Reduza despesas fixas e tente antecipar recebíveis."
            ),
            "nivel": "critico",
        })

    # 3) Margem negativa no mês -> prejuízo
    margem = indicadores["margem_liquida"]
    if margem is not None and margem < 0:
        alertas.append({
            "titulo": "Mês com prejuízo",
            "mensagem": (
                f"A margem do mês ficou em {margem:.1%}: as despesas superaram a receita. "
                "Revise a precificação e os custos variáveis."
            ),
            "nivel": "critico",
        })

    # 4) Receita caindo há 3 meses seguidos -> tendência de queda
    # (comparamos mês a mês: precisa de pelo menos 4 meses para ver 3 quedas)
    receitas = [item["receita_total"] for item in lancamentos]
    quedas_necessarias = gatilhos["meses_queda_receita"]
    if len(receitas) > quedas_necessarias:
        ultimas_variacoes = [
            receitas[i] - receitas[i - 1]
            for i in range(len(receitas) - quedas_necessarias, len(receitas))
        ]
        if all(variacao < 0 for variacao in ultimas_variacoes):
            alertas.append({
                "titulo": "Receita em queda contínua",
                "mensagem": (
                    f"A receita caiu por {quedas_necessarias} meses seguidos. "
                    "Vale investir em ações de venda e divulgação."
                ),
                "nivel": "atencao",
            })

    # 5) DAS do mês em atraso -> regularizar já
    if mes_atual["das_pago_em_dia"] == 0:
        alertas.append({
            "titulo": "DAS em atraso",
            "mensagem": (
                "Regularize o DAS o quanto antes: o atraso gera multa de 0,33% ao dia "
                "mais juros, e 12 meses seguidos em débito podem excluir o MEI do regime."
            ),
            "nivel": "critico",
        })

    # 6) Compras > 80% da receita -> atenção fiscal
    compras = indicadores["compras_receita"]
    if compras is not None and compras > gatilhos["compras_receita_maximo"]:
        alertas.append({
            "titulo": "Compras muito altas em relação à receita",
            "mensagem": (
                f"As compras de mercadorias somam {compras:.0%} da receita (acima de 80% "
                "levanta suspeita fiscal). Documente as notas e revise o estoque."
            ),
            "nivel": "atencao",
        })

    # 7) Modelo prevê queda do score >= 15 pontos -> piora à vista
    if (queda_score_prevista is not None
            and queda_score_prevista >= gatilhos["queda_score_previsao"]):
        alertas.append({
            "titulo": "O modelo projeta piora nos próximos meses",
            "mensagem": (
                f"A previsão indica queda de cerca de {queda_score_prevista:.0f} pontos "
                "no score. Veja na tela Previsão quais indicadores mais pesam."
            ),
            "nivel": "atencao",
        })

    return alertas
