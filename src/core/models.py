# src/core/models.py
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class Notebook:

    # Identificação
    name: str
    company: str

    # Processador
    cpu: str
    cpu_brand: str
    cpu_series: str
    cpu_model: str
    cpu_clock_ghz: float
    cpu_cores: int
    cpu_threads: int

    # Memória RAM
    ram_gb: int
    ram_type: str

    # GPU
    gpu: str
    gpu_brand: str
    gpu_model: str
    gpu_vram_gb: int
    gpu_dedicated: bool

    # Tela
    inches: float
    res_width: int
    res_height: int
    is_touchscreen: bool

    # Armazenamento
    storage: str
    storage_type: str
    storage_gb: int

    # Sistema
    os: str
    warranty_years: int

    # Avaliação
    rating: float

    # Preço
    price_brl: float