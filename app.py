import streamlit as st
from sqlalchemy import create_engine, text

st.title("Teste de Conexão Supabase")

engine = create_engine(
    st.secrets["DATABASE_URL"],
    connect_args={"sslmode": "require"}
)

with engine.connect() as conn:
    conn.execute(text("select 1"))

st.success("✅ Conectado com sucesso ao Supabase!")
