# src/core/data_loader.py

from __future__ import annotations

import csv
from pathlib import Path
from typing import List

from src.core.models import Notebook
from src.core.parsers import (
    parse_cpu_cores,
    parse_cpu_threads,
    parse_gpu_brand,
    parse_gpu_dedicated,
    parse_gpu_vram_gb,
    parse_ram_gb,
    parse_ram_type,
    parse_storage_gb,
    parse_storage_type,
    parse_warranty_years,
)

DEFAULT_ENCODING = "utf-8-sig"
DEFAULT_FILENAME = "base_dados.csv"


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _default_data_path() -> Path:
    return _project_root() / "data" / DEFAULT_FILENAME


# ------------------------------------------------------------------
# Helpers básicos
# ------------------------------------------------------------------

def _get_str(row: dict, key: str) -> str:
    value = row.get(key)
    return "" if value is None else str(value).strip()


def _get_int(row: dict, key: str) -> int:
    try:
        return int(float(str(row.get(key, "0")).strip()))
    except (ValueError, TypeError):
        return 0


def _get_float(row: dict, key: str) -> float:
    try:
        return float(str(row.get(key, "0")).replace(",", ".").strip())
    except (ValueError, TypeError):
        return 0.0


def _get_bool(row: dict, key: str) -> bool:
    value = str(row.get(key, "")).strip().lower()
    return value in ("true", "1", "yes", "sim", "y")


# ------------------------------------------------------------------
# Loader principal
# ------------------------------------------------------------------

def load_notebooks(path: Path | None = None) -> List[Notebook]:

    csv_path = path or _default_data_path()

    notebooks: List[Notebook] = []

    with open(csv_path, encoding=DEFAULT_ENCODING, newline="") as file:

        reader = csv.DictReader(file)

        # Normaliza os nomes das colunas (o CSV possui " price_brl ")
        rows = [
            {key.strip(): value for key, value in row.items()}
            for row in reader
        ]

    for row in rows:

        ram_str = _get_str(row, "ram")
        core_str = _get_str(row, "core")
        memory_str = _get_str(row, "memory")
        gpu_str = _get_str(row, "graphic_card")
        warranty_str = _get_str(row, "warrenty")  # nome original do CSV

        notebooks.append(

            Notebook(

                # -------------------------------------------------
                # Identificação
                # -------------------------------------------------
                name=_get_str(row, "model"),
                company=_get_str(row, "brand"),

                # -------------------------------------------------
                # CPU
                # -------------------------------------------------
                cpu=_get_str(row, "processor"),
                cpu_brand="",           # poderá ser inferido futuramente
                cpu_series="",          # poderá ser inferido futuramente
                cpu_model="",           # poderá ser inferido futuramente
                cpu_clock_ghz=0.0,      # não disponível na base
                cpu_cores=parse_cpu_cores(core_str),
                cpu_threads=parse_cpu_threads(core_str),

                # -------------------------------------------------
                # RAM
                # -------------------------------------------------
                ram_gb=parse_ram_gb(ram_str),
                ram_type=parse_ram_type(ram_str),

                # -------------------------------------------------
                # GPU
                # -------------------------------------------------
                gpu=gpu_str,
                gpu_brand=parse_gpu_brand(gpu_str),
                gpu_model="",           # poderá ser inferido futuramente
                gpu_vram_gb=parse_gpu_vram_gb(gpu_str),
                gpu_dedicated=parse_gpu_dedicated(gpu_str),

                # -------------------------------------------------
                # Tela
                # -------------------------------------------------
                inches=_get_float(row, "inches"),
                res_width=_get_int(row, "screen_width"),
                res_height=_get_int(row, "screen_height"),
                is_touchscreen=_get_bool(row, "is_touchscreen"),

                # -------------------------------------------------
                # Armazenamento
                # -------------------------------------------------
                storage=memory_str,
                storage_type=parse_storage_type(memory_str),
                storage_gb=parse_storage_gb(memory_str),

                # -------------------------------------------------
                # Sistema
                # -------------------------------------------------
                os=_get_str(row, "os"),
                warranty_years=parse_warranty_years(warranty_str),

                # -------------------------------------------------
                # Avaliação
                # -------------------------------------------------
                rating=_get_float(row, "rating"),

                # -------------------------------------------------
                # Preço
                # -------------------------------------------------
                price_brl=_get_float(row, "price_brl"),
            )

        )

    return notebooks