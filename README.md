# Saúde MEI — Diagnóstico Inteligente do Negócio

Sistema que avalia a **saúde financeira de um MEI** a partir dos números que o próprio
microempreendedor tem na mão (vendas, despesas, caixa, dívidas, DAS...):

- calcula **10 indicadores** financeiros mês a mês;
- resume tudo num **Score de Saúde (0–100)** com semáforo
  (🟢 Saudável · 🟡 Atenção · 🟠 Alerta · 🔴 Crítico);
- usa **machine learning local** (Random Forest, scikit-learn — **sem nenhuma API externa**)
  para classificar o estado e mostrar *o que mais derruba a nota*;
- **prevê os próximos 6 meses** (receita, caixa e score) com cenários
  pessimista / base / otimista;
- dispara **alertas** com recomendações práticas (risco de desenquadramento,
  caixa crítico, DAS atrasado...);
- importa/exporta **Excel** e gera **relatório PDF**.

> Projeto acadêmico — grupo de 1º período de IA. Toda a lógica e a IA são Python;
> o HTML/CSS é só a camada de apresentação (Flask + Jinja).

## Como rodar

**Jeito fácil (Windows):** dê **duplo clique em `Iniciar Saude MEI.bat`**. Ele instala as
dependências se faltarem, treina o modelo na primeira vez e abre o site sozinho no navegador.
Para desligar, aperte `Ctrl+C` na janela preta (ou feche-a).

**Jeito manual (qualquer sistema):**

```bash
# 1. Instalar as dependências
pip install -r requirements.txt

# 2. Treinar o modelo de IA (uma vez — gera modelos/classificador.joblib)
python treinar.py

# 3. Subir o aplicativo
python app.py
```

Depois abra **http://127.0.0.1:5000** no navegador.

**Acesso de outras pessoas:** quem estiver na **mesma rede (wifi)** pode acessar pelo IP do
computador que está rodando o app — o endereço aparece no terminal ao iniciar (ex.:
`http://192.168.0.104:5000`). Na primeira vez o Windows pode perguntar se libera o acesso
do Python na rede: clique em **Permitir**.

**Para ver uma demonstração** (o site abre vazio na primeira vez), a própria tela de
boas-vindas oferece dois caminhos:
- **"Carregar dados de demonstração"** — 1 clique, carrega 18 meses de um negócio fictício; ou
- **"Baixe o CSV de exemplo"** — baixa o `dados_exemplo_mei.csv` (12 meses de um comércio
  fictício) para importar na tela Lançamentos, experimentando o mesmo fluxo que um usuário
  real faria com o arquivo da empresa dele.

> O passo 2 é opcional para o app abrir: sem modelo treinado, a classificação usa um
> **plano B por regras** e avisa isso na tela. Mas rode o `treinar.py` — é ele que ativa
> o Random Forest, as probabilidades e o gráfico de importâncias.

## O fluxo, em uma linha

cadastro do negócio → lançamento dos meses (formulário ou planilha) → indicadores →
score + semáforo → classificação por ML → previsão com cenários → alertas → exportação.

## Estrutura do código (cada arquivo tem UMA responsabilidade)

| Arquivo | O que faz |
|---|---|
| `app.py` | O site (Flask): recebe cliques/formulários e chama os módulos abaixo |
| `config.yaml` | Pesos, faixas dos indicadores e limite MEI — **comentado**, ajustável sem mexer em código |
| `configuracao.py` | Lê o `config.yaml` para os demais módulos |
| `dados.py` | Banco SQLite (`data/app.db`): perfil do negócio + lançamentos de 13 campos |
| `analise.py` | Os **10 indicadores** (fórmulas nas docstrings) — matemática pura, sem IA |
| `score.py` | Normaliza cada indicador (0–100) e faz a média ponderada → score + classe |
| `alertas.py` | As 7 regras de alerta (seção 3.5 da especificação) |
| `ia_analise.py` | **A IA local**: classificador Random Forest + previsão por regressão linear |
| `gerar_sintetico.py` | Dataset sintético: 360 negócios × 24 meses a partir de 6 arquétipos |
| `treinar.py` | Treina RF vs. baseline, avalia (acurácia, matriz de confusão) e salva em `modelos/` |
| `io_excel.py` | Importação validada linha a linha, template `.xlsx` e export com 3 abas |
| `relatorio.py` | Relatório PDF (ReportLab + gráficos matplotlib) |
| `templates/` | As 6 telas (HTML + Plotly para os gráficos) |
| `notebooks/metodologia_e_treino.ipynb` | **O pipeline de ML narrado passo a passo, com métricas** |
| `docs/relatorio_tecnico.md` | Relatório técnico: problema → dados → metodologia → resultados |

## As 6 telas

1. **Diagnóstico** — gauge do score, classificação da IA com probabilidades, resumo do mês, alertas.
2. **Indicadores** — cartão por indicador com evolução e o expander *"Como calculamos?"*.
3. **Previsão** — receita, caixa e score projetados, com a faixa de cenários sombreada.
4. **Lançamentos** — formulário dos 13 campos, tabela dos meses, importação/exportação.
5. **Metodologia** — explicação didática de tudo + métricas reais do último treino.
6. **Configurações** — perfil do negócio e parâmetros do `config.yaml`.

## Onde a IA é (e não é) usada

- **É IA (scikit-learn, treinada e rodando localmente):** a classificação do estado
  (Random Forest com probabilidades e feature importance) e a previsão dos próximos meses
  (regressão linear + cenários pela margem de erro). Nenhuma API externa é chamada.
- **Não é IA:** leitura dos dados, cálculo dos indicadores e o score por regras — matemática
  escrita por nós, explicada na página Metodologia. O score por regras também **rotula o
  dataset sintético** que treina o modelo (a saída para a falta de dados reais de MEIs).

## Resultados do modelo (dados de teste, que o modelo nunca viu)

- Acurácia Random Forest: **~97%** (meta do critério de aceite: ≥ 85%)
- Baseline (Regressão Logística) documentada para comparação
- Matriz de confusão, precision/recall e o backtest da previsão (MAE/RMSE) estão no
  notebook e na tela Metodologia

## Uso de ferramentas de IA na produção deste trabalho

A Claude (Anthropic) foi usada como apoio para estruturar os módulos e revisar o código.
Todo o código foi revisado e é de entendimento do grupo. Diferente do checkpoint anterior,
o produto final **não chama nenhuma API de IA**: os modelos são treinados e executados
localmente com scikit-learn, como exige a especificação.
