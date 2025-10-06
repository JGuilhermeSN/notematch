import flet as ft

def results_view(page: ft.Page) -> ft.View:
    content = ft.Column(
        [ft.Text("Tela de Resultados"), 
         ft.OutlinedButton("Voltar", on_click=lambda _: page.go("/homepage"))],
        alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=16,
    )
    return ft.View(
        route="/results",
        appbar=ft.AppBar(title=ft.Text("Resultados")),
        controls=[ft.Container(
                               expand=True,
                               shadow=ft.BoxShadow(blur_radius=300, color=ft.Colors.BLUE_900), 
                               alignment=ft.alignment.center,
                               content=content, 
                               )],
    )
