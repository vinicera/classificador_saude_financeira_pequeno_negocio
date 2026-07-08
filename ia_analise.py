"""
ia_analise.py
-------------
Aqui é onde a IA entra de fato na análise do negócio. Este é o requisito
do professor: o app TEM que ter IA, não é um extra.

Como funciona:
  1) Recebemos os indicadores JÁ CALCULADOS (isso é trabalho nosso, em
     analise.py — matemática pura, sem IA).
  2) Montamos uma pergunta (prompt) explicando os números pra IA.
  3) Pedimos pra IA responder em JSON, num formato fixo, com:
     classificação, fator crítico e um comentário curto.
  4) Lemos essa resposta com json.loads() e usamos no programa.

Ou seja: quem faz o "julgamento" (saudável/atenção/risco) é a IA, não uma
regra nossa. Isso é diferente de treinar um modelo do zero — estamos usando
um modelo de linguagem já pronto (Claude, via API), só damos os números e
pedimos uma análise.

PLANO B: se não houver uma chave de API configurada (variável de ambiente
ANTHROPIC_API_KEY) ou se a chamada falhar (sem internet, por exemplo), o
programa NÃO trava. Ele avisa isso no comentário e usa, como reserva, a
classificação por regra simples de analise.py. Isso é importante pra
apresentação: se a wifi falhar na hora, o programa continua funcionando.
"""

import json
import os
import urllib.request
import urllib.error

from analise import classificar_saude_regra

MODELO = "claude-3-5-haiku-20241022"
URL_API = "https://api.anthropic.com/v1/messages"


def diagnosticar(mes, indicadores, setor):
    """
    Pede pra IA analisar o mês e devolve um dicionário:
        {"classificacao": ..., "fator_critico": ..., "comentario": ..., "fonte": ...}

    "fonte" diz se veio da IA ("ia") ou do plano B ("regra (plano B)"),
    pra ficar transparente na tela qual caminho foi usado.
    """
    chave = os.environ.get("ANTHROPIC_API_KEY")

    if not chave:
        return _plano_b(indicadores, setor, motivo="nenhuma ANTHROPIC_API_KEY configurada")

    pergunta = (
        f"Você é um analista financeiro avaliando um pequeno negócio do setor "
        f"'{setor}'. Dados do mês de {mes['mes']}: margem de lucro de "
        f"{indicadores['margem']:.1%}, custos representam {indicadores['peso_custo']:.1%} "
        f"da receita, liquidez (caixa dividido pelo custo mensal) de "
        f"{indicadores['liquidez']:.2f}, endividamento de {indicadores['endividamento']:.1%} "
        f"da receita.\n\n"
        "Classifique a saúde financeira do mês como 'saudável', 'atenção' ou 'risco', "
        "aponte qual indicador (margem, peso_custo, liquidez ou endividamento) é o fator "
        "mais crítico, e escreva um comentário curto (no máximo 2 frases) com um conselho "
        "prático em português.\n\n"
        "Responda SOMENTE em JSON, exatamente neste formato, sem nenhum texto antes ou depois:\n"
        '{"classificacao": "...", "fator_critico": "...", "comentario": "..."}'
    )

    corpo = json.dumps({
        "model": MODELO,
        "max_tokens": 300,
        "messages": [{"role": "user", "content": pergunta}],
    }).encode("utf-8")

    requisicao = urllib.request.Request(
        URL_API,
        data=corpo,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "x-api-key": chave,
            "anthropic-version": "2023-06-01",
        },
    )

    try:
        with urllib.request.urlopen(requisicao, timeout=15) as resposta:
            dados_resposta = json.loads(resposta.read().decode("utf-8"))
            texto = dados_resposta["content"][0]["text"].strip()
            resultado = json.loads(texto)
            resultado["fonte"] = "ia"
            return resultado
    except (urllib.error.URLError, KeyError, IndexError, TimeoutError, json.JSONDecodeError) as erro:
        return _plano_b(indicadores, setor, motivo=f"falha ao chamar a API de IA ({erro})")


def _plano_b(indicadores, setor, motivo):
    """
    Reserva usada só quando a IA não pode ser chamada.
    Usa a regra simples de analise.py e deixa avisado o motivo.
    """
    classificacao, fator_critico = classificar_saude_regra(indicadores, setor)
    return {
        "classificacao": classificacao,
        "fator_critico": fator_critico or "nenhum",
        "comentario": f"[Plano B, sem IA: {motivo}] Classificação feita por regra simples de comparação com o setor.",
        "fonte": "regra (plano B)",
    }
