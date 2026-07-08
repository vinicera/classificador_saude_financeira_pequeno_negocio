"""
dados.py
--------
Este arquivo cuida só da ENTRADA e do SALVAMENTO dos dados do negócio.
Não faz nenhum cálculo de indicador (isso é trabalho do analise.py).

Cada "mês" do negócio é representado por um dicionário Python, por exemplo:
    {"mes": "Janeiro", "receita": 10000, "custos": 7000, "caixa": 4000, "divida": 2000}
"""

import csv
import os

CAMPOS = ["mes", "receita", "custos", "caixa", "divida"]
ARQUIVO_HISTORICO = "historico.csv"


def digitar_mes():
    """
    Pergunta os números de UM mês pro usuário, digitando no teclado.
    Retorna um dicionário com os dados desse mês.
    """
    print("\n--- Digitar dados de um novo mês ---")
    mes = input("Nome do mês (ex: Janeiro/2026): ").strip()

    # input() sempre devolve texto (str), por isso usamos float() pra
    # transformar em número. Se a pessoa digitar algo inválido, pedimos de novo.
    receita = pedir_numero("Receita total do mês (R$): ")
    custos = pedir_numero("Custos totais do mês (R$): ")
    caixa = pedir_numero("Caixa/saldo disponível (R$): ")
    divida = pedir_numero("Dívida total atual (R$): ")

    return {
        "mes": mes,
        "receita": receita,
        "custos": custos,
        "caixa": caixa,
        "divida": divida,
    }


def pedir_numero(mensagem):
    """
    Fica pedindo um número até a pessoa digitar um valor válido.
    Isso evita que o programa quebre (dê erro) se alguém digitar letras.
    """
    while True:
        texto = input(mensagem).replace(",", ".")
        try:
            return float(texto)
        except ValueError:
            print("Valor inválido, digite apenas números (ex: 1500.50).")


def carregar_csv(caminho):
    """
    Lê um arquivo CSV com colunas: mes,receita,custos,caixa,divida
    Retorna uma lista de dicionários, um por mês.
    """
    meses = []
    if not os.path.exists(caminho):
        print(f"Arquivo '{caminho}' não encontrado.")
        return meses

    with open(caminho, newline="", encoding="utf-8") as arquivo:
        leitor = csv.DictReader(arquivo)
        for linha in leitor:
            try:
                meses.append({
                    "mes": linha["mes"],
                    "receita": float(linha["receita"]),
                    "custos": float(linha["custos"]),
                    "caixa": float(linha["caixa"]),
                    "divida": float(linha["divida"]),
                })
            except (KeyError, ValueError):
                print(f"Linha ignorada (dados incompletos ou inválidos): {linha}")
    return meses


def salvar_historico(meses, caminho=ARQUIVO_HISTORICO):
    """
    Salva a lista de meses num CSV local, para não perder os dados
    quando o programa for fechado (isso é o "Passo 8: Salvar" do fluxo original).
    """
    with open(caminho, "w", newline="", encoding="utf-8") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=CAMPOS)
        escritor.writeheader()
        for mes in meses:
            escritor.writerow(mes)


def carregar_historico(caminho=ARQUIVO_HISTORICO):
    """Carrega o histórico salvo em execuções anteriores, se existir."""
    if os.path.exists(caminho):
        return carregar_csv(caminho)
    return []
