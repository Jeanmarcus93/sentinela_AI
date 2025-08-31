import streamlit as st
import psycopg
import pandas as pd
from config import DB_CONFIG

# ------------------ FUNÇÃO DE CONSULTA ------------------
def consultar_dados(placa):
    with psycopg.connect(**DB_CONFIG) as conn:
        # Veículo
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, placa, marca_modelo, tipo, ano_modelo, cor,
                       local_emplacamento, transferencia_recente, comunicacao_venda,
                       crime_prf, abordagem_prf
                FROM veiculos WHERE placa = %s;
            """, (placa,))
            veiculo = cur.fetchone()

        if not veiculo:
            return None

        veiculo_id = veiculo[0]

        # Pessoas
        with conn.cursor() as cur:
            cur.execute("""
                SELECT nome, cpf_cnpj, cnh, validade_cnh, local_cnh,
                       suspeito, relevante, proprietario, condutor, possuidor
                FROM pessoas WHERE veiculo_id = %s;
            """, (veiculo_id,))
            pessoas = cur.fetchall()

        # Passagens (já com datahora unificada)
        with conn.cursor() as cur:
            cur.execute("""
                SELECT estado, municipio, rodovia, datahora
                FROM passagens WHERE veiculo_id = %s ORDER BY datahora DESC;
            """, (veiculo_id,))
            passagens = cur.fetchall()

    return {"veiculo": veiculo, "pessoas": pessoas, "passagens": passagens}


# ------------------ ESTILO CUSTOM ------------------
st.set_page_config(page_title="Sentinela IA", layout="wide")

st.markdown("""
<style>
.container {
    max-width: 1200px;
    margin: auto;
}
.page-header {
    background: #1e3a8a; /* Azul sólido */
    color: white;
    padding: 1.2rem;
    border-radius: 10px;
    margin-bottom: 1.5rem;
    text-align: center;
}
.page-header h1 {
    margin: 0;
    font-size: 2rem;
    font-weight: bold;
}
.page-header p {
    margin: 0;
    font-size: 1rem;
}
.content-block {
    background: white;
    padding: 1rem;
    border-radius: 10px;
    box-shadow: 0px 3px 8px rgba(0,0,0,0.1);
    margin-bottom: 1.5rem;
}
.rule-box {
    background: #f9fafb;
    padding: 1rem;
    border: 1px solid #e5e7eb;
    border-radius: 10px;
    box-shadow: 0px 1px 3px rgba(0,0,0,0.1);
}
.rule-box h3 {
    margin-top: 0;
}
</style>
""", unsafe_allow_html=True)


# ------------------ INTERFACE ------------------
st.markdown('<div class="container">', unsafe_allow_html=True)
st.markdown('<div class="page-header"><h1>🚔 Sentinela IA</h1><p>Consulta de Veículos e Pessoas</p></div>', unsafe_allow_html=True)

placa = st.text_input("Digite a placa do veículo:", placeholder="Ex: ABC1234")

if placa:
    dados = consultar_dados(placa.upper())

    if not dados:
        st.error("❌ Nenhum dado encontrado para essa placa.")
    else:
        veiculo = dados["veiculo"]
        pessoas = dados["pessoas"]
        passagens = dados["passagens"]

        # ================== VEÍCULO ==================
        st.markdown('<div class="content-block">', unsafe_allow_html=True)
        st.markdown("### 🚘 Dados do Veículo")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"**Placa:** {veiculo[1]}")
            st.markdown(f"**Marca/Modelo:** {veiculo[2]}")
            st.markdown(f"**Tipo:** {veiculo[3]}")
            st.markdown(f"**Ano/Modelo:** {veiculo[4]}")
        with col2:
            st.markdown(f"**Cor:** {veiculo[5]}")
            st.markdown(f"**Local Emplacamento:** {veiculo[6]}")
            st.markdown(f"**Transferência Recente:** {veiculo[7] or '—'}")
            st.markdown(f"**Comunicação de Venda:** {veiculo[8] or '—'}")
        with col3:
            st.markdown(f"**Crime na PRF:** {veiculo[9] or '—'}")
            st.markdown(f"**Abordagem na PRF:** {veiculo[10] or '—'}")
        st.markdown('</div>', unsafe_allow_html=True)

        # ================== PESSOAS ==================
        st.markdown('<div class="content-block">', unsafe_allow_html=True)
        st.markdown("### 👥 Pessoas Relacionadas")

        cols = st.columns(len(pessoas) if pessoas else 1)
        if pessoas:
            for idx, pessoa in enumerate(pessoas):
                papel = "Proprietário" if pessoa[7] else "Condutor" if pessoa[8] else "Possuidor"
                with cols[idx]:
                    st.markdown('<div class="rule-box">', unsafe_allow_html=True)
                    st.markdown(f"#### 🔹 {papel}")
                    st.markdown(f"**Nome:** {pessoa[0]}")
                    st.markdown(f"**CPF/CNPJ:** {pessoa[1] or '—'}")
                    st.markdown(f"**CNH:** {pessoa[2] or '—'}")
                    st.markdown(f"**Validade CNH:** {pessoa[3] or '—'}")
                    st.markdown(f"**Local CNH:** {pessoa[4] or '—'}")
                    st.markdown(f"**Suspeito:** {pessoa[5]}")
                    st.markdown(f"**Relevante:** {pessoa[6]}")
                    st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.info("Nenhuma pessoa cadastrada para este veículo.")
        st.markdown('</div>', unsafe_allow_html=True)

        # ================== PASSAGENS ==================
        st.markdown('<div class="content-block">', unsafe_allow_html=True)
        st.markdown("### 📍 Passagens Registradas")
        if passagens:
            df_passagens = pd.DataFrame(passagens, columns=["Estado", "Município", "Rodovia", "Data/Hora"])
            df_passagens["Data/Hora"] = pd.to_datetime(df_passagens["Data/Hora"]).dt.strftime("%d/%m/%Y %H:%M:%S")
            st.dataframe(df_passagens, use_container_width=True)
        else:
            st.info("Nenhuma passagem encontrada para este veículo.")
        st.markdown('</div>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)
