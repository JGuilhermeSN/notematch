import flet as ft
from src.ui.quiz_controller import quiz

def questions_view(page: ft.Page) -> ft.View:
    # Reinicia o fluxo ao entrar na rota de perguntas
    quiz.reset()

    prompt_txt = ft.Text(quiz.get_prompt(), size=22, weight=ft.FontWeight.W_600, color="WHITE")
    options_col = ft.Column(spacing=12, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)

    def rebuild_options(do_update: bool = False):
        # Só popula a lista; atualizar a UI só quando a View já estiver na página
        options_col.controls.clear()
        for key, label in quiz.get_options().items():
            options_col.controls.append(
                ft.ElevatedButton(
                    f"{key}. {label}",
                    on_click=lambda e, k=key: on_option_click(k),
                )
            )
        if do_update:
            # Aqui já é seguro (após a view estar montada)
            options_col.update()

    def on_option_click(key: str):
        has_next = quiz.answer(key)
        if has_next:
            prompt_txt.value = quiz.get_prompt()
            rebuild_options(do_update=False)
            page.update()  # redesenha tudo
        else:
            page.go("/results")


    # Construção inicial: popula sem .update()
    rebuild_options(do_update=False)

    content = ft.Column(
        controls=[
            ft.Container(
                padding=20,
                content=ft.Column(
                    [
                        prompt_txt,
                        options_col,
                        ft.Row(
                            [ft.OutlinedButton("Voltar", on_click=lambda _: page.go("/homepage"))],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                    ],
                    spacing=24,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            )
        ],
        alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )

    return ft.View(
        route="/questions",
        appbar=ft.AppBar(title=ft.Text("Questionário")),
        controls=[ft.Container(expand=True, alignment=ft.Alignment.CENTER, content=content)],
    )
