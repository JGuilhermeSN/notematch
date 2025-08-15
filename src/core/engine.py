"""Motor genérico para encadear perguntas de múltipla escolha."""
from dataclasses import dataclass, field
from typing import Dict, Callable, Optional

__all__ = ["Question", "run"]  # exporta apenas o que o restante do projeto usa

@dataclass
class Question:
    prompt: str
    options: Dict[str, str]  # chave → texto
    next_step: Dict[str, Callable[[], Optional["Question"]]] = field(default_factory=dict)

    def ask(self) -> str:
        """Exibe a pergunta no console e devolve a chave escolhida."""
        while True:
            print(f"\n{self.prompt}")
            for key, text in self.options.items():
                print(f"  [{key}] {text}")
            choice = input("Escolha: ").strip().lower()
            if choice in self.options:
                return choice
            print("Opção inválida. Tente novamente.")

def run(first_q: "Question") -> Dict[str, str]:
    """Executa o fluxo a partir da primeira pergunta e retorna o dicionário de respostas."""
    answers: Dict[str, str] = {}
    current_q: Optional[Question] = first_q
    while current_q:
        choice = current_q.ask()
        answers[current_q.prompt] = current_q.options[choice]
        next_func = current_q.next_step.get(choice)
        current_q = next_func() if next_func else None
    return answers

# Opcional: mantenha compatibilidade com código antigo
run_flow = run
