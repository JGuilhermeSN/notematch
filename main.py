import flet as ft
from router import handle_route_change, handle_view_pop, INITIAL_ROUTE

def main(page: ft.Page):
    page.title = "NoteMatch"
    page.bgcolor = "#4561FF" #So para referencia do hashcode
    page.on_route_change = lambda e: handle_route_change(page)
    page.on_view_pop = lambda e: handle_view_pop(page)
    page.go(INITIAL_ROUTE)

ft.app(target=main, assets_dir="assets")