import flet as ft

def homepage_view(page: ft.Page) -> ft.View:
    body = ft.Container(
        expand=True,
        shadow=ft.BoxShadow(blur_radius=300, color=ft.Colors.BLUE_900),
        alignment=ft.Alignment.CENTER,  # centraliza tudo no meio da tela
        padding=ft.padding.symmetric(vertical=60),
        content=ft.Column(
            alignment=ft.MainAxisAlignment.CENTER,              # eixo vertical
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,  # eixo horizontal
            spacing=24,
            controls=[
                ft.Image(src="/assets/logo_notematch.png", width=100, height=100), 
                ft.Text("NoteMatch", size=48, weight=ft.FontWeight.BOLD, color="WHITE70"),
                ft.Text("Seu assistente para o notebook ideal", size=18, color="WHITE70"),
                ft.Button("Começar", on_click=lambda _: page.go("/questions"), width=200),
                #ft.ElevatedButton("teste/resultado", on_click=lambda _: page.go("/results"), width=200),
            ],
        ),
    )
 

    return ft.View(route="/homepage", controls=[body])