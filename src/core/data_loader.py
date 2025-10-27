# src/core/data_loader.py
from __future__ import annotations
from pathlib import Path
import csv
import re
from typing import List

from src.core.models import Notebook

DEFAULT_ENCODING = "latin1"
DEFAULT_FILENAME = "base_dados.csv"  # Kaggle: laptops.csv adaptado

def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]

def _default_data_path() -> Path:
    return _project_root() / "data" / DEFAULT_FILENAME

_num = re.compile(r"[\d\.]+")  # aceita '1,37kg' -> 1.37

def _to_float(s: object, default: float = 0.0) -> float:
    if s is None:
        return default
    txt = str(s).strip().replace(",", ".")
    m = _num.findall(txt)
    return float(m[0]) if m else default

def _parse_inches(row: dict) -> float:
    return _to_float(row.get("Inches") or row.get("inches") or row.get("Tela"))

def _parse_weight(row: dict) -> float:
    w = row.get("Weight") or row.get("weight_kg") or row.get("Peso")
    if not w:
        return 0.0
    return _to_float(w)

def _parse_ram_gb(v: object) -> int:
    if not v:
        return 0
    txt = str(v).lower()
    m = re.search(r"(\d+)\s*gb", txt)
    if m:
        return int(m.group(1))
    try:
        return int(float(txt.replace(",", ".")))
    except Exception:
        return 0

def _get_str(row: dict, *keys: str) -> str:
    for k in keys:
        v = row.get(k)
        if v is not None:
            return str(v).strip()
    return ""

def _get_price_eur(row: dict) -> float:
    return _to_float(row.get("Price_in_euros") or row.get("Price_euros") or row.get("price_eur") or row.get("price"))

def load_notebooks(path: Path | None = None) -> List[Notebook]:
    """Lê a base do Kaggle (CSV) SEM pandas e devolve uma lista de Notebooks normalizados.

    Campos mapeados (quando disponíveis):
      - name      <- Product / Model / Name
      - company   <- Company / Brand
      - cpu       <- Cpu / CPU / cpu
      - ram_gb    <- Ram / RAM / ram (converte '8GB' -> 8)
      - gpu       <- Gpu / GPU / gpu
      - inches    <- Inches
      - screen_res<- ScreenResolution / Screen_Resolution / screen_resolution
      - weight_kg <- Weight (converte '1.37kg' -> 1.37)
      - price_eur <- Price_in_euros / Price_euros / price_eur / price
    """
    csv_path = path or _default_data_path()
    out: List[Notebook] = []
    with open(csv_path, "r", encoding=DEFAULT_ENCODING, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            nb = Notebook(
                name=_get_str(row, "Product", "product_name", "Model", "Name", "model"),
                company=_get_str(row, "Company", "Brand", "brand"),
                cpu=_get_str(row, "Cpu", "CPU", "cpu"),
                ram_gb=_parse_ram_gb(row.get("Ram") or row.get("RAM") or row.get("ram")),
                gpu=_get_str(row, "Gpu", "GPU", "gpu"),
                inches=_parse_inches(row),
                screen_res=_get_str(row, "ScreenResolution", "Screen_Resolution", "screen_resolution"),
                weight_kg=_parse_weight(row),
                price_eur=_get_price_eur(row),
            )
            out.append(nb)
    return out
