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
    # pega o menor índice entre as alternativas válidas
    alts_idx = [ordem.index(alt) for alt in alternativas if alt in ordem]
    if not alts_idx:
        return True  # se não reconheceu o min, seja conservador (não reprova)
    idx_min = min(alts_idx)
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
    # tenta extrair maior capacidade citada em GB/TB
    sizes = [int(x) for x in re.findall(r"(\d+)\s*GB", text, flags=re.IGNORECASE)]
    if not sizes:
        tbs = [int(x) for x in re.findall(r"(\d+)\s*TB", text, flags=re.IGNORECASE)]
        if tbs:
            sizes = [tb * 1024 for tb in tbs]
    # se não achou número, assume SSD presente (sem validar tamanho)
    return max(sizes) >= min_gb if sizes else True

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
    out["DedicatedGPU"] = out["Gpu"].apply(_gpu_is_dedicated)
    out["ScreenWidth"] = out["ScreenResolution"].apply(_resolution_width)
    # garantir Inches numérico se existir
    try:
        out["Inches"] = pd.to_numeric(out.get("Inches"), errors="coerce")
    except Exception:
        pass
    return out

def filter_by_specs(df: pd.DataFrame, specs: Specs) -> pd.DataFrame:
    df2 = df.copy()
    # CPU
    df2 = df2[df2["CPUFamily"].apply(lambda fam: _meets_cpu(fam, specs.cpu_min))]
    # RAM
    df2 = df2[df2["RAM_GB"].fillna(0) >= specs.ram_gb_min]
    # SSD (mínimo real)
    df2 = df2[df2["Memory"].apply(lambda s: _has_ssd_and_size(s, specs.ssd_min_gb))]
    # GPU
    if specs.gpu_type == "dedicated":
        df2 = df2[df2["DedicatedGPU"] == True]
        if specs.gpu_min_hint:
            df2 = df2[df2["Gpu"].apply(lambda g: _gpu_meets_hint(g, specs.gpu_min_hint))]
    else:
        # se integrada, aceita qualquer
        pass
    # Tela
    if specs.screen_min_width:
        df2 = df2[df2["ScreenWidth"].fillna(0) >= specs.screen_min_width]
    if specs.inches_min:
        df2 = df2[df2["Inches"].fillna(0) >= specs.inches_min]
    return df2

def _parse_money_span(text: str) -> Tuple[Optional[float], Optional[float]]:
    """
    Converte strings como:
      - "Até R$ 3.000"        -> (0.0, 3000.0)
      - "R$ 3.001 - 4.000"    -> (3001.0, 4000.0)
      - "Acima de R$ 6.000"   -> (6000.0, None)
    Ignora "R$", pontos e espaços.
    """
    nums = [float(n.replace(".", "")) for n in re.findall(r"\d[\d\.]*", text)]
    txt = text.strip()
    if "Acima" in txt or "ou mais" in txt:
        lo = nums[0] if nums else None
        return lo, None
    if "Até" in txt:
        hi = nums[0] if nums else None
        return 0.0, hi
    if len(nums) >= 2:
        lo, hi = nums[0], nums[1]
        return lo, hi
    return None, None

def budget_bounds(budget_str: Optional[str]) -> Tuple[Optional[float], Optional[float]]:
    if not budget_str:
        return None, None
    return _parse_money_span(budget_str)


# Conversão e orçamento

def brl_to_eur(value_brl: Optional[float], fx_brl_per_eur: float) -> Optional[float]:
    if value_brl is None:
        return None
    return value_brl / fx_brl_per_eur

def add_price_in_brl(df: pd.DataFrame, fx_brl_per_eur: float) -> pd.DataFrame:
    out = df.copy()
    if "Price_in_euros" in out.columns:
        out["Price_in_brl"] = (out["Price_in_euros"] * fx_brl_per_eur).round(2)
    return out

def filter_by_price_brl(
    df: pd.DataFrame,
    budget_str: Optional[str],
    fx_brl_per_eur: float,
) -> pd.DataFrame:
    """Filtra por faixa de preço informada em BRL, convertendo limites para EUR."""
    lo_brl, hi_brl = budget_bounds(budget_str)
    lo_eur = brl_to_eur(lo_brl, fx_brl_per_eur)
    hi_eur = brl_to_eur(hi_brl, fx_brl_per_eur)

    out = df.copy()
    out = out[out["Price_in_euros"].notna()]
    if lo_eur is not None:
        out = out[out["Price_in_euros"] >= lo_eur]
    if hi_eur is not None:
        out = out[out["Price_in_euros"] <= hi_eur]
    return out


# Ordenação e seleção 

def sort_by_price_then_ram(df: pd.DataFrame) -> pd.DataFrame:
    """Ordena por preço crescente e, em empate, por RAM decrescente."""
    cols_present = set(df.columns)
    # Garante colunas necessárias existam; se RAM_GB não existir, só ordena por preço.
    if "Price_in_euros" in cols_present and "RAM_GB" in cols_present:
        return df.sort_values(
            by=["Price_in_euros", "RAM_GB"],
            ascending=[True, False],
            na_position="last"
        )
    elif "Price_in_euros" in cols_present:
        return df.sort_values(by=["Price_in_euros"], ascending=[True], na_position="last")
    return df

def pick_top_k(df: pd.DataFrame, k: int, cols: Optional[list] = None) -> pd.DataFrame:
    """Seleciona os k primeiros; opcionalmente reduz para colunas desejadas."""
    out = df.head(k)
    if cols:
        cols = [c for c in cols if c in out.columns]
        out = out[cols]
    return out

def rank_and_pick(
    df: pd.DataFrame,
    budget_str: Optional[str],
    k: int = 3,
    fx_brl_per_eur: float = 6.0,
) -> pd.DataFrame:
    """
    Mantido por compatibilidade: apenas orquestra as funções SRP.
    1) filtra por orçamento (BRL -> EUR)
    2) ordena por preço↑ e RAM↓
    3) adiciona preço em BRL
    4) devolve top-k com colunas principais
    """
    filtered = filter_by_price_brl(df, budget_str, fx_brl_per_eur)
    ranked = sort_by_price_then_ram(filtered)
    ranked = add_price_in_brl(ranked, fx_brl_per_eur)

    cols = ["Company", "Product", "Cpu", "Ram", "Memory", "Gpu",
            "ScreenResolution", "Inches", "Weight", "OpSys",
            "Price_in_euros", "Price_in_brl"]
    return pick_top_k(ranked, k, cols)



def explain(item: pd.Series, specs: Specs) -> str:
    msgs = []

    # RAM
    ram = item.get("RAM_GB")
    if pd.notna(ram) and ram >= specs.ram_gb_min:
        msgs.append("Memória atende ao mínimo")

    # SSD (usa o mínimo real do perfil)
    mem_txt = item.get("Memory")
    if isinstance(mem_txt, str):
        if _has_ssd_and_size(mem_txt, specs.ssd_min_gb):
            msgs.append(f"Armazenamento SSD adequado (≥ {specs.ssd_min_gb} GB)")
        elif "SSD" in mem_txt.upper():
            msgs.append("SSD presente, porém abaixo do mínimo")

    # CPU
    fam = item.get("CPUFamily")
    if fam and _meets_cpu(fam, specs.cpu_min):
        msgs.append("Processador compatível")

    # GPU
    dedicated = bool(item.get("DedicatedGPU"))
    if specs.gpu_type == "dedicated":
        if dedicated:
            msgs.append("GPU dedicada presente")
        else:
            msgs.append("Sem GPU dedicada (não atende preferência)")
    else:
        msgs.append("GPU integrada aceitável para o perfil")

    # Tela
    w = item.get("ScreenWidth")
    if specs.screen_min_width and pd.notna(w) and w >= specs.screen_min_width:
        msgs.append("Resolução de tela adequada")
    inch = item.get("Inches")
    if specs.inches_min and pd.notna(inch) and inch >= specs.inches_min:
        msgs.append("Tamanho de tela adequado")

    return "; ".join(msgs) if msgs else "Atende parcialmente aos requisitos"