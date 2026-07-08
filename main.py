"""
main.py
-------
Programa principal. Junta os outros arquivos (dados.py, analise.py,
insight_ia.py) num fluxo só, com um menu simples no terminal.

Como rodar:
    python main.py

Fluxo (versão CLI do checkpoint; a versão final terá uma interface
gráfica em tkinter, ainda não incluída nesta entrega parcial):
    1) escolher o setor do negócio
    2) importar um CSV OU digitar um mês novo
    3) ver o diagnóstico (indicadores + classificação + tendência + comentário)
"""

from dados import digitar_mes, carregar_csv, salvar_historico, carregar_historico
from analise import calcular_indicadores, analisar_tendencia
from ia_analise import diagnosticar

SETORES_VALIDOS = ["comercio", "servicos", "industria"]


def escolher_setor():
    print("\nSetor do negócio:")
    for i, setor in enumerate(SETORES_VALIDOS, start=1):
        print(f"  {i}. {setor}")
    while True:
        escolha = input("Escolha o número do setor: ").strip()
        if escolha in ("1", "2", "3"):
            return SETORES_VALIDOS[int(escolha) - 1]
        print("Opção inválida.")


def mostrar_diagnostico(mes, setor, historico_indicadores):
    indicadores = calcular_indicadores(mes)
    historico_indicadores.append(indicadores)

    # Aqui é onde a IA analisa o mês de verdade (ver ia_analise.py).
    # Se a API não estiver disponível, "resultado" vem do plano B (regra).
    resultado = diagnosticar(mes, indicadores, setor)

    print(f"\n=== Diagnóstico de {mes['mes']} ===")
    print(f"Margem:         {indicadores['margem']:.1%}")
    print(f"Peso do custo:  {indicadores['peso_custo']:.1%}")
    print(f"Liquidez:       {indicadores['liquidez']:.2f}")
    print(f"Endividamento:  {indicadores['endividamento']:.1%}")
    print(f"Classificação:  {resultado['classificacao'].upper()}  (fonte: {resultado['fonte']})")
    print(f"Fator crítico:  {resultado['fator_critico']}")
    print(f"Tendência:      {analisar_tendencia(historico_indicadores)}")
    print(f"\nComentário: {resultado['comentario']}")


def menu():
    print("=" * 50)
    print(" Diagnóstico de Saúde Financeira - Pequenos Negócios")
    print("=" * 50)

    setor = escolher_setor()
    historico = carregar_historico()
    historico_indicadores = []

    # Se já existe histórico salvo, recalcula os indicadores dele
    # para a tendência funcionar corretamente desde o início.
    for mes_salvo in historico:
        historico_indicadores.append(calcular_indicadores(mes_salvo))

    while True:
        print("\n--- Menu ---")
        print("1. Importar dados de um CSV")
        print("2. Digitar um novo mês")
        print("3. Sair")
        opcao = input("Escolha uma opção: ").strip()

        if opcao == "1":
            caminho = input("Caminho do arquivo CSV: ").strip()
            novos_meses = carregar_csv(caminho)
            for mes in novos_meses:
                historico.append(mes)
                mostrar_diagnostico(mes, setor, historico_indicadores)
            salvar_historico(historico)

        elif opcao == "2":
            mes = digitar_mes()
            historico.append(mes)
            mostrar_diagnostico(mes, setor, historico_indicadores)
            salvar_historico(historico)

        elif opcao == "3":
            print("Até mais!")
            break

        else:
            print("Opção inválida, tente novamente.")


if __name__ == "__main__":
    menu()
