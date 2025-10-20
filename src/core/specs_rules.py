# src/core/specs_rules.py
from __future__ import annotations
from typing import Dict, Any, Mapping
import unicodedata

def _norm(s: str) -> str:
    if not s:
        return ""
    s = s.lower()
    s = unicodedata.normalize("NFKD", s)
    return "".join(ch for ch in s if not unicodedata.combining(ch))

def _answers_text(answers: Mapping[str, object]) -> str:
    return " ".join(_norm(str(v)) for v in answers.values())

def _has_any(text: str, kws: list[str]) -> bool:
    return any(kw in text for kw in kws)

def _rules_for_use(text: str) -> Dict[str, Any]:
    # Palavras-chave (sem acento)
    kw_prog    = ["programacao", "desenvolvedor", "dev", "ide", "backend", "frontend", "fullstack", "python", "java", "node", "c#", "c++", "golang"]
    kw_dados   = ["dados", "data science", "cientista de dados", "etl", "sql", "spark", "power bi"]
    kw_ml      = ["machine learning", "deep learning", "pytorch", "tensorflow", "treinar", "cuda"]
    kw_design  = ["design", "criacao", "photoshop", "illustrator", "figma", "ux", "ui", "lightroom"]
    kw_video   = ["edicao de video", "premiere", "after effects", "davinci", "render", "timeline", "color"]
    kw_3d      = ["3d", "modelagem", "blender", "maya", "3ds", "vray", "arnold", "zbrush"]
    kw_cad     = ["autocad", "revit", "bim", "solidworks", "catia", "inventor", "engenharia", "arquitetura"]
    kw_games   = ["jogos", "gaming", "gamer", "steam", "fps", "valorant", "fortnite", "lol"]
    kw_leve    = ["navegacao", "pesquisa", "office", "word", "excel", "powerpoint", "aulas", "estudos", "ead"]
    kw_neg     = ["negocios", "erp", "gestao", "crm", "apresentacoes"]

    needs_gpu = False
    min_cpu_tier = 5   # i5/R5 base
    min_ram = 8

    # Pesados que exigem GPU
    if _has_any(text, kw_games) or _has_any(text, kw_3d) or _has_any(text, kw_video) or _has_any(text, kw_cad):
        needs_gpu = True
        min_cpu_tier = 7
        min_ram = 16
    elif _has_any(text, kw_design):
        needs_gpu = True
        min_cpu_tier = 5
        min_ram = 16

    # Programação
    if _has_any(text, kw_prog):
        if _has_any(text, kw_ml):
            needs_gpu = True
            min_cpu_tier = max(min_cpu_tier, 7)
            min_ram = max(min_ram, 16)
        else:
            min_cpu_tier = max(min_cpu_tier, 5)
            min_ram = max(min_ram, 16)

    # Dados/analítica
    if _has_any(text, kw_dados):
        min_cpu_tier = max(min_cpu_tier, 5)
        min_ram = max(min_ram, 16)

    # Uso leve/negócios
    if _has_any(text, kw_leve) or _has_any(text, kw_neg):
        min_cpu_tier = max(min_cpu_tier, 3)
        min_ram = max(min_ram, 8)

    return {
        "min_ram_gb": int(min_ram),
        "min_cpu_tier": int(min_cpu_tier),
        "needs_dedicated_gpu": bool(needs_gpu),
    }

def infer_specs(answers: Mapping[str, object]) -> Dict[str, Any]:
    text = _answers_text(answers)
    rules = _rules_for_use(text)
    if not rules or rules.get("min_ram_gb", 0) == 0:
        rules = {"min_ram_gb": 8, "min_cpu_tier": 4, "needs_dedicated_gpu": False}
    return rules
