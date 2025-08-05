import pandas as pd

pd.options.display.max_colwidth = None

# carrega a base de dados
df = pd.read_csv('src/data/processed/note_dataset.csv')

#print(df.head())
print(df['product_name'])