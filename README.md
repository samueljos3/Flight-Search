# Flight Search

Este projeto utiliza o Apache Airflow para automatizar a busca de voos promocionais por meio da API da Amadeus, organizando e armazenando os resultados em um banco de dados PostgreSQL para ser utilizado posteriormente em aplicações de análise de dados e IA.

## 📁 Estrutura do Projeto

- `dags/`
  - `flight_search_dag.py`: DAG principal para coleta e armazenamento dos dados.
  - `daily_flight_report_dag`: DAG para criação do report. (inicialmente como print no log, mas será enviado no e-mail)
  - `lib/amadeus_api.py`: Classe responsável por se conectar à API da Amadeus e processar os dados retornados.

## Funcionalidades

- Consulta voos com origem, destino e data definidos.
- Processamento e limpeza dos dados retornados da API.
- Armazenamento dos voos em uma tabela estruturada no PostgreSQL.
- Em desenvolvimento: Análise dos dados, chatbot interativo e alertas.

## Pré-requisitos

- Apache Airflow instalado e em execução.
- As seguintes conexões e variáveis devem ser criadas na interface do Airflow:

### Conexão com a API Amadeus

- **`api_connection_amadeus` em connections no airflow (HTTP)

### Conexão com o PostgreSQL

- **`postgres` em connections no airflow (Postgres)

### Variáveis da aplicação

- **`exit_location` exemplo: (REC) -> Recife
- **`arrival_location` exemplo: (MAD) -> Madrid
- **`departure_date` exemplo: (25/06/2025) 

## 📌 Observações

A lógica de integração com a API Amadeus está modularizada na pasta `lib`, dentro de `dags`.
