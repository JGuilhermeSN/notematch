"""Árvore de decisão para coletar requisitos do usuário."""
from typing import Dict
from src.core.engine import Question, run

__all__ = ["build_flow", "gerar_specs", "q_area_principal"]

# Perguntas de primeiro nível -------------------------------------------------

def q_area_principal() -> Question:
    return Question(
        prompt="Para que você precisa de um notebook?",
        options={
            "1": "Navegação / Uso básico",
            "2": "Estudo",
            "3": "Trabalho",
            "4": "Jogos",
        },
        next_step={
            "1": q_orcamento,
            "2": q_orcamento,
            "3": q_area_profissional,
            "4": q_orcamento,
        },
    )

# Segundo nível ---------------------------------------------------------------

def q_area_profissional() -> Question:
    return Question(
        prompt="Qual área profissional?",
        options={
            "1": "Arquitetura",
            "2": "Programação",
            "3": "Design Gráfico",
            "4": "Engenharia",
        },
        next_step={
            "1": q_atividade_arquitetura,
            "2": q_orcamento,
            "3": q_orcamento,
            "4": q_orcamento,
        },
    )

# Terceiro nível (ramificação) -----------------------------------------------

def q_atividade_arquitetura() -> Question:
    return Question(
        prompt="Qual é a principal atividade?",
        options={
            "1": "Modelagem 3D",
            "2": "Renderização",
            "3": "CAD / BIM 2D",
        },
        next_step={
            "1": q_orcamento,
            "2": q_orcamento,
            "3": q_orcamento,
        },
    )

# Pergunta final de orçamento -------------------------------------------------

def q_orcamento() -> Question:
    return Question(
        prompt="Qual faixa de orçamento?",
        options={
            "1": "Até R$ 3.000",
            "2": "R$ 3.001 – 4.000",
            "3": "R$ 4.001 – 6.000",
            "4": "Acima de R$ 6.000",
        },
        next_step={},  # termina o fluxo
    )

# Expor a primeira pergunta para integração com a UI --------------------------

def build_flow() -> Question:
    """Retorna a primeira pergunta do fluxo."""
    return q_area_principal()

# Geração simplificada de especificações --------------------------------------

def gerar_specs(respostas: Dict[str, str]) -> Dict[str, str]:
    """Mapeia respostas a requisitos mínimos."""
    specs = {
        "CPU": "Intel Core i5 / Ryzen 5",
        "RAM": "8 GB",
        "Armazenamento": "SSD 256 GB",
        "GPU": "Integrada",
        "Tela": "14″ FHD",
    }

    perfil = respostas.get("Para que você precisa de um notebook?")
    if perfil == "Trabalho" and respostas.get("Qual área profissional?") == "Arquitetura":
        atividade = respostas.get("Qual é a principal atividade?")
        if atividade in {"Modelagem 3D", "Renderização"}:
            specs.update({
                "CPU": "Intel Core i7 / Ryzen 7",
                "RAM": "16 GB",
                "GPU": "Dedicada RTX 3050 ou equivalente",
                "Armazenamento": "SSD 512 GB",
                "Tela": "15″ FHD",
            })
        elif atividade == "CAD / BIM 2D":
            specs.update({
                "GPU": "Integrada ou dedicada de entrada",
            })

    return specs

# Execução direta (opcional, útil para teste rápido) --------------------------

if __name__ == "__main__":
    respostas = run(build_flow())

    print("\n=== Resumo das respostas ===")
    for pergunta, resposta in respostas.items():
        print(f"- {pergunta} → {resposta}")

    specs = gerar_specs(respostas)
    print("\n=== Especificações mínimas sugeridas ===")
    for campo, valor in specs.items():
        print(f"{campo}: {valor}")
