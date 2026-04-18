# notematch/src/ui/details.py
from __future__ import annotations

import flet as ft
from typing import Any

from src.ui.app_state import get_selected
from src.ui.explain_widget import explain_panel  # <- novo painel de explicação


def _fmt_brl(v: Any) -> str:
    try:
        f = float(v)
    except Exception:
        return "—"
    return f"R$ {f:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _fallback_chip(p: dict) -> ft.Control:
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


def details_view(page: ft.Page) -> ft.View:
    p = get_selected()
    if not p:
        return ft.View(
            route="/details",
            appbar=ft.AppBar(title=ft.Text("Detalhes")),
            scroll=ft.ScrollMode.AUTO,
            controls=[
                ft.Container(
                    padding=16,
                    content=ft.Column(
                        [
                            ft.Text("Nenhum item selecionado."),
                            ft.OutlinedButton("Voltar", on_click=lambda _: page.go("/results")),
                        ],
                        spacing=12,
                    ),
                )
            ],
        )

    # Tabela de especificações
    spec_table = ft.DataTable(
        columns=[ft.DataColumn(ft.Text("Atributo")), ft.DataColumn(ft.Text("Valor"))],
        rows=[
            ft.DataRow(cells=[ft.DataCell(ft.Text("Modelo")), ft.DataCell(ft.Text(p.get("name", "-")))]),
            ft.DataRow(cells=[ft.DataCell(ft.Text("CPU")), ft.DataCell(ft.Text(p.get("cpu", "-")))]),
            ft.DataRow(cells=[ft.DataCell(ft.Text("RAM")), ft.DataCell(ft.Text(f'{p.get("ram_gb", "-")} GB'))]),
            ft.DataRow(cells=[ft.DataCell(ft.Text("Armazenamento")), ft.DataCell(ft.Text(p.get("storage", "-")))]),
            ft.DataRow(cells=[ft.DataCell(ft.Text("GPU")), ft.DataCell(ft.Text(p.get("gpu", "-")))]),
            ft.DataRow(cells=[ft.DataCell(ft.Text("Tela")), ft.DataCell(ft.Text(p.get("screen", "-")))]),
            ft.DataRow(cells=[ft.DataCell(ft.Text("Preço")), ft.DataCell(ft.Text(_fmt_brl(p.get("price_brl"))))]),
        ],
    )

    # Razões legadas (curtas)
    reasons = p.get("reasons", []) or []
    reasons_list = (
        ft.Column([ft.Text(f"• {r}") for r in reasons], spacing=2)
        if reasons
        else ft.Text("—")
    )

    # Parecer Técnico (explicação sempre-ativa)
    explain = p.get("explain") or {}

    content = ft.Column(
        [
            ft.Row(
                [
                    ft.Text(p.get("name", "Detalhes"), size=22, weight=ft.FontWeight.W_600),
                    ft.Container(expand=True),
                    _fallback_chip(p),
                    ft.OutlinedButton("Resultados", on_click=lambda _: page.go("/results")),
                    ft.OutlinedButton("Home", on_click=lambda _: page.go("/homepage")),
                ],
                alignment=ft.MainAxisAlignment.START,
            ),
            spec_table,
            ft.Divider(),
            ft.Text("Por que recomendamos (resumo):", size=16, weight=ft.FontWeight.W_600),
            reasons_list,
            ft.Divider(),
            explain_panel(explain),  # <- Parecer Técnico completo
        ],
        spacing=16,
    )

    return ft.View(
        route="/details",
        appbar=ft.AppBar(title=ft.Text("Detalhes")),
        scroll=ft.ScrollMode.AUTO,
        controls=[ft.Container(expand=True, padding=16, content=content)],
    )