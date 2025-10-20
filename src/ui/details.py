import flet as ft
from src.ui.app_state import get_selected

def details_view(page: ft.Page) -> ft.View:
    p = get_selected()
    if not p:
        return ft.View(
            route="/details",
            appbar=ft.AppBar(title=ft.Text("Detalhes")),
            controls=[
                ft.Container(
                    padding=16,
                    content=ft.Column(
                        [
                            ft.Text("Nenhum item selecionado."),
                            ft.OutlinedButton("Voltar", on_click=lambda _: page.go("/results")),
                        ]
                    ),
                )
            ],
        )

    spec_table = ft.DataTable(
        columns=[ft.DataColumn(ft.Text("Atributo")), ft.DataColumn(ft.Text("Valor"))],
        rows=[
            ft.DataRow(cells=[ft.DataCell(ft.Text("Modelo")), ft.DataCell(ft.Text(p.get("name", "-")))]),
            ft.DataRow(cells=[ft.DataCell(ft.Text("CPU")), ft.DataCell(ft.Text(p.get("cpu", "-")))]),
            ft.DataRow(cells=[ft.DataCell(ft.Text("RAM")), ft.DataCell(ft.Text(f'{p.get("ram_gb", "-")} GB'))]),
            ft.DataRow(cells=[ft.DataCell(ft.Text("Armazenamento")), ft.DataCell(ft.Text(p.get("storage", "-")))]),
            ft.DataRow(cells=[ft.DataCell(ft.Text("GPU")), ft.DataCell(ft.Text(p.get("gpu", "-")))]),
            ft.DataRow(cells=[ft.DataCell(ft.Text("Tela")), ft.DataCell(ft.Text(p.get("screen", "-")))]),
            ft.DataRow(cells=[ft.DataCell(ft.Text("Preço")), ft.DataCell(
                ft.Text(f'R$ {p.get("price_brl", 0):,.2f}'.replace(",", "X").replace(".", ",").replace("X", "."))
            )]),
        ],
    )

    reasons = p.get("reasons", [])
    reasons_list = ft.Column([ft.Text(f"• {r}") for r in reasons], spacing=2)

    content = ft.Column(
        [
            ft.Row(
                [
                    ft.Text(p.get("name", "Detalhes"), size=22, weight=ft.FontWeight.W_600),
                    ft.Container(expand=True),
                    ft.OutlinedButton("Home", on_click=lambda _: page.go("/homepage")),
                ]
            ),
            spec_table,
            ft.Text("Por que recomendamos:", size=16, weight=ft.FontWeight.W_600),
            reasons_list if reasons else ft.Text("—"),
        ],
        spacing=16,
    )

    return ft.View(
        route="/details",
        appbar=ft.AppBar(title=ft.Text("Detalhes")),
        controls=[ft.Container(expand=True, padding=16, content=content)],
    )
