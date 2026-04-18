# src/ui/results.py
from __future__ import annotations
import traceback
import flet as ft
from typing import List, Dict, Any

from src.ui.quiz_controller import quiz
from src.core.recommender_service import recommend_topk
from src.ui.app_state import set_selected
from src.ui.explain_widget import explain_panel

CLASS_LABELS = ["Ótimo", "Custo-Benefício", "Entrada"]
CLASS_COLORS = [ft.Colors.GREEN_400, ft.Colors.BLUE_400, ft.Colors.ORANGE_400]


def _rating_row(value: float | int | None) -> ft.Control:
    try:
        v = float(value or 0)
    except Exception:
        v = 0.0

    if v <= 0:
        return ft.Container()

    full = int(v)
    half = 1 if v - full >= 0.5 else 0
    empty = max(0, 5 - full - half)

    icons: List[ft.Control] = []
    for _ in range(full):
        icons.append(ft.Icon(ft.Icons.STAR, size=18))
    if half:
        icons.append(ft.Icon(ft.Icons.STAR_HALF, size=18))
    for _ in range(empty):
        icons.append(ft.Icon(ft.Icons.STAR_OUTLINE, size=18))

    return ft.Row(icons, spacing=2)


def _spec_chip(text: str | None) -> ft.Control | None:
    s = (text or "").strip()
    if not s:
        return None
    return ft.Container(
        bgcolor=ft.Colors.with_opacity(0.08, ft.Colors.WHITE),
        padding=ft.padding.symmetric(vertical=6, horizontal=10),
        border_radius=999,
        content=ft.Text(s, size=12),
    )


def _format_price_brl(v: Any) -> str:
    try:
        f = float(v or 0)
    except Exception:
        f = 0.0
    return f"R$ {f:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _fallback_chip(p: Dict[str, Any]) -> ft.Control:
    relax = (p.get("explain") or {}).get("relaxation")
    if not relax:
        return ft.Container()

    level = relax.get("level", 0)
    return ft.Container(
        bgcolor=ft.Colors.with_opacity(0.10, ft.Colors.AMBER),
        padding=ft.padding.symmetric(4, 8),
        border_radius=999,
        content=ft.Row(
            spacing=6,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Icon(ft.Icons.TUNE, size=14),
                ft.Text(f"fallback L{level}", size=12),
            ],
        ),
    )


def _class_chip(label: str, color: ft.Colors) -> ft.Control:
    return ft.Container(
        bgcolor=ft.Colors.with_opacity(0.15, color),
        padding=ft.padding.symmetric(vertical=4, horizontal=8),
        border_radius=999,
        content=ft.Text(
            label,
            size=12,
            weight=ft.FontWeight.W_600,
            color=color,
        ),
    )


def _product_card(page: ft.Page, p: Dict[str, Any], class_label: str, class_color: ft.Colors) -> ft.Card:

    chips_controls: List[ft.Control] = []

    cpu_chip = _spec_chip(p.get("cpu", ""))
    if cpu_chip:
        chips_controls.append(cpu_chip)

    ram_val = p.get("ram_gb", None)
    ram_chip = _spec_chip(f"{ram_val}GB RAM" if ram_val not in (None, "", "-") else "")
    if ram_chip:
        chips_controls.append(ram_chip)

    storage_chip = _spec_chip(p.get("storage", ""))
    if storage_chip:
        chips_controls.append(storage_chip)

    gpu_chip = _spec_chip(p.get("gpu", ""))
    if gpu_chip:
        chips_controls.append(gpu_chip)

    screen_chip = _spec_chip(p.get("screen", ""))
    if screen_chip:
        chips_controls.append(screen_chip)

    chips_row = (
        ft.Row(wrap=True, spacing=8, run_spacing=8, controls=chips_controls)
        if chips_controls
        else ft.Container()
    )

    reasons: List[str] = []
    try:
        rr = p.get("reasons", []) or []
        if isinstance(rr, list):
            reasons = [str(x) for x in rr][:3]
        elif isinstance(rr, str):
            reasons = [rr]
    except Exception:
        reasons = []

    reasons_list = (
        ft.Column([ft.Text(f"• {r}", size=12, opacity=0.85) for r in reasons], spacing=2)
        if reasons
        else ft.Container()
    )

    explain_data = p.get("explain") or {}

    dlg = ft.AlertDialog(
        modal=True,
        content=ft.Container(
            content=explain_panel(explain_data),
            width=560,
            padding=10,
        ),
        actions_alignment=ft.MainAxisAlignment.END,
    )

    def close_dialog():
        dlg.open = False
        page.update()

    dlg.actions = [
        ft.TextButton("Fechar", on_click=lambda e: close_dialog())
    ]

    if dlg not in page.overlay:
        page.overlay.append(dlg)

    def open_explain(_):
        dlg.open = True
        page.update()

    def open_details(_):
        set_selected(p)
        page.go("/details")

    return ft.Card(
        elevation=2,
        content=ft.Container(
            padding=16,
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Text(
                                str(p.get("name", "—")),
                                size=18,
                                weight=ft.FontWeight.W_600,
                                max_lines=1,
                                overflow=ft.TextOverflow.ELLIPSIS,
                            ),
                            ft.Container(expand=True),
                            _class_chip(class_label, class_color),
                            _fallback_chip(p),
                        ],
                    ),

                    chips_row,

                    ft.Column(
                        [
                            ft.Text(
                                _format_price_brl(p.get("price_brl", 0)),
                                size=16,
                                weight=ft.FontWeight.W_600,
                            ),

                            ft.Row(
                                [
                                    ft.Container(
                                        expand=1,
                                        content=ft.TextButton(
                                            "Por que este?",
                                            on_click=open_explain,
                                        ),
                                    ),
                                    ft.Container(
                                        expand=1,
                                        content=ft.Button(
                                            "Detalhes",
                                            on_click=open_details,
                                            height=36,
                                        ),
                                    ),
                                ],
                                spacing=10,
                            ),
                        ],
                        spacing=8,
                    ),

                    ft.Container(height=6),

                    reasons_list,
                ],
                spacing=10,
            ),
        ),
    )


def results_view(page: ft.Page) -> ft.View:

    recs: List[Dict[str, Any]] = []
    error_text: str | None = None

    try:
        recs = recommend_topk(quiz.answers, k=3)
        if not isinstance(recs, list):
            recs = []
    except Exception as e:
        traceback.print_exc()
        error_text = f"Falha ao gerar recomendações: {e}"

    header = ft.Row(
        [
            ft.Text("Resultados", size=22, weight=ft.FontWeight.W_600),
            ft.Container(expand=True),
            ft.OutlinedButton("Refazer", on_click=lambda _: page.go("/questions")),
            ft.OutlinedButton("Home", on_click=lambda _: page.go("/homepage")),
        ]
    )

    cards: List[ft.Control] = []

    if recs:
        for idx, p in enumerate(recs):
            if isinstance(p, dict):
                label = CLASS_LABELS[idx] if idx < len(CLASS_LABELS) else "—"
                color = CLASS_COLORS[idx] if idx < len(CLASS_COLORS) else ft.Colors.GREY_400
                cards.append(_product_card(page, p, label, color))

    content_controls: List[ft.Control] = [
        header,
        ft.Text("Top 3 recomendados para você:", size=14, opacity=0.85),
    ]

    if error_text:
        content_controls.append(
            ft.Text(error_text, color=ft.Colors.RED_400, size=13, selectable=True)
        )

    if cards:
        content_controls.extend(cards)
    else:
        content_controls.append(ft.Text("Nenhuma recomendação encontrada.", size=14))

    body = ft.Column(
        controls=content_controls,
        spacing=14,
        expand=True,
    )

    return ft.View(
        route="/results",
        scroll=ft.ScrollMode.AUTO,
        appbar=ft.AppBar(title=ft.Text("NoteMatch")),
        controls=[ft.Container(expand=True, padding=16, content=body)],
    )