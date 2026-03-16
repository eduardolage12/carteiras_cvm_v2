# Consulta de Carteiras de Fundos - Dados CVM

Sistema para download, processamento e consulta de carteiras de fundos de investimento brasileiros, com dados públicos da CVM.

## Pré-requisitos

- Python 3.10 ou superior instalado ([download aqui](https://www.python.org/downloads/))
- Conexão com a internet (para baixar os dados da CVM)

## Como rodar

### 1. Instalar as dependências

Abra o terminal na pasta `carteiras_cvm` e execute:

```bash
pip install -r requirements.txt
```

### 2. Baixar os dados da CVM

```bash
python 01_baixar_dados.py
```

Isso vai baixar automaticamente os arquivos de carteiras dos últimos meses do site da CVM para a pasta `dados_brutos/`. Pode levar alguns minutos dependendo da velocidade da internet.

### 3. Processar os dados

```bash
python 02_processar_dados.py
```

Lê os dados brutos, consolida, filtra ativos de renda fixa e gera os arquivos na pasta `dados_processados/`:
- `carteiras_consolidadas.parquet` — base principal
- `carteiras_consolidadas.xlsx` — versão Excel (limitada a 500 mil linhas)

### 4. Abrir o app de consulta

```bash
streamlit run 03_app_consulta.py
```

Uma página web vai abrir no navegador com 3 abas de consulta:
- **Por ativo/emissor** — busca quais fundos investem em determinado ativo
- **Por fundo** — mostra a carteira completa de um fundo
- **Por gestor** — agrupa posições por gestor

## Estrutura de pastas

```
carteiras_cvm/
├── 01_baixar_dados.py         # Baixa dados da CVM
├── 02_processar_dados.py      # Processa e consolida os dados
├── 03_app_consulta.py         # App de consulta (Streamlit)
├── requirements.txt           # Dependências do projeto
├── base_emissores/            # Planilha de mapeamento ticker → emissor
├── dados_brutos/              # Dados baixados da CVM (gerado pelo script 01)
└── dados_processados/         # Dados consolidados (gerado pelo script 02)
```

## Observações

- Os scripts devem ser executados **na ordem** (01, 02, 03).
- O script 01 precisa ser re-executado quando quiser atualizar os dados com os meses mais recentes.
- A planilha `base_emissores/base_emissores.xlsx` é usada para mapear tickers de ativos para nomes de emissores. Atualize-a manualmente conforme necessário.
