# Diagnóstico de Saúde Financeira para Pequenos Negócios

Programa em Python que ajuda pequenos negócios a entender sua saúde financeira
mês a mês: calcula indicadores (margem, peso do custo, liquidez, endividamento)
e pede para uma **IA analisar esses números** e classificar o mês como
**saudável**, **atenção** ou **risco**, apontando o fator crítico e dando um
comentário. Também mostra a tendência quando há 2 ou mais meses de dados.

> Entrega parcial (Checkpoint) — Introdução à Programação, UFCAT.

## Como rodar

```bash
python main.py
```

Não é necessário instalar nenhuma biblioteca externa (usa só a biblioteca
padrão do Python: `csv`, `os`, `json`, `urllib`).

Para a IA analisar de verdade, configure sua chave da API da Anthropic antes
de rodar:
```bash
export ANTHROPIC_API_KEY="sua_chave_aqui"
```
Se essa variável não estiver definida (ou a chamada falhar), o programa
continua funcionando normalmente, usando um plano B (classificação por
regra simples) e avisando isso na tela.

Ao rodar, escolha o setor do negócio e depois:
- **Opção 1**: importar um CSV (use `dados_exemplo.csv` para testar rápido); ou
- **Opção 2**: digitar os dados de um mês na mão.

## Estrutura do código

| Arquivo | O que faz |
|---|---|
| `main.py` | Menu principal, junta tudo |
| `dados.py` | Lê dados (CSV ou digitados) e salva o histórico em `historico.csv` |
| `analise.py` | Calcula os indicadores (matemática, sem IA) e guarda o plano B (`classificar_saude_regra`) |
| `ia_analise.py` | **Aqui a IA analisa o mês**: recebe os indicadores e devolve classificação, fator crítico e comentário |
| `dados_exemplo.csv` | Dados fictícios de 3 meses para teste/demonstração |

## O que mudou em relação ao plano original

O plano original (documento inicial do grupo) previa "treinar um modelo" para
fazer a classificação. Decidimos **não treinar nenhum modelo de IA** — em vez
disso, usamos a API de um modelo de linguagem já pronto (Claude, da
Anthropic), porque:

1. Ainda não vimos machine learning na disciplina, treinar um modelo do zero
   está fora do nosso alcance atual;
2. Usar uma API é o que o professor pediu como alternativa ("usar IA para
   construir o app", não treinar uma);
3. A IA analisando os números é justamente o que dá inteligência ao app —
   é o requisito central, não um extra.

## Onde a IA é (e não é) usada

- **Usa IA (parte central do app)**: a função `diagnosticar()` em
  `ia_analise.py` recebe os indicadores já calculados e pede pra Claude
  analisar o mês, devolvendo a classificação (saudável/atenção/risco), o
  fator crítico e um comentário — tudo isso é decidido pela IA, não por uma
  regra nossa.
- **Não usa IA**: a leitura de dados e o **cálculo** dos indicadores
  (margem, peso do custo, liquidez, endividamento) são matemática pura,
  escrita por nós. A tendência entre meses também é só comparação de
  números, sem IA.
- **Plano B (reserva, não é o caminho principal)**: se não houver uma chave
  de API configurada na variável `ANTHROPIC_API_KEY`, ou se a chamada
  falhar (sem internet, por exemplo), o programa usa `classificar_saude_regra()`
  em `analise.py` — uma classificação por regra simples — e avisa isso
  claramente na tela, só para o app não travar durante a apresentação.

## Status atual (núcleo vs. diferencial)

**Funcionando (núcleo):**
- Leitura de dados por CSV e por digitação
- Cálculo dos 4 indicadores financeiros
- Diagnóstico feito pela IA via API (classificação + fator crítico + comentário)
- Plano B automático caso a IA não esteja disponível
- Tendência simples entre meses (regra dos 2 meses)
- Histórico salvo entre execuções (`historico.csv`)

**Ainda não feito (planejado até a entrega final):**
- Interface gráfica em tkinter (esta versão do checkpoint é em terminal/CLI)
- Configuração definitiva da chave de API para o comentário sempre usar IA
- Validações extras no import de CSV (colunas fora de ordem, valores faltando)
- Possível uso de RAG, se o grupo decidir que agrega valor real ao projeto

## Uso de ferramentas de IA na produção deste trabalho

A Claude (Anthropic) foi usada como apoio para estruturar o projeto em
módulos e revisar a lógica de código. Todo o código foi revisado e é de
entendimento do grupo, que é capaz de explicar cada trecho.

Isso é diferente do uso de IA **dentro do app**: lá, a IA (também a Claude,
via API) é chamada em tempo de execução para analisar os indicadores
financeiros e gerar o diagnóstico — essa é uma funcionalidade do produto,
não uma ferramenta usada para escrever o código.
