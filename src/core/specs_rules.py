# src/core/specs_rules.py
from __future__ import annotations

from typing import Dict, Any, Mapping, Tuple
import re
import unicodedata


# -----------------------------
# Normalização leve (mantida só para orçamento)
# -----------------------------
def _norm(s: str) -> str:
    if not s:
        return ""
    s = s.lower()
    s = unicodedata.normalize("NFKD", s)
    return "".join(ch for ch in s if not unicodedata.combining(ch))


def _extract_brl_numbers(text: str) -> list[float]:
    nums = re.findall(r"(\d[\d\.,]{2,})", text)
    out: list[float] = []
    for raw in nums:
        try:
            out.append(float(raw.replace(".", "").replace(",", ".")))
        except Exception:
            continue
    return out


def _parse_budget_bounds_brl(text: str) -> Tuple[float | None, float | None]:
    t = _norm(text)
    nums = _extract_brl_numbers(t)

    if not nums:
        return (None, None)

    has_acima = "acima" in t
    has_range = "-" in t

    if has_acima:
        return (None, max(nums))

    return (max(nums), None)


# -----------------------------
# 🔥 REGRAS DETERMINÍSTICAS
# -----------------------------
PROFESSION_RULES: Dict[str, Dict[str, Any]] = {

    # Uso geral
    "Pesquisa acadêmica básica": {"ram": 8, "cpu": 3, "gpu": False},
    "Navegação e internet": {"ram": 8, "cpu": 3, "gpu": False},
    "Estudos escolares": {"ram": 8, "cpu": 3, "gpu": False},
    "Consumo de mídia (Netflix, YouTube)": {"ram": 8, "cpu": 3, "gpu": False},
    "Jogos leves": {"ram": 8, "cpu": 5, "gpu": True},
    "Trabalho administrativo básico": {"ram": 8, "cpu": 3, "gpu": False},

    # TI
    "Desenvolvedor Backend": {"ram": 8, "cpu": 5, "gpu": False},
    "Desenvolvedor Frontend": {"ram": 8, "cpu": 5, "gpu": False},
    "Desenvolvedor Full Stack": {"ram": 16, "cpu": 7, "gpu": False},
    "Desenvolvedor Mobile": {"ram": 8, "cpu": 5, "gpu": False},
    "Engenheiro de Software": {"ram": 16, "cpu": 7, "gpu": False},
    "Cientista de Dados": {"ram": 16, "cpu": 7, "gpu": False},
    "Analista de Dados": {"ram": 16, "cpu": 5, "gpu": False},
    "Engenheiro de Machine Learning": {"ram": 16, "cpu": 7, "gpu": False},
    "Administrador de Sistemas": {"ram": 8, "cpu": 5, "gpu": False},
    "Administrador de Redes": {"ram": 8, "cpu": 5, "gpu": False},
    "DevOps": {"ram": 16, "cpu": 7, "gpu": False},
    "Analista de Segurança da Informação": {"ram": 16, "cpu": 7, "gpu": False},

    # Engenharia
    "Engenheiro Civil": {"ram": 16, "cpu": 7, "gpu": True},
    "Engenheiro Mecânico": {"ram": 16, "cpu": 7, "gpu": True},
    "Engenheiro Elétrico": {"ram": 16, "cpu": 7, "gpu": True},
    "Engenheiro de Produção": {"ram": 8, "cpu": 5, "gpu": False},
    "Engenheiro Químico": {"ram": 16, "cpu": 7, "gpu": False},
    "Arquiteto": {"ram": 16, "cpu": 7, "gpu": True},
    "Projetista CAD": {"ram": 16, "cpu": 7, "gpu": True},
    "Modelador BIM": {"ram": 16, "cpu": 7, "gpu": True},
    "Engenheiro Estrutural": {"ram": 16, "cpu": 7, "gpu": True},

    # Design
    "Designer Gráfico": {"ram": 16, "cpu": 5, "gpu": True},
    "Designer UX/UI": {"ram": 8, "cpu": 5, "gpu": False},
    "Editor de Vídeo": {"ram": 16, "cpu": 7, "gpu": True},
    "Animador 3D": {"ram": 16, "cpu": 7, "gpu": True},
    "Motion Designer": {"ram": 16, "cpu": 7, "gpu": True},
    "Fotógrafo Profissional": {"ram": 16, "cpu": 5, "gpu": False},
    "Ilustrador Digital": {"ram": 16, "cpu": 5, "gpu": True},
    "Criador de Conteúdo (YouTube/TikTok)": {"ram": 16, "cpu": 5, "gpu": True},

    # Saúde
    "Médico Radiologista": {"ram": 8, "cpu": 5, "gpu": False},
    "Médico Clínico": {"ram": 8, "cpu": 3, "gpu": False},
    "Médico Patologista": {"ram": 16, "cpu": 7, "gpu": False},
    "Biomédico": {"ram": 16, "cpu": 5, "gpu": False},
    "Pesquisador em Biotecnologia": {"ram": 16, "cpu": 7, "gpu": False},
    "Enfermeiro (telemedicina)": {"ram": 8, "cpu": 3, "gpu": False},
    "Farmacêutico": {"ram": 8, "cpu": 3, "gpu": False},
    "Dentista": {"ram": 8, "cpu": 3, "gpu": False},

    # Educação
    "Professor Universitário": {"ram": 8, "cpu": 3, "gpu": False},
    "Pesquisador Acadêmico": {"ram": 16, "cpu": 5, "gpu": False},
    "Tutor Online": {"ram": 8, "cpu": 3, "gpu": False},
    "Instrutor de Cursos Técnicos": {"ram": 8, "cpu": 3, "gpu": False},
    "Professor do Ensino Médio": {"ram": 8, "cpu": 3, "gpu": False},
    "Estudante Universitário": {"ram": 8, "cpu": 3, "gpu": False},

    # Negócios
    "Analista de Marketing Digital": {"ram": 8, "cpu": 5, "gpu": False},
    "Gestor de E-commerce": {"ram": 8, "cpu": 5, "gpu": False},
    "Especialista em SEO": {"ram": 8, "cpu": 5, "gpu": False},
    "Analista de Dados de Mercado": {"ram": 16, "cpu": 5, "gpu": False},
    "Consultor de Negócios": {"ram": 8, "cpu": 5, "gpu": False},
    "Empreendedor": {"ram": 8, "cpu": 5, "gpu": False},
    "Gestor Financeiro": {"ram": 8, "cpu": 5, "gpu": False},
    "Analista Administrativo": {"ram": 8, "cpu": 3, "gpu": False},

    # Humanas
    "Jornalista": {"ram": 8, "cpu": 3, "gpu": False},
    "Jornalista Multimídia": {"ram": 16, "cpu": 5, "gpu": True},
    "Advogado": {"ram": 8, "cpu": 3, "gpu": False},
    "Advogado Digital": {"ram": 8, "cpu": 5, "gpu": False},
    "Psicólogo": {"ram": 8, "cpu": 3, "gpu": False},
    "Sociólogo": {"ram": 8, "cpu": 3, "gpu": False},
    "Cientista Político": {"ram": 8, "cpu": 3, "gpu": False},
    "Assistente Social": {"ram": 8, "cpu": 3, "gpu": False},

    # Zoologia
    "Veterinário": {"ram": 8, "cpu": 3, "gpu": False},
    "Zootecnista": {"ram": 8, "cpu": 3, "gpu": False},
    "Biólogo": {"ram": 8, "cpu": 3, "gpu": False},
    "Pesquisador Ambiental": {"ram": 16, "cpu": 5, "gpu": False},
    "Zoologo": {"ram": 8, "cpu": 3, "gpu": False},
}


# -----------------------------
# Função principal
# -----------------------------
def infer_specs(answers: Mapping[str, object]) -> Dict[str, Any]:
    profissao = None
    orcamento = None

    for v in answers.values():
        if v in PROFESSION_RULES:
            profissao = v
        if "R$" in str(v):
            orcamento = str(v)

    rules = PROFESSION_RULES.get(profissao, {
        "ram": 8,
        "cpu": 3,
        "gpu": False
    })

    budget_teto, budget_piso = _parse_budget_bounds_brl(orcamento or "")

    return {
        "min_ram_gb": rules["ram"],
        "min_cpu_tier": rules["cpu"],
        "needs_dedicated_gpu": rules["gpu"],
        "budget_brl": budget_teto,
        "budget_floor_brl": budget_piso,
    }