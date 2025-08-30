# main.py
import os
import re
from datetime import datetime
from typing import Dict, List
import fitz  # PyMuPDF
import psycopg2
from psycopg2.extras import execute_values

from config import DB_CONFIG, criar_tabelas


# ---------- Funções utilitárias ----------

def extrair_texto_pdf(caminho_pdf: str) -> str:
    """Extrai todo o texto de um PDF."""
    doc = fitz.open(caminho_pdf)
    texto = "".join(page.get_text("text") for page in doc)
    doc.close()
    return texto


def extrair_dados(texto: str, placa: str) -> Dict[str, object]:
    """Extrai cabeçalho de veículo, proprietário e condutor."""
    dados = {
        "veiculo": {
            "placa": placa,
            "marca_modelo": None,
            "tipo": None,
            "ano_modelo": None,
            "cor": None,
            "local_emplacamento": None,
            "transferencia_recente": None,
            "suspeito": "Suspeito",
            "relevante": "Fiscalização",
            "crime_prf": None,
            "abordagem_prf": None,
        },
        "proprietario": {
            "nome": None,
            "cpf_cnpj": None,
            "cnh": None,
            "validade_cnh": None,
            "local_cnh": None,
            "suspeito": "Suspeito",
            "relevante": "Fiscalização",
            "proprietario": True,
            "condutor": False,
        },
        "condutor": {
            "nome": None,
            "cpf_cnpj": None,
            "cnh": None,
            "validade_cnh": None,
            "local_cnh": None,
            "suspeito": "Suspeito",
            "relevante": "Fiscalização",
            "proprietario": False,
            "condutor": True,
        }
    }

    # --- Veículo ---
    match = re.search(
        r"([A-Z0-9/\.\-\s]+)\s*\(([^)]+)\)\s*\(([^)]+)\)\s*\(([^)]+)\)\s*de\s*([^\n\r]+)",
        texto
    )
    if match:
        dados["veiculo"]["marca_modelo"] = match.group(1).strip()
        dados["veiculo"]["tipo"] = match.group(2).strip()
        dados["veiculo"]["ano_modelo"] = match.group(3).strip()
        dados["veiculo"]["cor"] = match.group(4).strip()
        dados["veiculo"]["local_emplacamento"] = match.group(5).strip()

    if "BOP" in texto:
        dados["veiculo"]["crime_prf"] = "BOP"
    if "PDI" in texto:
        dados["veiculo"]["abordagem_prf"] = "PDI"

    # --- Proprietário (prefixo ou não) ---
    match = re.search(r"Propriet[aá]rio:\s*([A-ZÁÉÍÓÚÃÕÇ\s]+)\s*\(([\d\./-]+)\)", texto, re.IGNORECASE)
    if not match:
        match = re.search(r"\n([A-ZÁÉÍÓÚÃÕÇ\s\n]+)\s*\(([\d\./-]+)\)", texto)
    if match:
        nome = match.group(1).strip().split("\n")[-1]
        dados["proprietario"]["nome"] = nome
        dados["proprietario"]["cpf_cnpj"] = match.group(2).strip()

    # --- Condutor ---
    match = re.search(r"Prov[aá]vel\s+Condutor:\s*([A-ZÁÉÍÓÚÃÕÇ\s]+)\s*\(([\d\./-]+)\)", texto, re.IGNORECASE)
    if match:
        dados["condutor"]["nome"] = match.group(1).strip()
        dados["condutor"]["cpf_cnpj"] = match.group(2).strip()

    # --- CNH (proprietário ou condutor) ---
    match = re.search(
        r"CNH:\s*([A-Z]+).*?Validade:\s*([\d/]+).*?(de|Local da CNH)\s*:? ([^\n\r]+)",
        texto,
        re.IGNORECASE
    )
    if match:
        cnh = match.group(1).strip()
        try:
            validade = datetime.strptime(match.group(2).strip(), "%d/%m/%Y").date()
        except ValueError:
            validade = None
        local = match.group(4).strip()
        if dados["condutor"]["nome"]:
            dados["condutor"]["cnh"] = cnh
            dados["condutor"]["validade_cnh"] = validade
            dados["condutor"]["local_cnh"] = local
        else:
            dados["proprietario"]["cnh"] = cnh
            dados["proprietario"]["validade_cnh"] = validade
            dados["proprietario"]["local_cnh"] = local

    return dados


def extrair_passagens(texto: str, placa: str) -> List[Dict[str, object]]:
    """Extrai passagens do veículo no relatório."""
    passagens = []
    linhas = texto.split("\n")
    for idx, linha in enumerate(linhas):
        if linha.startswith("RS - "):
            partes = [p.strip() for p in linha.split(" - ", 2)]
            if len(partes) >= 3:
                estado, municipio, rodovia = partes[0], partes[1], partes[2]
            else:
                continue
            data_str, hora_str = None, None
            for j in range(idx + 1, min(idx + 10, len(linhas))):
                match = re.search(r"(\d{2}/\d{2}/\d{4})\s*(\d{2}:\d{2}:\d{2})", linhas[j])
                if match:
                    data_str, hora_str = match.group(1), match.group(2)
                    break
            if data_str:
                try:
                    data_obj = datetime.strptime(data_str, "%d/%m/%Y").date()
                except ValueError:
                    data_obj = None
                passagens.append({
                    "placa": placa,
                    "estado": estado,
                    "municipio": municipio,
                    "rodovia": rodovia,
                    "data": data_obj,
                    "hora": hora_str,
                })
    return passagens


# ---------- Inserção no banco ----------

def inserir_dados(dados: Dict[str, object], passagens: List[Dict[str, object]]) -> None:
    """Insere veículo, pessoas e passagens no banco (com relação veículo-pessoa)."""
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        cur = conn.cursor()

        # --- Inserir veículo ---
        cur.execute("""
            INSERT INTO veiculos (placa, marca_modelo, tipo, ano_modelo, cor,
                                  local_emplacamento, transferencia_recente,
                                  suspeito, relevante, crime_prf, abordagem_prf)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (placa) DO UPDATE SET
                marca_modelo = EXCLUDED.marca_modelo,
                tipo = EXCLUDED.tipo,
                ano_modelo = EXCLUDED.ano_modelo,
                cor = EXCLUDED.cor,
                local_emplacamento = EXCLUDED.local_emplacamento,
                transferencia_recente = EXCLUDED.transferencia_recente,
                suspeito = EXCLUDED.suspeito,
                relevante = EXCLUDED.relevante,
                crime_prf = EXCLUDED.crime_prf,
                abordagem_prf = EXCLUDED.abordagem_prf
            RETURNING id;
        """, (
            dados["veiculo"]["placa"], dados["veiculo"]["marca_modelo"], dados["veiculo"]["tipo"],
            dados["veiculo"]["ano_modelo"], dados["veiculo"]["cor"], dados["veiculo"]["local_emplacamento"],
            dados["veiculo"]["transferencia_recente"], dados["veiculo"]["suspeito"],
            dados["veiculo"]["relevante"], dados["veiculo"]["crime_prf"], dados["veiculo"]["abordagem_prf"]
        ))
        veiculo_id = cur.fetchone()[0] if cur.rowcount > 0 else None

        if not veiculo_id:
            cur.execute("SELECT id FROM veiculos WHERE placa = %s", (dados["veiculo"]["placa"],))
            veiculo_id = cur.fetchone()[0]

        # --- Inserir pessoas (ligadas ao veículo) ---
        for papel in ["proprietario", "condutor"]:
            pessoa = dados[papel]
            if pessoa["nome"] and pessoa["cpf_cnpj"]:
                cur.execute("""
                    INSERT INTO pessoas (veiculo_id, nome, cpf_cnpj, cnh, validade_cnh, local_cnh,
                                         suspeito, relevante, proprietario, condutor)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (cpf_cnpj) DO UPDATE SET
                        nome = EXCLUDED.nome,
                        cnh = EXCLUDED.cnh,
                        validade_cnh = EXCLUDED.validade_cnh,
                        local_cnh = EXCLUDED.local_cnh,
                        suspeito = EXCLUDED.suspeito,
                        relevante = EXCLUDED.relevante,
                        proprietario = EXCLUDED.proprietario OR pessoas.proprietario,
                        condutor = EXCLUDED.condutor OR pessoas.condutor,
                        veiculo_id = EXCLUDED.veiculo_id;
                """, (
                    veiculo_id, pessoa["nome"], pessoa["cpf_cnpj"], pessoa["cnh"], pessoa["validade_cnh"],
                    pessoa["local_cnh"], pessoa["suspeito"], pessoa["relevante"],
                    pessoa["proprietario"], pessoa["condutor"]
                ))

        # --- Inserir passagens ---
        if passagens:
            registros = [
                (veiculo_id, p["estado"], p["municipio"], p["rodovia"], p["data"], p["hora"])
                for p in passagens
            ]
            execute_values(cur, """
                INSERT INTO passagens
                    (veiculo_id, estado, municipio, rodovia, data, hora)
                VALUES %s
            """, registros)

        conn.commit()
    finally:
        try:
            cur.close()
        except Exception:
            pass
        conn.close()


# ---------- Função principal ----------

def processar_pdfs(pasta: str = "entrada_pdfs") -> None:
    """Processa todos os PDFs da pasta especificada."""
    criar_tabelas()
    for arquivo in os.listdir(pasta):
        if arquivo.lower().endswith(".pdf"):
            caminho = os.path.join(pasta, arquivo)
            placa = os.path.splitext(arquivo)[0].upper()
            texto = extrair_texto_pdf(caminho)
            dados = extrair_dados(texto, placa)
            passagens = extrair_passagens(texto, placa)

            print(f"\n✅ Dados extraídos de {arquivo}:")
            print(dados)
            print(f"Passagens encontradas: {len(passagens)}")

            # 🔹 Agora insere no banco
            inserir_dados(dados, passagens)
            print("💾 Inserido no banco com sucesso!")


if __name__ == "__main__":
    processar_pdfs("entrada_pdfs")
