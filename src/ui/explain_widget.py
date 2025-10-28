# src/ui/explain_widgets.py
from __future__ import annotations
from typing import Dict, Any, List
import flet as ft

def _kv(label: str, value: str) -> ft.Row:
    return ft.Row([ft.Text(f"{label}: ", weight=ft.FontWeight.W_600), ft.Text(value)], spacing=6)

def _fmt_brl(v: Any) -> str:
    try:
        return f"R$ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "-"

def render_policy(policy: Dict[str, Any]) -> ft.Column:
    return ft.Column(spacing=4, controls=[
        _kv("RAM mínima", f"{policy.get('min_ram_gb', '-') } GB"),
        _kv("CPU (tier)", str(policy.get("min_cpu_tier", "-"))),
        _kv("GPU exigida", "dedicada" if policy.get("needs_dedicated_gpu") else "integrada ou dedicada"),
        _kv("Orçamento", _fmt_brl(policy.get("budget_brl"))),
    ])

def render_compliance(compliance: List[Dict[str, Any]]) -> ft.Column:
    items: List[ft.Control] = []
    for c in compliance or []:
        crit = c.get("crit", "?")
        status = c.get("status", "indefinido")
        if crit == "Preço":
            txt = f"{crit}: {_fmt_brl(c.get('val'))} (teto: {_fmt_brl(c.get('max'))}) → {status}"
        elif crit == "RAM":
            txt = f"{crit}: {c.get('val')} GB (mín {c.get('min')} GB) → {status}"
        elif crit == "CPU_tier":
            txt = f"{crit}: {c.get('val')} (mín {c.get('min')}) → {status}"
        else:
            txt = f"{crit}: {c.get('val')} (mín {c.get('min')}) → {status}"
        items.append(ft.Text(f"• {txt}"))
    return ft.Column(spacing=2, controls=items or [ft.Text("—")])

def render_score_breakdown(parts: List[Dict[str, Any]]) -> ft.Column:
    items: List[ft.Control] = []
    for p in parts or []:
        items.append(ft.Text(f"• {p.get('crit')}: {p.get('delta')}  — {p.get('why','')}"))
    return ft.Column(spacing=2, controls=items or [ft.Text("—")])

def render_contrastive(lines: List[str]) -> ft.Column:
    items = [ft.Text(f"• {ln}") for ln in (lines or [])]
    return ft.Column(spacing=2, controls=items or [ft.Text("—")])

def render_relaxation(relax: Dict[str, Any] | None) -> ft.Column:
    if not relax:
        return ft.Column(spacing=2, controls=[ft.Text("—")])
    level = relax.get("level", 0)
    diffs = relax.get("diffs", [])
    rows = [ft.Text(f"Nível de fallback aplicado: L{level}")]
    for d in diffs:
        rows.append(ft.Text(f"• {d.get('param')}: {d.get('from')} → {d.get('to')} ({d.get('why')})"))
    return ft.Column(spacing=2, controls=rows)

def explain_panel(explain: Dict[str, Any]) -> ft.Column:
    policy = explain.get("policy", {})
    compliance = explain.get("compliance", [])
    parts = explain.get("score_breakdown", [])
    contrast = explain.get("contrastive", [])
    relax = explain.get("relaxation")

    return ft.Column(spacing=10, controls=[
        ft.Text("Parecer Técnico", size=18, weight=ft.FontWeight.BOLD),
        ft.Text("Política aplicada", weight=ft.FontWeight.W_600),
        render_policy(policy),
        ft.Text("Atendimento por critério", weight=ft.FontWeight.W_600),
        render_compliance(compliance),
        ft.Text("Por que este entrou (score)", weight=ft.FontWeight.W_600),
        render_score_breakdown(parts),
        ft.Text("Comparado ao próximo", weight=ft.FontWeight.W_600),
        render_contrastive(contrast),
        ft.Text("Flexibilizações (se houver)", weight=ft.FontWeight.W_600),
        render_relaxation(relax),
    ])
