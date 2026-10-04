'''
responsável por transformar os textos da base em dados estruturados, concentrando a inteligência para interpretar os textos da base
'''
from __future__ import annotations

import re

# ------------------------------------------------------------------
# Constantes
# ------------------------------------------------------------------

_WORD_TO_CORES = {
    "dual": 2,
    "quad": 4,
    "hexa": 6,
    "octa": 8,
    "deca": 10,
    "dodeca": 12,
}


# ------------------------------------------------------------------
# RAM
# ------------------------------------------------------------------

def parse_ram_gb(ram_str: str) -> int:
    match = re.search(r"(\d+)\s*GB", ram_str, re.IGNORECASE)
    return int(match.group(1)) if match else 0


def parse_ram_type(ram_str: str) -> str:
    match = re.search(r"(LPDDR\d+x?|DDR\d+x?)", ram_str, re.IGNORECASE)
    return match.group(1).upper() if match else ""


# ------------------------------------------------------------------
# CPU
# ------------------------------------------------------------------

def parse_cpu_cores(core_str: str) -> int:
    match = re.search(r"(\d+)\s*Cores?", core_str, re.IGNORECASE)
    if match:
        return int(match.group(1))

    word = core_str.strip().split()[0].lower() if core_str else ""
    return _WORD_TO_CORES.get(word, 0)


def parse_cpu_threads(core_str: str) -> int:
    match = re.search(r"(\d+)\s*Threads?", core_str, re.IGNORECASE)
    return int(match.group(1)) if match else 0


# ------------------------------------------------------------------
# Armazenamento
# ------------------------------------------------------------------

def parse_storage_gb(memory_str: str) -> int:
    match = re.search(r"(\d+)\s*(GB|TB)", memory_str, re.IGNORECASE)

    if not match:
        return 0

    value = int(match.group(1))
    unit = match.group(2).upper()

    return value * 1024 if unit == "TB" else value


def parse_storage_type(memory_str: str) -> str:

    for storage in ("NVMe", "eMMC", "SSD", "HDD"):
        if storage.lower() in memory_str.lower():
            return storage

    return ""


# ------------------------------------------------------------------
# Garantia
# ------------------------------------------------------------------

def parse_warranty_years(text: str) -> int:
    match = re.search(r"(\d+)", text)
    return int(match.group(1)) if match else 0


# ------------------------------------------------------------------
# GPU
# ------------------------------------------------------------------

def parse_gpu_dedicated(gpu_str: str) -> bool:

    g = gpu_str.lower().strip()

    if "integrated" in g:
        return False

    if re.match(r"^\d+\s*gb", g):
        return True

    dedicated = (
        "rtx",
        "gtx",
        "geforce",
        "radeon rx",
        "rx ",
        "quadro",
        "firepro",
    )

    if any(k in g for k in dedicated):
        return True

    if "intel arc" in g:
        return True

    return False


def parse_gpu_vram_gb(gpu_str: str) -> int:
    match = re.match(r"^(\d+)\s*GB", gpu_str.strip(), re.IGNORECASE)
    return int(match.group(1)) if match else 0


def parse_gpu_brand(gpu_str: str) -> str:

    g = gpu_str.lower()

    if any(x in g for x in ("nvidia", "geforce", "rtx", "gtx")):
        return "NVIDIA"

    if any(x in g for x in ("amd", "radeon")):
        return "AMD"

    if "intel" in g:
        return "Intel"

    return ""