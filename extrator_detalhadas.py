import os
import re
import fitz  # PyMuPDF
import psycopg
from psycopg.rows import dict_row
from datetime import datetime
from config import DB_CONFIG, criar_tabelas


# ============================================================
# EXTRAÇÃO DE TEXTO DO PDF
# ============================================================
def extrair_texto_pdf(caminho_pdf: str) -> str:
    doc = fitz.open(caminho_pdf)
    texto = ""
    for pagina in doc:
        texto += pagina.get_text()
    return texto


# ============================================================
# EXTRAÇÃO DE VEÍCULOS (como antes)
# ============================================================
def extrair_dados_veiculo(texto: str) -> dict | None:
    placa_match = re.search(r"\b([A-Z]{3}\s?\d{4})\b", texto)
    placa = placa_match.group(1).replace(" ", "") if placa_match else None

    modelo_match = re.search(r"([A-Z]+/[A-Z0-9\s]+)\n", texto)
    marca_modelo = modelo_match.group(1).strip() if modelo_match else None

    if placa:
        return {
            "placa": placa,
            "marca_modelo": marca_modelo,
        }
    return None


# ============================================================
# EXTRAÇÃO DE OCORRÊNCIAS (Fiscalização Detalhada)
# ============================================================
def extrair_ocorrencias(texto: str):
    ocorrencias = []
    blocos = texto.split("Fiscalização Detalhada")
    for bloco in blocos:
        bloco = bloco.strip()
        if not bloco:
            continue

        # Placa
        placa_match = re.search(r"\b([A-Z]{3}\s?[0-9A-Z]{4})\b", bloco)
        placa = placa_match.group(1).replace(" ", "") if placa_match else None

        # Marca/modelo
        modelo_match = re.search(r"([A-Z/0-9\s\.]+)\n", bloco)
        marca_modelo = modelo_match.group(1).strip() if modelo_match else None

        # Pessoas
        pessoas = re.findall(r"Pessoa\s\d*:\s*([A-Z\s]+)\s*\(([\d\.\-]+)\)", bloco)
        lista_pessoas = [{"nome": p[0].title(), "cpf": p[1]} for p in pessoas]

        # Relato
        obs_match = re.search(r"Observa[cç][aã]o:([\s\S]+?)(?=Fiscaliza|$)", bloco, re.I)
        relato = obs_match.group(1).strip() if obs_match else None

        if placa and relato:
            ocorrencias.append({
                "placa": placa,
                "marca_modelo": marca_modelo,
                "pessoas": lista_pessoas,
                "relato": relato
            })
    return ocorrencias


# ============================================================
# INSERÇÃO NO BANCO
# ============================================================
def inserir_ocorrencias(ocorrencias):
    with psycopg.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:
            for oc in ocorrencias:
                # garante que o veículo existe
                cur.execute("""
                    INSERT INTO veiculos (placa, marca_modelo)
                    VALUES (%s,%s)
                    ON CONFLICT (placa) DO NOTHING
                    RETURNING id;
                """, (oc["placa"], oc["marca_modelo"]))

                veiculo_id = None
                if cur.rowcount > 0:
                    veiculo_id = cur.fetchone()[0]
                else:
                    cur.execute("SELECT id FROM veiculos WHERE placa = %s;", (oc["placa"],))
                    row = cur.fetchone()
                    veiculo_id = row[0] if row else None

                # insere ocorrência
                cur.execute("""
                    INSERT INTO ocorrencias (veiculo_id, tipo, relato, datahora)
                    VALUES (%s, %s, %s, NOW())
                """, (veiculo_id, "Fiscalização", oc["relato"]))

            conn.commit()


# ============================================================
# PROCESSAR PDF
# ============================================================
def processar_pdf(caminho_pdf: str):
    print(f"\n⏳ Processando {os.path.basename(caminho_pdf)}...")
    texto = extrair_texto_pdf(caminho_pdf)

    # veículos
    veiculo = extrair_dados_veiculo(texto)
    if veiculo:
        print(f"✅ Veículo detectado: {veiculo}")

    # ocorrências
    ocorrencias = extrair_ocorrencias(texto)
    print(f"✅ Ocorrências encontradas: {len(ocorrencias)}")

    if ocorrencias:
        inserir_ocorrencias(ocorrencias)
        print("💾 Ocorrências inseridas no banco com sucesso!")


# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    criar_tabelas()
    pasta = "entrada_pdfs"
    for arquivo in os.listdir(pasta):
        if arquivo.lower().endswith(".pdf"):
            processar_pdf(os.path.join(pasta, arquivo))
