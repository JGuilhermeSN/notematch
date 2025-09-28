# src/main.py
from src.ui.cli_app import run_cli
# no futuro: from ui.mobile_app import run_mobile

if __name__ == "__main__":
    print("\n Iniciando NoteMatch (modo CLI)...")
    run_cli()
    # no futuro, basta trocar aqui para rodar a versão mobile


# professor, eu estou com uma duvida em sobre o meu projeto ser suficiente para um tcc, eu avançei bem esses dias, so que começou me dar 
# essas duvidas, o senhor acha que o que tenho ate agora é suficiente para a banca?
# basicamente o projeto esta estruturado como um assistente de recomendação que atraves de perguntas, ve o que o usuario utiliza, e cruza os dados com
# a base de dados das especificações tecnicas, e com isso recomenda tres dispositivos, com base no preço e outros parametros.

# gostaria de ver com o sr. se é o bastante, ou que poderia implementar algo a mais.