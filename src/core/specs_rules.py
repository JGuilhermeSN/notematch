# src/core/specs_rules.py
from __future__ import annotations

from typing import Dict, Any, Mapping, Tuple
import re
import unicodedata


def _norm(s: str) -> str:
    if not s:
        return ""
    s = s.lower()
    s = unicodedata.normalize("NFKD", s)
    return "".join(ch for ch in s if not unicodedata.combining(ch))


def _answers_text(answers: Mapping[str, object]) -> str:
    return " ".join(_norm(str(v)) for v in answers.values())


def _extract_brl_numbers(text: str) -> list[float]:
    # Captura números como: 3000, 3.000, 3.001, 10.000, 3,000
    nums = re.findall(r"(\d[\d\.,]{2,})", text)
    out: list[float] = []
    for raw in nums:
        try:
            out.append(float(raw.replace(".", "").replace(",", ".")))
        except Exception:
            continue
    return out


def _parse_budget_bounds_brl(text: str) -> Tuple[float | None, float | None]:
    """
    Retorna (teto, piso) em BRL.

    Exemplos:
      - "Até R$ 3.000"       -> (3000, None)
      - "R$ 3.001 - 4.000"   -> (4000, None)
      - "R$ 4.001 - 6.000"   -> (6000, None)
      - "Acima de R$ 6.000"  -> (None, 6000)
    """
    t = _norm(text)

    nums = _extract_brl_numbers(t)
    if not nums:
        return (None, None)

    has_acima = any(k in t for k in ["acima de", "mais de", "superior a", ">= ", ">="])
    has_ate = any(k in t for k in ["ate", "até", "ate ", "até ", "<= ", "<="])
    has_range = "-" in t or " a " in t

    if has_acima:
        piso = max(nums)
        return (None, piso)

    if has_range:
        teto = max(nums)
        return (teto, None)

    if has_ate:
        teto = max(nums)
        return (teto, None)

    teto = max(nums)
    return (teto, None)


def infer_specs(answers: Mapping[str, object]) -> Dict[str, Any]:
    """Extrai requisitos mínimos a partir das respostas (texto livre)."""
    text = _answers_text(answers)

    needs_gpu = any(
        k in text
        for k in [
            "design", "arquitet", "3d", "jogo", "render", "cad", "adobe", "blender", "premiere", "edit", "video"
        ]
    )

    min_ram = 16 if any(k in text for k in ["dados", "data", "ml", "machine"]) else (12 if needs_gpu else 8)
    min_cpu = 7 if any(k in text for k in ["dados", "ml", "render", "3d"]) else (5 if any(k in text for k in ["dev", "program", "codigo"]) else 3)

    budget_teto, budget_piso = _parse_budget_bounds_brl(text)

    return {
        "min_ram_gb": int(min_ram),
        "min_cpu_tier": int(min_cpu),
        "needs_dedicated_gpu": bool(needs_gpu),
        "budget_brl": budget_teto,          # teto (quando houver)
        "budget_floor_brl": budget_piso,    # piso (quando escolher "Acima de ...")
    }
