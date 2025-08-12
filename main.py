# -*- coding: utf-8 -*-
import re
import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(
    page_title="Dashboard de Salários na Área de Dados",
    page_icon="📊",
    layout="wide",
)

DATA_URL = "https://raw.githubusercontent.com/vqrca/dashboard_salarios_dados/refs/heads/main/dados-imersao-final.csv"

@st.cache_data
def load_data(url: str) -> pd.DataFrame:
    df = pd.read_csv(url)
    # limpeza básica
    df = df.rename(columns=lambda x: x.strip())
    # normaliza ano para int (nullable)
    if 'ano' in df.columns:
        df['ano'] = pd.to_numeric(df['ano'], errors='coerce').astype('Int64')
    # normaliza nomes de colunas e cargos
    return df


def normalize_title(t):
    if pd.isna(t):
        return ""
    t = str(t).lower()
    t = re.sub(r'[^a-z0-9\s]', '', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t


# Load
df = load_data(DATA_URL)

# Cria coluna normalizada de cargo para busca
if 'cargo' in df.columns:
    df['cargo_norm'] = df['cargo'].apply(normalize_title)
else:
    df['cargo_norm'] = ""

st.sidebar.header("🔍 Filtros")

# Presets rápidos
preset = st.sidebar.selectbox("Presets", ["Todos", "Sênior 2025", "Remoto - 2024"])

# Valores disponíveis (com segurança caso coluna não exista)
anos_disponiveis = sorted(df['ano'].dropna().unique().tolist()) if 'ano' in df.columns else []
senioridades_disponiveis = sorted(df['senioridade'].dropna().unique().tolist()) if 'senioridade' in df.columns else []
contratos_disponiveis = sorted(df['contrato'].dropna().unique().tolist()) if 'contrato' in df.columns else []
tamanhos_disponiveis = sorted(df['tamanho_empresa'].dropna().unique().tolist()) if 'tamanho_empresa' in df.columns else []

# Inputs
anos_selecionados = st.sidebar.multiselect("Ano", anos_disponiveis, default=anos_disponiveis)
senioridades_selecionadas = st.sidebar.multiselect("Senioridade", senioridades_disponiveis, default=senioridades_disponiveis)
contratos_selecionados = st.sidebar.multiselect("Tipo de Contrato", contratos_disponiveis, default=contratos_disponiveis)
tamanhos_selecionados = st.sidebar.multiselect("Tamanho da Empresa", tamanhos_disponiveis, default=tamanhos_disponiveis)

# Busca livre por cargo (texto)
query = st.sidebar.text_input("Buscar cargo (texto livre)")

# Aplicar presets (se escolhidos) — sobrescreve seleções para facilidade de uso
if preset == "Sênior 2025":
    if 2025 in anos_disponiveis:
        anos_selecionados = [2025]
    # tenta mapear senioridade que contenha 'senior'
    senioridades_selecionadas = [s for s in senioridades_disponiveis if 'senior' in str(s).lower()] or senioridades_disponiveis

if preset == "Remoto - 2024":
    if 2024 in anos_disponiveis:
        anos_selecionados = [2024]
    # assume que coluna 'remoto' exista e tenha valor tipo 'sim'/'remoto'
    contratos_selecionados = contratos_selecionados  # não altera contrato aqui

# Filtragem base
df_filtrado = df.copy()

if anos_selecionados:
    df_filtrado = df_filtrado[df_filtrado['ano'].isin(anos_selecionados)] if 'ano' in df_filtrado.columns else df_filtrado
if senioridades_selecionadas:
    df_filtrado = df_filtrado[df_filtrado['senioridade'].isin(senioridades_selecionadas)] if 'senioridade' in df_filtrado.columns else df_filtrado
if contratos_selecionados:
    df_filtrado = df_filtrado[df_filtrado['contrato'].isin(contratos_selecionados)] if 'contrato' in df_filtrado.columns else df_filtrado
if tamanhos_selecionados:
    df_filtrado = df_filtrado[df_filtrado['tamanho_empresa'].isin(tamanhos_selecionados)] if 'tamanho_empresa' in df_filtrado.columns else df_filtrado

# Aplicar busca por texto no cargo (usando cargo_norm)
if query:
    qn = normalize_title(query)
    df_filtrado = df_filtrado[df_filtrado['cargo_norm'].str.contains(qn, na=False)]

st.title("🎲 Dashboard de Análise de Salários na Área de Dados")
st.markdown("Explore os dados salariais na área de dados nos últimos anos. Utilize os filtros à esquerda para refinar sua análise.")
st.info("Dica: use os presets para filtrar rapidamente. Use a busca por cargo para encontrar termos parciais como 'data', 'engenheiro', 'analista'.")

st.subheader("Métricas gerais (Salário anual em USD)")

# Métricas seguras
salario_medio = 0.0
salario_maximo = 0.0
total_registros = 0
cargo_mais_frequente = ""

year_metric = None

if not df_filtrado.empty:
    if 'usd' in df_filtrado.columns:
        salario_medio = df_filtrado['usd'].mean()
        salario_maximo = df_filtrado['usd'].max()
    total_registros = df_filtrado.shape[0]
    try:
        cargo_mais_frequente = df_filtrado["cargo"].mode().iloc[0]
    except Exception:
        cargo_mais_frequente = ""

# Cálculo YoY simples (último ano vs anterior) se houver coluna 'ano'
if (not df_filtrado.empty) and ('ano' in df_filtrado.columns) and ('usd' in df_filtrado.columns):
    medias_por_ano = df_filtrado.groupby('ano')['usd'].mean().sort_index()
    if len(medias_por_ano) >= 2:
        last = medias_por_ano.iloc[-1]
        prev = medias_por_ano.iloc[-2]
        try:
            delta = (last - prev) / prev if prev != 0 else 0
            year_metric = (last, delta)
        except Exception:
            year_metric = (last, 0)

col1, col2, col3, col4 = st.columns(4)
col1.metric("Salário médio", f"${salario_medio:,.0f}")
col2.metric("Salário máximo", f"${salario_maximo:,.0f}")
col3.metric("Total de registros", f"{total_registros:,}")
col4.metric("Cargo mais frequente", cargo_mais_frequente)

# Mostrar métrica YoY separada
if year_metric:
    last, delta = year_metric
    st.metric("Média salarial (último ano)", f"${last:,.0f}", f"{delta:+.1%}")

st.markdown("---")
st.subheader("Gráficos")

col_graf1, col_graf2 = st.columns(2)

with col_graf1:
    if not df_filtrado.empty and 'usd' in df_filtrado.columns and 'cargo' in df_filtrado.columns:
        top_cargos = df_filtrado.groupby('cargo')['usd'].mean().nlargest(10).sort_values(ascending=True).reset_index()
        grafico_cargos = px.bar(
            top_cargos,
            x='usd',
            y='cargo',
            orientation='h',
            title="Top 10 cargos por salário médio",
            labels={'usd': 'Média salarial anual (USD)', 'cargo': ''}
        )
        grafico_cargos.update_layout(title_x=0.1, yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(grafico_cargos, use_container_width=True)
    else:
        st.warning("Nenhum dado para exibir no gráfico de cargos.")

with col_graf2:
    if not df_filtrado.empty and 'usd' in df_filtrado.columns:
        grafico_hist = px.histogram(
            df_filtrado,
            x='usd',
            nbins=30,
            title="Distribuição de salários anuais",
            labels={'usd': 'Faixa salarial (USD)', 'count': ''}
        )
        grafico_hist.update_layout(title_x=0.1)
        st.plotly_chart(grafico_hist, use_container_width=True)
    else:
        st.warning("Nenhum dado para exibir no gráfico de distribuição.")

col_graf3, col_graf4 = st.columns(2)

with col_graf3:
    if not df_filtrado.empty and 'remoto' in df_filtrado.columns:
        remoto_contagem = df_filtrado['remoto'].value_counts().reset_index()
        remoto_contagem.columns = ['tipo_trabalho', 'quantidade']
        grafico_remoto = px.pie(
            remoto_contagem,
            names='tipo_trabalho',
            values='quantidade',
            title='Proporção dos tipos de trabalho',
            hole=0.5
        )
        grafico_remoto.update_traces(textinfo='percent+label')
        grafico_remoto.update_layout(title_x=0.1)
        st.plotly_chart(grafico_remoto, use_container_width=True)
    else:
        st.warning("Nenhum dado para exibir no gráfico dos tipos de trabalho.")

with col_graf4:
    if (not df_filtrado.empty) and ('residencia_iso3' in df_filtrado.columns) and ('cargo' in df_filtrado.columns):
        df_ds = df_filtrado[df_filtrado['cargo'] == 'Data Scientist']
        if not df_ds.empty:
            media_ds_pais = df_ds.groupby('residencia_iso3')['usd'].mean().reset_index()
            grafico_paises = px.choropleth(media_ds_pais,
                locations='residencia_iso3',
                color='usd',
                color_continuous_scale='RdYlGn',
                title='Salário médio de Cientista de Dados por país',
                labels={'usd': 'Salário médio (USD)', 'residencia_iso3': 'País'})
            grafico_paises.update_layout(title_x=0.1)
            st.plotly_chart(grafico_paises, use_container_width=True)
        else:
            st.warning("Nenhum registro de 'Data Scientist' na seleção atual.")
    else:
        st.warning("Nenhum dado para exibir no gráfico de países.")

st.subheader("Dados Detalhados")
# botão para baixar os dados filtrados
try:
    csv_bytes = df_filtrado.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Baixar dados filtrados (CSV)",
        data=csv_bytes,
        file_name="dados_filtrados.csv",
        mime="text/csv"
    )
except Exception:
    st.info("Falha ao gerar CSV para download.")

st.dataframe(df_filtrado)

st.caption("Código: adaptado para melhor performance (cache), busca por cargo, presets e download dos dados filtrados.")
