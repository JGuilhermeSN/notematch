# src/core/data_loader.py
from pathlib import Path
import pandas as pd

def load_notebooks_df(
    file_path_kaggle: str = "laptop_price (1).csv",
    encoding: str = "latin1",
    cache_path: Path | None = None,
):
    # caminho padrão para cache
    if cache_path is None:
        base_dir = Path(__file__).resolve().parents[2]   # raiz do projeto (NoteMatch)
        cache_path = base_dir / "data" / "base_dados.csv"

    # 1) tenta usar cache local
    if cache_path.exists():
        return pd.read_csv(cache_path, encoding=encoding)

    # 2) se não houver, baixa via kagglehub
    import kagglehub
    from kagglehub import KaggleDatasetAdapter

    df = kagglehub.load_dataset(
        KaggleDatasetAdapter.PANDAS,
        "durgeshrao9993/laptop-specification-dataset",
        file_path_kaggle,
        pandas_kwargs={"encoding": encoding}
    )

    # 3) salva cache para execuções futuras
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(cache_path, index=False, encoding=encoding)

    return df
