from typing import Optional, Dict, Any

_selected_product: Optional[Dict[str, Any]] = None

def set_selected(product: Dict[str, Any]) -> None:
    global _selected_product
    _selected_product = product

def get_selected() -> Optional[Dict[str, Any]]:
    return _selected_product
