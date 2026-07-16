"""
gerar_sintetico.py
------------------
Gera o DATASET SINTÉTICO que treina o modelo de machine learning
(seção 4.3 da especificação) e alimenta o modo demo do app.

Por que dados sintéticos? Não existem dados financeiros reais de MEIs
disponíveis publicamente. A saída é simular negócios plausíveis a partir
de 6 ARQUÉTIPOS (perfis típicos) + ruído aleatório, e rotular cada mês
com o score por regras (score.py) — que funciona como a "resposta certa"
que o modelo vai aprender a reconhecer.

Como usar:
    python gerar_sintetico.py
Cria o arquivo data/dataset_sintetico.csv com N negócios × 24 meses.
"""

import csv
import math
import os
import random

# ---------------------------------------------------------------------------
# Os 6 arquétipos de negócio (seção 4.3)
# ---------------------------------------------------------------------------
# Cada parâmetro descreve o "jeitão" do negócio; o gerador soma ruído
# aleatório em cima para nenhum negócio ficar igual ao outro.
#   crescimento      -> variação média da receita por mês (0.03 = +3%/mês)
#   fracao_despesas  -> quanto da receita vai embora em despesas (0.95 = margem ~5%)
#   sazonalidade     -> amplitude da onda ao longo do ano (0.35 = ±35%)
#   caixa_inicial    -> caixa inicial medido em "meses de despesa"
#   divida_inicial   -> dívida inicial medida em "meses de receita"
#   prob_das_em_dia  -> chance de pagar o DAS em dia num mês qualquer
#   inadimplencia    -> fração da receita presa em fiado atrasado
#   concentracao     -> fração da receita vinda do maior cliente
ARQUETIPOS = {
    "saudavel_estavel": {
        "crescimento": 0.003, "fracao_despesas": 0.70, "sazonalidade": 0.05,
        "caixa_inicial": 4.0, "divida_inicial": 0.5, "prob_das_em_dia": 0.98,
        "inadimplencia": 0.02, "concentracao": 0.20,
    },
    "em_crescimento": {
        "crescimento": 0.030, "fracao_despesas": 0.78, "sazonalidade": 0.08,
        "caixa_inicial": 3.0, "divida_inicial": 0.8, "prob_das_em_dia": 0.95,
        "inadimplencia": 0.03, "concentracao": 0.30,
    },
    "sazonal": {
        "crescimento": 0.002, "fracao_despesas": 0.80, "sazonalidade": 0.35,
        "caixa_inicial": 2.5, "divida_inicial": 0.7, "prob_das_em_dia": 0.92,
        "inadimplencia": 0.04, "concentracao": 0.25,
    },
    "endividado": {
        "crescimento": 0.000, "fracao_despesas": 0.95, "sazonalidade": 0.10,
        "caixa_inicial": 1.0, "divida_inicial": 4.5, "prob_das_em_dia": 0.65,
        "inadimplencia": 0.10, "concentracao": 0.50,
    },
    "em_declinio": {
        "crescimento": -0.035, "fracao_despesas": 0.92, "sazonalidade": 0.08,
        "caixa_inicial": 1.5, "divida_inicial": 2.5, "prob_das_em_dia": 0.75,
        "inadimplencia": 0.09, "concentracao": 0.50,
    },
    "critico": {
        "crescimento": -0.050, "fracao_despesas": 1.20, "sazonalidade": 0.10,
        "caixa_inicial": 0.3, "divida_inicial": 6.0, "prob_das_em_dia": 0.30,
        "inadimplencia": 0.20, "concentracao": 0.70,
    },
}

MESES_POR_NEGOCIO = 24
NEGOCIOS_POR_ARQUETIPO = 60
ARQUIVO_SAIDA = os.path.join("data", "dataset_sintetico.csv")


def proximo_mes(mes):
    """Recebe "2025-12" e devolve "2026-01" (aritmética simples de AAAA-MM)."""
    ano, numero_mes = int(mes[:4]), int(mes[5:7])
    numero_mes += 1
    if numero_mes > 12:
        ano, numero_mes = ano + 1, 1
    return f"{ano:04d}-{numero_mes:02d}"


def gerar_negocio(nome_arquetipo, sorteio, mes_inicial="2024-01", num_meses=MESES_POR_NEGOCIO):
    """
    Simula UM negócio por `num_meses` meses e devolve a lista de
    lançamentos (mesmos 13 campos que o usuário preencheria no app).

    `sorteio` é um random.Random com semente fixa, para o dataset ser
    reprodutível (rodar de novo gera exatamente os mesmos dados).
    """
    parametros = ARQUETIPOS[nome_arquetipo]

    # Cada negócio nasce com um tamanho diferente (receita típica mensal)
    receita_base = sorteio.uniform(3000, 6500)
    ticket_medio_tipico = sorteio.uniform(25, 120)  # R$ por venda

    despesa_tipica = receita_base * parametros["fracao_despesas"]
    caixa = despesa_tipica * parametros["caixa_inicial"]
    divida = receita_base * parametros["divida_inicial"]

    lancamentos = []
    mes = mes_inicial

    for indice_mes in range(num_meses):
        # Receita = base × crescimento acumulado × onda sazonal × ruído
        fator_crescimento = (1 + parametros["crescimento"]) ** indice_mes
        onda_sazonal = 1 + parametros["sazonalidade"] * math.sin(2 * math.pi * (indice_mes % 12) / 12)
        ruido = sorteio.uniform(0.92, 1.08)
        receita = max(300.0, receita_base * fator_crescimento * onda_sazonal * ruido)

        # Despesas: fixas mudam pouco; variáveis acompanham a receita
        despesas_fixas = despesa_tipica * 0.45 * sorteio.uniform(0.95, 1.05)
        despesas_variaveis = receita * parametros["fracao_despesas"] * 0.55 * sorteio.uniform(0.92, 1.08)
        despesas = despesas_fixas + despesas_variaveis

        # Dívida: paga-se ~5% ao mês; o negócio "endividado" contrai mais
        parcelas = divida * 0.05
        divida = max(0.0, divida - parcelas * 0.6)  # parte da parcela é juros
        chance_novo_emprestimo = 0.40 if nome_arquetipo == "critico" else 0.25
        if nome_arquetipo in ("endividado", "critico") and sorteio.random() < chance_novo_emprestimo:
            divida += receita * sorteio.uniform(0.2, 0.5)  # novo empréstimo

        # Caixa: sobe com o lucro, desce com prejuízo/parcelas/retirada do dono
        lucro = receita - despesas - parcelas
        retirada_do_dono = max(0.0, lucro * 0.5)
        caixa = max(0.0, caixa + lucro - retirada_do_dono)

        num_vendas = max(1, round(receita / ticket_medio_tipico * sorteio.uniform(0.9, 1.1)))

        lancamentos.append({
            "mes": mes,
            "receita_total": round(receita, 2),
            "despesas_fixas": round(despesas_fixas, 2),
            "despesas_variaveis": round(despesas_variaveis, 2),
            "compras_mercadorias": round(receita * sorteio.uniform(0.25, 0.55), 2),
            "saldo_caixa_final": round(caixa, 2),
            "parcelas_dividas_mes": round(parcelas, 2),
            "divida_total": round(divida, 2),
            "num_vendas": num_vendas,
            "num_clientes": max(1, round(num_vendas * sorteio.uniform(0.6, 0.8))),
            "recebiveis_atrasados": round(receita * parametros["inadimplencia"] * sorteio.uniform(0.5, 1.5), 2),
            "das_pago_em_dia": 1 if sorteio.random() < parametros["prob_das_em_dia"] else 0,
            "receita_maior_cliente": round(receita * parametros["concentracao"] * sorteio.uniform(0.8, 1.2), 2),
        })
        mes = proximo_mes(mes)

    return lancamentos


def gerar_dataset(negocios_por_arquetipo=NEGOCIOS_POR_ARQUETIPO, semente=42):
    """
    Gera todos os negócios de todos os arquétipos e devolve uma lista de
    linhas (dicionários) com duas colunas extras de identificação:
    id_negocio e arquetipo. A rotulagem com o score por regras acontece
    depois, em treinar.py (que reaproveita analise.py e score.py).
    """
    sorteio = random.Random(semente)  # semente fixa = resultado reprodutível
    linhas = []
    id_negocio = 0

    for nome_arquetipo in ARQUETIPOS:
        for _ in range(negocios_por_arquetipo):
            id_negocio += 1
            for lancamento in gerar_negocio(nome_arquetipo, sorteio):
                linha = {"id_negocio": id_negocio, "arquetipo": nome_arquetipo}
                linha.update(lancamento)
                linhas.append(linha)

    return linhas


def gerar_negocio_demo():
    """
    Gera UM negócio de 18 meses para o MODO DEMO do app (botão na tela
    de lançamentos). Usamos o arquétipo "em_crescimento" com semente
    fixa: a demonstração fica boa e sempre igual.
    """
    sorteio = random.Random(7)
    return gerar_negocio("em_crescimento", sorteio, mes_inicial="2025-01", num_meses=18)


def salvar_csv(linhas, caminho=ARQUIVO_SAIDA):
    """Grava as linhas geradas num CSV dentro de data/."""
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    with open(caminho, "w", newline="", encoding="utf-8") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=list(linhas[0].keys()))
        escritor.writeheader()
        escritor.writerows(linhas)


if __name__ == "__main__":
    print("Gerando dataset sintético...")
    linhas = gerar_dataset()
    salvar_csv(linhas)
    total_negocios = len(ARQUETIPOS) * NEGOCIOS_POR_ARQUETIPO
    print(f"Pronto: {total_negocios} negócios × {MESES_POR_NEGOCIO} meses "
          f"= {len(linhas)} linhas em {ARQUIVO_SAIDA}")
