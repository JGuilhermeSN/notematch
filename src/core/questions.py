from typing import Dict
from src.core.engine import Question, run
from src.core.professions_loader import load_professions

# Pergunta inicial de categoria ----------------------------------------------

def q_area_categoria() -> Question:
    dados = load_professions()
    categorias = list(dados.keys())

    return Question(
        prompt="O que mais se encaixa no seu uso?",
        options={str(i+1): cat for i, cat in enumerate(categorias)},
        next_step={str(i+1): (lambda c=cat: lambda: q_profissao(c))() for i, cat in enumerate(categorias)},
    )

# Pergunta de profissões dentro da categoria --------------------------------

def q_profissao(categoria: str) -> Question:
    dados = load_professions()
    profs = dados[categoria]["subcategoria"]

    return Question(
        prompt=f"Dentro de {categoria}, o que melhor define?",
        options={str(i+1): p for i, p in enumerate(profs)},
        next_step={str(i+1): q_orcamento for i, _ in enumerate(profs)},
    )

# Pergunta final de orçamento ------------------------------------------------

def q_orcamento() -> Question:
    return Question(
        prompt="Qual faixa de orçamento?",
        options={
            "1": "Até R$ 3.000",
            "2": "R$ 3.001 - 4.000",
            "3": "R$ 4.001 - 6.000",
            "4": "Acima de R$ 6.000",
        },
        next_step={},  # fim do fluxo
    )

# Geração simplificada de specs ----------------------------------------------

def gerar_specs(respostas: Dict[str, str]) -> Dict[str, str]:
    specs = {
        "CPU": "Intel Core i5 / Ryzen 5",
        "RAM": "8 GB",
        "Armazenamento": "SSD 256 GB",
        "GPU": "Integrada",
        "Tela": "14″ FHD",
    }
    return specs

def build_flow() -> Question:
    return q_area_categoria()

if __name__ == "__main__":
    respostas = run(build_flow())
    print("\n=== Resumo das respostas ===")
    for pergunta, resposta in respostas.items():
        print(f"- {pergunta} → {resposta}")
