"""
configuracao.py
---------------
Módulo minúsculo com uma única responsabilidade: ler o config.yaml
(pesos, faixas, limite MEI, gatilhos de alerta) e entregar como um
dicionário Python para o resto do programa.

Vários módulos precisam do config (analise, score, alertas, ia_analise);
centralizar a leitura aqui evita repetir código e abrir o arquivo várias
vezes sem necessidade.
"""

import yaml

ARQUIVO_CONFIG = "config.yaml"

# Guardamos o config em memória depois da primeira leitura ("cache"),
# porque ele não muda enquanto o programa roda.
_config_em_memoria = None


def carregar_config():
    """
    Lê o config.yaml (uma vez só) e devolve o dicionário com todas as
    seções: mei, pesos, faixas, classes, alertas e previsao.
    """
    global _config_em_memoria
    if _config_em_memoria is None:
        with open(ARQUIVO_CONFIG, encoding="utf-8") as arquivo:
            _config_em_memoria = yaml.safe_load(arquivo)
    return _config_em_memoria
