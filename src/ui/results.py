import flet as ft
from typing import List, Dict, Any
from src.ui.quiz_controller import quiz
from src.core.recommender_service import recommend_topk
from src.ui.app_state import set_selected

def _rating_row(value: float) -> ft.Row:
    full = int(value)
    half = 1 if value - full >= 0.5 else 0
    empty = 5 - full - half
    icons = []
    for _ in range(full):
        icons.append(ft.Icon(ft.Icons.STAR, size=18))
    if half:
        icons.append(ft.Icon(ft.Icons.STAR_HALF, size=18))
    for _ in range(empty):
        icons.append(ft.Icon(ft.Icons.STAR_BORDER, size=18))
    return ft.Row(icons, spacing=0)

def _spec_chip(text: str) -> ft.Container:
    return ft.Container(
        bgcolor=ft.Colors.with_opacity(0.08, ft.Colors.WHITE),
        padding=ft.padding.symmetric(6, 10),
        border_radius=999,
        content=ft.Text(text, size=12),
    )

def _product_card(page: ft.Page, p: Dict[str, Any]) -> ft.Card:
    chips = ft.ResponsiveRow(
        controls=[
            ft.Column(col=3, controls=[_spec_chip(p.get("cpu", ""))]),
            ft.Column(col=3, controls=[_spec_chip(f'{p.get("ram_gb", "-")}GB RAM')]),
            ft.Column(col=3, controls=[_spec_chip(p.get("storage", ""))]),
            ft.Column(col=3, controls=[_spec_chip(p.get("gpu", ""))]),
            ft.Column(col=3, controls=[_spec_chip(p.get("screen", ""))]),
        ]
)



    reasons = p.get("reasons", [])[:3]
    reasons_list = ft.Column([ft.Text(f"• {r}", size=12, opacity=0.85) for r in reasons], spacing=2)

    def open_details(_):
        set_selected(p)
        page.go("/details")

    return ft.Card(
        elevation=2,
        surface_tint_color=ft.Colors.with_opacity(0.04, ft.Colors.WHITE),
        content=ft.Container(
            padding=16,
            content=ft.Column(
                [
                    ft.Row([
                            ft.Text(p["name"], size=18, weight=ft.FontWeight.W_600),
                            ft.Container(expand=True),
                            _rating_row(float(p.get("rating", 0))),
                        ],
                        alignment=ft.MainAxisAlignment.START,
                    ),
                    ft.Row([chips]),
                    ft.Row(
                        [
                            ft.Text(
                                f'R$ {p.get("price_brl", 0):,.2f}'.replace(",", "X").replace(".", ",").replace("X", "."),
                                size=16, weight=ft.FontWeight.W_600,
                            ),
                            ft.Container(expand=True),
                            ft.ElevatedButton("Detalhes", on_click=open_details),
                        ]
                    ),
                    ft.Container(height=6),
                    reasons_list if reasons else ft.Container(),
                ],
                spacing=10,
            ),
        ),
    )

def results_view(page: ft.Page) -> ft.View:
    recs: List[Dict[str, Any]] = recommend_topk(quiz.answers, k=3)
    
    header = ft.Row(
        [
            ft.Text("Resultados", size=22, weight=ft.FontWeight.W_600),
            ft.Container(expand=True),
            ft.OutlinedButton("Refazer", on_click=lambda _: page.go("/questions")),
            ft.OutlinedButton("Home", on_click=lambda _: page.go("/homepage")),
        ]
    )

    cards = [_product_card(page, p) for p in recs]

    body = ft.Column(
        controls=[
            header,
            ft.Text("Top 3 recomendados para você:", size=14, opacity=0.85),
            *(cards if cards else [ft.Text("Nenhuma recomendação encontrada.", size=14)]),
        ],
        spacing=14,
        expand=True,
    )

    return ft.View(
        route="/results",
        scroll=ft.ScrollMode.AUTO,
        appbar=ft.AppBar(title=ft.Text("NoteMatch")),
        controls=[ft.Container(expand=True, padding=16, content=body)],
    )
