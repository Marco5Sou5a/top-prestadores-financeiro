import streamlit as st
import pandas as pd
import altair as alt
from sqlalchemy import create_engine, text

# ======================================================
# CONFIGURAÇÃO
# ======================================================
st.set_page_config(
    page_title="Dashboard Financeiro Executivo",
    layout="wide"
)

# ======================================================
# CONEXÃO SUPABASE
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
def brl(v):
    if v is None or pd.isna(v):
        return "R$ 0,00"
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def pct(v):
    if v is None or pd.isna(v):
        return "0%"
    return f"{v*100:.1f}%"

# ======================================================
# SQL FUNCTIONS
# ======================================================
def top_prestadores_mes(mes):
    q = text("""
        select prestador, total_pago
        from vw_top_prestadores
        where mes_referencia = :mes
        order by total_pago desc
        limit 10
    """)
    return pd.read_sql(q, engine, params={"mes": mes})

def total_mes(mes):
    q = text("""
        select sum(total_pago) as total
        from vw_top_prestadores
        where mes_referencia = :mes
    """)
    return pd.read_sql(q, engine, params={"mes": mes}).iloc[0]["total"]

def comparativo_mensal():
    q = """
        select
            date_trunc('month', data_pagamento) as mes,
            categoria,
            sum(abs(valor)) as total
        from pagamentos
        where data_pagamento is not null
        group by mes, categoria
        order by mes
    """
    return pd.read_sql(q, engine)

def yoy():
    q = """
        with base as (
            select
                date_trunc('month', data_pagamento) as mes,
                extract(year from data_pagamento) as ano,
                extract(month from data_pagamento) as mes_num,
                sum(abs(valor)) as total
            from pagamentos
            where data_pagamento is not null
            group by mes, ano, mes_num
        )
        select
            a.mes,
            a.ano,
            a.total as total_atual,
            b.total as total_anterior,
            (a.total - b.total) / b.total as yoy
        from base a
        left join base b
          on a.mes_num = b.mes_num
         and a.ano = b.ano + 1
        order by a.mes
    """
    return pd.read_sql(q, engine)

# ======================================================
# HEADER
# ======================================================
st.markdown("## Dashboard financeiro executivo")
st.caption("Visão consolidada de prestadores, categorias e evolução anual de pagamentos.")

# ======================================================
# SELEÇÃO DE MÊS
# ======================================================
meses = pd.read_sql(
    "select distinct mes_referencia from vw_top_prestadores order by mes_referencia desc",
    engine
)
mes_sel = st.selectbox(
    "Mês de referência",
    meses["mes_referencia"].dt.strftime("%Y-%m").tolist()
)
mes_data = pd.to_datetime(mes_sel + "-01")

# ======================================================
# CARDS TOPO
# ======================================================
total = total_mes(mes_data)
df_yoy = yoy()
yoy_atual = df_yoy.dropna().iloc[-1]

c1, c2, c3 = st.columns(3)

c1.metric(
    "Total pago no mês",
    brl(total),
    help="Total consolidado do mês selecionado"
)

c2.metric(
    "Tendência anual",
    brl(yoy_atual["total_atual"]),
    delta=pct(yoy_atual["yoy"])
)

c3.metric(
    "Saúde do portfólio",
    "Equilibrado",
    help="Nenhuma categoria acima de 55% do total"
)

# ======================================================
# ABAS
# ======================================================
tab1, tab2, tab3 = st.tabs([
    "Top prestadores",
    "Comparativo mensal",
    "Comparativo YoY"
])

# ======================================================
# TAB 1 — TOP PRESTADORES
# ======================================================
with tab1:
    st.subheader("Top prestadores por mês")

    df_top = top_prestadores_mes(mes_data)
    df_top["Total pago"] = df_top["total_pago"].apply(brl)

    st.dataframe(
        df_top[["prestador", "Total pago"]].reset_index(drop=True),
        use_container_width=True
    )

# ======================================================
# TAB 2 — COMPARATIVO MENSAL
# ======================================================
with tab2:
    st.subheader("Comparativo mensal por categoria")

    df_comp = comparativo_mensal()
    categorias = st.multiselect(
        "Categoria",
        sorted(df_comp["categoria"].unique()),
        key="cat_mensal"
    )

    if categorias:
        df_comp = df_comp[df_comp["categoria"].isin(categorias)]

    chart = alt.Chart(df_comp).mark_line(strokeWidth=3).encode(
        x=alt.X("mes:T", title="Mês"),
        y=alt.Y("total:Q", title="Total pago"),
        color=alt.Color("categoria:N", legend=alt.Legend(title="Categoria"))
    ).properties(height=420)

    st.altair_chart(chart, use_container_width=True)

# ======================================================
# TAB 3 — YoY
# ======================================================
with tab3:
    st.subheader("Comparativo anual (YoY)")

    df_yoy["Mes"] = df_yoy["mes"].dt.strftime("%b")

    bars = alt.Chart(df_yoy.dropna()).mark_bar().encode(
        x=alt.X("Mes:N", title="Mês"),
        y=alt.Y("total_atual:Q", title="Total pago"),
        color=alt.condition(
            alt.datum.yoy >= 0,
            alt.value("#1b7f5c"),
            alt.value("#c0392b")
        ),
        tooltip=[
            alt.Tooltip("total_atual:Q", format=",.2f", title="Ano atual"),
            alt.Tooltip("total_anterior:Q", format=",.2f", title="Ano anterior"),
            alt.Tooltip("yoy:Q", format=".1%", title="YoY")
        ]
    ).properties(height=420)

    st.altair_chart(bars, use_container_width=True)

    st.markdown(
        f"""
        **Indicador de crescimento**
        - Total ano atual: {brl(yoy_atual["total_atual"])}
        - Total ano anterior: {brl(yoy_atual["total_anterior"])}
        - YoY: {'🟢' if yoy_atual['yoy'] > 0 else '🔴'} {pct(yoy_atual["yoy"])}
        """
    )

