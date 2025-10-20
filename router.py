import flet as ft
from flet import TemplateRoute
from src.ui.homepage import homepage_view
from src.ui.questions import questions_view
from src.ui.results import results_view
from src.ui.details import details_view

INITIAL_ROUTE = "/homepage"

def handle_route_change(page: ft.Page):
    tr = TemplateRoute(page.route)
    page.views.clear()
    page.views.append(homepage_view(page))
    if tr.match("/questions") or tr.match("/results") or tr.match("/details"):
        page.views.append(questions_view(page))
    if tr.match("/results"):
        page.views.append(results_view(page))
    if tr.match("/details"):
        page.views.append(details_view(page))

    page.update()

def handle_view_pop(page: ft.Page):
    page.views.pop()
    route = page.views[-1].route if page.views and page.views[-1].route else "/homepage"
    page.go(route)
