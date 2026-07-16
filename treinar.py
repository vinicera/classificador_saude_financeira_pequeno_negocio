"""
treinar.py
----------
Treina o CLASSIFICADOR do estado de saúde (seção 4.1 da especificação):

  1. Lê o dataset sintético (data/dataset_sintetico.csv) — se não existir,
     gera na hora chamando gerar_sintetico.py.
  2. Para cada negócio, calcula os indicadores (analise.py) e o score por
     regras (score.py). A CLASSE do score vira o RÓTULO de treino.
  3. Monta as features (as mesmas que o app usa — definidas em ia_analise.py).
  4. Treina dois modelos e compara:
       - Random Forest (modelo principal)
       - Regressão Logística (baseline de comparação)
  5. Avalia com dados que o modelo NUNCA viu (divisão treino/teste) e
     imprime acurácia, matriz de confusão e precision/recall por classe.
  6. Salva o modelo + métricas em modelos/ para o app usar.

Como usar:
    python treinar.py
"""

import json
import os

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from analise import calcular_indicadores
from gerar_sintetico import ARQUIVO_SAIDA, gerar_dataset, salvar_csv
from ia_analise import FEATURES, montar_linha_de_features
from score import calcular_score

PASTA_MODELOS = "modelos"
ARQUIVO_MODELO = os.path.join(PASTA_MODELOS, "classificador.joblib")
ARQUIVO_METRICAS = os.path.join(PASTA_MODELOS, "metricas.json")

# Ordem fixa das classes (da melhor para a pior) — deixa a matriz de
# confusão legível e sempre igual entre execuções.
ORDEM_CLASSES = ["saudavel", "atencao", "alerta", "critico"]


def montar_tabela_de_treino():
    """
    Transforma o dataset sintético (lançamentos crus) na tabela de treino:
    uma linha por mês de cada negócio, com as FEATURES + o rótulo "classe".

    Pulamos os 3 primeiros meses de cada negócio porque os indicadores de
    tendência (crescimento e variações de 3 meses) ainda não existem neles.
    """
    if not os.path.exists(ARQUIVO_SAIDA):
        print("Dataset sintético não encontrado — gerando agora...")
        salvar_csv(gerar_dataset())

    dataset = pd.read_csv(ARQUIVO_SAIDA)
    linhas_de_treino = []

    # Cada negócio é uma série temporal independente: processamos um por um
    for _, grupo in dataset.groupby("id_negocio"):
        # DataFrame -> lista de dicionários (o formato que analise.py espera).
        # where(notnull) troca NaN do pandas por None do Python.
        lancamentos = grupo.sort_values("mes").where(pd.notnull(grupo), None).to_dict("records")

        indicadores_por_mes = calcular_indicadores(lancamentos)

        for posicao in range(3, len(lancamentos)):
            features = montar_linha_de_features(indicadores_por_mes, posicao)
            # O rótulo é a classe dada pelo score por regras — a "verdade"
            # que o modelo deve aprender a reproduzir a partir das features.
            features["classe"] = calcular_score(indicadores_por_mes[posicao])["nivel"]
            linhas_de_treino.append(features)

    return pd.DataFrame(linhas_de_treino)


def treinar():
    """Executa o pipeline completo de treino + avaliação + salvamento."""
    tabela = montar_tabela_de_treino()
    print(f"\nTabela de treino: {len(tabela)} meses rotulados")
    print("Distribuição das classes:")
    print(tabela["classe"].value_counts().to_string(), "\n")

    X = tabela[FEATURES]
    y = tabela["classe"]

    # Divisão treino/teste: o modelo aprende com 75% e é avaliado nos 25%
    # que nunca viu (stratify mantém a proporção das classes nos dois lados).
    X_treino, X_teste, y_treino, y_teste = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=y
    )

    # Pipeline = imputação + modelo. O SimpleImputer preenche valores
    # faltantes com a MEDIANA do treino — importante porque o usuário real
    # pode deixar campos opcionais em branco.
    modelo_rf = Pipeline([
        ("imputador", SimpleImputer(strategy="median")),
        ("floresta", RandomForestClassifier(n_estimators=200, random_state=42)),
    ])

    # Baseline: modelo mais simples para comparação honesta. A Regressão
    # Logística precisa dos dados na mesma escala, por isso o StandardScaler.
    modelo_baseline = Pipeline([
        ("imputador", SimpleImputer(strategy="median")),
        ("escala", StandardScaler()),
        ("logistica", LogisticRegression(max_iter=2000)),
    ])

    modelo_rf.fit(X_treino, y_treino)
    modelo_baseline.fit(X_treino, y_treino)

    previsao_rf = modelo_rf.predict(X_teste)
    previsao_baseline = modelo_baseline.predict(X_teste)

    acuracia_rf = accuracy_score(y_teste, previsao_rf)
    acuracia_baseline = accuracy_score(y_teste, previsao_baseline)

    print(f"Acurácia Random Forest:       {acuracia_rf:.1%}")
    print(f"Acurácia Regressão Logística: {acuracia_baseline:.1%}  (baseline)\n")

    print("Relatório por classe (Random Forest):")
    print(classification_report(y_teste, previsao_rf, labels=ORDEM_CLASSES, zero_division=0))

    matriz = confusion_matrix(y_teste, previsao_rf, labels=ORDEM_CLASSES)
    print("Matriz de confusão (linhas = classe real, colunas = classe prevista):")
    print(pd.DataFrame(matriz, index=ORDEM_CLASSES, columns=ORDEM_CLASSES).to_string(), "\n")

    # Importância das features: quanto cada indicador pesou nas decisões
    # da floresta. É o que o dashboard mostra como "o que derruba sua nota".
    importancias = sorted(
        zip(FEATURES, modelo_rf.named_steps["floresta"].feature_importances_),
        key=lambda par: par[1],
        reverse=True,
    )
    print("Importância das features:")
    for nome, peso in importancias:
        print(f"  {nome:26s} {peso:.3f}")

    # Salva o "pacote" completo: pipeline + nomes das features + métricas.
    # O app só precisa carregar este arquivo (ver ia_analise.py).
    os.makedirs(PASTA_MODELOS, exist_ok=True)
    joblib.dump({
        "pipeline": modelo_rf,
        "features": FEATURES,
        "importancias": [(nome, float(peso)) for nome, peso in importancias],
        "acuracia": acuracia_rf,
    }, ARQUIVO_MODELO)

    with open(ARQUIVO_METRICAS, "w", encoding="utf-8") as arquivo:
        json.dump({
            "acuracia_random_forest": acuracia_rf,
            "acuracia_regressao_logistica": acuracia_baseline,
            "relatorio_por_classe": classification_report(
                y_teste, previsao_rf, labels=ORDEM_CLASSES, zero_division=0, output_dict=True
            ),
            "matriz_confusao": matriz.tolist(),
            "ordem_classes": ORDEM_CLASSES,
            "importancias": [(nome, float(peso)) for nome, peso in importancias],
            "tamanho_treino": len(X_treino),
            "tamanho_teste": len(X_teste),
        }, arquivo, ensure_ascii=False, indent=2)

    print(f"\nModelo salvo em {ARQUIVO_MODELO}")
    print(f"Métricas salvas em {ARQUIVO_METRICAS}")

    if acuracia_rf < 0.85:
        print("\nATENÇÃO: acurácia abaixo da meta de 85% do critério de aceite!")


if __name__ == "__main__":
    treinar()
