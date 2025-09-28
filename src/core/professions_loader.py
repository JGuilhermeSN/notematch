import json
from pathlib import Path

def load_professions():
    base_dir = Path(__file__).resolve().parents[2]
    path = base_dir / "data" / "profissoes.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
