# src/core/models.py
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class Notebook:
    # Campos essenciais SEM None (valores padrão quando faltar no CSV)
    name: str               # ex.: Product / Model
    company: str            # ex.: Company / Brand
    cpu: str                # ex.: Cpu
    ram_gb: int             # ex.: "8GB" -> 8 (0 se não parsear)
    gpu: str                # ex.: Gpu
    inches: float           # ex.: Inches (0.0 se não parsear)
    screen_res: str         # ex.: ScreenResolution ("" se ausente)
    weight_kg: float        # ex.: Weight (0.0 se não parsear)
    price_eur: float        # ex.: Price_euros (0.0 se não parsear)
