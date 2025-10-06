# src/ui/cli_app.py
from pathlib import Path
import pandas as pd
import sys

from src.core.data_loader import load_notebooks_df
from src.core.recommender import (
    preprocess,
    filter_by_specs,
    rank_and_pick,  # mantém orquestrador fino
    explain,
)
from src.core.specs_rules import infer_specs  # ou gerar_specs, conforme seu módulo
from src.core.questions import build_flow
from src.core.engine import run


# taxa de conversão BRL por EUR (ajustar conforme necessário)
FX_BRL_PER_EUR = 6.0


def _fmt_brl(v) -> str:
    try:
        return f"R$ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "—"


def _fmt_eur(v) -> str:
    try:
        return f"€ {float(v):,.2f}"
    except Exception:
        return "—"


def run_cli() -> None:
    try:
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

        # 5) Top K (com orçamento em BRL convertido internamente para EUR)
        budget = answers.get("Qual faixa de orçamento?")
        topk = rank_and_pick(
            candidates,
            budget,
            k=3,
            fx_brl_per_eur=FX_BRL_PER_EUR,  # importante!
        )

        print("\n=== Especificações mínimas recomendadas ===")
        print(specs)

        print("\n=== Top notebooks compatíveis (base de dados) ===")
        if topk.empty:
            print("Nenhum modelo encontrado com esses critérios.")
            return

        # Exibição amigável: formata BRL/EUR se presentes
        df_show = topk.copy()
        if "Price_in_brl" in df_show.columns:
            df_show["Price_in_brl"] = df_show["Price_in_brl"].map(_fmt_brl)
        if "Price_in_euros" in df_show.columns:
            df_show["Price_in_euros"] = df_show["Price_in_euros"].map(_fmt_eur)

        print(df_show.to_string(index=False))

        # 6) Explicações por item
        print("\n--- Explicações por item ---")
        for idx in topk.index:
            # Recupera a linha COMPLETA (com colunas engenheiradas) a partir de candidates
            # (rank_and_pick preserva o índice original, então funciona com loc)
            try:
                full_row = candidates.loc[idx]
            except KeyError:
                # fallback: tenta com dfp (caso candidates tenha sido reindexado em algum ponto)
                full_row = dfp.loc[idx] if idx in dfp.index else topk.loc[idx]

            try:
                msg = explain(full_row, specs)
            except Exception as e:
                msg = f"Explicação indisponível ({e})"

            ident = f"{full_row.get('Company', '?')} {full_row.get('Product', '?')}"
            price_brl = topk.loc[idx].get("Price_in_brl", None)
            price_brl_txt = _fmt_brl(price_brl) if price_brl is not None else "—"
            print(f"* {ident} ({price_brl_txt}): {msg}")

    except KeyboardInterrupt:
        print("\nExecução interrompida pelo usuário.")
        sys.exit(1)


if __name__ == "__main__":
    run_cli()
