# src/core/recommender.py
import re
import pandas as pd
from typing import Tuple, Optional
from src.core.specs_rules import Specs

CPU_PATTERNS = {
    "i3": r"\bi3\b|\bCore i3\b",
    "i5": r"\bi5\b|\bCore i5\b",
    "i7": r"\bi7\b|\bCore i7\b",
    "i9": r"\bi9\b|\bCore i9\b",
    "Ryzen 3": r"\bRyzen\s*3\b",
    "Ryzen 5": r"\bRyzen\s*5\b",
    "Ryzen 7": r"\bRyzen\s*7\b",
    "Ryzen 9": r"\bRyzen\s*9\b",
}

def _family_from_cpu(text: str) -> str:
    if not isinstance(text, str):
        return ""
    for fam, pat in CPU_PATTERNS.items():
        if re.search(pat, text, flags=re.IGNORECASE):
            return fam
    return ""

def _meets_cpu(family: str, cpu_min: str) -> bool:
    ordem = ["i3", "i5", "i7", "i9",
             "Ryzen 3", "Ryzen 5", "Ryzen 7", "Ryzen 9"]
    # trata “i5/Ryzen 5” etc.
    alternativas = [c.strip() for c in cpu_min.split("/")]
    idx_fam = ordem.index(family) if family in ordem else -1
    idx_min = min(ordem.index(alt) for alt in alternativas if alt in ordem)
    return idx_fam >= idx_min

def _parse_ram_gb(text: str) -> Optional[int]:
    if not isinstance(text, str):
        return None
    m = re.search(r"(\d+)\s*GB", text, flags=re.IGNORECASE)
    return int(m.group(1)) if m else None

def _has_ssd_and_size(text: str, min_gb: int) -> bool:
    if not isinstance(text, str):
        return False
    has = re.search(r"SSD", text, flags=re.IGNORECASE) is not None
    if not has:
        return False
    # tenta extrair maior capacidade citada
    sizes = [int(x) for x in re.findall(r"(\d+)\s*GB", text, flags=re.IGNORECASE)]
    if not sizes:
        # casos com “1TB”
        tbs = [int(x) for x in re.findall(r"(\d+)\s*TB", text, flags=re.IGNORECASE)]
        if tbs:
            sizes = [tb * 1024 for tb in tbs]
    return max(sizes) >= min_gb if sizes else True  # se não achou número, assume SSD presente

def _gpu_is_dedicated(text: str) -> bool:
    if not isinstance(text, str):
        return False
    return re.search(r"NVIDIA|GeForce|RTX|GTX|Radeon|RX", text, flags=re.IGNORECASE) is not None

def _gpu_meets_hint(text: str, hint: Optional[str]) -> bool:
    if not hint:
        return True
    return re.search(re.escape(hint), str(text), flags=re.IGNORECASE) is not None

def _resolution_width(text: str) -> Optional[int]:
    if not isinstance(text, str):
        return None
    m = re.search(r"(\d+)\s*x\s*(\d+)", text)
    if not m:
        return None
    w = int(m.group(1))
    h = int(m.group(2))
    return max(w, h)  # garante largura “maior” mesmo se invertido

def preprocess(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["CPUFamily"] = out["Cpu"].apply(_family_from_cpu)
    out["RAM_GB"] = out["Ram"].apply(_parse_ram_gb)
    out["HasSSD"] = out["Memory"].apply(lambda s: _has_ssd_and_size(s, 1))  # só presença
    out["SSD_OK"] = out["Memory"].apply(lambda s: _has_ssd_and_size(s, 0))  # placeholder
    out["DedicatedGPU"] = out["Gpu"].apply(_gpu_is_dedicated)
    out["ScreenWidth"] = out["ScreenResolution"].apply(_resolution_width)
    # peso, polegadas, etc., se precisar:
    return out

def filter_by_specs(df: pd.DataFrame, specs: Specs) -> pd.DataFrame:
    df2 = df.copy()

    # CPU
    df2 = df2[df2["CPUFamily"].apply(lambda fam: _meets_cpu(fam, specs.cpu_min))]

    # RAM
    df2 = df2[df2["RAM_GB"].fillna(0) >= specs.ram_gb_min]

    # SSD
    df2 = df2[df2["Memory"].apply(lambda s: _has_ssd_and_size(s, specs.ssd_min_gb))]

    # GPU
    if specs.gpu_type == "dedicated":
        df2 = df2[df2["DedicatedGPU"] == True]
        if specs.gpu_min_hint:
            df2 = df2[df2["Gpu"].apply(lambda g: _gpu_meets_hint(g, specs.gpu_min_hint))]
    else:
        # se integr. aceita qualquer, mas pode excluir dedicadas muito antigas se quiser
        pass

    # Tela
    if specs.screen_min_width:
        df2 = df2[df2["ScreenWidth"].fillna(0) >= specs.screen_min_width]
    if specs.inches_min:
        df2 = df2[df2["Inches"].fillna(0) >= specs.inches_min]

    return df2

def budget_bounds(budget_str: Optional[str]) -> Tuple[Optional[float], Optional[float]]:
    if not budget_str:
        return None, None
    budget_str = budget_str.strip()
    if budget_str.startswith("Até"):
        return 0.0, 3000.0
    if "3 001 – 4 000" in budget_str or "3 001 – 4 000" in budget_str:
        return 3001.0, 4000.0
    if "4 001 – 6 000" in budget_str:
        return 4001.0, 6000.0
    if "6 000 ou mais" in budget_str:
        return 6000.0, None
    return None, None

def rank_and_pick(df: pd.DataFrame, budget_str: Optional[str], k: int = 3) -> pd.DataFrame:
    lo, hi = budget_bounds(budget_str)
    df2 = df.copy()
    if lo is not None:
        df2 = df2[df2["Price_in_euros"].notna()]
        # como a base está em euros, você pode manter sem converter
        if hi is not None:
            df2 = df2[(df2["Price_in_euros"] >= 0) & (df2["Price_in_euros"] <= 999999)]
        # aqui só ordenamos por preço crescente e, em empate, por RAM desc
    df2 = df2.sort_values(by=["Price_in_euros", "RAM_GB"], ascending=[True, False], na_position="last")
    return df2.head(k)[["Company", "Product", "Cpu", "Ram", "Memory", "Gpu", "ScreenResolution", "Inches", "Weight", "OpSys", "Price_in_euros"]]
