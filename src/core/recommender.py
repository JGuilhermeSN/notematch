# notematch/src/core/recommender.py
from typing import Dict, Any, List
import math

def _cpu_score(cpu_name: str, cpu_tier: str) -> float:
    # Heurística simples: quanto melhor a tier mínima, mais exigente.
    name = (cpu_name or "").lower()
    tiers = ["i3", "r3", "i5", "r5", "i7", "r7", "i9", "r9"]
    base = 0
    for i, t in enumerate(tiers):
        if t in name:
            base = i
            break
    target = {"i3/r3": 0, "i5/r5": 2, "i7/r7": 4, "i9/r9": 6}.get(cpu_tier.lower().replace(" ", ""), 0)
    return 1.0 + max(0, base - target) * 0.5

def _gpu_ok(gpu_name: str, gpu_required: bool) -> bool:
    if not gpu_required:
        return True
    name = (gpu_name or "").lower()
    return any(x in name for x in ["rtx", "gtx", "radeon", "arc", "rx"])

def load_dataset() -> List[Dict[str, Any]]:
       raise NotImplementedError("sem conexao com o dataset")

def filter_and_rank(rows: List[Dict[str, Any]], specs: Dict[str, Any]) -> List[Dict[str, Any]]:
    out = []
    for r in rows:
        ram = int(r.get("ram_gb", 0) or 0)
        storage = str(r.get("storage", "") or "")
        storage_gb = 0
        # heurística para extrair num de armazenamento
        for tok in storage.replace(" ", "").lower().split("+"):
            if "tb" in tok:
                try:
                    storage_gb += float(tok.replace("tb", "")) * 1024
                except:
                    pass
            elif "gb" in tok:
                try:
                    storage_gb += float(tok.replace("gb", ""))
                except:
                    pass
        ssd_ok = ("ssd" in storage.lower()) if specs.get("need_ssd") else True
        gpu_name = str(r.get("gpu", "") or "")
        price = float(r.get("price_brl", 0) or 0)
        screen = str(r.get("screen", "") or "")

        # filtros duros
        if ram < specs["min_ram_gb"]:
            continue
        if storage_gb < specs["min_storage_gb"]:
            continue
        if not ssd_ok:
            continue
        if not _gpu_ok(gpu_name, specs["gpu_required"]):
            continue
        if specs.get("budget_brl") and price and price > specs["budget_brl"]:
            continue
        if specs.get("screen_min_fhd") and ("1080" not in screen and "fhd" not in screen.lower() and "1920" not in screen):
            # se quiser ficar relax, remova este filtro
            pass

        # escore
        score = 0.0
        score += (ram - specs["min_ram_gb"]) * 0.2
        score += _cpu_score(str(r.get("cpu", "")), specs["cpu_tier"]) * 0.6
        if specs["gpu_required"]:
            score += 1.0 if _gpu_ok(gpu_name, True) else 0.0
        # quanto mais próximo do orçamento, melhor (se existir)
        if specs.get("budget_brl") and price:
            diff = max(0.0, specs["budget_brl"] - price)
            score += diff / max(1.0, specs["budget_brl"])  # normaliza

        r2 = dict(r)
        r2["_score"] = round(score, 3)
        # razões simples
        reasons = []
        if ram >= specs["min_ram_gb"]:
            reasons.append(f"RAM ≥ {specs['min_ram_gb']}GB")
        if "ssd" in storage.lower():
            reasons.append("Tem SSD")
        if specs["gpu_required"]:
            reasons.append("Possui GPU dedicada" if _gpu_ok(gpu_name, True) else "GPU não atende")
        r2["reasons"] = reasons
        out.append(r2)

    # ordena por score desc, preço asc como critério 2
    out.sort(key=lambda x: (-x["_score"], x.get("price_brl", float("inf"))))
    return out
