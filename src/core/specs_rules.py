# src/core/specs_rules.py
from __future__ import annotations
from typing import Dict, Any, Mapping
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

def _parse_budget_brl(text: str) -> float | None:
    m = re.findall(r"(\d[\d\.,]{2,})", text)
    if not m:
        return None
    try:
        v = float(m[0].replace(".", "").replace(",", "."))
        return v if v > 500 else None
    except Exception:
        return None

def infer_specs(answers: Mapping[str, object]) -> Dict[str, Any]:
    """Extrai requisitos mínimos a partir das respostas (texto livre)."""
    text = _answers_text(answers)

    needs_gpu = any(k in text for k in ["design", "arquitet", "3d", "jogo", "render", "cad", "adobe", "blender", "premiere"])
    min_ram = 16 if any(k in text for k in ["dados", "data", "ml", "machine"]) else (12 if needs_gpu else 8)
    min_cpu = 7 if any(k in text for k in ["dados", "ml", "render", "video"]) else (5 if any(k in text for k in ["dev", "program", "codigo"]) else 3)

    budget_brl = _parse_budget_brl(text)

    return {
        "min_ram_gb": int(min_ram),
        "min_cpu_tier": int(min_cpu),
        "needs_dedicated_gpu": bool(needs_gpu),
        "budget_brl": budget_brl,
    }
