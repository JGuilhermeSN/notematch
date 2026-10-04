# README – NoteMatch

> **Sistema de Recomendação de Notebooks Baseado em Conhecimento e Restrições**
> Projeto de TCC – IFMT, 2026.

---

## Visão Geral

O **NoteMatch** é um assistente que recomenda notebooks de acordo com as necessidades do usuário. A lógica consiste em um motor de perguntas que afunila as escolhas até gerar **especificações mínimas** (CPU, GPU, RAM, SSD, tela). Em seguida, o sistema filtra uma base de dados real de notebooks para sugerir três modelos compatíveis e dentro do orçamento informado.

## Funcionalidades

* Fluxo de perguntas dinâmico (CLI ou **Flet** – PWA/mobile).
* Geração automática de especificações mínimas.
* Consulta a uma base `CSV` com mais de 1 000 modelos.
* Classificação por orçamento (≤ R\$ 3 000 · 3 001–4 000 · 4 001–6 000 · ≥ 6 000).
* Módulo central desacoplado (`core/`) — fácil manutenção e testes.



## Requisitos

* Python 3.10+

## Instalação Rápida

```bash
# clone o repositório
git clone https://github.com/JGuilhermeSN/notematch.git
cd notematch

# instale as dependências
pip install -r requirements.txt
```

## Executar (CLI)

```bash
python -m src.ui.cli_app
```

## Executar (Flet – PWA)

```bash
flet run --android -r main.py # rodar no android
```
