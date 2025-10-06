import flet as ft

def questions_view(page: ft.Page) -> ft.View:
    content = ft.Column(
        [ft.Text("Aqui vão as perguntas…"), 
         ft.OutlinedButton("Voltar", on_click=lambda _: page.go("/homepage")),
         ft.OutlinedButton("Resultados", on_click=lambda _: page.go("/results"))
         ],
        alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=16,
    )
    return ft.View(
        route="/questions",
        appbar=ft.AppBar(title=ft.Text("Questionário")),
        controls=[ft.Container(
                               expand=True,
                               shadow=ft.BoxShadow(blur_radius=300, color=ft.Colors.BLUE_900), 
                               alignment=ft.alignment.center,
                               content=content, 
                               )],
    )
