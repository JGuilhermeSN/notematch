# README – NoteMatch

> **Assitente de Recomendação de Notebooks Baseado em Análise Inteligente de Especificações Técnicas**
> Projeto de TCC – IFMT, 2025.

---

## Visão Geral

O **NoteMatch** é um assistente que recomenda notebooks de acordo com as necessidades do usuário. A lógica consiste em um motor de perguntas que afunila as escolhas até gerar **especificações mínimas** (CPU, GPU, RAM, SSD, tela). Em seguida, o sistema filtra uma base de dados real de notebooks para sugerir modelos compatíveis e dentro do orçamento informado.

## Funcionalidades

* Fluxo de perguntas dinâmico (CLI ou **Flet** – PWA/mobile).
* Geração automática de especificações mínimas.
* Consulta a uma base `CSV` com mais de 1 000 modelos.
* Classificação por orçamento (≤ R\$ 3 000 · 3 001–4 000 · 4 001–6 000 · ≥ 6 000).
* Módulo central desacoplado (`core/`) — fácil manutenção e testes.

## Estrutura do Repositório

```
notematch/
├─ src/
│  ├─ core/
│  │  ├─ question_engine.py   # fluxo de perguntas
│  │  ├─ specs_rules.py       # regras → especificações mínimas
│  │  └─ __init__.py
│  ├─ ui/
│  │  ├─ cli_app.py           # interface de linha de comando
│  │  ├─ flet_app.py          # interface mobile/desktop
│  │  └─ __init__.py
│  └─ main.py                # ponto de entrada
├─ data/
│  └─ base_dados.csv
├─ requirements.txt
└─ README.md
```

## Requisitos

* Python 3.10+

## Instalação Rápida

```bash
# clone o repositório
git clone https://github.com/<usuario>/notematch.git
cd notematch

# crie e ative um ambiente virtual
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\Activate.ps1

# instale as dependências
pip install -r requirements.txt
```

## Executar (CLI)

```bash
python -m src.ui.cli_app
```

## Executar (Flet – PWA)

```bash
python -m src.ui.flet_app
# abra http://localhost:8555 no navegador ou “Adicionar à tela inicial” no celular
```

## Testes

```bash
pip install pytest
pytest tests/
```
