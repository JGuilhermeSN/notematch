# src/core/recommender_service.py
"""
Motor de recomendação determinística de notebooks.

Fluxo principal (recommend_topk):
  1. Derivar política de requisitos mínimos a partir do perfil do usuário.
  2. Filtrar (hard-filter) e pontuar todos os notebooks elegíveis.
  3. Selecionar três perfis distintos: Ótimo, Custo-Benefício e Entrada.
  4. Aplicar fallback progressivo caso não haja candidatos suficientes.
  5. Montar e retornar os resultados enriquecidos com explicação.
"""
from __future__ import annotations

import math
import re
from typing import Any, Dict, List, Mapping, Optional, Tuple

from src.core.data_loader import load_notebooks
from src.core.models import Notebook
from src.core.specs_rules import infer_specs

# ---------------------------------------------------------------------------
# Tipos internos
# ---------------------------------------------------------------------------
_Rules  = Dict[str, Any]
_Scored = Tuple[float, float, Notebook, List[str], Optional[int], List[Dict[str, Any]]]
#               spec_s  full_s  nb        reasons    price_brl     score_parts

# ---------------------------------------------------------------------------
# Helpers de normalização
# ---------------------------------------------------------------------------
def _cpu_tier(cpu: str) -> int:
    """
    Classifica o processador em um tier de desempenho (1–9).

    Hierarquia:
      9 — Core Ultra 9, Ryzen AI 9, i9, Apple M4 / M3 Pro / M3 Max
      7 — Core Ultra 7, Core 7, Ryzen 7, i7, Apple M1–M3, Snapdragon X Elite
      5 — Core Ultra 5, Core 5, Ryzen 5, i5, Snapdragon X Plus / X
      3 — Core 3, Ryzen 3, i3
      1 — Celeron, Pentium, Athlon, MediaTek, N-series (básico / entrada)
    """
    s = (cpu or "").lower()

    # Tier 9 — workstation / flagship
    if "core ultra 9" in s:                          return 9
    if "ryzen ai 9" in s or "ryzen 9 ai" in s:       return 9
    if re.search(r"ryzen\s*9\b", s):                return 9
    if "i9" in s:                                    return 9
    if "apple" in s and ("m4" in s or "m3 max" in s or "m3 pro" in s): return 9

    # Tier 7 — alto desempenho
    if "core ultra 7" in s:                          return 7
    if re.search(r"core\s+7\b", s):                 return 7
    if re.search(r"ryzen\s*(ai\s*)?7\b", s):       return 7
    if "i7" in s:                                    return 7
    if "apple" in s and re.search(r"m[123]\b", s):  return 7
    if "snapdragon x elite" in s:                    return 7

    # Tier 5 — desempenho intermediário
    if "core ultra 5" in s:                          return 5
    if re.search(r"core\s+5\b", s):                 return 5
    if re.search(r"ryzen\s*(ai\s*)?5\b", s):       return 5
    if "i5" in s:                                    return 5
    if "snapdragon x plus" in s or "snapdragon x" in s: return 5

    # Tier 3 — entrada produtiva
    if re.search(r"ryzen\s*(ai\s*)?3\b", s):       return 3
    if re.search(r"core\s+3\b", s):                 return 3
    if "i3" in s:                                    return 3

    # Tier 1 — básico (Celeron, Pentium, Athlon, MediaTek, N-series)
    return 1

def _screen_label(nb: Notebook) -> str:
    res = f"{nb.res_width}x{nb.res_height}" if nb.res_width and nb.res_height else ""
    if nb.inches > 0:
        return f'{nb.inches:.1f}" {res}'.strip()
    return res or "—"

def _to_brl(price: float) -> Optional[int]:
    return int(round(price)) if price and price > 0 else None

# ---------------------------------------------------------------------------
# Elegibilidade (hard-filter)
# ---------------------------------------------------------------------------
def _is_eligible(nb: Notebook, rules: _Rules) -> bool:
    """Descarta notebooks que não atingem os requisitos mínimos do perfil."""
    if not nb.ram_gb or nb.ram_gb < int(rules.get("min_ram_gb", 8) or 8):
        return False
    if not (nb.cpu or "").strip() or _cpu_tier(nb.cpu) < int(rules.get("min_cpu_tier", 3) or 3):
        return False
    if rules.get("needs_dedicated_gpu") and not nb.gpu_dedicated:
        return False

    price = _to_brl(nb.price_brl)
    teto  = rules.get("budget_brl")
    piso  = rules.get("budget_floor_brl")
    if (teto or piso) and price is None:
        return False
    if teto and price > float(teto):
        return False
    if piso and price < float(piso):
        return False
    return True

# ---------------------------------------------------------------------------
# Pontuação de especificações (sem influência de preço)
#
# Utilizado para selecionar o perfil Ótimo e como numerador do Custo-Benefício.
# Aplica tetos de utilidade para evitar que specs excessivas (overkill) dominem:
#   RAM     → cap em 4× o mínimo do perfil
#   CPU     → cap em min_tier + 4 (máx 9)
#   GPU VRAM→ cap de 8 GB se dedicada exigida, 4 GB se opcional
#   Storage → cap em 1 TB
# ---------------------------------------------------------------------------
def _spec_score(nb: Notebook, rules: _Rules) -> float:
    min_ram   = int(rules.get("min_ram_gb", 8) or 8)
    min_tier  = int(rules.get("min_cpu_tier", 3) or 3)
    needs_gpu = bool(rules.get("needs_dedicated_gpu", False))
    score     = 0.0

    # RAM
    eff_ram = min(nb.ram_gb, min_ram * 4)
    if nb.ram_gb >= min_ram:
        score += 1.0 + math.log2(max(1, eff_ram / min_ram)) * 0.5

    # CPU
    tier     = _cpu_tier(nb.cpu)
    eff_tier = min(tier, min(9, min_tier + 4))
    if tier >= min_tier:
        score += 1.0 + (eff_tier - min_tier) * 0.25

    # GPU
    vram_cap = 8 if needs_gpu else 4
    if needs_gpu and nb.gpu_dedicated:
        score += 1.0 + math.log2(max(1, min(nb.gpu_vram_gb or 0, vram_cap))) * 0.2
    elif not needs_gpu and nb.gpu_dedicated:
        score += 0.5 + math.log2(max(1, min(nb.gpu_vram_gb or 0, vram_cap))) * 0.1

    # Storage
    eff_storage = min(nb.storage_gb or 0, 1024)
    if eff_storage > 0:
        score += math.log2(max(1, eff_storage / 256)) * 0.15
    if (nb.storage_type or "").upper() in ("SSD", "NVME"):
        score += 0.2

    # Avaliação do usuário
    if nb.rating and nb.rating > 0:
        score += (nb.rating / 5.0) * 0.5

    return score

# ---------------------------------------------------------------------------
# Pontuação completa (specs + orçamento)
#
# Utilizado para compor o `score_breakdown` da explicação e como desempate.
# ---------------------------------------------------------------------------
def _full_score(
    nb: Notebook,
    rules: _Rules,
    budget_ceiling: Optional[float],
    budget_floor:   Optional[float] = None,
) -> Tuple[float, List[str], Optional[int], List[Dict[str, Any]]]:
    """Retorna (score, reasons, price_brl, score_parts)."""
    score, reasons, parts = 0.0, [], []

    def _add(crit, delta, why, reason=None):
        nonlocal score
        score += delta
        parts.append({"crit": crit, "delta": delta, "why": why})
        if reason:
            reasons.append(reason)

    # RAM
    if nb.ram_gb >= rules["min_ram_gb"]:
        _add("RAM", +1.0, f"RAM ≥ {rules['min_ram_gb']} GB", f"RAM ≥ {rules['min_ram_gb']}GB")

    # CPU
    if _cpu_tier(nb.cpu) >= rules["min_cpu_tier"]:
        _add("CPU", +1.0, "CPU atende o mínimo exigido", "CPU adequada")

    # GPU
    if rules["needs_dedicated_gpu"]:
        if nb.gpu_dedicated:
            _add("GPU", +1.0, "GPU dedicada exigida", "GPU dedicada")
        else:
            _add("GPU", -0.5, "Exigia dedicada; item tem integrada", "GPU integrada")
    elif nb.gpu_dedicated:
        _add("GPU", +0.5, "Dedicada opcional (melhora desempenho gráfico)")

    # Avaliação
    if nb.rating and nb.rating > 0:
        bonus = round((nb.rating / 5.0) * 0.5, 3)
        _add("Rating", +bonus, f"Avaliação {nb.rating:.1f}/5.0")

    # Orçamento
    price = _to_brl(nb.price_brl)
    floor = budget_floor or rules.get("budget_floor_brl")

    if (budget_ceiling or floor) and price is not None:
        if budget_ceiling:
            if price <= budget_ceiling:
                proximity = max(0.0, min(1.0, 1.0 - (budget_ceiling - price) / max(budget_ceiling, 1)))
                _add("Preço (teto)", +proximity, "Dentro do orçamento",
                     f"Preço dentro do orçamento (≈ R$ {price:,})".replace(",", "."))
            else:
                penal = min(1.5, (price - budget_ceiling) / max(budget_ceiling, 1))
                _add("Preço (teto)", -penal, "Acima do orçamento",
                     f"Acima do orçamento (≈ R$ {price:,})".replace(",", "."))
        if floor:
            if price < floor:
                _add("Preço (piso)", -min(1.0, (floor - price) / max(floor, 1)), "Abaixo do piso do orçamento")
            else:
                _add("Preço (piso)", +0.25, "Atende o piso do orçamento")

    return score, reasons, price, parts

# ---------------------------------------------------------------------------
# Pipeline de pontuação
# ---------------------------------------------------------------------------
def _score_all(rule_set: _Rules) -> List[_Scored]:
    results = []
    for nb in load_notebooks():
        if not _is_eligible(nb, rule_set):
            continue
        ss = _spec_score(nb, rule_set)
        fs, reasons, price, parts = _full_score(
            nb, rule_set,
            rule_set.get("budget_brl"),
            rule_set.get("budget_floor_brl"),
        )
        results.append((ss, fs, nb, reasons, price, parts))
    return results

# ---------------------------------------------------------------------------
# Fallback progressivo
# ---------------------------------------------------------------------------
def _apply_fallback(base: _Rules, scored: List[_Scored], k: int) -> Tuple[List[_Scored], int, List[Dict]]:
    """
    Relaxa critérios progressivamente até obter ao menos k candidatos.
    Retorna (scored, fallback_level, diffs).

    L1 — remove exigência de GPU dedicada; reduz RAM mínima pela metade (mín. 8 GB).
    L2 — reduz tier mínimo de CPU em 4 pontos.
    """
    diffs: List[Dict] = []

    if len(scored) >= k:
        return scored, 0, diffs

    relaxed = dict(base)

    # L1
    for param, new_val in [
        ("needs_dedicated_gpu", False),
        ("min_ram_gb", max(8, base["min_ram_gb"] // 2)),
    ]:
        if relaxed[param] != new_val:
            diffs.append({"param": param, "from": relaxed[param], "to": new_val, "why": "fallback L1"})
            relaxed[param] = new_val

    scored = _score_all(relaxed)
    if len(scored) >= k:
        return scored, 1, diffs

    # L2
    new_tier = max(3, relaxed["min_cpu_tier"] - 4)
    if new_tier != relaxed["min_cpu_tier"]:
        diffs.append({"param": "min_cpu_tier", "from": relaxed["min_cpu_tier"], "to": new_tier, "why": "fallback L2"})
        relaxed["min_cpu_tier"] = new_tier

    scored = _score_all(relaxed)
    return scored, 2, diffs

# ---------------------------------------------------------------------------
# Seleção do trio de perfis
# ---------------------------------------------------------------------------
def _select_trio(scored: List[_Scored]) -> List[Tuple[str, str, _Scored]]:
    """
    Seleciona três notebooks distintos, um por perfil:
      Ótimo           → maior spec_score  (máxima utilidade absoluta)
      Custo-Benefício → maior spec_score / price  (eficiência por real gasto)
      Entrada         → menor preço entre os elegíveis
    """
    if not scored:
        return []

    by_spec  = sorted(scored, key=lambda t: -t[0])
    by_ratio = sorted(scored, key=lambda t: -(t[0] / t[4]) if t[4] else 0)
    by_price = sorted(scored, key=lambda t:  t[4] if t[4] is not None else math.inf)

    profiles = [
        ("otimo",           "Ótimo",           by_spec),
        ("custo_beneficio", "Custo-Benefício",  by_ratio),
        ("entrada",         "Entrada",          by_price),
    ]

    used: set[str] = set()
    result = []
    for key, label, ranking in profiles:
        pick = next((item for item in ranking if item[2].name not in used), ranking[0])
        used.add(pick[2].name)
        result.append((key, label, pick))
    return result

# ---------------------------------------------------------------------------
# Montagem da explicação
# ---------------------------------------------------------------------------
def _build_explanation(
    nb_dict:        Dict[str, Any],
    policy:         _Rules,
    score_parts:    List[Dict[str, Any]],
    neighbor:       Optional[Dict[str, Any]],
    fallback_level: int,
    diffs:          List[Dict],
) -> Dict[str, Any]:

    def _status(val, minimum) -> str:
        try:
            return "atingido" if float(val) >= float(minimum) else "abaixo"
        except (TypeError, ValueError):
            return "indefinido"

    def _contrast() -> List[str]:
        if not neighbor:
            return []
        lines = []
        a, b = nb_dict.get("ram_gb", 0), neighbor.get("ram_gb", 0)
        if a != b:
            lines.append(f"RAM: {a} GB vs {b} GB")
        ga = "dedicada" if nb_dict.get("gpu_dedicated") else "integrada"
        gb = "dedicada" if neighbor.get("gpu_dedicated") else "integrada"
        if ga != gb:
            lines.append(f"GPU: {ga} vs {gb}")
        pa, pb = nb_dict.get("price_brl"), neighbor.get("price_brl")
        if isinstance(pa, (int, float)) and isinstance(pb, (int, float)) and pa != pb:
            fmt = lambda v: f"R$ {v:,.2f}".replace(",","X").replace(".",",").replace("X",".")
            lines.append(f"Preço: {fmt(pa)} vs {fmt(pb)}")
        return lines[:3]

    compliance = [
        {"crit": "RAM",      "min": policy.get("min_ram_gb"),   "val": nb_dict.get("ram_gb"),
         "status": _status(nb_dict.get("ram_gb"), policy.get("min_ram_gb"))},
        {"crit": "CPU_tier", "min": policy.get("min_cpu_tier"), "val": nb_dict.get("cpu_tier"),
         "status": _status(nb_dict.get("cpu_tier"), policy.get("min_cpu_tier"))},
        {"crit": "GPU",
         "min": "dedicada" if policy.get("needs_dedicated_gpu") else "integrada ou dedicada",
         "val": "dedicada" if nb_dict.get("gpu_dedicated") else "integrada",
         "status": "atingido" if (not policy.get("needs_dedicated_gpu") or nb_dict.get("gpu_dedicated")) else "abaixo"},
    ]

    pr, teto, piso = nb_dict.get("price_brl"), policy.get("budget_brl"), policy.get("budget_floor_brl")
    if piso:
        compliance.append({"crit": "Preço (piso)", "min": piso, "val": pr,
                            "status": "atingido" if isinstance(pr, (int, float)) and pr >= piso else "abaixo"})
    if teto:
        compliance.append({"crit": "Preço (teto)", "max": teto, "val": pr,
                            "status": "abaixo_teto" if isinstance(pr, (int, float)) and pr <= teto else "acima"})

    explain: Dict[str, Any] = {
        "policy": {k: policy.get(k) for k in
                   ("min_ram_gb", "min_cpu_tier", "needs_dedicated_gpu", "budget_brl", "budget_floor_brl")},
        "compliance":      compliance,
        "score_breakdown": score_parts,
        "contrastive":     _contrast(),
    }
    if fallback_level > 0:
        explain["relaxation"] = {"level": fallback_level, "diffs": diffs}
    return explain

# ---------------------------------------------------------------------------
# Ponto de entrada público
# ---------------------------------------------------------------------------
def recommend_topk(answers: Mapping[str, Any], k: int = 3) -> List[Dict[str, Any]]:
    """
    Retorna k recomendações com perfis distintos.

    Cada item carrega:
      - Dados do notebook (name, company, cpu, ram_gb, gpu, screen, price_brl…)
      - category / category_key  →  identifica o perfil (Ótimo, Custo-Benefício, Entrada)
      - reasons                  →  lista textual resumida dos critérios atendidos
      - explain                  →  breakdown estruturado (policy, compliance, score, contraste)
    """
    rules = infer_specs(answers)
    base_rules: _Rules = {
        "min_ram_gb":          int(rules.get("min_ram_gb", 8) or 8),
        "min_cpu_tier":        int(rules.get("min_cpu_tier", 3) or 3),
        "needs_dedicated_gpu": bool(rules.get("needs_dedicated_gpu", False)),
        "budget_brl":          float(rules["budget_brl"]) if rules.get("budget_brl") else None,
        "budget_floor_brl":    float(rules["budget_floor_brl"]) if rules.get("budget_floor_brl") else None,
    }

    scored = _score_all(base_rules)
    scored, fallback_level, diffs = _apply_fallback(base_rules, scored, k)

    policy = base_rules if fallback_level == 0 else {
        **base_rules, **{d["param"]: d["to"] for d in diffs}
    }

    trio  = _select_trio(scored)
    flat  = [{"key": key, "label": label, "item": item} for key, label, item in trio]
    results: List[Dict[str, Any]] = []

    for idx, entry in enumerate(flat):
        key, label             = entry["key"], entry["label"]
        ss, fs, nb, reasons, price, parts = entry["item"]

        nb_dict: Dict[str, Any] = {
            "category":      label,
            "category_key":  key,
            "name":          nb.name,
            "company":       nb.company,
            "cpu":           nb.cpu,
            "cpu_tier":      _cpu_tier(nb.cpu),
            "ram_gb":        nb.ram_gb,
            "gpu":           nb.gpu,
            "gpu_dedicated": nb.gpu_dedicated,
            "gpu_vram_gb":   nb.gpu_vram_gb,
            "screen":        _screen_label(nb),
            "storage":       nb.storage,
            "storage_gb":    nb.storage_gb,
            "storage_type":  nb.storage_type,
            "os":            nb.os,
            "rating":        nb.rating,
            "warranty_years":nb.warranty_years,
            "price_brl":     price,
        }

        neighbor = None
        if idx + 1 < len(flat):
            _, _, nb2, _, price2, _ = flat[idx + 1]["item"]
            neighbor = {"ram_gb": nb2.ram_gb, "gpu_dedicated": nb2.gpu_dedicated, "price_brl": price2}

        results.append({
            **nb_dict,
            "reasons": reasons,
            "explain": _build_explanation(nb_dict, policy, parts, neighbor, fallback_level, diffs),
        })

    return results