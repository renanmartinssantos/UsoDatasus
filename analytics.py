# %%
import pandas as pd
import glob
import os
import time
import pyarrow as pa
import pyarrow.dataset as ds
import pyarrow.parquet as pq
import plotly.express as px
import optuna
import pandas as pd
from sklearn.linear_model import LinearRegression
import plotly.colors as pc
import plotly.graph_objects as go
import numpy as np

# %%
padrao = os.path.join('raw', 'parquet', 'RJ*.parquet')
arquivos = glob.glob(padrao)
print(f"Arquivos encontrados: {arquivos}")

# %%
### Executando com Pandas (Não é gpt escrevendo comentário...)
inicioPandas = time.time()
if arquivos:
    df = pd.concat([pd.read_parquet(f) for f in arquivos], ignore_index=True)
    print("Dados com Pandas carregados com sucesso!")
else:
    print("Nenhum arquivo encontrado.")
fimPandas = time.time()

# %%

timePandas = fimPandas - inicioPandas

print(f"Tempo de execução do Pandas: {timePandas:.2f} s")

# %% 
df.info()

# %%
df.head()


### DICIONÁRIO
### https://pcdas.icict.fiocruz.br/conjunto-de-dados/sistema-de-informacoes-hospitalares-do-sus-sihsus/documentacao/

# %%
df
# %%
cols_fluxo = [
    'MUNIC_RES', 'res_MUNNOME', 'res_SIGLA_UF',  
    'MUNIC_MOV', 'int_MUNNOME', 'int_SIGLA_UF',  
    'DIAG_PRINC', 'PROC_REA', 'COMPLEX'         
]

cols_existentes = [c for c in cols_fluxo if c in df.columns]
df_flow = df[cols_existentes].copy()

# Remove linhas onde Município é nulo ou 000000 (comum em erros de registro)
df_flow = df_flow.dropna(subset=['MUNIC_RES', 'MUNIC_MOV'])
df_flow = df_flow[df_flow['MUNIC_RES'] != '000000']

def classificar_fluxo(row):
    if row['MUNIC_RES'] == row['MUNIC_MOV']:
        return 'Atendimento Local'
    elif row.get('res_SIGLA_UF') != row.get('int_SIGLA_UF') and pd.notnull(row.get('res_SIGLA_UF')):
        return 'Migração Interestadual'
    else:
        return 'Migração Intermunicipal'

# Aplica a classificação
df_flow['TIPO_FLUXO'] = df_flow.apply(classificar_fluxo, axis=1)

print(df_flow['TIPO_FLUXO'].value_counts(normalize=True))

#%%

try:
    df_municipios = pd.read_csv('municipios.csv', encoding='latin1', sep=';')
    coluna_codigo_ibge = 'CÓDIGO DO MUNICÍPIO - IBGE' 
    coluna_municipio = 'MUNICÍPIO - IBGE'
    coluna_uf = 'UF'

    df_municipios['COD_6'] = df_municipios[coluna_codigo_ibge].astype(str).str.slice(0, 6)

    # Criar dicionários para mapeamento
    mapa_nomes = dict(zip(df_municipios['COD_6'], df_municipios[coluna_municipio]))
    mapa_uf = dict(zip(df_municipios['COD_6'], df_municipios[coluna_uf]))
    df_flow['MUNIC_RES'] = df_flow['MUNIC_RES'].astype(str)
    df_flow['MUNIC_MOV'] = df_flow['MUNIC_MOV'].astype(str)

    # Mapeamento
    df_flow['NOME_ORIGEM'] = df_flow['MUNIC_RES'].map(mapa_nomes).fillna(df_flow['MUNIC_RES'])
    df_flow['UF_ORIGEM'] = df_flow['MUNIC_RES'].map(mapa_uf)
    
    df_flow['NOME_DESTINO'] = df_flow['MUNIC_MOV'].map(mapa_nomes).fillna(df_flow['MUNIC_MOV'])
    df_flow['UF_DESTINO'] = df_flow['MUNIC_MOV'].map(mapa_uf)

except KeyError as e:
    print("Colunas encontradas no CSV:", df_municipios.columns.tolist())
except Exception as e:
    print(f"Ocorreu um erro: {e}")

# %%

fluxo_od = df_flow.groupby(['NOME_ORIGEM', 'UF_ORIGEM', 'NOME_DESTINO', 'UF_DESTINO']).size().reset_index(name='QTD_INTERNACOES')
fluxo_migratorio = fluxo_od[fluxo_od['NOME_ORIGEM'] != fluxo_od['NOME_DESTINO']]
fluxo_migratorio = fluxo_migratorio.sort_values(by='QTD_INTERNACOES', ascending=False)

# 4. Exibição
print("10 Maiores Fluxos de Migração")
print(fluxo_migratorio.head(10))

# %%

top_fluxos = fluxo_migratorio.head(20).copy()
top_fluxos['Origem_Label'] = top_fluxos['NOME_ORIGEM'] + ' (' + top_fluxos['UF_ORIGEM'].astype(str) + ')'
top_fluxos['Destino_Label'] = top_fluxos['NOME_DESTINO'] + ' (' + top_fluxos['UF_DESTINO'].astype(str) + ')'

origens = top_fluxos['Origem_Label'].tolist()
destinos = top_fluxos['Destino_Label'].tolist()
valores = top_fluxos['QTD_INTERNACOES'].tolist()
all_nodes = list(set(origens + destinos))
node_map = {name: i for i, name in enumerate(all_nodes)}
source_indices = [node_map[x] for x in origens]
target_indices = [node_map[x] for x in destinos]

fig = go.Figure(data=[go.Sankey(
    node = dict(
      pad = 15,
      thickness = 20,
      line = dict(color = "black", width = 0.5),
      label = all_nodes,
      hovertemplate = '<b>%{label}</b><br>' +
                      'Total de Movimento: %{value}<br>' +
                      '<extra></extra>' 
    ),
    link = dict(
      source = source_indices,
      target = target_indices,
      value = valores,
      color = "rgba(128, 128, 128, 0.5)",
      hovertemplate = '<b>De:</b> %{source.label}<br>' +
                      '<b>Para:</b> %{target.label}<br>' +
                      '<b>Pacientes:</b> %{value}' +
                      '<extra></extra>'
  ))])

fig.update_layout(
    title_text="Top 20 Fluxos de Internação (Origem -> Destino)", 
    font_size=12,
    height=600
)

fig.show()
# %%

cols_analise = ['ANO_CMPT', 'SEXO', 'MUNIC_MOV']
df_atend = df[cols_analise].copy()
df_atend['ANO'] = df_atend['ANO_CMPT'].astype(str).str.slice(0, 4)
dict_sexo = {
    '1': 'Masculino', 
    '2': 'Feminino', 
    '3': 'Feminino', 
    '0': 'Ignorado', 
    '9': 'Ignorado'
}
df_atend['SEXO'] = df_atend['SEXO'].astype(str).map(dict_sexo).fillna('Ignorado')
df_atend['MUNIC_MOV'] = df_atend['MUNIC_MOV'].astype(str)
df_atend['NOME_CIDADE'] = df_atend['MUNIC_MOV'].map(mapa_nomes).fillna(df_atend['MUNIC_MOV'])
df_atend['UF'] = df_atend['MUNIC_MOV'].map(mapa_uf).fillna('')
df_atend['CIDADE_LABEL'] = df_atend['NOME_CIDADE'] + ' (' + df_atend['UF'] + ')'

# %%
resumo_atendimentos = df_atend.groupby(['ANO', 'SEXO', 'CIDADE_LABEL']).size().reset_index(name='QTD_ATENDIMENTOS')
resumo_atendimentos = resumo_atendimentos[resumo_atendimentos['SEXO'] != 'Ignorado']
resumo_atendimentos = resumo_atendimentos.sort_values(by=['ANO', 'QTD_ATENDIMENTOS'], ascending=[True, False])
print(resumo_atendimentos.head(10))
# %%
top_cidades = resumo_atendimentos.groupby('CIDADE_LABEL')['QTD_ATENDIMENTOS'].sum().nlargest(10).index
df_grafico = resumo_atendimentos[resumo_atendimentos['CIDADE_LABEL'].isin(top_cidades)]

fig = px.bar(
    df_grafico, 
    x='CIDADE_LABEL', 
    y='QTD_ATENDIMENTOS', 
    color='SEXO', 
    animation_frame='ANO',
    barmode='group',
    title='Evolução dos Atendimentos por Cidade e Sexo (Top 10 Cidades)',
    labels={'QTD_ATENDIMENTOS': 'Quantidade', 'CIDADE_LABEL': 'Cidade', 'ANO': 'Ano'},
    color_discrete_map={'Masculino': "#283f33", 'Feminino': "#e48416"}
)

fig.update_layout(height=600)
fig.show()

# %%


df_atend = df[cols_analise].copy()
df_atend['ANO'] = df_atend['ANO_CMPT'].astype(str).str.slice(0, 4)

df_atend = df[cols_analise].copy()
df_atend['ANO'] = df_atend['ANO_CMPT'].astype(str).str.slice(0, 4)