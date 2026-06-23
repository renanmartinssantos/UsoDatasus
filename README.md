# 📊 Análise de Internações Hospitalares do SUS — SIH/RJ

> Iniciação Científica (IC) · Pipeline de ingestão, transformação e análise de dados do Sistema de Informações Hospitalares do SUS (SIH/SUS)

---

## 📋 Sumário

1. [Visão Geral do Projeto](#visão-geral-do-projeto)
2. [O que é o SIH/SUS e por que usá-lo](#o-que-é-o-sihsus-e-por-que-usá-lo)
3. [Metodologia: Como os dados do SUS são utilizados](#metodologia-como-os-dados-do-sus-são-utilizados)
4. [Estrutura de Diretórios](#estrutura-de-diretórios)
5. [Etapa 1 — Download dos arquivos .dbc (Python)](#etapa-1--download-dos-arquivos-dbc-python)
6. [Etapa 2 — Conversão de .dbc para .csv (R)](#etapa-2--conversão-de-dbc-para-csv-r)
7. [Etapa 3 — Conversão de .csv para .parquet (Python)](#etapa-3--conversão-de-csv-para-parquet-python)
8. [Etapa 4 — Análise e Visualização (Python)](#etapa-4--análise-e-visualização-python)
9. [Requisitos e Instalação](#requisitos-e-instalação)
10. [Como Executar](#como-executar)
11. [Referências e Dicionário de Dados](#referências-e-dicionário-de-dados)

---

## Visão Geral do Projeto

Este projeto implementa um **pipeline de dados end-to-end** para coleta, transformação e análise de dados de internações hospitalares do estado do **Rio de Janeiro**, provenientes do **SIH/SUS** (Sistema de Informações Hospitalares do Sistema Único de Saúde).

O objetivo principal é estudar o **fluxo migratório de pacientes** — ou seja, entender de quais municípios os pacientes se originam e para quais municípios se deslocam para receber atendimento hospitalar. Isso permite identificar:

- Municípios que atraem pacientes de outras regiões (polos de referência)
- Desigualdades no acesso à saúde
- Padrões de migração intermunicipal e interestadual
- Evolução temporal do volume de internações por sexo e cidade

O pipeline é dividido em **4 etapas** usando **duas linguagens** (Python e R), cada uma escolhida por razões técnicas específicas descritas neste documento.

---

## O que é o SIH/SUS e por que usá-lo

### O Sistema de Informações Hospitalares (SIH/SUS)

O **SIH/SUS** é um sistema oficial do Ministério da Saúde do Brasil, gerenciado pelo **DATASUS** (Departamento de Informática do SUS). Ele registra todas as **Autorizações de Internação Hospitalar (AIH)** pagas pelo SUS em todo o território nacional.

Cada registro no SIH representa uma **internação hospitalar** e contém dezenas de variáveis, incluindo:

| Campo | Descrição |
|---|---|
| `MUNIC_RES` | Código IBGE do município de residência do paciente |
| `MUNIC_MOV` | Código IBGE do município onde ocorreu a internação |
| `DIAG_PRINC` | Diagnóstico principal (CID-10) |
| `ANO_CMPT` | Ano de competência da AIH |
| `SEXO` | Sexo do paciente (1=Masc, 2/3=Fem, 0/9=Ignorado) |
| `PROC_REA` | Procedimento realizado |
| `COMPLEX` | Nível de complexidade do atendimento |

### Por que usar o SIH/SUS?

1. **Cobertura nacional**: Registra praticamente 100% das internações pagas pelo SUS
2. **Histórico longo**: Disponível desde 1992, permite análises temporais ricas
3. **Granularidade municipal**: Permite analisar fluxos ao nível de município
4. **Acesso público e gratuito**: Disponibilizado pelo DATASUS via FTP público
5. **Dado oficial**: Fonte primária para políticas públicas de saúde no Brasil

---

## Metodologia: Como os dados do SUS são utilizados

O DATASUS disponibiliza os dados do SIH em um formato proprietário chamado **`.dbc`** (uma variante comprimida do formato `.dbf` / dBase). Esse formato **não pode ser lido diretamente pelo Python ou pelo Pandas**, o que exigiu o uso estratégico de R na pipeline.

### Fluxo Completo dos Dados

```
DATASUS (FTP)              R                     Python                  Python
    │                      │                       │                       │
    │   Arquivos .dbc       │  Arquivos .csv         │  Arquivos .parquet     │  Análise e Gráficos
    ├──────────────────────►├──────────────────────►├──────────────────────►│
    │                       │                       │                       │
  ftp://ftp.datasus.gov.br  │  read.dbc()           │  pandas + pyarrow     │  plotly + sklearn
  /dissemin/publicos/SIA/   │  write.csv2()         │  chunked_csv_to_      │  fluxo O-D, Sankey,
                            │                       │  parquet()            │  barras animadas
```

### Por que 3 formatos de arquivo?

| Formato | Papel | Motivo |
|---|---|---|
| `.dbc` | Formato bruto do DATASUS | É o formato original, comprimido, distribuído pelo servidor FTP |
| `.csv` | Formato intermediário | Resultado da leitura pelo R; legível por qualquer linguagem |
| `.parquet` | Formato final de análise | Colunar, comprimido (zstd/gzip), muito mais rápido para leitura analítica |

---

## Estrutura de Diretórios

```
IC2/
│
├── dbc/                        # Arquivos brutos baixados do DATASUS
│   ├── RJ_2506.dbc             # Rio de Janeiro — Junho/2025
│   ├── RJ_2507.dbc             # Rio de Janeiro — Julho/2025
│   └── RJ_2508.dbc             # Rio de Janeiro — Agosto/2025
│
├── raw/
│   ├── csv/                    # CSVs gerados pelo R a partir dos .dbc
│   │   ├── RJ_2506.csv
│   │   ├── RJ_2507.csv
│   │   └── RJ_2508.csv
│   │
│   └── parquet/                # Parquets gerados pelo Python a partir dos CSVs
│       ├── RJ_2506.parquet
│       ├── RJ_2507.parquet
│       ├── RJ_2508.parquet
│       └── processed.log       # Log de controle de progresso da conversão
│
├── ingestao.ipynb              # Etapa 1: Download dos .dbc via FTP (Python)
├── rIgestao.ipynb              # Etapa 2: Conversão .dbc → .csv (R, Jupyter)
├── ingest.r                    # Etapa 2: Conversão .dbc → .csv (R, script puro)
├── csv_to_parquet.py           # Etapa 3: Conversão .csv → .parquet (Python)
├── csv_to_parquet.ipynb        # Etapa 3: Versão notebook da conversão
├── analytics.py                # Etapa 4: Análise exploratória e visualizações
└── municipios.csv              # Tabela de referência: código IBGE → nome do município
```

---

## Etapa 1 — Download dos arquivos .dbc (Python)

**Arquivo:** [`ingestao.ipynb`](ingestao.ipynb)

### O que faz

Este notebook realiza o **download automatizado** dos arquivos `.dbc` diretamente do servidor FTP público do DATASUS.

### Como funciona

O DATASUS disponibiliza os dados por meio do protocolo **FTP anônimo** no endereço:

```
ftp://ftp.datasus.gov.br/dissemin/publicos/{FONTE}/{PERIODO}/Dados/{TIPO}{UF}{ANOMES}.dbc
```

Onde:
- `FONTE` = sistema de saúde (ex: `SIA`, `SIH`)
- `TIPO` = tipo do arquivo (ex: `RD` para Registro de Dados do SIA)
- `UF` = sigla do estado (ex: `RJ`)
- `ANOMES` = ano e mês no formato `YYMM` (ex: `2506` para junho/2025)

### Código principal

```python
def import_file(fonte, tipo_arquivo, uf, ano_mes):
    url = f"ftp://ftp.datasus.gov.br/dissemin/publicos/{fonte}/200801_/Dados/{tipo_arquivo}{uf}{ano_mes}.dbc"
    file_name = f"{uf}_{ano_mes}.dbc"
    folder_name = "dbc/"
    os.makedirs(folder_name, exist_ok=True)
    urllib.request.urlretrieve(url, f"{folder_name}{file_name}")
```

### Configuração usada neste projeto

```python
date_start = "2025-06-01"
date_stop  = "2025-08-01"
fonte      = "SIA"          # Sistema de Informações Ambulatoriais
tipo_arquivo = "RD"         # Registro de AIH
ufs        = ['RJ']         # Rio de Janeiro
```

Resultado: os arquivos `RJ_2506.dbc`, `RJ_2507.dbc` e `RJ_2508.dbc` são salvos na pasta `dbc/`.

---

## Etapa 2 — Conversão de .dbc para .csv (R)

**Arquivos:** [`ingest.r`](ingest.r) · [`rIgestao.ipynb`](rIgestao.ipynb)

### Por que R foi usado aqui?

O formato `.dbc` é uma compressão proprietária aplicada sobre arquivos `.dbf` (dBase IV). **Não existe uma biblioteca Python madura e confiável** para ler esse formato com fidelidade total — especialmente no que diz respeito à codificação de caracteres (`latin1`) e campos numéricos com casas decimais implícitas, que são comuns nas bases do DATASUS.

O pacote R **`read.dbc`** foi desenvolvido especificamente para ler esses arquivos do DATASUS, sendo a solução de referência na comunidade de dados de saúde pública brasileira. Ele:

- Descomprime o `.dbc` corretamente
- Lê o `.dbf` subjacente mantendo os tipos de dados originais
- Produz um `data.frame` R pronto para exportação

### Como funciona

```r
require("read.dbc")

origin_folder  <- "/dbc/"          # pasta com os .dbc
destiny_folder <- "/raw/csv/"      # pasta de destino dos .csv

# Cria a pasta de destino se não existir
if (!dir.exists(destiny_folder)) {
  dir.create(destiny_folder)
}

# Itera sobre todos os arquivos .dbc
files_names <- list.files(origin_folder)
for (f in files_names) {
  origin_path  <- paste(origin_folder, f, sep="")
  destiny_path <- paste(destiny_folder, f, sep="")
  destiny_path <- sub(".dbc", ".csv", destiny_path)   # troca a extensão
  
  df <- read.dbc(origin_path)                         # lê o .dbc
  write.csv2(df, destiny_path, sep=";", row.names=FALSE)  # salva como .csv
}
```

### Por que `write.csv2` e separador `;`?

O `write.csv2` é a variante do R para padrão europeu/brasileiro, onde:
- O **separador de colunas** é `;` (ponto-e-vírgula)
- O **separador decimal** é `,` (vírgula)

Isso evita conflito entre o separador decimal e o separador de colunas ao exportar números como `1.500,75`.

Resultado: cada `.dbc` gera um `.csv` correspondente na pasta `raw/csv/`, com tamanho médio de ~46 MB por arquivo.

---

## Etapa 3 — Conversão de .csv para .parquet (Python)

**Arquivos:** [`csv_to_parquet.py`](csv_to_parquet.py) · [`csv_to_parquet.ipynb`](csv_to_parquet.ipynb)

### Por que converter para Parquet?

O **Apache Parquet** é um formato de arquivo colunar amplamente utilizado em análise de dados. Ele apresenta vantagens expressivas sobre o CSV para cargas de trabalho analíticas:

| Característica | CSV | Parquet |
|---|---|---|
| Compressão | Nenhuma (texto puro) | zstd / gzip / snappy |
| Tamanho em disco | ~46 MB por arquivo | ~3 MB por arquivo (**93% menor**) |
| Velocidade de leitura | Lenta (parse linha a linha) | Muito rápida (colunar, lazy loading) |
| Tipos de dados | Tudo como string | Preserva int, float, date etc. |
| Projeção de colunas | Não suporta | Lê apenas as colunas necessárias |

Neste projeto, os 3 CSVs de ~46 MB cada se tornaram 3 Parquets de ~3 MB cada — uma redução de **93% no tamanho**.

### Como funciona o script

O script [`csv_to_parquet.py`](csv_to_parquet.py) implementa uma conversão robusta com suporte a:

#### 1. Detecção automática do engine Parquet

```python
try:
    import pyarrow as pa
    import pyarrow.parquet as pq
    use_pyarrow = True               # pyarrow é preferido
except:
    import fastparquet
    use_fastparquet = True           # fallback para fastparquet
```

#### 2. Leitura em chunks (processamento incremental)

Os CSVs têm centenas de milhares de linhas. Para evitar estouro de memória RAM, o script processa em **lotes de 100.000 linhas**:

```python
iterator = pd.read_csv(path, sep=';', encoding='latin1',
                       chunksize=100000, low_memory=False)
for chunk in iterator:
    # processa e escreve cada chunk no arquivo .parquet
```

#### 3. Adição automática de colunas de proveniência

O nome do arquivo (`RJ_2506.csv`) contém o estado e o período. O script extrai e adiciona essas informações como colunas no dataset:

```python
estado, anomes = base.split('_')     # 'RJ', '2506'
ano = 2000 + int(anomes[:2])         # 2025
mes = anomes[2:]                     # '06'

chunk['estado_origem'] = estado       # 'RJ'
chunk['ano_origem']    = ano          # 2025
chunk['mes_origem']    = mes          # '06'
```

#### 4. Unificação de esquema (union de colunas)

Diferentes arquivos podem ter colunas distintas. O script coleta o conjunto de **todas as colunas** antes de iniciar a conversão e garante que cada chunk tenha todas elas (preenchendo com `pd.NA` quando necessário):

```python
union_cols = collect_union_columns(csv_files)
# Garante alinhamento de colunas em todo chunk
for c in union_cols:
    if c not in chunk.columns:
        chunk[c] = pd.NA
chunk = chunk[union_cols]
```

#### 5. Compressão automática com fallback

O script tenta comprimir com `zstd` (melhor ratio), depois `gzip`, depois `snappy`, e por último sem compressão:

```python
preferred_compressions = ['zstd', 'gzip', 'snappy']
for comp in preferred_compressions:
    try:
        w = pq.ParquetWriter(out_file, schema, compression=comp)
        break
    except:
        continue
```

#### 6. Log de progresso e retomada

O arquivo `raw/parquet/processed.log` registra quais arquivos já foram processados e quantas linhas já foram escritas. Se o processo for interrompido (queda de luz, erro), ele **retoma de onde parou** sem reprocessar arquivos já concluídos.

---

## Etapa 4 — Análise e Visualização (Python)

**Arquivo:** [`analytics.py`](analytics.py)

### O que é analisado

Este script realiza a análise exploratória dos dados, focada em dois temas principais:

#### Tema A: Fluxo Migratório de Pacientes (Análise Origem-Destino)

Classifica cada internação em uma de três categorias:

| Categoria | Critério |
|---|---|
| **Atendimento Local** | `MUNIC_RES == MUNIC_MOV` (paciente atendido no próprio município) |
| **Migração Intermunicipal** | Municípios diferentes, mesmo estado |
| **Migração Interestadual** | Estados diferentes |

```python
def classificar_fluxo(row):
    if row['MUNIC_RES'] == row['MUNIC_MOV']:
        return 'Atendimento Local'
    elif row['res_SIGLA_UF'] != row['int_SIGLA_UF']:
        return 'Migração Interestadual'
    else:
        return 'Migração Intermunicipal'
```

**Visualização:** Diagrama de Sankey interativo mostrando os 20 maiores fluxos de internação, construído com Plotly:

```python
fig = go.Figure(data=[go.Sankey(
    node=dict(label=all_nodes),
    link=dict(source=source_indices, target=target_indices, value=valores)
)])
```

#### Tema B: Evolução de Atendimentos por Cidade e Sexo

Agrupa internações por:
- Ano de competência (`ANO_CMPT`)
- Sexo do paciente (Masculino / Feminino)
- Cidade de internação (`MUNIC_MOV`)

**Visualização:** Gráfico de barras animado (frame = Ano) para as 10 cidades com mais internações.

#### Enriquecimento com tabela de municípios

O arquivo [`municipios.csv`](municipios.csv) contém os **5.570 municípios brasileiros** com código IBGE de 6 dígitos, nome e UF. Ele é usado para converter os códigos numéricos do SIH em nomes legíveis:

```python
df_municipios = pd.read_csv('municipios.csv', encoding='latin1', sep=';')
mapa_nomes = dict(zip(df_municipios['COD_6'], df_municipios['MUNICÍPIO - IBGE']))
mapa_uf    = dict(zip(df_municipios['COD_6'], df_municipios['UF']))

df_flow['NOME_ORIGEM']  = df_flow['MUNIC_RES'].map(mapa_nomes)
df_flow['NOME_DESTINO'] = df_flow['MUNIC_MOV'].map(mapa_nomes)
```

---

## Requisitos e Instalação

### Python

Recomenda-se usar um ambiente virtual (conda ou venv).

```bash
pip install pandas pyarrow plotly scikit-learn optuna tqdm lxml python-dateutil
```

Ou via conda:

```bash
conda install pandas pyarrow plotly scikit-learn tqdm
pip install optuna lxml
```

**Versões testadas:** Python 3.10, pandas ≥ 1.5, pyarrow ≥ 10

### R

Instale o R no seu sistema: [https://cran.r-project.org/](https://cran.r-project.org/)

Com o R instalado, abra o console R ou RStudio e execute:

```r
install.packages("read.dbc")
```

O pacote `read.dbc` é o **único pacote R necessário** no projeto. Ele está disponível no CRAN e é mantido especificamente para leitura de arquivos `.dbc` do DATASUS.

**Versão testada:** R ≥ 3.6

> **Jupyter com kernel R (opcional):** Para executar o notebook `rIgestao.ipynb`, instale o kernel IRkernel:
> ```r
> install.packages('IRkernel')
> IRkernel::installspec()
> ```

### Python

Recomenda-se usar um ambiente virtual (conda ou venv).

**Bibliotecas necessárias:**

| Biblioteca | Uso no projeto | Instalação |
|---|---|---|
| `pandas` | Leitura de CSV, manipulação de dados | `pip install pandas` |
| `pyarrow` | Leitura e escrita de arquivos Parquet | `pip install pyarrow` |
| `plotly` | Gráficos interativos (Sankey, barras animadas) | `pip install plotly` |
| `scikit-learn` | Regressão linear (analytics) | `pip install scikit-learn` |
| `optuna` | Otimização de hiperparâmetros (analytics) | `pip install optuna` |
| `tqdm` | Barra de progresso no download | `pip install tqdm` |
| `lxml` | Parser XML/HTML auxiliar | `pip install lxml` |
| `python-dateutil` | Geração de intervalos de datas por mês | `pip install python-dateutil` |

Instalação de tudo de uma vez:

```bash
pip install pandas pyarrow plotly scikit-learn optuna tqdm lxml python-dateutil
```

Ou via conda:

```bash
conda install pandas pyarrow plotly scikit-learn tqdm
pip install optuna lxml python-dateutil
```

**Versões testadas:** Python 3.10, pandas ≥ 1.5, pyarrow ≥ 10

> **Alternativa ao pyarrow:** Se o `pyarrow` não estiver disponível no seu ambiente, o script `csv_to_parquet.py` tenta automaticamente usar o `fastparquet` como fallback:
> ```bash
> pip install fastparquet
> ```

---

## ⚠️ Testando do Zero (Reset Completo)

Se você deseja rodar o pipeline completo desde o início — como se nunca tivesse executado nada — é necessário **apagar todos os arquivos gerados** nas etapas anteriores. Caso contrário, os scripts vão pular arquivos já existentes.

### Arquivos a deletar

**Pasta `dbc/`** — arquivos baixados do DATASUS:
```
dbc/RJ_2506.dbc
dbc/RJ_2507.dbc
dbc/RJ_2508.dbc
```

**Pasta `raw/csv/`** — CSVs gerados pelo R:
```
raw/csv/RJ_2506.csv
raw/csv/RJ_2507.csv
raw/csv/RJ_2508.csv
```

**Pasta `raw/parquet/`** — Parquets gerados pelo Python:
```
raw/parquet/RJ_2506.parquet
raw/parquet/RJ_2507.parquet
raw/parquet/RJ_2508.parquet
raw/parquet/processed.log
```

> **Atenção:** O arquivo `processed.log` é o log de controle do script `csv_to_parquet.py`. Se ele não for deletado junto com os `.parquet`, o script vai considerar que os arquivos já foram processados e não vai regerar nada.

### Comandos para reset (terminal)

**Windows (PowerShell):**
```powershell
Remove-Item dbc\*.dbc
Remove-Item raw\csv\*.csv
Remove-Item raw\parquet\*.parquet
Remove-Item raw\parquet\processed.log
```

**Linux / macOS (bash):**
```bash
rm dbc/*.dbc
rm raw/csv/*.csv
rm raw/parquet/*.parquet raw/parquet/processed.log
```

Após deletar, execute as etapas na ordem abaixo.

---

## Como Executar

Execute as etapas **na ordem indicada**:

### Etapa 1 — Download dos .dbc

Abra e execute o notebook [`ingestao.ipynb`](ingestao.ipynb) com Jupyter.

Você pode ajustar o período e o estado:

```python
date_start   = "2025-06-01"   # início do período
date_stop    = "2025-08-01"   # fim do período
fonte        = "SIA"           # sistema (SIA, SIH, etc.)
tipo_arquivo = "RD"            # tipo de registro
ufs          = ['RJ']          # lista de estados
```

Os arquivos `.dbc` serão salvos em `dbc/`.

### Etapa 2 — Conversão .dbc → .csv (R)

Opção A — Script puro:
```bash
Rscript ingest.r
```

Opção B — Jupyter com kernel R:
```
Abra rIgestao.ipynb e execute todas as células
```

> **Atenção:** certifique-se de que os caminhos `origin_folder` e `destiny_folder` no script R estão corretos para o seu sistema.

Os CSVs serão salvos em `raw/csv/`.

### Etapa 3 — Conversão .csv → .parquet

```bash
python csv_to_parquet.py
```

O script encontra automaticamente todos os CSVs em `raw/csv/` e salva os Parquets em `raw/parquet/`.

### Etapa 4 — Análise

```bash
python analytics.py
```

Ou abra o arquivo em um ambiente que suporte cells (VS Code com extensão Jupyter, por exemplo), pois o arquivo usa a marcação `# %%` para separação de células.

Os gráficos interativos abrirão automaticamente no navegador via Plotly.

---

## Referências e Dicionário de Dados

- **Dicionário de variáveis do SIH/SUS:** [PCDaS/Fiocruz](https://pcdas.icict.fiocruz.br/conjunto-de-dados/sistema-de-informacoes-hospitalares-do-sus-sihsus/documentacao/)
- **FTP DATASUS:** `ftp://ftp.datasus.gov.br/dissemin/publicos/`
- **Pacote R `read.dbc`:** [CRAN](https://cran.r-project.org/web/packages/read.dbc/index.html)
- **Apache Parquet:** [parquet.apache.org](https://parquet.apache.org/)
- **PyArrow:** [arrow.apache.org/docs/python](https://arrow.apache.org/docs/python/)
- **Plotly:** [plotly.com/python](https://plotly.com/python/)

---

*Renan Martins*
*Ciência de Dados*
*Fatec Baixada Santista Rubens Lara*
