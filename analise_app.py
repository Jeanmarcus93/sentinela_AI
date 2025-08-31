
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date
from sqlalchemy import create_engine, text
from config import DB_CONFIG

# ---------------- Utils ----------------

def get_engine():
    return create_engine(
        f"postgresql+psycopg2://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['dbname']}"
    )

def ensure_schema():
    """Garante que a coluna 'ilicito' exista em passagens."""
    try:
        engine = get_engine()
        with engine.begin() as conn:
            conn.execute(text("""
                ALTER TABLE passagens
                ADD COLUMN IF NOT EXISTS ilicito BOOLEAN DEFAULT FALSE;
            """))
    except Exception as e:
        st.warning(f"Não foi possível validar o esquema: {e}")

def carregar_dados(query: str, params=None) -> pd.DataFrame:
    engine = get_engine()
    with engine.connect() as conn:
        return pd.read_sql(text(query), conn, params=params)

# ---------------- App ----------------

st.set_page_config(page_title="Análise de Veículos", layout="wide")
st.title("📊 Dashboard de Análise de Veículos e Passagens")

ensure_schema()

# ---- Análise de Passagens Ilícitas (no topo) ----
st.header("🚨 Análise de Passagens com Ilícitos")
df_ilicitos = carregar_dados(
    """
    SELECT municipio, rodovia, EXTRACT(HOUR FROM datahora) AS hora, EXTRACT(DOW FROM datahora) AS dow
    FROM passagens
    WHERE ilicito IS TRUE;
    """
)

if df_ilicitos.empty:
    st.info("Nenhum ilícito registrado ainda.")
else:
    total_ilicitos = len(df_ilicitos)
    st.metric("Total de passagens com ilícitos", total_ilicitos)

    # Municípios
    df_mun = df_ilicitos.groupby("municipio").size().reset_index(name="total").sort_values("total", ascending=False).head(10)
    fig_mun = px.bar(df_mun, x="municipio", y="total", title="Top Municípios (Ilícitos)")
    st.plotly_chart(fig_mun, width="stretch")

    # Rodovias
    df_rodo = df_ilicitos.groupby("rodovia").size().reset_index(name="total").sort_values("total", ascending=False).head(10)
    fig_rodo = px.bar(df_rodo, x="rodovia", y="total", title="Top Rodovias (Ilícitos)")
    st.plotly_chart(fig_rodo, width="stretch")

    # Horários
    df_hora = df_ilicitos.groupby("hora").size().reset_index(name="total")
    fig_hora = px.bar(df_hora, x="hora", y="total", title="Horários de Movimento (Ilícitos)")
    st.plotly_chart(fig_hora, width="stretch")

    # Dias da semana
    dias_map = {0: "Domingo", 1: "Segunda", 2: "Terça", 3: "Quarta", 4: "Quinta", 5: "Sexta", 6: "Sábado"}
    df_ilicitos["dow"] = df_ilicitos["dow"].astype(int).map(dias_map)
    df_dow = df_ilicitos.groupby("dow").size().reset_index(name="total")
    fig_dow = px.bar(df_dow, x="dow", y="total", title="Movimento por Dia da Semana (Ilícitos)")
    st.plotly_chart(fig_dow, width="stretch")

# ---- Análise por Município (geral) ----
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
fig1 = px.bar(df_municipios, x="municipio", y="total", title="Top 10 Municípios (Geral)")
st.plotly_chart(fig1, width="stretch")

# ---- Rodovias (geral) ----
st.header("Rodovias mais frequentes (geral)")
df_rodovia = carregar_dados(
    """
    SELECT rodovia, COUNT(*) as total
    FROM passagens
    GROUP BY rodovia
    ORDER BY total DESC
    LIMIT 10;
    """
)
fig2 = px.bar(df_rodovia, x="rodovia", y="total", title="Top 10 Rodovias (Geral)")
st.plotly_chart(fig2, width="stretch")

# ---- Horários (geral) ----
st.header("Horários de maior movimento (geral)")
df_horarios = carregar_dados(
    """
    SELECT EXTRACT(HOUR FROM datahora) AS hora, COUNT(*) AS total
    FROM passagens
    GROUP BY hora
    ORDER BY hora;
    """
)
fig3 = px.bar(df_horarios, x="hora", y="total",
              title="Movimento por Hora do Dia (Geral)",
              labels={"hora": "Hora do Dia", "total": "Quantidade de Passagens"})
st.plotly_chart(fig3, width="stretch")

# ---- Dias da semana (geral) ----
st.header("Movimento por Dia da Semana (geral)")
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
fig4 = px.bar(df_dias, x="dia_semana", y="total",
              title="Movimento por Dia da Semana (Geral)",
              labels={"dia_semana": "Dia da Semana", "total": "Quantidade de Passagens"})
st.plotly_chart(fig4, width="stretch")

# ---- Inserção Manual de Ilícitos (individual e em lote) ----
st.header("✍️ Inserção Manual de Dados de Ilícitos (individual e em lote)")

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
        WHERE p.veiculo_id = (SELECT id FROM veiculos WHERE placa = :placa)
        """
    )
    params = {"placa": placa_escolhida}

    if data_inicio and data_fim:
        query_passagens += " AND p.datahora::date BETWEEN :data_inicio AND :data_fim"
        params.update({"data_inicio": data_inicio, "data_fim": data_fim})

    query_passagens += " ORDER BY p.datahora DESC"

    df_passagens = carregar_dados(query_passagens, params=params)

    if not df_passagens.empty:
        # Preparar dados para a tabela editável com checkbox por linha
        df_edit = df_passagens.copy()
        df_edit["Data/Hora"] = pd.to_datetime(df_edit["datahora"]).dt.strftime("%d/%m/%Y %H:%M:%S")
        df_edit = df_edit[["id", "Data/Hora", "municipio", "rodovia", "ilicito"]]
        df_edit.rename(columns={"ilicito": "Selecionado (ilícito)"}, inplace=True)

        # Caixa "selecionar todas"
        selecionar_todas = st.checkbox("Selecionar todas as passagens do intervalo", value=False)

        if selecionar_todas:
            df_edit["Selecionado (ilícito)"] = True

        edited = st.data_editor(
            df_edit,
            width="stretch",
            hide_index=True,
            num_rows="fixed",
            column_config={
                "id": st.column_config.NumberColumn("ID", disabled=True),
                "Data/Hora": st.column_config.TextColumn("Data/Hora", disabled=True),
                "municipio": st.column_config.TextColumn("Município", disabled=True),
                "rodovia": st.column_config.TextColumn("Rodovia", disabled=True),
                "Selecionado (ilícito)": st.column_config.CheckboxColumn("Selecionado (ilícito)"),
            },
            key="editor_passagens"
        )

        # IDs selecionados
        ids_selecionados = [int(row["id"]) for _, row in edited.iterrows() if row["Selecionado (ilícito)"]]

        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("Marcar selecionados como ILÍCITO"):
                if ids_selecionados:
                    engine = get_engine()
                    with engine.begin() as conn:
                        conn.execute(text("UPDATE passagens SET ilicito = TRUE WHERE id = ANY(:ids)"), {"ids": ids_selecionados})
                    st.success(f"✅ {len(ids_selecionados)} passagens marcadas como ilícito.")
                    st.rerun()
                else:
                    st.warning("Selecione pelo menos uma passagem.")

        with col_b:
            if st.button("Desmarcar selecionados (não ilícito)"):
                if ids_selecionados:
                    engine = get_engine()
                    with engine.begin() as conn:
                        conn.execute(text("UPDATE passagens SET ilicito = FALSE WHERE id = ANY(:ids)"), {"ids": ids_selecionados})
                    st.success(f"✅ {len(ids_selecionados)} passagens desmarcadas.")
                    st.rerun()
                else:
                    st.warning("Selecione pelo menos uma passagem.")
    else:
        st.info("Nenhuma passagem encontrada para este veículo nesse intervalo de datas.")
else:
    st.info("Selecione uma placa para listar as passagens.")
