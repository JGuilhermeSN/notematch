# src/ui/cli_app.py
import sys
from typing import Any, Dict, List, Tuple

from src.core.recommender_service import recommend_topk
from src.core.questions import build_flow
from src.core.engine import run

# ----------------- helpers de formatação/segurança -----------------

def _fmt_brl(v: Any) -> str:
    """Formata número em BRL; se não for numérico, retorna '—'."""
    if isinstance(v, (int, float)):
        return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return "—"

def _safe_get(d: Dict[str, Any], key: str, default: str = "—") -> Any:
    try:
        v = d.get(key)
        return default if v in (None, "", "nan") else v
    except Exception:
        return default

def _print_recommendations(recs: List[Dict[str, Any]]) -> None:
    print("\n=== RECOMENDAÇÕES ===")
    seen: set[Tuple[Any, Any, Any]] = set()  # evita repetidos pelo (nome, cpu, ram)
    idx = 1
    for r in recs:
        key = (r.get("name"), r.get("cpu"), r.get("ram_gb"))
        if key in seen:
            continue
        seen.add(key)

        name  = _safe_get(r, "name")
        cpu   = _safe_get(r, "cpu")
        ram   = _safe_get(r, "ram_gb")
        gpu   = _safe_get(r, "gpu")
        scr   = _safe_get(r, "screen")
        price = _fmt_brl(r.get("price_brl"))

        ram_txt = f"{ram}GB" if isinstance(ram, (int, float)) else str(ram)
        print(f"{idx}. {name}  •  CPU: {cpu}  •  RAM: {ram_txt}  •  GPU: {gpu}  •  Tela: {scr}  •  {price}")

        reasons = r.get("reasons") or []
        if isinstance(reasons, str):
            reasons = [reasons]

        for mot in reasons:
            print(f"   - {str(mot)}")
        idx += 1
    sys.stdout.flush()

# ------------------------------- modos ------------------------------

def _selftest() -> int:
    """Roda um teste rápido, sem fluxo de perguntas, para validar o CLI."""
    print("[+] Modo selftest: chamando recommend_topk com 3 cenários...", flush=True)
    scenarios = [
        {"Qual faixa de orçamento?": "1", "Dentro de Uso geral, o que melhor define?": "Jogos"},
        {"Qual faixa de orçamento?": "4", "Dentro de Design e Criatividade, o que melhor define?": "Animador 3D"},
        {"Qual faixa de orçamento?": "2", "Dentro de Tecnologia da Informação, o que melhor define?": "Cientista de Dados"},
    ]
    for i, ans in enumerate(scenarios, start=1):
        print(f"\n[+] Cenário {i}: {ans}", flush=True)
        recs = recommend_topk(ans, k=3)
        _print_recommendations(recs)
    print("\n[+] Selftest concluído.", flush=True)
    return 0

def run_cli() -> int:
    try:
        # Modo diagnóstico opcional
        if len(sys.argv) > 1 and sys.argv[1] == "--selftest":
            return _selftest()

        print("[+] Iniciando fluxo de perguntas...", flush=True)
        # 1) Perguntas → respostas
        first_q = build_flow()
        answers = run(first_q)
        print(f"[+] Respostas coletadas: {answers}", flush=True)

        # 2) Recomendações (top-k)
        print("[+] Gerando recomendações...", flush=True)
        topk = recommend_topk(answers, k=3)

        # 3) Impressão amigável
        _print_recommendations(topk)
        return 0

    except KeyboardInterrupt:
        print("\nExecução interrompida pelo usuário.")
        return 1
    except Exception as e:
        # imprime erro no stdout também para aparecer no PowerShell
        print(f"[ERRO] {e}")
        return 2

if __name__ == "__main__":
    sys.exit(run_cli())
