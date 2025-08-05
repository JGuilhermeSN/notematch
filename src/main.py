# pip install kagglehub[pandas-datasets]
import pandas as pd
import kagglehub
from kagglehub import KaggleDatasetAdapter

# Configura o Pandas para exibir o conteúdo completo das colunas
pd.set_option('display.max_colwidth', None)

# Define o caminho do arquivo que deseja carregar
file_path = "laptop_price (1).csv"

# Carrega o dataset usando o adaptador para Pandas, especificando a codificação correta
df = kagglehub.load_dataset(
    KaggleDatasetAdapter.PANDAS,
    "durgeshrao9993/laptop-specification-dataset",
    file_path,
    pandas_kwargs={'encoding': 'latin1'}  # ou 'ISO-8859-1' se necessário
)

# Seleciona os 5 primeiros registros e os 5 últimos registros
first_five = df.head()
last_five = df.tail()
# Combina esses dois subconjuntos em um único DataFrame
partial_df = pd.concat([first_five, last_five])

# Visualiza os registros selecionados
print("Primeiros 5 e últimos 5 registros:")
print(partial_df)

# Gera um novo arquivo CSV contendo somente esses registros
output_file = "laptop_specifications_partial.csv"
partial_df.to_csv(output_file, index=False)

print(f"Novo arquivo CSV gerado: {output_file}")
