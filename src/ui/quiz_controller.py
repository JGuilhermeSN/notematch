from typing import Optional, Dict, Any, Callable, Union
from src.core.questions import build_flow
from src.core.engine import Question

NextRef = Union[Question, Callable[[], Optional[Question]], None]

class QuizController:
    def __init__(self):
        self.reset()

    def reset(self):
        self.first: Question = build_flow()
        self.current: Optional[Question] = self.first
        self.answers: Dict[str, str] = {}

    def _norm_key(self, k: Any) -> str:
        return str(k).strip()

    def get_prompt(self) -> str:
        return self.current.prompt if self.current else "—"

    def get_options(self) -> Dict[str, str]:
        """
        Normaliza as chaves das opções para str.
        """
        if not self.current or not self.current.options:
            return {}
        return {self._norm_key(k): v for k, v in self.current.options.items()}

    def _resolve_next(self, key_norm: str) -> Optional[Question]:
        """
        Busca no next_step usando chave normalizada e aceita:
        - callable que retorna Question,
        - Question direta,
        - None.
        """
        if not self.current or not self.current.next_step:
            return None

        # normaliza o dict de next_step para chaves str
        ns: Dict[str, NextRef] = {self._norm_key(k): v for k, v in self.current.next_step.items()}
        ref: NextRef = ns.get(key_norm)

        if ref is None:
            return None
        if callable(ref):
            return ref()
        if isinstance(ref, Question):
            return ref
        # se por acaso vier algo fora do esperado, ignora
        return None

    def answer(self, key_clicked: Any) -> bool:
        """
        Registra a resposta e avança.
        Retorna True se ainda há próxima pergunta; False se acabou.
        """
        if not self.current:
            return False

        key_norm = self._norm_key(key_clicked)
        options_norm = self.get_options()

        # Se a opção não existir (mismatch), não avança
        if key_norm not in options_norm:
            # debug opcional:
            print(f"[Quiz] key '{key_norm}' não encontrada em {list(options_norm.keys())}")
            return True  # mantém a pergunta atual

        # guarda resposta humana
        self.answers[self.current.prompt] = options_norm[key_norm]

        # resolve próxima pergunta
        nxt = self._resolve_next(key_norm)
        self.current = nxt
        return self.current is not None

# instância global
quiz = QuizController()
