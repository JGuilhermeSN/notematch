# src/ui/cli_app.py
from pathlib import Path
import pandas as pd

from src.core.data_loader import load_notebooks_df
from src.core.recommender import preprocess, filter_by_specs, rank_and_pick
from src.core.specs_rules import infer_specs  # ou gerar_specs, conforme seu módulo
from src.core.questions import build_flow
from src.core.engine import run

def main():
    # 1) Perguntas → respostas
    first_q = build_flow()
    answers = run(first_q)

    # 2) Respostas → especificações mínimas
    specs = infer_specs(answers)  # ou gerar_specs(answers)

    # 3) Carrega a base: usa cache se existir, senão baixa do Kaggle e cria cache
    df = load_notebooks_df(file_path_kaggle="laptop_price (1).csv", encoding="latin1")
    dfp = preprocess(df)

    # 4) Filtra por especificações
    candidates = filter_by_specs(dfp, specs)

    # 5) Top 3
    budget = answers.get("Qual faixa de orçamento?")
    top3 = rank_and_pick(candidates, budget, k=3)

    print("\n=== Especificações mínimas recomendadas ===")
    print(specs)
    print("\n=== Top 3 notebooks compatíveis (base de dados) ===")
    if top3.empty:
        print("Nenhum modelo encontrado com esses critérios.")
    else:
        print(top3.to_string(index=False))

if __name__ == "__main__":
    main()
