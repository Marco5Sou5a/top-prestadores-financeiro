import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text

# ======================================================
# CONFIGURAÇÃO DA PÁGINA
# ======================================================
st.set_page_config(
    page_title="Top Prestadores",
    layout="centered"
)

st.title("🏆 Top Prestadores de Serviços")
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

def carregar_meses():
    query = """
        select distinct mes_referencia
        from vw_top_prestadores
        order by mes_referencia desc
    """
    return pd.read_sql(query, engine)

def carregar_top_prestadores(mes, top_n):
    query = text("""
        select
            prestador,
            total_pago
        from vw_top_prestadores
        where mes_referencia = :mes
        order by total_pago desc
        limit :top_n
    """)
    df = pd.read_sql(
        query,
        engine,
        params={"mes": mes, "top_n": top_n}
    )

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
    df = pd.read_sql(
        query,
        engine,
        params={"mes": mes, "top_n": top_n}
    )
    return df.iloc[0]["total"] or 0

# ======================================================
# CONTROLES DE INTERFACE
# ======================================================
df_meses = carregar_meses()

if df_meses.empty:
    st.warning("Nenhum dado encontrado no banco.")
    st.stop()

mes_selecionado = st.selectbox(
    "📅 Selecione o mês de referência",
    df_meses["mes_referencia"].dt.strftime("%Y-%m").tolist()
)

top_n = st.selectbox(
    "🔢 Quantidade de prestadores (Top N)",
    [5, 10, 20, 50],
    index=1
)

# Converter mês para date
mes_data = pd.to_datetime(mes_selecionado + "-01")

# ======================================================
# EXECUÇÃO
# ======================================================
if st.button("▶ Gerar Ranking"):
    resultado = carregar_top_prestadores(mes_data, top_n)
    total_sem_agua = total_sem_agua_do_cernes(mes_data, top_n)

    st.success("Ranking gerado com sucesso!")

    # Tabela sem índice
    st.dataframe(
        resultado.reset_index(drop=True),
        use_container_width=True
    )

    st.markdown(
        f"### 💰 Total geral dos Top {top_n} (sem Água do Cernes): "
        f"**{formatar_real(total_sem_agua)}**"
    )

    st.caption("📌 VIEW oficial: vw_top_prestadores")
