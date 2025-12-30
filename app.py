import streamlit as st
from sqlalchemy import create_engine, text

st.set_page_config(page_title="Teste Supabase")

st.title("🔌 Teste de Conexão Supabase")

engine = create_engine(
    st.secrets["DATABASE_URL"],
    connect_args={"sslmode": "require"}
)

try:
    with engine.connect() as conn:
        conn.execute(text("select 1"))
    st.success("✅ Conectado com sucesso ao Supabase!")
except Exception as e:
    st.error("❌ Falha na conexão com o Supabase")
    st.exception(e)
