"""
dados.py
--------
Camada de DADOS do projeto: guarda e recupera tudo no SQLite (arquivo
data/app.db). Nenhum cálculo de indicador acontece aqui — isso é trabalho
do analise.py. Aqui só entra e sai informação.

O banco tem duas tabelas:
  - perfil       -> os dados do negócio (nome, atividade, data de abertura...)
  - lancamentos  -> um registro por mês, com os 13 campos da especificação

Usamos o sqlite3 da biblioteca padrão do Python: não precisa instalar nada
e o banco inteiro é um único arquivo, fácil de apagar/copiar/entregar.
"""

import os
import sqlite3

# Pasta e arquivo do banco. A pasta data/ é criada automaticamente.
PASTA_DADOS = "data"
ARQUIVO_BANCO = os.path.join(PASTA_DADOS, "app.db")

# ---------------------------------------------------------------------------
# Descrição dos 13 campos de um lançamento mensal (seção 3.2 da especificação)
# ---------------------------------------------------------------------------
# Esta lista é usada em vários lugares (formulário, importação, exportação),
# então fica definida UMA vez aqui. Cada campo tem:
#   nome        -> como a coluna se chama no banco e no CSV/Excel
#   rotulo      -> como aparece na tela para o usuário
#   tipo        -> "texto", "valor" (R$), "inteiro" ou "sim_nao"
#   obrigatorio -> True se o campo não pode ficar vazio
CAMPOS_LANCAMENTO = [
    {"nome": "mes",                  "rotulo": "Mês (AAAA-MM)",          "tipo": "texto",   "obrigatorio": True},
    {"nome": "receita_total",        "rotulo": "Receita total (R$)",     "tipo": "valor",   "obrigatorio": True},
    {"nome": "despesas_fixas",       "rotulo": "Despesas fixas (R$)",    "tipo": "valor",   "obrigatorio": True},
    {"nome": "despesas_variaveis",   "rotulo": "Despesas variáveis (R$)","tipo": "valor",   "obrigatorio": True},
    {"nome": "compras_mercadorias",  "rotulo": "Compras de mercadorias (R$)", "tipo": "valor", "obrigatorio": False},
    {"nome": "saldo_caixa_final",    "rotulo": "Saldo de caixa final (R$)",   "tipo": "valor", "obrigatorio": True},
    {"nome": "parcelas_dividas_mes", "rotulo": "Parcelas de dívidas no mês (R$)", "tipo": "valor", "obrigatorio": False},
    {"nome": "divida_total",         "rotulo": "Dívida total (R$)",      "tipo": "valor",   "obrigatorio": False},
    {"nome": "num_vendas",           "rotulo": "Nº de vendas",           "tipo": "inteiro", "obrigatorio": False},
    {"nome": "num_clientes",         "rotulo": "Nº de clientes",         "tipo": "inteiro", "obrigatorio": False},
    {"nome": "recebiveis_atrasados", "rotulo": "Recebíveis atrasados / fiado (R$)", "tipo": "valor", "obrigatorio": False},
    {"nome": "das_pago_em_dia",      "rotulo": "DAS pago em dia?",       "tipo": "sim_nao", "obrigatorio": True},
    {"nome": "receita_maior_cliente","rotulo": "Receita do maior cliente (R$)", "tipo": "valor", "obrigatorio": False},
]

# Só os nomes, na ordem — útil para montar CSV/Excel.
NOMES_CAMPOS = [campo["nome"] for campo in CAMPOS_LANCAMENTO]


def conectar():
    """
    Abre a conexão com o banco (criando a pasta data/ se não existir).
    row_factory = sqlite3.Row faz cada linha vir como um "dicionário",
    permitindo acessar por nome: linha["receita_total"].
    """
    os.makedirs(PASTA_DADOS, exist_ok=True)
    conexao = sqlite3.connect(ARQUIVO_BANCO)
    conexao.row_factory = sqlite3.Row
    return conexao


def criar_tabelas():
    """Cria as tabelas na primeira execução (se já existem, não faz nada)."""
    with conectar() as conexao:
        conexao.execute("""
            CREATE TABLE IF NOT EXISTS perfil (
                id INTEGER PRIMARY KEY CHECK (id = 1),  -- só existe 1 perfil
                nome TEXT NOT NULL,
                cnpj TEXT,
                atividade TEXT NOT NULL,      -- comercio, servico ou ambos
                data_abertura TEXT NOT NULL,  -- AAAA-MM
                meta_anual REAL               -- meta de faturamento do ano (R$)
            )
        """)
        conexao.execute("""
            CREATE TABLE IF NOT EXISTS lancamentos (
                mes TEXT PRIMARY KEY,         -- AAAA-MM (chave: 1 registro por mês)
                receita_total REAL NOT NULL,
                despesas_fixas REAL NOT NULL,
                despesas_variaveis REAL NOT NULL,
                compras_mercadorias REAL,     -- campos opcionais podem ser NULL
                saldo_caixa_final REAL NOT NULL,
                parcelas_dividas_mes REAL,
                divida_total REAL,
                num_vendas INTEGER,
                num_clientes INTEGER,
                recebiveis_atrasados REAL,
                das_pago_em_dia INTEGER NOT NULL,  -- 1 = SIM, 0 = NÃO
                receita_maior_cliente REAL
            )
        """)


# ---------------------------------------------------------------------------
# Perfil do negócio
# ---------------------------------------------------------------------------

def salvar_perfil(perfil):
    """
    Grava (ou atualiza) o perfil do negócio.
    Recebe um dicionário com: nome, cnpj, atividade, data_abertura, meta_anual.
    Como o app acompanha UM negócio, o id é sempre 1 (REPLACE atualiza).
    """
    with conectar() as conexao:
        conexao.execute(
            """INSERT OR REPLACE INTO perfil (id, nome, cnpj, atividade, data_abertura, meta_anual)
               VALUES (1, ?, ?, ?, ?, ?)""",
            (perfil["nome"], perfil.get("cnpj"), perfil["atividade"],
             perfil["data_abertura"], perfil.get("meta_anual")),
        )


def carregar_perfil():
    """Devolve o perfil como dicionário, ou None se ainda não foi cadastrado."""
    with conectar() as conexao:
        linha = conexao.execute("SELECT * FROM perfil WHERE id = 1").fetchone()
    return dict(linha) if linha else None


# ---------------------------------------------------------------------------
# Lançamentos mensais
# ---------------------------------------------------------------------------

def salvar_lancamento(lancamento):
    """
    Grava um mês no banco. Se o mês já existe, substitui (assim dá pra
    corrigir um lançamento reenviando o formulário).
    Recebe um dicionário com os campos de CAMPOS_LANCAMENTO
    (os opcionais podem faltar ou vir como None).
    """
    valores = [lancamento.get(nome) for nome in NOMES_CAMPOS]
    marcadores = ", ".join(["?"] * len(NOMES_CAMPOS))
    colunas = ", ".join(NOMES_CAMPOS)
    with conectar() as conexao:
        conexao.execute(
            f"INSERT OR REPLACE INTO lancamentos ({colunas}) VALUES ({marcadores})",
            valores,
        )


def carregar_lancamentos():
    """
    Devolve TODOS os meses lançados, em ordem cronológica, como lista de
    dicionários. A ordem funciona porque o formato AAAA-MM ordena certo
    como texto ("2026-02" < "2026-10").
    """
    with conectar() as conexao:
        linhas = conexao.execute("SELECT * FROM lancamentos ORDER BY mes").fetchall()
    return [dict(linha) for linha in linhas]


def excluir_lancamento(mes):
    """Apaga o lançamento de um mês específico (formato AAAA-MM)."""
    with conectar() as conexao:
        conexao.execute("DELETE FROM lancamentos WHERE mes = ?", (mes,))


def apagar_todos_lancamentos():
    """Apaga todos os lançamentos (usado ao carregar o modo demo)."""
    with conectar() as conexao:
        conexao.execute("DELETE FROM lancamentos")


# Garante que as tabelas existem assim que o módulo é importado,
# para nenhuma outra parte do código precisar se preocupar com isso.
criar_tabelas()
