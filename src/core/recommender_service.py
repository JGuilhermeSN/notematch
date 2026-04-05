# src/core/recommender_service.py
from __future__ import annotations
from typing import List, Dict, Any, Tuple, Optional, Mapping
import math
import re

from src.core.data_loader import load_notebooks
from src.core.models import Notebook
from src.core.specs_rules import infer_specs

EUR_TO_BRL = 6.0  # taxa de câmbio - converte Euro em Real

# -----------------------------
# Helpers de normalização/tiers
# -----------------------------
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

def _gpu_label(gpu: Optional[str]) -> str:
    return "dedicada" if _has_dedicated_gpu(gpu or "") else "integrada"

def _safe_brl(price_eur: float) -> Optional[int]:
    if not price_eur or price_eur <= 0:
        return None
    return int(round(price_eur * EUR_TO_BRL))

# -----------------------------
# Elegibilidade (mínimos = mínimos)
# -----------------------------
def _is_eligible(nb: Notebook, rules: Dict[str, Any]) -> bool:
    """Hard-filter: remove itens que NÃO atendem os mínimos do perfil (L0/L1)."""
    # RAM é essencial (se faltou ou ficou abaixo, sai)
    if nb.ram_gb is None or nb.ram_gb <= 0:
        return False
    if nb.ram_gb < int(rules.get("min_ram_gb", 8) or 8):
        return False

    # CPU é essencial (se faltou ou não atingiu o tier, sai)
    if not (nb.cpu or "").strip():
        return False
    if _cpu_tier(nb.cpu) < int(rules.get("min_cpu_tier", 3) or 3):
        return False

    # GPU dedicada: só exigir quando o perfil pede explicitamente
    if bool(rules.get("needs_dedicated_gpu", False)):
        if not _has_dedicated_gpu(nb.gpu):
            return False

    # Orçamento também é "hard" quando houver teto/piso (senão distorce o top-3)
    price_brl = _safe_brl(nb.price_eur)
    teto = rules.get("budget_brl")
    piso = rules.get("budget_floor_brl")

    if teto and (price_brl is not None) and price_brl > float(teto):
        return False
    if piso and (price_brl is not None) and price_brl < float(piso):
        return False

    return True

# -----------------------------------
# Score com breakdown (explicabilidade)
# -----------------------------------
def _score(nb: Notebook, rules: Dict[str, Any], budget_brl: Optional[float], budget_floor_brl: Optional[float] = None) -> Tuple[float, List[str], Optional[int], List[Dict[str, Any]]]:
    """
    Retorna:
      score: float
      reasons: lista textual curta (compatibilidade com código anterior)
      price_brl: preço convertido
      score_parts: breakdown estruturado [{'crit': 'RAM', 'delta': +1.0}, ...]
    """
    reasons: List[str] = []
    score_parts: List[Dict[str, Any]] = []
    score = 0.0

    # RAM
    if nb.ram_gb >= rules["min_ram_gb"]:
        score += 1.0
        score_parts.append({"crit": "RAM", "delta": +1.0, "why": f"RAM ≥ {rules['min_ram_gb']}GB"})
        reasons.append(f"RAM ≥ {rules['min_ram_gb']}GB")

    # CPU
    if _cpu_tier(nb.cpu) >= rules["min_cpu_tier"]:
        score += 1.0
        score_parts.append({"crit": "CPU", "delta": +1.0, "why": "CPU atende/min exigida"})
        reasons.append("CPU adequada")

    # GPU
    if rules["needs_dedicated_gpu"]:
        if _has_dedicated_gpu(nb.gpu):
            score += 1.0
            score_parts.append({"crit": "GPU", "delta": +1.0, "why": "GPU dedicada exigida"})
            reasons.append("GPU dedicada")
        else:
            score -= 0.5
            score_parts.append({"crit": "GPU", "delta": -0.5, "why": "Exigia dedicada; item tem integrada"})
            reasons.append("GPU integrada")
    else:
        # bonificação pequena por ter dedicada mesmo não sendo requisito
        if _has_dedicated_gpu(nb.gpu):
            score += 0.5
            score_parts.append({"crit": "GPU", "delta": +0.5, "why": "Dedicada opcional (melhora desempenho gráfico)"})


    # Orçamento (teto e/ou piso)
    price_brl = _safe_brl(nb.price_eur)

    budget_ceiling = budget_brl
    budget_floor = budget_floor_brl if budget_floor_brl else rules.get("budget_floor_brl")

    if (budget_ceiling or budget_floor) and price_brl is not None:
        # --- teto (faixas "até" / "x - y")
        if budget_ceiling:
            if price_brl <= budget_ceiling:
                # quanto mais próximo do teto, mais ponto (sem exagero)
                proximity = 1.0 - (budget_ceiling - price_brl) / max(budget_ceiling, 1)
                proximity = max(0.0, min(1.0, proximity))
                score += proximity
                score_parts.append({"crit": "Preço (teto)", "delta": +proximity, "why": "Dentro do orçamento"})
                reasons.append(f"Preço dentro do orçamento (≈ R$ {price_brl:,})".replace(",", "."))
            else:
                over = (price_brl - budget_ceiling) / max(budget_ceiling, 1)
                penal = min(1.5, over)
                score -= penal
                score_parts.append({"crit": "Preço (teto)", "delta": -penal, "why": "Acima do orçamento"})
                reasons.append(f"Acima do orçamento (≈ R$ {price_brl:,})".replace(",", "."))

        # --- piso (opção "Acima de R$ ...")
        if budget_floor:
            if price_brl < budget_floor:
                under = (budget_floor - price_brl) / max(budget_floor, 1)
                penal = min(1.0, under)
                score -= penal
                score_parts.append({"crit": "Preço (piso)", "delta": -penal, "why": "Abaixo do piso do orçamento"})
            else:
                bonus = 0.25
                score += bonus
                score_parts.append({"crit": "Preço (piso)", "delta": +bonus, "why": "Atende o piso do orçamento"})

    return score, reasons, price_brl, score_parts

# -----------------------------
# Diversificação simples por marca/tela
# -----------------------------
def _diversify_topk(items: List[Tuple[float, Notebook, List[str], Optional[int], List[Dict[str, Any]]]], k: int) -> List[Tuple[float, Notebook, List[str], Optional[int], List[Dict[str, Any]]]]:
    out: List[Tuple[float, Notebook, List[str], Optional[int], List[Dict[str, Any]]]] = []
    seen: set[tuple] = set()
    for s, nb, r, p, sp in items:
        key = (nb.company, round(nb.inches or 0))
        if key in seen and len(out) < k - 1:
            continue
        seen.add(key)
        out.append((s, nb, r, p, sp))
        if len(out) >= k:
            break
    return out

# -----------------------------
# Explicação (sempre ativa)
# -----------------------------
def _status_num(val: float | int | None, min_required: float | int | None) -> str:
    if val is None or min_required is None:
        return "indefinido"
    try:
        return "atingido" if float(val) >= float(min_required) else "abaixo"
    except Exception:
        return "indefinido"

def _contrast_lines(curr: Dict[str, Any], other: Dict[str, Any] | None) -> List[str]:
    """Comparação objetiva e curta com o próximo candidato."""
    if not other:
        return []
    out: List[str] = []
    # RAM
    try:
        a, b = int(curr.get("ram_gb") or 0), int(other.get("ram_gb") or 0)
        if a != b:
            out.append(f"RAM: {a} GB vs {b} GB")
    except Exception:
        pass
    # GPU
    gl = _gpu_label(curr.get("gpu"))
    gl2 = _gpu_label(other.get("gpu"))
    if gl != gl2:
        out.append(f"GPU: {gl} vs {gl2}")
    # Preço
    pb, pb2 = curr.get("price_brl"), other.get("price_brl")
    if isinstance(pb, (int, float)) and isinstance(pb2, (int, float)) and pb != pb2:
        out.append(f"Preço: R$ {pb:,.2f} vs R$ {pb2:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    return out[:3]

def _build_explanation_dict(
    nb_dict: Dict[str, Any],
    policy_after: Dict[str, Any],
    score_parts: List[Dict[str, Any]],
    neighbor_dict: Dict[str, Any] | None,
    fallback_level: int,
    diffs: List[Dict[str, Any]]
) -> Dict[str, Any]:
    compliance: List[Dict[str, Any]] = []

    # RAM
    compliance.append({
        "crit": "RAM",
        "min": policy_after.get("min_ram_gb"),
        "val": nb_dict.get("ram_gb"),
        "status": _status_num(nb_dict.get("ram_gb"), policy_after.get("min_ram_gb")),
    })
    # CPU tier
    compliance.append({
        "crit": "CPU_tier",
        "min": policy_after.get("min_cpu_tier"),
        "val": nb_dict.get("cpu_tier"),
        "status": _status_num(nb_dict.get("cpu_tier"), policy_after.get("min_cpu_tier")),
    })
    # GPU
    if policy_after.get("needs_dedicated_gpu"):
        compliance.append({
            "crit": "GPU",
            "min": "dedicada",
            "val": _gpu_label(nb_dict.get("gpu")),
            "status": "atingido" if _gpu_label(nb_dict.get("gpu")) == "dedicada" else "abaixo",
        })
    else:
        compliance.append({
            "crit": "GPU",
            "min": "integrada ou dedicada",
            "val": _gpu_label(nb_dict.get("gpu")),
            "status": "atingido",
        })
    # Preço
    pr = nb_dict.get("price_brl")
    teto = policy_after.get("budget_brl")
    piso = policy_after.get("budget_floor_brl")

    if piso:
        compliance.append({
            "crit": "Preço (piso)",
            "min": piso,
            "val": pr,
            "status": "atingido" if (isinstance(pr, (int, float)) and pr >= piso) else "abaixo",
        })

    if teto:
        compliance.append({
            "crit": "Preço (teto)",
            "max": teto,
            "val": pr,
            "status": "abaixo_teto" if (isinstance(pr, (int, float)) and pr <= teto) else "acima",
        })


    explain = {
        "policy": {
            "min_ram_gb": policy_after.get("min_ram_gb"),
            "min_cpu_tier": policy_after.get("min_cpu_tier"),
            "needs_dedicated_gpu": policy_after.get("needs_dedicated_gpu"),
            "budget_brl": policy_after.get("budget_brl"),
            "budget_floor_brl": policy_after.get("budget_floor_brl"),
        },
        "compliance": compliance,
        "score_breakdown": score_parts,   # [{crit, delta, why}]
        "contrastive": _contrast_lines(nb_dict, neighbor_dict),
    }
    if fallback_level > 0:
        explain["relaxation"] = {"level": fallback_level, "diffs": diffs}
    return explain

# -----------------------------
# Recomendações
# -----------------------------
def recommend_topk(answers: Mapping[str, Any], k: int = 3) -> List[Dict[str, Any]]:
    """
    Gera recomendações REAIS (sem mock) a partir da base Kaggle.
    Agora com explicação sempre-ativa (explain) e fallback só quando necessário.
    """
    # 1) Política base (regras estritas do perfil)
    rules = infer_specs(answers)
    budget_brl = rules.get("budget_brl", None)
    base_rules: Dict[str, Any] = {
        "min_ram_gb": int(rules.get("min_ram_gb", 8) or 8),
        "min_cpu_tier": int(rules.get("min_cpu_tier", 3) or 3),
        "needs_dedicated_gpu": bool(rules.get("needs_dedicated_gpu", False)),
        "budget_brl": float(budget_brl) if budget_brl else None,
        "budget_floor_brl": float(rules.get("budget_floor_brl")) if rules.get("budget_floor_brl") else None,
    }

    # 2) Scoring em L0 (sem relax)
    notebooks = load_notebooks()
    scored: List[Tuple[float, Notebook, List[str], Optional[int], List[Dict[str, Any]]]] = []
    for nb in notebooks:
        if not _is_eligible(nb, base_rules):
            continue
        s, reasons, price_brl, score_parts = _score(
            nb,
            base_rules,
            base_rules["budget_brl"],
            base_rules.get("budget_floor_brl"),
        )
        scored.append((s, nb, reasons, price_brl, score_parts))

    scored.sort(key=lambda t: (-t[0], t[3] if t[3] is not None else math.inf))
    top_scored = _diversify_topk(scored, k)

    fallback_level = 0
    diffs: List[Dict[str, Any]] = []

    # 3) Caso não haja candidatos suficientes, aplicar relaxação simples (emergencial)
    # (mantida discretamente; registrada quando usada)
    if not top_scored:
        fallback_level = 1
        relaxed = dict(base_rules)
        # registrar diffs
        old_ram = relaxed["min_ram_gb"]
        old_gpu = relaxed["needs_dedicated_gpu"]

        relaxed["needs_dedicated_gpu"] = False
        relaxed["min_ram_gb"] = max(8, relaxed["min_ram_gb"] // 2)  # nunca < 8 GB

        if old_ram != relaxed["min_ram_gb"]:
            diffs.append({"param": "min_ram_gb", "from": old_ram, "to": relaxed["min_ram_gb"], "why": "fallback L1"})
        if old_gpu != relaxed["needs_dedicated_gpu"]:
            diffs.append({"param": "needs_dedicated_gpu", "from": old_gpu, "to": relaxed["needs_dedicated_gpu"], "why": "fallback L1"})

        scored = []
        for nb in notebooks:
            if not _is_eligible(nb, relaxed):
                continue
            s, reasons, price_brl, score_parts = _score(
                nb,
                relaxed,
                relaxed["budget_brl"],
                relaxed.get("budget_floor_brl"),
            )
            scored.append((s, nb, reasons, price_brl, score_parts))

        scored.sort(key=lambda t: (-t[0], t[3] if t[3] is not None else math.inf))

        # Se ainda não houver candidatos, relaxa CPU também (fallback L2)
        if not top_scored:
            fallback_level = 2
            old_cpu = relaxed["min_cpu_tier"]
            relaxed["min_cpu_tier"] = max(3, int(old_cpu) - 4)

            if old_cpu != relaxed["min_cpu_tier"]:
                diffs.append({"param": "min_cpu_tier", "from": old_cpu, "to": relaxed["min_cpu_tier"], "why": "fallback L2"})

            scored = []
            for nb in notebooks:
                if not _is_eligible(nb, relaxed):
                    continue
                s, reasons, price_brl, score_parts = _score(
                    nb,
                    relaxed,
                    relaxed["budget_brl"],
                    relaxed.get("budget_floor_brl"),
                )
                reasons.append("Relaxação de critérios (CPU)")  # auditável
                scored.append((s, nb, reasons, price_brl, score_parts))

            scored.sort(key=lambda t: (-t[0], t[3] if t[3] is not None else math.inf))
            top_scored = _diversify_topk(scored, k)
        top_scored = _diversify_topk(scored, k)

    # 4) Montagem dos resultados com EXPLICAÇÃO
    #    - policy_after = base_rules (L0) ou relaxed (L1)
    policy_after = base_rules if fallback_level == 0 else {**base_rules, **{d["param"]: d["to"] for d in diffs}}

    # vizinhos para contraste (próximo candidato no ranking)
    results: List[Dict[str, Any]] = []
    # Construir uma lista “plana” para facilitar neighbor do próximo
    flat_top: List[Dict[str, Any]] = []
    for score, nb, reasons, price_brl, score_parts in top_scored:
        flat_top.append({
            "_score": score,
            "nb": nb,
            "reasons": reasons,
            "price_brl": price_brl,
            "score_parts": score_parts
        })

    for idx, entry in enumerate(flat_top):
        nb = entry["nb"]
        price_brl = entry["price_brl"]
        nb_dict = {
            "name": nb.name,
            "company": nb.company,
            "cpu": nb.cpu,
            "cpu_tier": _cpu_tier(nb.cpu),
            "ram_gb": nb.ram_gb,
            "gpu": nb.gpu,
            "screen": _screen_short(nb),
            "price_brl": price_brl,
        }

        # próximo candidato para contraste (se houver)
        neighbor_dict = None
        if idx + 1 < len(flat_top):
            nb2 = flat_top[idx + 1]["nb"]
            neighbor_dict = {
                "ram_gb": nb2.ram_gb,
                "gpu": nb2.gpu,
                "price_brl": flat_top[idx + 1]["price_brl"],
            }

        explain = _build_explanation_dict(
            nb_dict=nb_dict,
            policy_after=policy_after,
            score_parts=entry["score_parts"],
            neighbor_dict=neighbor_dict,
            fallback_level=fallback_level,
            diffs=diffs
        )

        # manter “reasons” legadas + “explain” novo
        results.append({**nb_dict, "reasons": entry["reasons"], "explain": explain})

    return results