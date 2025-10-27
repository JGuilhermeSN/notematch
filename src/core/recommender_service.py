# src/core/recommender_service.py
from __future__ import annotations
from typing import List, Dict, Any, Tuple, Optional, Mapping
import math
import re

from src.core.data_loader import load_notebooks
from src.core.models import Notebook
from src.core.specs_rules import infer_specs

EUR_TO_BRL = 6.0  # mantenha sincronizado com README

def _screen_short(nb: Notebook) -> str:
    return (f'{nb.inches:.1f}" {nb.screen_res}' if nb.screen_res else f'{nb.inches:.1f}"') if nb.inches > 0 else (nb.screen_res or "—")

def _cpu_tier(cpu: str) -> int:
    s = (cpu or "").lower()
    if "i9" in s or "ryzen 9" in s or re.search(r"\br\s*9\b", s): return 9
    if "i7" in s or "ryzen 7" in s or re.search(r"\br\s*7\b", s): return 7
    if "i5" in s or "ryzen 5" in s or re.search(r"\br\s*5\b", s): return 5
    if "i3" in s or "ryzen 3" in s or re.search(r"\br\s*3\b", s): return 3
    if "m1" in s or "m2" in s or "m3" in s: return 7  # Apple Silicon
    return 1

def _has_dedicated_gpu(gpu: str) -> bool:
    g = (gpu or "").lower()
    if any(x in g for x in ["gtx", "rtx", "radeon", "rx ", "vega", "geforce"]): return True
    if "nvidia" in g and "mx" in g: return True
    return False

def _safe_brl(price_eur: float) -> Optional[int]:
    if not price_eur or price_eur <= 0:
        return None
    return int(round(price_eur * EUR_TO_BRL))

def _score(nb: Notebook, rules: Dict[str, Any], budget_brl: Optional[float]) -> Tuple[float, List[str], Optional[int]]:
    reasons: List[str] = []
    score = 0.0

    if nb.ram_gb >= rules["min_ram_gb"]:
        score += 1.0
        reasons.append(f"RAM ≥ {rules['min_ram_gb']}GB")

    if _cpu_tier(nb.cpu) >= rules["min_cpu_tier"]:
        score += 1.0
        reasons.append("CPU adequada")

    if rules["needs_dedicated_gpu"]:
        if _has_dedicated_gpu(nb.gpu):
            score += 1.0
            reasons.append("GPU dedicada")
        else:
            score -= 0.5
            reasons.append("GPU integrada")  # explicita por que perdeu

    price_brl = _safe_brl(nb.price_eur)
    if budget_brl:
        if price_brl is not None and price_brl <= budget_brl:
            # quanto mais perto do orçamento, melhor
            proximity = 1.0 - (budget_brl - price_brl) / max(budget_brl, 1)
            score += max(0.0, proximity)
            reasons.append(f"Preço dentro do orçamento (≈ R$ {price_brl:,})".replace(",", "."))
        elif price_brl is not None and price_brl > budget_brl:
            over = (price_brl - budget_brl) / budget_brl
            score -= min(1.5, over)
            reasons.append(f"Acima do orçamento (≈ R$ {price_brl:,})".replace(",", "."))

    return score, reasons, price_brl

def _diversify_topk(items: List[Tuple[float, Notebook, List[str], Optional[int]]], k: int) -> List[Tuple[float, Notebook, List[str], Optional[int]]]:
    out: List[Tuple[float, Notebook, List[str], Optional[int]]] = []
    seen: set[tuple] = set()
    for s, nb, r, p in items:
        key = (nb.company, round(nb.inches or 0))
        if key in seen and len(out) < k - 1:
            continue
        seen.add(key)
        out.append((s, nb, r, p))
        if len(out) >= k:
            break
    return out

def recommend_topk(answers: Mapping[str, Any], k: int = 3) -> List[Dict[str, Any]]:
    """Gera recomendações REAIS (sem mock) a partir da base Kaggle."""
    rules = infer_specs(answers)
    budget_brl = rules.pop("budget_brl", None)

    notebooks = load_notebooks()
    scored: List[Tuple[float, Notebook, List[str], Optional[int]]] = []
    for nb in notebooks:
        s, reasons, price_brl = _score(nb, rules, budget_brl)
        scored.append((s, nb, reasons, price_brl))

    # Ordenação primária por score desc, secundária por preço asc (quando houver)
    scored.sort(key=lambda t: (-t[0], t[3] if t[3] is not None else math.inf))
    top_scored = _diversify_topk(scored, k)

    # Se vazio, relaxa os critérios (AINDA SEM MOCK)
    if not top_scored:
        relaxed = dict(rules)
        relaxed["needs_dedicated_gpu"] = False
        relaxed["min_ram_gb"] = max(4, relaxed["min_ram_gb"] // 2)

        scored = []
        for nb in notebooks:
            s, reasons, price_brl = _score(nb, relaxed, budget_brl)
            reasons.append("Relaxação de critérios")  # auditável
            scored.append((s, nb, reasons, price_brl))
        scored.sort(key=lambda t: (-t[0], t[3] if t[3] is not None else math.inf))
        top_scored = _diversify_topk(scored, k)

    results: List[Dict[str, Any]] = []
    for _, nb, reasons, price_brl in top_scored:
        results.append({
            "name": nb.name,
            "company": nb.company,
            "cpu": nb.cpu,
            "ram_gb": nb.ram_gb,
            "gpu": nb.gpu,
            "screen": _screen_short(nb),
            "price_brl": price_brl,
            "reasons": reasons,
        })
    return results
