#!/usr/bin/env python3
"""
Script para criar um novo banco de dados PostgreSQL
com a estrutura completa da tabela passagens

Uso:
    python create_database.py --db-name novo_banco --host localhost --port 5432
"""

import argparse
import os
import sys
import logging
from pathlib import Path

# Adicionar o diretório backend ao path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.models.database import DatabaseConfig, get_db_connection, create_database_if_not_exists
from sqlalchemy import create_engine, text

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_passagens_table(engine):
    """Cria a tabela passagens com a estrutura completa"""
    
    with engine.connect() as conn:
        # Criar tabela passagens com todas as colunas especificadas
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS passagens (
            id SERIAL PRIMARY KEY,
            dataHoraUTC TIMESTAMP NOT NULL,
            placa VARCHAR(10) NOT NULL,
            pontoCaptura VARCHAR(200),
            cidade VARCHAR(200),
            uf VARCHAR(5),
            codigoEquipamento VARCHAR(100),
            codigoRodovia VARCHAR(50),
            km NUMERIC(10,3),
            faixa INTEGER,
            sentido VARCHAR(50),
            velocidade NUMERIC(5,2),
            latitude NUMERIC(10,8),
            longitude NUMERIC(11,8),
            refImagem1 VARCHAR(500),
            refImagem2 VARCHAR(500),
            sistemaOrigem VARCHAR(100),
            ehEquipamentoMovel BOOLEAN DEFAULT FALSE,
            ehLeituraHumana BOOLEAN DEFAULT FALSE,
            tipoInferidoIA VARCHAR(100),
            marcaModeloInferidoIA VARCHAR(200),
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """))
        
        # Criar índices para otimização
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_passagens_dataHoraUTC ON passagens(dataHoraUTC)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_passagens_placa ON passagens(placa)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_passagens_cidade ON passagens(cidade)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_passagens_uf ON passagens(uf)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_passagens_codigoRodovia ON passagens(codigoRodovia)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_passagens_codigoEquipamento ON passagens(codigoEquipamento)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_passagens_sistemaOrigem ON passagens(sistemaOrigem)"))
        
        # Índice composto para consultas frequentes
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_passagens_placa_data ON passagens(placa, dataHoraUTC)"))
        
        conn.commit()
        logger.info("✅ Tabela passagens criada com sucesso!")

def create_veiculos_table(engine):
    """Cria a tabela veículos"""
    
    with engine.connect() as conn:
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS veiculos (
            id SERIAL PRIMARY KEY,
            placa VARCHAR(10) UNIQUE NOT NULL,
            marca_modelo VARCHAR(200),
            cor VARCHAR(50),
            tipo VARCHAR(100),
            ano_modelo INTEGER,
            local_emplacamento VARCHAR(100),
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """))
        
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_veiculos_placa ON veiculos(placa)"))
        conn.commit()
        logger.info("✅ Tabela veiculos criada com sucesso!")

def create_pessoas_table(engine):
    """Cria a tabela pessoas"""
    
    with engine.connect() as conn:
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS pessoas (
            id SERIAL PRIMARY KEY,
            nome VARCHAR(200),
            cpf_cnpj VARCHAR(20) UNIQUE,
            veiculo_id INTEGER REFERENCES veiculos(id) ON DELETE CASCADE,
            relevante BOOLEAN DEFAULT TRUE,
            condutor BOOLEAN DEFAULT FALSE,
            possuidor BOOLEAN DEFAULT FALSE,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """))
        
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_pessoas_cpf_cnpj ON pessoas(cpf_cnpj)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_pessoas_veiculo ON pessoas(veiculo_id)"))
        conn.commit()
        logger.info("✅ Tabela pessoas criada com sucesso!")

def create_ocorrencias_table(engine):
    """Cria a tabela ocorrências"""
    
    with engine.connect() as conn:
        # Enum para tipos de apreensão
        conn.execute(text("""
        DO $$ BEGIN
            CREATE TYPE tipo_apreensao_enum AS ENUM (
                'Maconha', 'Skunk', 'Cocaina', 'Crack', 'Sintéticos', 'Arma'
            );
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$
        """))
        
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS ocorrencias (
            id SERIAL PRIMARY KEY,
            veiculo_id INTEGER REFERENCES veiculos(id) ON DELETE CASCADE,
            tipo VARCHAR(50) NOT NULL,
            datahora TIMESTAMP NOT NULL,
            datahora_fim TIMESTAMP,
            relato TEXT,
            ocupantes JSONB,
            presos JSONB,
            apreensoes JSONB,
            veiculos JSONB,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """))
        
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_ocorrencias_veiculo ON ocorrencias(veiculo_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_ocorrencias_datahora ON ocorrencias(datahora)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_ocorrencias_tipo ON ocorrencias(tipo)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_ocorrencias_relato ON ocorrencias USING gin(to_tsvector('portuguese', relato)) WHERE relato IS NOT NULL"))
        
        conn.commit()
        logger.info("✅ Tabela ocorrencias criada com sucesso!")

def create_apreensoes_table(engine):
    """Cria a tabela apreensões"""
    
    with engine.connect() as conn:
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS apreensoes (
            id SERIAL PRIMARY KEY,
            ocorrencia_id INTEGER REFERENCES ocorrencias(id) ON DELETE CASCADE,
            tipo tipo_apreensao_enum NOT NULL,
            quantidade NUMERIC(10,3) NOT NULL,
            unidade VARCHAR(10) NOT NULL,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """))
        
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_apreensoes_ocorrencia ON apreensoes(ocorrencia_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_apreensoes_tipo ON apreensoes(tipo)"))
        
        conn.commit()
        logger.info("✅ Tabela apreensoes criada com sucesso!")

def create_municipios_table(engine):
    """Cria a tabela municípios"""
    
    with engine.connect() as conn:
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS municipios (
            id SERIAL PRIMARY KEY,
            nome VARCHAR(200) NOT NULL,
            uf VARCHAR(5) NOT NULL,
            codigo_ibge VARCHAR(10),
            regiao VARCHAR(50),
            eh_fronteira BOOLEAN DEFAULT FALSE,
            eh_suspeito BOOLEAN DEFAULT FALSE,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """))
        
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_municipios_nome ON municipios(nome)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_municipios_uf ON municipios(uf)"))
        conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS idx_municipios_nome_uf ON municipios(nome, uf)"))
        
        conn.commit()
        logger.info("✅ Tabela municipios criada com sucesso!")

def create_cache_analises_table(engine):
    """Cria a tabela de cache de análises"""
    
    with engine.connect() as conn:
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS cache_analises (
            id SERIAL PRIMARY KEY,
            chave_cache VARCHAR(64) UNIQUE NOT NULL,
            placa VARCHAR(10) NOT NULL,
            resultado JSONB NOT NULL,
            data_calculo TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            valido_ate TIMESTAMP DEFAULT (CURRENT_TIMESTAMP + INTERVAL '24 hours')
        )
        """))
        
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_cache_chave ON cache_analises(chave_cache)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_cache_placa ON cache_analises(placa)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_cache_valido_ate ON cache_analises(valido_ate)"))
        
        conn.commit()
        logger.info("✅ Tabela cache_analises criada com sucesso!")

def create_logs_analise_table(engine):
    """Cria a tabela de logs de análise"""
    
    with engine.connect() as conn:
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS logs_analise (
            id SERIAL PRIMARY KEY,
            placa VARCHAR(10) NOT NULL,
            tipo_analise VARCHAR(50) NOT NULL,
            tempo_execucao NUMERIC(8,3),
            sucesso BOOLEAN DEFAULT TRUE,
            erro TEXT,
            metadados JSONB,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """))
        
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_logs_placa ON logs_analise(placa)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_logs_tipo ON logs_analise(tipo_analise)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_logs_criado_em ON logs_analise(criado_em)"))
        
        conn.commit()
        logger.info("✅ Tabela logs_analise criada com sucesso!")

def create_triggers(engine):
    """Cria triggers para atualização automática de timestamps"""
    
    with engine.connect() as conn:
        # Função para atualizar timestamp
        conn.execute(text("""
        CREATE OR REPLACE FUNCTION atualizar_timestamp()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.atualizado_em = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ language 'plpgsql'
        """))
        
        # Aplicar trigger nas tabelas relevantes
        for tabela in ['veiculos', 'ocorrencias']:
            conn.execute(text(f"""
            DROP TRIGGER IF EXISTS trigger_atualizar_{tabela} ON {tabela};
            CREATE TRIGGER trigger_atualizar_{tabela}
                BEFORE UPDATE ON {tabela}
                FOR EACH ROW
                EXECUTE FUNCTION atualizar_timestamp()
            """))
        
        conn.commit()
        logger.info("✅ Triggers criados com sucesso!")

def insert_sample_municipios(engine):
    """Insere municípios básicos para o sistema"""
    
    municipios_basicos = [
        # Fronteiras importantes
        ('Foz do Iguaçu', 'PR', True, True),
        ('Ponta Porã', 'MS', True, True), 
        ('Corumbá', 'MS', True, True),
        ('Uruguaiana', 'RS', True, True),
        ('Santana do Livramento', 'RS', True, True),
        ('Jaguarão', 'RS', True, True),
        
        # Capitais importantes
        ('São Paulo', 'SP', False, False),
        ('Rio de Janeiro', 'RJ', False, False),
        ('Brasília', 'DF', False, False),
        ('Belo Horizonte', 'MG', False, False),
        ('Porto Alegre', 'RS', False, False),
        ('Curitiba', 'PR', False, False),
        ('Salvador', 'BA', False, False),
        ('Recife', 'PE', False, False),
        ('Fortaleza', 'CE', False, False),
        ('Manaus', 'AM', False, False),
    ]
    
    with engine.connect() as conn:
        for nome, uf, eh_fronteira, eh_suspeito in municipios_basicos:
            conn.execute(text("""
            INSERT INTO municipios (nome, uf, eh_fronteira, eh_suspeito)
            VALUES (:nome, :uf, :eh_fronteira, :eh_suspeito)
            ON CONFLICT (nome, uf) DO NOTHING
            """), {
                "nome": nome, 
                "uf": uf, 
                "eh_fronteira": eh_fronteira,
                "eh_suspeito": eh_suspeito
            })
        
        conn.commit()
        logger.info("✅ Municípios básicos inseridos!")

def create_database(db_config: DatabaseConfig):
    """Cria o banco de dados completo"""
    
    logger.info(f"🚀 Criando banco de dados: {db_config.dbname}")
    
    # 1. Criar o banco se não existir
    if not create_database_if_not_exists(db_config):
        logger.error("❌ Falha ao criar o banco de dados")
        return False
    
    # 2. Conectar ao banco criado
    engine = create_engine(db_config.to_sqlalchemy_url())
    
    try:
        # 3. Criar todas as tabelas
        logger.info("📋 Criando estrutura das tabelas...")
        
        create_veiculos_table(engine)
        create_pessoas_table(engine)
        create_passagens_table(engine)  # Tabela principal com dataHoraUTC
        create_ocorrencias_table(engine)
        create_apreensoes_table(engine)
        create_municipios_table(engine)
        create_cache_analises_table(engine)
        create_logs_analise_table(engine)
        
        # 4. Criar triggers
        create_triggers(engine)
        
        # 5. Inserir dados básicos
        insert_sample_municipios(engine)
        
        logger.info("✅ Banco de dados criado com sucesso!")
        logger.info(f"📊 Banco: {db_config.dbname}")
        logger.info(f"🏠 Host: {db_config.host}:{db_config.port}")
        logger.info(f"👤 Usuário: {db_config.user}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro ao criar estrutura do banco: {e}")
        return False

def main():
    """Função principal"""
    parser = argparse.ArgumentParser(description='Criar novo banco PostgreSQL com estrutura completa')
    
    parser.add_argument('--db-name', required=True, help='Nome do banco de dados')
    parser.add_argument('--host', default='localhost', help='Host do PostgreSQL')
    parser.add_argument('--port', type=int, default=5432, help='Porta do PostgreSQL')
    parser.add_argument('--user', default='postgres', help='Usuário do PostgreSQL')
    parser.add_argument('--password', default='Jmkjmk.00', help='Senha do PostgreSQL')
    parser.add_argument('--force', action='store_true', help='Forçar recriação se o banco já existir')
    
    args = parser.parse_args()
    
    # Configuração do banco
    db_config = DatabaseConfig(
        host=args.host,
        port=args.port,
        dbname=args.db_name,
        user=args.user,
        password=args.password
    )
    
    logger.info("🔧 Configuração do banco:")
    logger.info(f"   Host: {db_config.host}")
    logger.info(f"   Porta: {db_config.port}")
    logger.info(f"   Banco: {db_config.dbname}")
    logger.info(f"   Usuário: {db_config.user}")
    
    # Criar banco
    success = create_database(db_config)
    
    if success:
        logger.info("🎉 Banco de dados criado com sucesso!")
        logger.info("📋 Estrutura da tabela passagens:")
        logger.info("   - dataHoraUTC: TIMESTAMP (principal)")
        logger.info("   - placa: VARCHAR(10)")
        logger.info("   - pontoCaptura: VARCHAR(200)")
        logger.info("   - cidade: VARCHAR(200)")
        logger.info("   - uf: VARCHAR(5)")
        logger.info("   - codigoEquipamento: VARCHAR(100)")
        logger.info("   - codigoRodovia: VARCHAR(50)")
        logger.info("   - km: NUMERIC(10,3)")
        logger.info("   - faixa: INTEGER")
        logger.info("   - sentido: VARCHAR(50)")
        logger.info("   - velocidade: NUMERIC(5,2)")
        logger.info("   - latitude: NUMERIC(10,8)")
        logger.info("   - longitude: NUMERIC(11,8)")
        logger.info("   - refImagem1: VARCHAR(500)")
        logger.info("   - refImagem2: VARCHAR(500)")
        logger.info("   - sistemaOrigem: VARCHAR(100)")
        logger.info("   - ehEquipamentoMovel: BOOLEAN")
        logger.info("   - ehLeituraHumana: BOOLEAN")
        logger.info("   - tipoInferidoIA: VARCHAR(100)")
        logger.info("   - marcaModeloInferidoIA: VARCHAR(200)")
        sys.exit(0)
    else:
        logger.error("❌ Falha ao criar banco de dados")
        sys.exit(1)

if __name__ == "__main__":
    main()

