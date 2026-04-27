import streamlit as st
import pandas as pd
import plotly.express as px
import os
import numpy as np

# ---------------- CONFIGURAÇÃO DA PÁGINA ----------------
st.set_page_config(page_title="Análise Técnica SNIS", layout="wide")

# ---------------- CARREGAMENTO E MAPEAMENTO ----------------
@st.cache_data
def load_data():
    caminho = os.path.join(os.path.dirname(__file__), "br_mdr_snis_municipio_agua_esgoto.csv")
    df = pd.read_csv(caminho)
    
    # Mapeamento de Regiões
    regioes = {
        'Norte': ['AC', 'AM', 'AP', 'PA', 'RO', 'RR', 'TO'],
        'Nordeste': ['AL', 'BA', 'CE', 'MA', 'PB', 'PE', 'PI', 'RN', 'SE'],
        'Centro-Oeste': ['DF', 'GO', 'MT', 'MS'],
        'Sudeste': ['ES', 'MG', 'RJ', 'SP'],
        'Sul': ['PR', 'RS', 'SC']
    }
    
    # Inversão do dicionário para mapeamento
    uf_to_regiao = {uf: regiao for regiao, ufs in regioes.items() for uf in ufs}
    df['regiao'] = df['sigla_uf'].map(uf_to_regiao)
    
    return df

df = load_data()

# ---------------- SIDEBAR: FILTROS AVANÇADOS ----------------
st.sidebar.header("Parâmetros de Análise")

# Filtro Temporal
anos = sorted(df['ano'].unique(), reverse=True)
ano_sel = st.sidebar.selectbox("Ano de Referência", anos)

# Filtro Regional (Hierárquico)
regioes_disponiveis = sorted(df['regiao'].dropna().unique())
regiao_sel = st.sidebar.multiselect("Regiões", regioes_disponiveis, default=regioes_disponiveis)

# Filtro de Estados (Dinâmico com base na Região)
ufs_disponiveis = sorted(df[df['regiao'].isin(regiao_sel)]['sigla_uf'].unique())
uf_sel = st.sidebar.multiselect("Estados (UF)", ufs_disponiveis, default=ufs_disponiveis)

# Filtro de Medidas Extremas
st.sidebar.divider()
remover_outliers = st.sidebar.toggle("Remover Valores Extremos (Outliers)")

# ---------------- PROCESSAMENTO DE DADOS ----------------
df_filt = df[
    (df['ano'] == ano_sel) &
    (df['regiao'].isin(regiao_sel)) &
    (df['sigla_uf'].isin(uf_sel))
].copy()

# Lógica de Outliers (Método IQR)
if remover_outliers and not df_filt.empty:
    def filter_iqr(dataframe, column):
        q1 = dataframe[column].quantile(0.25)
        q3 = dataframe[column].quantile(0.75)
        iqr = q3 - q1
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        return dataframe[(dataframe[column] >= lower) & (dataframe[column] <= upper)]
    
    # Aplicando na variável principal de atendimento
    df_filt = filter_iqr(df_filt, 'populacao_atendida_agua')

# Cálculos de Cobertura
df_filt["perc_esgoto"] = (df_filt["populacao_atentida_esgoto"] / df_filt["populacao_atendida_agua"] * 100).clip(0, 100)

# ---------------- INTERFACE PRINCIPAL ----------------
st.title("Relatório Técnico de Saneamento Municipal")
st.caption("Base de dados: SNIS (Sistema Nacional de Informações sobre Saneamento)")

# ---------------- FUNÇÃO DE FORMATAÇÃO ----------------
def formatar_numero(valor):
    """
    Abrevia valores na casa dos milhões (ex: 112.7M) e retorna o valor exato formatado.
    Mantém valores menores intactos.
    """
    valor_exato = f"{valor:,.0f}".replace(",", ".")
    
    if valor >= 1000000:
        # Divide por 1 milhão e coloca 1 casa decimal
        valor_abrev = f"{valor / 1000000:.1f}M".replace(".", ",")
    else:
        # Se for mil ou cem mil, mantém o número inteiro com os pontos
        valor_abrev = valor_exato
        
    return valor_abrev, valor_exato

# ---------------- INDICADORES DE DESEMPENHO (KPIs) ----------------
col_m1, col_m2, col_m3, col_m4 = st.columns(4)

with col_m1:
    soma_agua = df_filt['populacao_atendida_agua'].sum()
    abrev_agua, exato_agua = formatar_numero(soma_agua)
    
    st.metric(
        label="População com Água", 
        value=abrev_agua,
        help=f"Valor exato: {exato_agua} habitantes" # O hover (tooltip) entra aqui!
    )
    
with col_m2:
    soma_esgoto = df_filt['populacao_atentida_esgoto'].sum()
    abrev_esgoto, exato_esgoto = formatar_numero(soma_esgoto)
    
    st.metric(
        label="População com Esgoto", 
        value=abrev_esgoto,
        help=f"Valor exato: {exato_esgoto} habitantes"
    )
    
with col_m3:
    mediana = df_filt['perc_esgoto'].median()
    # A porcentagem é mantida exatamente como você instruiu
    st.metric(
        label="Mediana de Cobertura", 
        value=f"{mediana:.1f}%",
        help="Valor central da cobertura de esgoto (ignora os extremos)."
    )
    
with col_m4:
    total_municipios = len(df_filt)
    # Valores menores (milhares) também ficam intactos
    abrev_mun, exato_mun = formatar_numero(total_municipios)
    
    st.metric(
        label="Municípios Analisados", 
        value=abrev_mun
    )

st.divider()

# Organização por Abas para clareza analítica
tab_dist, tab_corr, tab_ranking = st.tabs(["Distribuição Regional", "Correlação e Densidade", "Rankings de Eficiência"])

with tab_dist:
    col_a, col_b = st.columns(2)
    
    with col_a:
        st.subheader("Cobertura de Esgoto por UF")
        df_uf = df_filt.groupby("sigla_uf").agg({
            "populacao_atendida_agua": "sum",
            "populacao_atentida_esgoto": "sum"
        }).reset_index()
        df_uf["perc"] = (df_uf["populacao_atentida_esgoto"] / df_uf["populacao_atendida_agua"] * 100)
        
        fig_bar = px.bar(df_uf.sort_values("perc"), x="perc", y="sigla_uf", orientation="h",
                         template="plotly_white", color="perc", color_continuous_scale="Blues")
        fig_bar.update_layout(coloraxis_showscale=False, xaxis_title="Cobertura (%)", yaxis_title="")
        st.plotly_chart(fig_bar, use_container_width=True)

    with col_b:
        st.subheader("Variabilidade por Estado")
        fig_box = px.box(df_filt, x="sigla_uf", y="perc_esgoto", template="plotly_white", points="outliers")
        fig_box.update_layout(xaxis_title="", yaxis_title="Percentual de Cobertura (%)")
        st.plotly_chart(fig_box, use_container_width=True)

with tab_corr:
    col_c, col_d = st.columns(2)
    
    with col_c:
        st.subheader("Concentração Municipal (Densidade)")
        # NOVO GRÁFICO 1: Histograma de Densidade
        fig_hist = px.histogram(df_filt, x="perc_esgoto", nbins=20, marginal="rug",
                               template="plotly_white", color_discrete_sequence=['#3176bb'])
        fig_hist.update_layout(xaxis_title="Faixa de Cobertura de Esgoto (%)", yaxis_title="Frequência (Municípios)")
        st.plotly_chart(fig_hist, use_container_width=True)

    with col_d:
        st.subheader("Correlação: Água vs Esgoto")
        # NOVO GRÁFICO 2: Scatter Plot com Linha de Tendência
        fig_scat = px.scatter(df_filt, x="populacao_atendida_agua", y="populacao_atentida_esgoto",
                             trendline="ols", template="plotly_white", opacity=0.5,
                             labels={'populacao_atendida_agua': 'Pop. Água', 'populacao_atentida_esgoto': 'Pop. Esgoto'})
        st.plotly_chart(fig_scat, use_container_width=True)

with tab_ranking:
    st.subheader("Análise Comparativa de Extremos")
    top_uf = df_uf.sort_values("perc", ascending=False).head(5)
    bottom_uf = df_uf.sort_values("perc").head(5)
    
    col_top, col_bot = st.columns(2)
    with col_top:
        st.markdown("**Maiores Índices de Cobertura por UF**")
        st.table(top_uf[["sigla_uf", "perc"]].rename(columns={"sigla_uf": "Estado", "perc": "% Cobertura"}))
    
    with col_bot:
        st.markdown("**Menores Índices de Cobertura por UF**")
        st.table(bottom_uf[["sigla_uf", "perc"]].rename(columns={"sigla_uf": "Estado", "perc": "% Cobertura"}))

# ---------------- TABELA DE DADOS ----------------
with st.expander("Visualizar Base de Dados Detalhada"):
    st.dataframe(df_filt, use_container_width=True, hide_index=True)