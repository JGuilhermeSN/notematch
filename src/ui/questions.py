import flet as ft
from src.ui.quiz_controller import quiz

def questions_view(page: ft.Page) -> ft.View:
    quiz.reset()

    prompt_txt = ft.Text(
        quiz.get_prompt(),
        size=22,
        weight=ft.FontWeight.W_600,
        color="WHITE"
    )

    options_list = ft.ListView(
        spacing=10,
        expand=True,
        auto_scroll=False
    )

    def rebuild_options(do_update: bool = False):
        options_list.controls.clear()

        for key, label in quiz.get_options().items():
            options_list.controls.append(
                ft.Button(
                    content=ft.Text(f"{key}. {label}"),
                    on_click=lambda e, k=key: on_option_click(k),
                    width=float("inf"),
                )
            )

        # 🔴 só atualiza se já estiver na tela
        if do_update:
            options_list.update()

    def on_option_click(key: str):
        has_next = quiz.answer(key)

        if has_next:
            prompt_txt.value = quiz.get_prompt()
            rebuild_options(do_update=True)  # agora pode atualizar
            page.update()
        else:
            page.go("/results")

    # 🚫 NÃO atualizar aqui
    rebuild_options(do_update=False)

    content = ft.Container(
        padding=20,
        expand=True,
        content=ft.Column(
            [
                prompt_txt,
                ft.Container(
                    content=options_list,
                    expand=True
                ),
                ft.Row(
                    [
                        ft.OutlinedButton(
                            "Voltar",
                            on_click=lambda _: page.go("/homepage")
                        )
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
            ],
            spacing=24,
            expand=True
        ),
    )

    return ft.View(
        route="/questions",
        appbar=ft.AppBar(title=ft.Text("Questionário")),
        controls=[
            ft.Container(
                expand=True,
                content=content
            )
        ],
        scroll=ft.ScrollMode.AUTO,
    )