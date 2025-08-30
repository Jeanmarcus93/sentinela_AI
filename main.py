# -*- coding: utf-8 -*-
"""
main.py
-------

Script principal responsável por ler um arquivo PDF contendo informações
sobre veículos e condutores, extrair os dados relevantes e inseri‑los
em um banco de dados PostgreSQL. Utiliza o módulo ``config.py`` para
configurar a conexão e garantir que as tabelas existam antes da
inserção.

Os dados são divididos em duas categorias:

* Cabeçalho: contém dados do veículo e do provável condutor.
* Passagens: lista cada ocorrência de passagem do veículo por
  determinado ponto, contendo município, rodovia/endereço, data e hora.

Para executar este script com um PDF específico, utilize por exemplo:

    python main.py /caminho/para/arquivo.pdf

Se ``__name__ == '__main__'`` for ``True``, o script assumirá que o
primeiro argumento de linha de comando é o caminho do PDF. Caso nenhum
argumento seja passado, ele tentará processar ``TQO3F99.pdf`` no
diretório corrente.
"""

import sys
import os
import re
from datetime import datetime
from typing import Dict, List

import fitz  # PyMuPDF para leitura de PDF
import psycopg2
from psycopg2.extras import execute_values

from config import DB_CONFIG, criar_tabelas


def extrair_texto_pdf(caminho_pdf: str) -> str:
    """Lê todas as páginas de um PDF e concatena o texto.

    :param caminho_pdf: Caminho absoluto ou relativo para o arquivo PDF.
    :returns: Conteúdo textual extraído de todas as páginas do PDF.
    """
    doc = fitz.open(caminho_pdf)
    texto = "".join(page.get_text("text") for page in doc)
    doc.close()
    return texto


def extrair_dados_cabecalho(texto: str, placa: str) -> Dict[str, object]:
    """Extrai informações do cabeçalho do relatório a partir do texto.

    Este método usa expressões regulares para localizar os campos de
    interesse no texto. Caso algum campo não seja encontrado, o valor
    correspondente será ``None``. A placa é passada como argumento para
    vincular o registro às passagens encontradas.

    :param texto: Texto completo extraído do PDF.
    :param placa: Placa do veículo, normalmente derivada do nome do arquivo.
    :returns: Dicionário com os campos esperados para a tabela
              ``veiculos_condutores``.
    """
    dados: Dict[str, object] = {
        "placa": placa,
        "marca_modelo": None,
        "tipo": None,
        "ano_modelo": None,
        "cor": None,
        "local_emplacamento": None,
        "transferencia_recente": None,
        "suspeito": "Suspeito",  # valor padrão conforme relatório
        "relevante": "Fiscalização",  # valor padrão conforme relatório
        "proprietario": None,
        "cpf_cnpj_proprietario": None,
        "condutor": None,
        "cpf_condutor": None,
        "cnh": None,
        "validade_cnh": None,
        "local_cnh": None,
        "suspeito_condutor": "Suspeito",  # valor padrão conforme relatório
        "relevante_condutor": "Fiscalização",  # valor padrão conforme relatório
        "teve_mp": None,
        "crime_prf": None,
        "abordagem_prf": None,
    }

    # Marca/modelo, tipo, ano/modelo, cor e local de emplacamento
    # Exemplo de string: "VW/VIRTUS AB (AUTOMOVEL) (2025/2026) (BRANCA) de ESTANCIA VELHA/RS"
    match = re.search(
        r"([A-Z0-9/\s]+)\s*\(([^\)]+)\)\s*\(([^\)]+)\)\s*\(([^\)]+)\)\s*de\s*([A-ZÁÉÍÓÚÃÕÇ/\s]+)",
        texto,
    )
    if match:
        marca_modelo = match.group(1).strip()
        tipo = match.group(2).strip()
        ano_modelo = match.group(3).strip()
        cor = match.group(4).strip()
        local_emplacamento = match.group(5).strip()
        dados.update(
            {
                "marca_modelo": marca_modelo,
                "tipo": tipo,
                "ano_modelo": ano_modelo,
                "cor": cor,
                "local_emplacamento": local_emplacamento,
            }
        )

    # Transferência recente (aparece após RENAVAM)
    match = re.search(r"RENAVAM\s+([A-Z0-9/]+)", texto)
    if match:
        dados["transferencia_recente"] = match.group(1).strip()

    # Proprietário e CPF/CNPJ
    match = re.search(r"Proprietário:\s*(.*?)\s*\(([\d\./-]+)\)", texto)
    if match:
        dados["proprietario"] = match.group(1).strip()
        dados["cpf_cnpj_proprietario"] = match.group(2).strip()

    # Condutor e CPF do condutor
    match = re.search(r"Provável Condutor:\s*(.*?)\s*\(([^\)]+)\)", texto)
    if match:
        dados["condutor"] = match.group(1).strip()
        dados["cpf_condutor"] = match.group(2).strip()

    # CNH: categoria, validade e local de emissão
    match = re.search(
        r"CNH:\s*([A-Z]),\s*Validade:\s*([\d/]+),\s*de\s*([A-ZÁÉÍÓÚÃÕÇ/\s]+)",
        texto,
    )
    if match:
        dados["cnh"] = match.group(1).strip()
        # converte a validade de string para objeto date
        try:
            dados["validade_cnh"] = datetime.strptime(match.group(2).strip(), "%d/%m/%Y").date()
        except ValueError:
            # Se a data estiver em formato inesperado, mantém como None
            dados["validade_cnh"] = None
        # Remove quebras de linha do local da CNH
        local_cnh = match.group(3).strip().split("\n")[0].strip()
        dados["local_cnh"] = local_cnh

    # Teve MP, Crime na PRF e Abordagem na PRF.
    # Estes termos aparecem como siglas isoladas, então verifica se
    # existem no texto completo.
    if "BNMP" in texto:
        dados["teve_mp"] = "BNMP"
    if "BOP" in texto:
        dados["crime_prf"] = "BOP"
    if "PDI" in texto:
        dados["abordagem_prf"] = "PDI"

    return dados


def extrair_passagens(texto: str, placa: str) -> List[Dict[str, object]]:
    """Extrai as passagens do veículo a partir do texto completo.

    O relatório apresenta cada passagem em linhas separadas, começando com
    ``RS - <município> - <rodovia/endereço>``. As linhas seguintes contêm
    informações como códigos de operação e, finalmente, a data e hora da
    ocorrência. Esta função percorre todas as linhas do relatório,
    procurando pelo padrão ``RS -`` e, quando encontra, busca a próxima
    linha contendo uma data no formato ``dd/mm/aaaa hh:mm:ss``. Cada
    passagem encontrada gera um dicionário com os campos esperados para
    inserção na tabela ``passagens``.

    :param texto: Texto completo extraído do PDF.
    :param placa: Placa do veículo para associação das passagens.
    :returns: Lista de dicionários com estado, município, rodovia, data e hora.
    """
    passagens: List[Dict[str, object]] = []
    linhas = texto.split("\n")
    # Percorre cada linha em busca do padrão "RS - município - rodovia"
    for idx, linha in enumerate(linhas):
        if linha.startswith("RS - "):
            partes = [p.strip() for p in linha.split(" - ", 2)]
            if len(partes) >= 3:
                estado = partes[0]
                municipio = partes[1]
                rodovia = partes[2]
            else:
                continue
            # Procura a data e hora nas linhas subsequentes
            data_str = None
            hora_str = None
            for j in range(idx + 1, min(idx + 10, len(linhas))):
                match = re.search(r"(\d{2}/\d{2}/\d{4})\s*(\d{2}:\d{2}:\d{2})", linhas[j])
                if match:
                    data_str = match.group(1)
                    hora_str = match.group(2)
                    break
            if data_str:
                # Converte a data em objeto date e cria registro
                try:
                    data_obj = datetime.strptime(data_str, "%d/%m/%Y").date()
                except ValueError:
                    data_obj = None
                passagens.append(
                    {
                        "placa": placa,
                        "estado": estado,
                        "municipio": municipio,
                        "rodovia": rodovia,
                        "data": data_obj,
                        "hora": hora_str,
                    }
                )
    return passagens


def inserir_no_banco(dados_cabecalho: Dict[str, object], passagens: List[Dict[str, object]]) -> None:
    """Insere os dados extraídos no banco de dados.

    A função primeiro insere um registro na tabela ``veiculos_condutores``
    usando o dicionário ``dados_cabecalho``. Em seguida, utiliza
    ``execute_values`` para inserir em lote todas as passagens
    associadas. A transação é confirmada ao final. Caso ocorra
    qualquer exceção, a conexão é fechada normalmente.

    :param dados_cabecalho: Dicionário com os campos do cabeçalho.
    :param passagens: Lista de dicionários com as passagens extraídas.
    """
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        cur = conn.cursor()
        # Inserção do cabeçalho. Monta colunas e valores dinamicamente.
        colunas = list(dados_cabecalho.keys())
        valores = [dados_cabecalho[col] for col in colunas]
        colunas_str = ",".join(colunas)
        placeholders = ",".join(["%s"] * len(valores))
        cur.execute(
            f"INSERT INTO veiculos_condutores ({colunas_str}) VALUES ({placeholders})",
            valores,
        )
        # Inserção em lote das passagens
        if passagens:
            registros = [
                (
                    p["placa"],
                    p["estado"],
                    p["municipio"],
                    p["rodovia"],
                    p["data"],
                    p["hora"],
                )
                for p in passagens
            ]
            execute_values(
                cur,
                """
                INSERT INTO passagens
                    (placa, estado, municipio, rodovia, data, hora)
                VALUES %s
                """,
                registros,
            )
        conn.commit()
    finally:
        try:
            cur.close()
        except Exception:
            pass
        conn.close()


def main(caminho_pdf: str) -> None:
    """Processa um PDF específico: extrai texto, dados e insere no banco.

    :param caminho_pdf: Caminho para o arquivo PDF a ser processado.
    """
    # Garante que as tabelas existem
    criar_tabelas()
    # Deriva placa do nome do arquivo, removendo extensão e caminhos
    placa = os.path.splitext(os.path.basename(caminho_pdf))[0].upper()
    texto = extrair_texto_pdf(caminho_pdf)
    dados_cabecalho = extrair_dados_cabecalho(texto, placa)
    passagens = extrair_passagens(texto, placa)
    inserir_no_banco(dados_cabecalho, passagens)
    print(f"✅ Processamento concluído para {placa}: {len(passagens)} passagens inseridas.")


if __name__ == "__main__":
    # O caminho do PDF pode ser passado como argumento; senão, assume arquivo padrão
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
    else:
        pdf_path = "TQO3F99.pdf"
    main(pdf_path)