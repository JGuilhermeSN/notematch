# src/core/specs_rules.py
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class Specs:
    cpu_min: str         # ex.: "i5" | "i7" | "Ryzen 5" | "Ryzen 7"
    ram_gb_min: int      # ex.: 8, 16
    ssd_min_gb: int      # ex.: 256, 512
    gpu_type: str        # "integrated" | "dedicated"
    gpu_min_hint: Optional[str] = None  # ex.: "RTX 3050"
    screen_min_width: int = 1920        # ex.: 1920 para FHD
    inches_min: float = 14.0            # tamanho mínimo, se quiser forçar algo

def infer_specs(answers: Dict[str, str]) -> Specs:
    """Converte respostas do questionário em especificações mínimas."""
    area = answers.get("Para que você precisa de um notebook?")
    prof = answers.get("Qual área profissional?")
    atividade = answers.get("Qual é a principal atividade?")
    # orçamento pode ser usado apenas para filtragem, não para specs
    # budget = answers.get("Qual faixa de orçamento?")

    # Defaults conservadores
    specs = Specs(cpu_min="i5/Ryzen 5", ram_gb_min=8, ssd_min_gb=256,
                  gpu_type="integrated", gpu_min_hint=None,
                  screen_min_width=1366, inches_min=13.3)

    # Jogos
    if area == "Jogos":
        return Specs(cpu_min="i5/Ryzen 5", ram_gb_min=16, ssd_min_gb=512,
                     gpu_type="dedicated", gpu_min_hint="GTX 1650/RTX 3050",
                     screen_min_width=1920, inches_min=15.0)

    # Estudo e Navegação
    if area in {"Navegação / Uso básico", "Estudo"}:
        return Specs(cpu_min="i3/Ryzen 3", ram_gb_min=8, ssd_min_gb=256,
                     gpu_type="integrated", gpu_min_hint=None,
                     screen_min_width=1366, inches_min=13.3)

    # Trabalho → especializações
    if area == "Trabalho":
        if prof == "Programação":
            return Specs(cpu_min="i5/Ryzen 5", ram_gb_min=16, ssd_min_gb=512,
                         gpu_type="integrated", gpu_min_hint=None,
                         screen_min_width=1920, inches_min=14.0)

        if prof == "Design Gráfico":
            return Specs(cpu_min="i5/Ryzen 5", ram_gb_min=16, ssd_min_gb=512,
                         gpu_type="dedicated", gpu_min_hint="GTX 1650/RTX 3050",
                         screen_min_width=1920, inches_min=15.0)

        if prof == "Engenharia":
            return Specs(cpu_min="i5/Ryzen 5", ram_gb_min=16, ssd_min_gb=512,
                         gpu_type="integrated", gpu_min_hint=None,
                         screen_min_width=1920, inches_min=14.0)

        if prof == "Arquitetura":
            # A atividade define a GPU
            if atividade in {"Modelagem 3D", "Renderização"}:
                return Specs(cpu_min="i7/Ryzen 7", ram_gb_min=16, ssd_min_gb=512,
                             gpu_type="dedicated", gpu_min_hint="RTX 3050",
                             screen_min_width=1920, inches_min=15.0)
            if atividade == "CAD / BIM 2D":
                return Specs(cpu_min="i5/Ryzen 5", ram_gb_min=16, ssd_min_gb=512,
                             gpu_type="integrated", gpu_min_hint=None,
                             screen_min_width=1920, inches_min=15.0)

    # fallback
    return specs
