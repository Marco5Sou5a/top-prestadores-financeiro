import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text

# ======================================================
# CONFIGURAÇÃO DA PÁGINA
# ======================================================
st.set_page_config(
    page_title="Análises Financeiras",
    layout="centered"
)

st.title("📊 Análises Financeiras")
st.caption("Dados oficiais direto do Supabase")

# ======================================================
# CONEXÃO COM SUPABASE
# ======================================================
@st.cache_resource
def get_engine():
    return create_engine(
        st.secrets["DATABASE_URL"],
        connect_args={"sslmode": "require"}
    )

engine = get_engine()

# ======================================================
# FUNÇÕES AUXILIARES
# ======================================================
def formatar_real(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# ======================================================
# FUNÇÕES — TOP PRESTADORES
# ======================================================
def carregar_meses():
    query = """
        select distinct mes_referencia
        from vw_top_prestadores
        order by mes_referencia desc
    """
    return pd.read_sql(query, engine)

def carregar_top_prestadores(mes, top_n):
    query = text("""
        select prestador, total_pago
        from vw_top_prestadores
        where mes_referencia = :mes
        order by total_pago desc
        limit :top_n
    """)
    df = pd.read_sql(query, engine, params={"mes": mes, "top_n": top_n})
    df["Total Pago (R$)"] = df["total_pago"].apply(formatar_real)
    return df[["prestador", "Total Pago (R$)"]]

def total_sem_agua_do_cernes(mes, top_n):
    query = text("""
        select sum(total_pago) as total
        from (
            select prestador, total_pago
            from vw_top_prestadores
            where mes_referencia = :mes
            order by total_pago desc
            limit :top_n
        ) t
        where prestador <> 'Agua do Cernes (Levy)'
    """)
    df = pd.read_sql(query, engine, params={"mes": mes, "top_n": top_n})
    return df.iloc[0]["total"] or 0

# ======================================================
# FUNÇÕES — COMPARATIVO MENSAL POR CATEGORIA
# ======================================================
def carregar_comparativo_categoria():
    query = """
        select
            date_trunc('month', data_pagamento) as mes,
            categoria,
            sum(abs(valor)) as total_pago
        from pagamentos
        where data_pagamento is not null
        group by mes, categoria
        order by mes desc, total_pago desc
    """
    return pd.read_sql(query, engine)

# ======================================================
# INTERFACE — ABAS
# ======================================================
aba1, aba2 = st.tabs(["🏆 Top Prestadores", "📈 Comparativo Mensal"])

# ======================================================
# ABA 1 — TOP PRESTADORES
# ======================================================
with aba1:
    df_meses = carregar_meses()

    if df_meses.empty:
        st.warning("Nenhum dado encontrado.")
        st.stop()

    mes_selecionado = st.selectbox(
        "📅 Selecione o mês",
        df_meses["mes_referencia"].dt.strftime("%Y-%m").tolist()
    )

    top_n = st.selectbox(
        "🔢 Top N",
        [5, 10, 20, 50],
        index=1
    )

    mes_data = pd.to_datetime(mes_selecionado + "-01")

    if st.button("▶ Gerar Top Prestadores"):
        resultado = carregar_top_prestadores(mes_data, top_n)
        total_sem_agua = total_sem_agua_do_cernes(mes_data, top_n)

        st.success("Ranking gerado com sucesso!")

        st.dataframe(
            resultado.reset_index(drop=True),
            use_container_width=True
        )

        st.markdown(
            f"### 💰 Total geral dos Top {top_n} (sem Água do Cernes): "
            f"**{formatar_real(total_sem_agua)}**"
        )

# ======================================================
# ABA 2 — COMPARATIVO MENSAL POR CATEGORIA
# ======================================================
with aba2:
    st.subheader("📈 Comparativo Mensal por Categoria")

    df_comp = carregar_comparativo_categoria()

    if df_comp.empty:
        st.warning("Nenhum dado encontrado.")
        st.stop()

    # Filtros
    categorias = st.multiselect(
        "Selecione as categorias",
        sorted(df_comp["categoria"].dropna().unique()),
        default=None
    )

    if categorias:
        df_comp = df_comp[df_comp["categoria"].isin(categorias)]

    # Pivot para visualização
    df_pivot = (
        df_comp
        .pivot_table(
            index="mes",
            columns="categoria",
            values="total_pago",
            aggfunc="sum"
        )
        .fillna(0)
        .sort_index()
    )

    st.dataframe(
        df_pivot.applymap(formatar_real),
        use_container_width=True
    )

    st.line_chart(df_pivot)

    st.caption("📌 Valores absolutos • Base: data_pagamento • Supabase")

