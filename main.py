'''
import flet as ft
from pathlib import Path
from src.ui.homepage import main as app_main


APP_DIR = Path(__file__).resolve().parent
ASSETS_DIR = APP_DIR / "assets"

"""
if __name__ == "__main__":
    print("\n Iniciando NoteMatch (modo CLI)...")
    run_cli()"""
    # no futuro, basta trocar aqui para rodar a versão mobile

if __name__ == "__main__":
    ft.app(target=app_main, 
        assets_dir=str(ASSETS_DIR))

'''

import flet as ft
from router import handle_route_change, handle_view_pop, INITIAL_ROUTE

def main(page: ft.Page):
    page.title = "NoteMatch"
    #page.bgcolor = "#4561FF" So para referencia do hashcode
    page.on_route_change = lambda e: handle_route_change(page)
    page.on_view_pop = lambda e: handle_view_pop(page)
    page.go(INITIAL_ROUTE)

ft.app(target=main, assets_dir="assets")