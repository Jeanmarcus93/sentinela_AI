
import streamlit as st
import psycopg2
import pandas as pd
import plotly.express as px
from datetime import date
from config import DB_CONFIG

# ---------------- Utils ----------------

def ensure_schema():
    """Garante que a coluna 'ilicito' exista em passagens."""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("""
            ALTER TABLE passagens
            ADD COLUMN IF NOT EXISTS ilicito BOOLEAN DEFAULT FALSE;
        """)
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        st.warning(f"Não foi possível validar o esquema: {e}")

def carregar_dados(query: str, params=None) -> pd.DataFrame:
    conn = psycopg2.connect(**DB_CONFIG)
    df = pd.read_sql(query, conn, params=params)
    conn.close()
    return df

# ---------------- App ----------------

st.set_page_config(page_title="Análise de Veículos", layout="wide")
st.title("📊 Dashboard de Análise de Veículos e Passagens")

ensure_schema()

# ---- Análise por Município ----
st.header("Top Municípios com mais passagens")
df_municipios = carregar_dados(
    """
    SELECT municipio, COUNT(*) as total
    FROM passagens
    GROUP BY municipio
    ORDER BY total DESC
    LIMIT 10;
    """
)
fig1 = px.bar(df_municipios, x="municipio", y="total", title="Top 10 Municípios")
st.plotly_chart(fig1, use_container_width=True)

# ---- Distribuição de suspeitos ----
st.header("Distribuição de Veículos Suspeitos")
df_suspeitos = carregar_dados(
    """
    SELECT
        COUNT(*) FILTER (WHERE suspeito IS TRUE) AS suspeitos,
        COUNT(*) FILTER (WHERE suspeito IS FALSE) AS nao_suspeitos
    FROM veiculos;
    """
)
df_suspeitos = df_suspeitos.melt(var_name="Categoria", value_name="Quantidade")
fig2 = px.pie(df_suspeitos, names="Categoria", values="Quantidade",
              title="Veículos Suspeitos vs Não Suspeitos")
st.plotly_chart(fig2, use_container_width=True)

# ---- Rodovias ----
st.header("Rodovias mais frequentes")
df_rodovia = carregar_dados(
    """
    SELECT rodovia, COUNT(*) as total
    FROM passagens
    GROUP BY rodovia
    ORDER BY total DESC
    LIMIT 10;
    """
)
fig3 = px.bar(df_rodovia, x="rodovia", y="total", title="Top 10 Rodovias")
st.plotly_chart(fig3, use_container_width=True)

# ---- Horários de maior movimento ----
st.header("Horários de maior movimento dos alvos")
df_horarios = carregar_dados(
    """
    SELECT EXTRACT(HOUR FROM datahora) AS hora, COUNT(*) AS total
    FROM passagens
    GROUP BY hora
    ORDER BY hora;
    """
)
fig4 = px.bar(df_horarios, x="hora", y="total",
              title="Movimento por Hora do Dia",
              labels={"hora": "Hora do Dia", "total": "Quantidade de Passagens"})
st.plotly_chart(fig4, use_container_width=True)

# ---- Movimento por Dia da Semana ----
st.header("Movimento por Dia da Semana")
df_dias = carregar_dados(
    """
    SELECT EXTRACT(DOW FROM datahora) AS dia_semana, COUNT(*) AS total
    FROM passagens
    GROUP BY dia_semana
    ORDER BY dia_semana;
    """
)
dias_map = {0: "Domingo", 1: "Segunda", 2: "Terça", 3: "Quarta", 4: "Quinta", 5: "Sexta", 6: "Sábado"}
df_dias["dia_semana"] = df_dias["dia_semana"].astype(int).map(dias_map)
fig5 = px.bar(df_dias, x="dia_semana", y="total",
              title="Movimento por Dia da Semana",
              labels={"dia_semana": "Dia da Semana", "total": "Quantidade de Passagens"})
st.plotly_chart(fig5, use_container_width=True)

# ---- Inserção Manual de Ilícitos ----
st.header("✍️ Inserção Manual de Dados de Ilícitos")

# Selecionar veículo
df_veiculos = carregar_dados("SELECT id, placa FROM veiculos ORDER BY placa;")
placa_escolhida = st.selectbox("Selecione a placa do veículo", df_veiculos["placa"] if not df_veiculos.empty else [])

# Filtros de intervalo de datas com calendário
col1, col2 = st.columns(2)
with col1:
    data_inicio = st.date_input("Data inicial", value=date.today())
with col2:
    data_fim = st.date_input("Data final", value=date.today())

if placa_escolhida:
    query_passagens = (
        """
        SELECT p.id, p.datahora, p.municipio, p.rodovia, p.ilicito
        FROM passagens p
        WHERE p.veiculo_id = (SELECT id FROM veiculos WHERE placa = %s)
        """
    )
    params = [placa_escolhida]

    if data_inicio and data_fim:
        query_passagens += " AND p.datahora::date BETWEEN %s AND %s"
        params.extend([data_inicio, data_fim])

    query_passagens += " ORDER BY p.datahora DESC"

    df_passagens = carregar_dados(query_passagens, params=params)

    if not df_passagens.empty:
        # Formatar data para BR nas opções
        opcoes = df_passagens.apply(
            lambda row: f"{row['id']} | {pd.to_datetime(row['datahora']).strftime('%d/%m/%Y %H:%M:%S')} | {row['municipio']} | {row['rodovia']} | Ilícito: {row['ilicito']}",
            axis=1
        )
        passagem_escolhida = st.selectbox("Selecione a passagem", opcoes)

        ilicito_flag = st.checkbox("Marcar como transporte de ilícito", value=True)

        if st.button("Salvar"):
            passagem_id = int(passagem_escolhida.split("|")[0].strip())
            conn = psycopg2.connect(**DB_CONFIG)
            cur = conn.cursor()
            cur.execute("UPDATE passagens SET ilicito = %s WHERE id = %s;", (ilicito_flag, passagem_id))
            conn.commit()
            cur.close()
            conn.close()
            st.success("✅ Registro atualizado com sucesso!")
    else:
        st.info("Nenhuma passagem encontrada para este veículo nesse intervalo de datas.")
else:
    st.info("Selecione uma placa para listar as passagens.")
