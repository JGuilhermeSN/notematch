# src/core/specs_rules.py
'''
Função de manipulação determinística / atribui as regras referentes às especificações por categoria de uso
'''
from __future__ import annotations

from typing import Dict, Any, Mapping, Tuple
import re
import unicodedata


# -----------------------------
# Normalização leve
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
    """
    Interpreta strings de orçamento e retorna (teto, piso).

    Exemplos:
      "Até R$ 3.000"          → (3000, None)
      "R$ 2.000 - R$ 4.000"   → (4000, 2000)   ← BUG corrigido: piso não era retornado
      "Acima de R$ 5.000"     → (None, 5000)
    """
    t = _norm(text)
    nums = _extract_brl_numbers(t)

    if not nums:
        return (None, None)

    # "Acima de R$ X" → sem teto, com piso
    if "acima" in t:
        return (None, max(nums))

    # "R$ X - R$ Y" → teto = maior valor, piso = menor valor
    if "-" in t and len(nums) >= 2:
        return (max(nums), min(nums))

    # "Até R$ X" ou valor único → só teto
    return (max(nums), None)


# -----------------------------
# REGRAS DETERMINÍSTICAS
# Critérios: ram (GB), cpu (tier), gpu (dedicada?)
#
# Tiers de CPU:
#   3 = i3 / Ryzen 3   (tarefas leves)
#   5 = i5 / Ryzen 5   (produtividade, multitarefa)
#   7 = i7 / Ryzen 7   (cargas pesadas, compilação, simulação)
#   9 = i9 / Ryzen 9   (workstation, renderização profissional)
#
# Metodologia de calibração (levantamento jul/2026):
# Cada patamar é ancorado no requisito mínimo/piso realista publicado por um
# software representativo da categoria de uso — não no requisito absoluto de
# instalação do fabricante (que costuma ser artificialmente baixo), e sim no
# menor patamar em que a ferramenta é de fato utilizável para o trabalho real
# da profissão. Esse é o mesmo critério já usado para vídeo/3D/engenharia e
# foi estendido às demais categorias nesta revisão. Fontes centrais:
#   - Windows 11 24H2/26H2 (Microsoft): mínimo oficial de instalação 4 GB;
#     piso prático de uso confortável convergido por múltiplas fontes: 8 GB.
#   - Visual Studio 2026 (Microsoft): mínimo 4 GB; recomendado para "soluções
#     profissionais típicas" (Docker, múltiplos serviços locais): 16 GB.
#   - Android Studio (Google): mínimo oficial 8 GB, porém toda fonte
#     consultada (inclusive comunidade oficial de devs) converge que esse
#     patamar satura assim que o emulador é aberto; 16 GB é o piso funcional.
#   - DaVinci Resolve 21 (Blackmagic Design): piso realista para HD/4K leve
#     em 2026 é 16 GB RAM, CPU tier i7/Ryzen 7, GPU dedicada com 8 GB VRAM.
#   - Blender (Blender Foundation): 32 GB é tratado como "não opcional" para
#     uso sério (não hobby), CPU de 8 núcleos, GPU dedicada com 8 GB VRAM.
#   - Autodesk Revit 2026: requisito mínimo OFICIAL do fabricante já é
#     16 GB RAM + GPU dedicada DirectX 11 com 2-4 GB VRAM.
# -----------------------------
PROFESSION_RULES: Dict[str, Dict[str, Any]] = {

    # ------------------------------------------------------------------
    # Uso geral
    # Base: Windows 11 (piso prático de uso confortável, acima do mínimo
    # oficial de 4 GB de instalação) — não exige GPU dedicada nem CPU acima
    # do tier de entrada produtiva.
    # ------------------------------------------------------------------
    "Pesquisa acadêmica básica":            {"ram":  8, "cpu": 3, "gpu": False},
    "Navegação e internet":                 {"ram":  8, "cpu": 3, "gpu": False},
    "Estudos escolares":                    {"ram":  8, "cpu": 3, "gpu": False},
    "Consumo de mídia (Netflix, YouTube)":  {"ram":  8, "cpu": 3, "gpu": False},
    "Trabalho administrativo básico":       {"ram":  8, "cpu": 3, "gpu": False},

    # Jogos leves — 16 GB para suportar títulos modernos sem travar
    "Jogos leves":                          {"ram": 16, "cpu": 5, "gpu": True},

    # ------------------------------------------------------------------
    # TI / Desenvolvimento
    # ------------------------------------------------------------------

    # Backend — IDE completa + containers (Docker) + banco de dados local
    # rodando ao mesmo tempo; 8 GB não sustenta esse conjunto em 2026
    # (Visual Studio 2026 recomenda 16 GB para esse perfil de uso).
    "Desenvolvedor Backend":                {"ram": 16, "cpu": 5, "gpu": False},

    # Frontend — editor leve (VS Code) + bundler + navegador; carga bem
    # menor que backend, sem containers/banco local. 8 GB permanece
    # suficiente para esse escopo.
    "Desenvolvedor Frontend":               {"ram":  8, "cpu": 5, "gpu": False},

    "Desenvolvedor Full Stack":             {"ram": 16, "cpu": 7, "gpu": False},

    # Mobile — Android Studio + emulador ligado consome sozinho de 6-8 GB;
    # 8 GB satura, 16 GB é o piso onde o fluxo real (IDE + emulador +
    # navegador) funciona sem swap constante.
    "Desenvolvedor Mobile":                 {"ram": 16, "cpu": 5, "gpu": False},

    "Engenheiro de Software":               {"ram": 16, "cpu": 7, "gpu": False},

    # Ciência/Análise de dados — GPU para bibliotecas como PyTorch, RAPIDS
    "Cientista de Dados":                   {"ram": 16, "cpu": 7, "gpu": True},
    "Analista de Dados":                    {"ram": 16, "cpu": 5, "gpu": False},

    # ML Engineer — GPU é requisito para treino e inferência locais
    "Engenheiro de Machine Learning":       {"ram": 32, "cpu": 7, "gpu": True},

    "Administrador de Sistemas":            {"ram":  8, "cpu": 5, "gpu": False},
    "Administrador de Redes":               {"ram":  8, "cpu": 5, "gpu": False},
    "DevOps":                               {"ram": 16, "cpu": 7, "gpu": False},
    "Analista de Segurança da Informação":  {"ram": 16, "cpu": 7, "gpu": False},

    # ------------------------------------------------------------------
    # Engenharia
    # Base: Autodesk Revit 2026 — requisito mínimo OFICIAL do próprio
    # fabricante já é 16 GB RAM + GPU dedicada (DirectX 11, 2-4 GB VRAM);
    # AutoCAD segue o mesmo patamar para os demais pacotes CAD/BIM.
    # ------------------------------------------------------------------
    "Engenheiro Civil":                     {"ram": 16, "cpu": 7, "gpu": True},
    "Engenheiro Mecânico":                  {"ram": 16, "cpu": 7, "gpu": True},
    "Engenheiro Elétrico":                  {"ram": 16, "cpu": 7, "gpu": True},
    "Engenheiro de Produção":               {"ram":  8, "cpu": 5, "gpu": False},

    # Químico — simulações moleculares (Gaussian, LAMMPS, GROMACS) usam GPU
    "Engenheiro Químico":                   {"ram": 16, "cpu": 7, "gpu": True},

    "Arquiteto":                            {"ram": 16, "cpu": 7, "gpu": True},
    "Projetista CAD":                       {"ram": 16, "cpu": 7, "gpu": True},
    "Modelador BIM":                        {"ram": 16, "cpu": 7, "gpu": True},
    "Engenheiro Estrutural":                {"ram": 16, "cpu": 7, "gpu": True},

    # ------------------------------------------------------------------
    # Design / Criação de conteúdo
    # Base: DaVinci Resolve 21 (piso realista HD/4K leve = 16 GB, CPU
    # tier7, GPU dedicada 8 GB VRAM) e Blender (32 GB "não opcional" para
    # 3D sério, CPU de 8 núcleos, GPU dedicada 8 GB VRAM).
    # ------------------------------------------------------------------
    "Designer Gráfico":                     {"ram": 16, "cpu": 5, "gpu": True},
    "Designer UX/UI":                       {"ram":  8, "cpu": 5, "gpu": False},
    "Editor de Vídeo":                      {"ram": 16, "cpu": 7, "gpu": True},

    # Animação 3D — 32 GB não é mais opcional para cenas complexas (Blender)
    "Animador 3D":                          {"ram": 32, "cpu": 7, "gpu": True},

    "Motion Designer":                      {"ram": 16, "cpu": 7, "gpu": True},
    "Fotógrafo Profissional":               {"ram": 16, "cpu": 5, "gpu": False},
    "Ilustrador Digital":                   {"ram": 16, "cpu": 5, "gpu": True},

    # Criador de conteúdo — edição de vídeo para YouTube/TikTok exige GPU
    "Criador de Conteúdo (YouTube/TikTok)": {"ram": 16, "cpu": 5, "gpu": True},

    # Jornalista Multimídia — edição básica de foto/vídeo; GPU integrada suficiente
    "Jornalista Multimídia":                {"ram": 16, "cpu": 5, "gpu": False},

    # ------------------------------------------------------------------
    # Saúde
    # ------------------------------------------------------------------
    "Médico Radiologista":                  {"ram":  8, "cpu": 5, "gpu": False},
    "Médico Clínico":                       {"ram":  8, "cpu": 3, "gpu": False},

    # Patologista — visualização de lâminas digitais; i5 e 8 GB são suficientes
    "Médico Patologista":                   {"ram":  8, "cpu": 5, "gpu": False},

    "Biomédico":                            {"ram": 16, "cpu": 5, "gpu": False},
    "Pesquisador em Biotecnologia":         {"ram": 16, "cpu": 7, "gpu": False},
    "Enfermeiro (telemedicina)":            {"ram":  8, "cpu": 3, "gpu": False},
    "Farmacêutico":                         {"ram":  8, "cpu": 3, "gpu": False},
    "Dentista":                             {"ram":  8, "cpu": 3, "gpu": False},

    # ------------------------------------------------------------------
    # Educação
    # ------------------------------------------------------------------
    "Professor Universitário":              {"ram":  8, "cpu": 3, "gpu": False},
    "Pesquisador Acadêmico":                {"ram": 16, "cpu": 5, "gpu": False},
    "Tutor Online":                         {"ram":  8, "cpu": 3, "gpu": False},
    "Instrutor de Cursos Técnicos":         {"ram":  8, "cpu": 3, "gpu": False},
    "Professor do Ensino Médio":            {"ram":  8, "cpu": 3, "gpu": False},
    "Estudante Universitário":              {"ram":  8, "cpu": 3, "gpu": False},

    # ------------------------------------------------------------------
    # Negócios
    # ------------------------------------------------------------------
    "Analista de Marketing Digital":        {"ram":  8, "cpu": 5, "gpu": False},
    "Gestor de E-commerce":                 {"ram":  8, "cpu": 5, "gpu": False},
    "Especialista em SEO":                  {"ram":  8, "cpu": 5, "gpu": False},
    "Analista de Dados de Mercado":         {"ram": 16, "cpu": 5, "gpu": False},
    "Consultor de Negócios":                {"ram":  8, "cpu": 5, "gpu": False},
    "Empreendedor":                         {"ram":  8, "cpu": 5, "gpu": False},
    "Gestor Financeiro":                    {"ram":  8, "cpu": 5, "gpu": False},
    "Analista Administrativo":              {"ram":  8, "cpu": 3, "gpu": False},

    # ------------------------------------------------------------------
    # Humanas / Direito / Social
    # ------------------------------------------------------------------
    "Jornalista":                           {"ram":  8, "cpu": 3, "gpu": False},
    "Advogado":                             {"ram":  8, "cpu": 3, "gpu": False},
    "Advogado Digital":                     {"ram":  8, "cpu": 5, "gpu": False},
    "Psicólogo":                            {"ram":  8, "cpu": 3, "gpu": False},
    "Sociólogo":                            {"ram":  8, "cpu": 3, "gpu": False},
    "Cientista Político":                   {"ram":  8, "cpu": 3, "gpu": False},
    "Assistente Social":                    {"ram":  8, "cpu": 3, "gpu": False},

    # ------------------------------------------------------------------
    # Biologia / Meio ambiente / Veterinária
    # ------------------------------------------------------------------
    "Veterinário":                          {"ram":  8, "cpu": 3, "gpu": False},
    "Zootecnista":                          {"ram":  8, "cpu": 3, "gpu": False},
    "Biólogo":                              {"ram":  8, "cpu": 3, "gpu": False},
    "Pesquisador Ambiental":                {"ram": 16, "cpu": 5, "gpu": False},
    "Zoologo":                              {"ram":  8, "cpu": 3, "gpu": False},
}


# -----------------------------
# Função principal - esta função coleta a profissão escolhida pelo usuário e faz uma iteração na "PROFESSION_RULES", coletando o nome da profissão e suas specs.
# 
# -----------------------------
def infer_specs(answers: Mapping[str, object]) -> Dict[str, Any]:
    profissao = None
    orcamento = None

    for v in answers.values():
        if v in PROFESSION_RULES:
            profissao = v
        if "R$" in str(v):
            orcamento = str(v)

    rules = PROFESSION_RULES.get(profissao, { # Busca no dict os valores da profissão selecionada, caso não encontrar, usará os valores padrão setados (fallback):
        "ram": 8,
        "cpu": 3,
        "gpu": False,
    })

    budget_teto, budget_piso = _parse_budget_bounds_brl(orcamento or "")

    return {
        "min_ram_gb":         rules["ram"],
        "min_cpu_tier":       rules["cpu"],
        "needs_dedicated_gpu": rules["gpu"],
        "budget_brl":         budget_teto,
        "budget_floor_brl":   budget_piso,
    }