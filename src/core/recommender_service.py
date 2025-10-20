# src/core/recommender_service.py
from __future__ import annotations
from typing import List, Dict, Any, Tuple, Optional, Mapping
import re

from src.core.data_loader import load_notebooks
from src.core.models import Notebook
from src.core.specs_rules import infer_specs

EUR_TO_BRL = 6.0  # ajuste se quiser

# ---------- Helpers determinísticos ----------

def _screen_short(nb: Notebook) -> str:
    if nb.inches > 0:
        inches_txt = f'{nb.inches:.1f}"'
    else:
        inches_txt = "—"
    return f'{inches_txt} {nb.screen_res}' if nb.screen_res else inches_txt

def _cpu_tier(cpu: str) -> int:
    s = (cpu or "").lower()
    if "i9" in s or "ryzen 9" in s: return 9
    if "i7" in s or "ryzen 7" in s: return 7
    if "i5" in s or "ryzen 5" in s: return 5
    if "i3" in s or "ryzen 3" in s: return 3
    if "m3" in s or "m2" in s: return 8
    if "m1" in s: return 6
    return 4

def _has_dedicated_gpu(gpu: str) -> bool:
    s = (gpu or "").lower()
    if "nvidia" in s: return True
    if "radeon" in s and "vega" not in s: return True
    return False

# ---------- Orçamento (corrigido) ----------

def _as_int_choice(v: object) -> Optional[int]:
    if isinstance(v, bool):
        return None
    if isinstance(v, int):
        return v if 1 <= v <= 4 else None
    if isinstance(v, str) and v.strip().isdigit():
        n = int(v.strip())
        return n if 1 <= n <= 4 else None
    return None

def _map_brl_to_choice(brl: int) -> int:
    if brl <= 3000: return 1
    if brl <= 4000: return 2
    if brl <= 6000: return 3
    return 4

def _parse_budget_text(txt: str) -> Optional[int]:
    """
    Interpreta textos como:
      - 'Até R$ 3.000' → 1
      - 'R$ 3.001 - 4.000' → usa o valor MAIOR (4000) → 2
      - 'Acima de R$ 6.000' → 4
      - 'R$ 4500' → 3
    """
    s = txt.lower().strip()

    # atalhos semânticos
    if "acima" in s:
        return 4
    if "ate" in s or "até" in s:
        m = re.search(r"(\d{1,3}(?:[\.,]\d{3})*|\d+)", s)
        if m:
            num = int(re.sub(r"[^\d]", "", m.group(1)))
            return _map_brl_to_choice(num)
        return 1  # sem número, assume menor faixa

    # extrai todos os números (mantendo milhar com . ou ,)
    nums = [int(re.sub(r"[^\d]", "", x)) for x in re.findall(r"(\d{1,3}(?:[\.,]\d{3})*|\d+)", s)]
    if not nums:
        return None
    brl = max(nums)  # em intervalos pega o MAIOR
    return _map_brl_to_choice(brl)

def _get_budget_choice(ans: Mapping[str, object]) -> Optional[int]:
    for k in ("budget_choice", "orcamento", "budget"):
        if k in ans:
            val = _as_int_choice(ans.get(k))
            if val is not None:
                return val
    return None

def _infer_budget_choice_from_answers(ans: Mapping[str, object]) -> Optional[int]:
    # 1) numérico direto em chaves clássicas
    val = _get_budget_choice(ans)
    if val is not None:
        return val

    # 2) numérico 1..4 em QUALQUER chave
    for v in ans.values():
        c = _as_int_choice(v)
        if c is not None:
            return c

    # 3) textos com 'orçamento', 'budget', 'preço/preco' → parse semântico
    for k, v in ans.items():
        if isinstance(v, str):
            kl = k.lower()
            if any(t in kl for t in ("orçamento", "orcamento", "budget", "preço", "preco")):
                c = _parse_budget_text(v)
                if c is not None:
                    return c
    return None

# ---------- Sanidade de preço ----------

def _price_sanity(price_eur: float) -> Tuple[float, bool]:
    if price_eur <= 0:
        return 0.0, False
    if price_eur > 10000:
        return price_eur, False
    return price_eur, True

def _safe_brl(price_eur: float) -> Optional[float]:
    p, ok = _price_sanity(price_eur)
    if not ok:
        return None
    return round(p * EUR_TO_BRL, 2)

# ---------- Diversificação ----------

def _family_key(nb: Notebook) -> tuple[str, str]:
    company = (nb.company or "").strip().lower()
    product = re.sub(r"\b(pro|plus|retina|touch\s*bar|202\d|201\d)\b", "", nb.name or "", flags=re.I).strip().lower()
    return (company, product)

def _diversify_topk(sorted_items: List[Tuple[float, Notebook, List[str]]], k: int) -> List[Tuple[float, Notebook, List[str]]]:
    seen: set[tuple[str, str]] = set()
    out: List[Tuple[float, Notebook, List[str]]] = []
    for item in sorted_items:
        key = _family_key(item[1])
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
        if len(out) >= k:
            break
    i = 0
    while len(out) < k and i < len(sorted_items):
        if sorted_items[i] not in out:
            out.append(sorted_items[i])
        i += 1
    return out

# ---------- “Especificação ideal” para fallback ----------

def _budget_hint(choice: Optional[int]) -> str:
    if choice == 1: return "até R$ 3.000"
    if choice == 2: return "R$ 3.001–4.000"
    if choice == 3: return "R$ 4.001–6.000"
    if choice == 4: return "acima de R$ 6.000"
    return "sem faixa definida"

def _specs_to_human(specs: Dict[str, Any], budget_choice: Optional[int]) -> List[str]:
    """
    Gera uma lista de bullets com recomendações de compra que independem do dataset.
    Usa as regras inferidas (CPU/RAM/GPU) + sugestões pragmáticas (SSD/tela).
    """
    lines: List[str] = []

    # CPU
    min_cpu = int(specs.get("min_cpu_tier") or 4)
    if min_cpu >= 7:
        cpu_text = "Intel Core i7 / Ryzen 7 (ou superior)"
    elif min_cpu >= 5:
        cpu_text = "Intel Core i5 / Ryzen 5 (ou superior)"
    else:
        cpu_text = "Intel Core i3 / Ryzen 3 (ou superior)"
    lines.append(f"CPU: {cpu_text}")

    # RAM
    min_ram = int(specs.get("min_ram_gb") or 8)
    lines.append(f"Memória RAM: {max(8, min_ram)} GB (preferencialmente 16 GB)")

    # GPU
    needs_gpu = bool(specs.get("needs_dedicated_gpu"))
    if needs_gpu:
        if min_cpu >= 7:
            gpu_text = "GPU dedicada (ex.: NVIDIA RTX 3050/3060 ou superior; AMD RX 6600 ou superior)"
        else:
            gpu_text = "GPU dedicada (ex.: NVIDIA GTX 1650/1660/RTX 3050; AMD RX 5600/6600)"
        lines.append(f"GPU: {gpu_text}")
    else:
        lines.append("GPU: integrada é aceitável (Iris Xe / Radeon iGPU).")

    # Armazenamento
    storage = "SSD NVMe 512 GB" if (needs_gpu or min_ram >= 16) else "SSD NVMe 256-512 GB"
    lines.append(f"Armazenamento: {storage}")

    # Tela
    screen = '15,6" Full HD (para GPU dedicada) ou 14" Full HD (mobilidade)'
    lines.append(f"Tela: {screen}")

    # Orçamento (dica de busca)
    lines.append(f"Faixa de preço alvo: { _budget_hint(budget_choice) }")

    # Extras
    lines.append("Extras recomendados: 2 slots de RAM (para upgrade), Wi-Fi 6, USB-C, boa ventilação.")
    return lines

# ---------- Scoring ----------

def _score(nb: Notebook, specs: Dict[str, Any]) -> tuple[float, List[str]]:
    reasons: List[str] = []
    score = 0.0

    # RAM
    min_ram = int(specs.get("min_ram_gb") or specs.get("ram_min") or 8)
    if nb.ram_gb >= min_ram:
        score += 2.0
        reasons.append(f"RAM ≥ {min_ram}GB")
    else:
        return -1.0, ["RAM insuficiente"]

    # GPU
    need_ded = bool(specs.get("needs_dedicated_gpu") or specs.get("gpu_dedicada"))
    has_ded = _has_dedicated_gpu(nb.gpu)
    if need_ded:
        if has_ded:
            score += 2.0
            reasons.append("GPU dedicada")
        else:
            return -1.0, ["Exige GPU dedicada"]
    else:
        if has_ded:
            score += 0.8
            reasons.append("GPU dedicada (não obrigatória)")
        else:
            score += 0.5
            reasons.append("GPU integrada aceitável")

    # CPU
    min_tier = int(specs.get("min_cpu_tier") or 5)
    if _cpu_tier(nb.cpu) >= min_tier:
        score += 1.5
        reasons.append("CPU adequada")
    else:
        reasons.append("CPU básica")

    # Peso (penaliza acima de ~1.5kg)
    if nb.weight_kg > 0:
        score += max(0.0, 0.6 - 0.1 * max(0.0, nb.weight_kg - 1.5))

    # Preço com sanidade
    price_eur_adj, reliable = _price_sanity(nb.price_eur)
    if reliable:
        score += max(0.0, 1.0 - (price_eur_adj / 2000.0))
        reasons.append("Bom custo/benefício" if price_eur_adj < 1000 else "Preço intermediário")
    else:
        reasons.append("Preço ausente/atípico no dataset")

    # Desempate determinístico
    score += (hash(nb.name) % 1000) / 100000.0

    return score, reasons

# ---------- API ----------

def _meets_budget(price_eur: float, answers: Mapping[str, object]) -> bool:
    """
    Respeita orçamento informado; ignora preços não confiáveis.
    """
    choice = _infer_budget_choice_from_answers(answers)
    p, reliable = _price_sanity(price_eur)

    if choice is None:
        return True       # sem orçamento -> não filtra
    if not reliable:
        return False      # com orçamento, preço ruim -> descarta

    if choice == 1:   # Até R$ 3.000  (~≤ €500)
        return p <= 500
    if choice == 2:   # R$ 3.001–4.000 (~€500–700)
        return 500 < p <= 700
    if choice == 3:   # R$ 4.001–6.000 (~€700–1000)
        return 700 < p <= 1000
    if choice == 4:   # Acima de R$ 6.000 (~> €1000)
        return p > 1000
    return True

def recommend_topk(answers: Dict[str, Any], k: int = 3) -> List[Dict[str, Any]]:
    """
    Gera top-k recomendações diversificadas com base nas respostas.
    Se não houver match estrito, retorna os mais próximos e, principalmente,
    uma orientação de compra com as especificações ideais para o perfil.
    """
    specs = infer_specs(answers)
    budget_choice = _infer_budget_choice_from_answers(answers)
    notebooks: List[Notebook] = load_notebooks()

    # Filtra por orçamento
    filtered = [nb for nb in notebooks if _meets_budget(nb.price_eur, answers)]
    if not filtered:
        filtered = notebooks

    scored: List[Tuple[float, Notebook, List[str]]] = []
    for nb in filtered:
        sc, rs = _score(nb, specs)
        if sc >= 0:
            scored.append((sc, nb, rs))

    # Caso não haja match estrito, devolver orientação + “mais próximos”
    if not scored:
        guidance = [
            "Não foi possível encontrar o modelo ideal na base de dados nativa.",
            "Porém, para este uso, recomendo um notebook com as seguintes configurações:"
        ] + _specs_to_human(specs, budget_choice) + [
            "Com isso, pesquise em varejistas usando essas especificações como comparativo."
        ]

        # Pega os k “menos ruins” só para ilustrar alternativas próximas
        nearby = sorted(filtered, key=lambda x: (_cpu_tier(x.cpu), x.ram_gb), reverse=True)[:k]
        return [{
            "name": nb.name,
            "cpu": nb.cpu,
            "ram_gb": nb.ram_gb,
            "gpu": nb.gpu,
            "screen": _screen_short(nb),
            "price_brl": _safe_brl(nb.price_eur),
            "reasons": guidance,
        } for nb in nearby]

    # Ordena por score e diversifica
    scored.sort(key=lambda t: t[0], reverse=True)
    top_scored = _diversify_topk(scored, k)

    results: List[Dict[str, Any]] = []
    for _, nb, reasons in top_scored:
        results.append({
            "name": nb.name,
            "cpu": nb.cpu,
            "ram_gb": nb.ram_gb,
            "gpu": nb.gpu,
            "screen": _screen_short(nb),
            "price_brl": _safe_brl(nb.price_eur),
            "reasons": reasons,
        })
    return results
