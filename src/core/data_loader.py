# src/core/data_loader.py
from __future__ import annotations
from pathlib import Path
import csv
import re
from typing import List, Dict, Any

from src.core.models import Notebook

DEFAULT_ENCODING = "latin1"
DEFAULT_FILENAME = "base_dados.csv"

def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]

def _default_data_path() -> Path:
    return _project_root() / "data" / DEFAULT_FILENAME

# ---------- Parsers determinísticos (sem None no retorno) ----------

def _to_float_generic(s: Any) -> float:
    """
    Conversor genérico para peso/polegadas etc.
    Aceita '1.37', '1,37', '1.370', '1,370' etc.
    """
    if s is None:
        return 0.0
    text = str(s).strip()
    if not text:
        return 0.0

    cleaned = (
        text.replace("€", "")
            .replace("R$", "")
            .replace("kg", "")
            .replace("KG", "")
            .replace("Kg", "")
            .strip()
    )

    m = re.search(r"[\d.,]+", cleaned)
    if not m:
        return 0.0
    num = m.group(0)

    if "." in num and "," in num:
        # Decide pelo último separador como decimal
        if num.rfind(".") > num.rfind(","):
            num = num.replace(",", "")
        else:
            num = num.replace(".", "").replace(",", ".")
    else:
        if "," in num:
            num = num.replace(",", ".")
    try:
        return float(num)
    except Exception:
        return 0.0

def _parse_price_eur(s: Any) -> float:
    """
    Parser específico de preço (em euros) com validação de plausibilidade.
    Tenta '1.234,56' e '1,234.56' e escolhe o plausível.
    Considera plausível na faixa [100, 10000] €.
    """
    if s is None:
        return 0.0
    raw = str(s).strip()
    if not raw:
        return 0.0

    cleaned = raw.replace("€", "").replace("R$", "").replace(" ", "")
    m = re.search(r"[\d.,]+", cleaned)
    if not m:
        return 0.0
    num = m.group(0)

    candidates = set()

    # vírgula como decimal
    a = num.replace(".", "")
    a = a.replace(",", ".")
    candidates.add(a)

    # ponto como decimal
    b = num.replace(",", "")
    candidates.add(b)

    best = 0.0
    for c in candidates:
        try:
            v = float(c)
        except Exception:
            continue
        if 100.0 <= v <= 10000.0:
            if best == 0.0 or abs(v - 1500) < abs(best - 1500):
                best = v

    if best == 0.0:
        v = _to_float_generic(num)
        if 100.0 <= v <= 10000.0:
            return v
        return 0.0
    return best

def _parse_ram_gb(s: Any) -> int:
    if s is None:
        return 0
    text = str(s)
    m = re.search(r"(\d+)\s*GB", text, flags=re.I)
    if m:
        try:
            return int(m.group(1))
        except Exception:
            return 0
    m2 = re.search(r"(\d+)", text)
    if m2:
        try:
            return int(m2.group(1))
        except Exception:
            return 0
    return 0

def _get_str(row: Dict[str, Any], *keys: str) -> str:
    for k in keys:
        v = row.get(k)
        if v is not None:
            t = str(v).strip()
            if t:
                return t
    return ""

def _get_in_inches(row: Dict[str, Any]) -> float:
    v = row.get("Inches") or row.get("inches") or row.get("Screen Size") or row.get("ScreenSize")
    return _to_float_generic(v)

def _get_weight(row: Dict[str, Any]) -> float:
    v = row.get("Weight") or row.get("weight") or row.get("Weight(kg)") or row.get("Weight_kg")
    return _to_float_generic(v)

def _get_price_eur(row: Dict[str, Any]) -> float:
    for k in (
        "Price_in_euros", "Price_euros", "Price_in_Euros",
        "price_in_euros", "price_euros",
        "Price (Euro)", "PriceEuro", "Price", "price"
    ):
        if k in row and row[k]:
            return _parse_price_eur(row[k])
    return 0.0

# ---------- API pública ----------

def load_notebooks() -> List[Notebook]:
    csv_path = _default_data_path()
    if not csv_path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {csv_path}")

    out: List[Notebook] = []
    with open(csv_path, mode="r", encoding=DEFAULT_ENCODING, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            nb = Notebook(
                name=_get_str(row, "Product", "product_name", "Model", "Name", "model"),
                company=_get_str(row, "Company", "Brand", "brand"),
                cpu=_get_str(row, "Cpu", "CPU", "cpu"),
                ram_gb=_parse_ram_gb(row.get("Ram") or row.get("RAM") or row.get("ram")),
                gpu=_get_str(row, "Gpu", "GPU", "gpu"),
                inches=_get_in_inches(row),
                screen_res=_get_str(row, "ScreenResolution", "Screen_Resolution", "screen_resolution"),
                weight_kg=_get_weight(row),
                price_eur=_get_price_eur(row),
            )
            out.append(nb)
    return out
