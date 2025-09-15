#!/usr/bin/env python3
"""
Script simplificado para criar banco PostgreSQL
Tenta conectar diretamente ao banco alvo
"""

import argparse
import logging
import sys
from pathlib import Path

# Adicionar o diretório backend ao path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.models.database import DatabaseConfig, get_db_connection
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

def create_database_simple(db_config: DatabaseConfig):
    """Cria o banco de dados de forma simplificada"""
    
    logger.info(f"🚀 Tentando criar/acessar banco: {db_config.dbname}")
    
    # Tentar conectar diretamente ao banco alvo
    try:
        engine = create_engine(db_config.to_sqlalchemy_url())
        
        # Testar conexão
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        
        logger.info(f"✅ Banco {db_config.dbname} está acessível!")
        
        # Criar tabelas
        logger.info("📋 Criando estrutura das tabelas...")
        
        create_veiculos_table(engine)
        create_passagens_table(engine)
        create_municipios_table(engine)
        
        # Inserir dados básicos
        insert_sample_municipios(engine)
        
        logger.info("✅ Estrutura criada com sucesso!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro ao acessar banco {db_config.dbname}: {e}")
        logger.info("💡 Dicas:")
        logger.info("   1. Verifique se o PostgreSQL está rodando")
        logger.info("   2. Confirme se o banco já foi criado manualmente")
        logger.info("   3. Verifique host, porta, usuário e senha")
        logger.info("   4. Execute: CREATE DATABASE sentinela_treino; no PostgreSQL")
        return False

def main():
    """Função principal"""
    parser = argparse.ArgumentParser(description='Criar banco PostgreSQL de forma simplificada')
    
    parser.add_argument('--db-name', default='sentinela_treino', help='Nome do banco de dados')
    parser.add_argument('--host', default='localhost', help='Host do PostgreSQL')
    parser.add_argument('--port', type=int, default=5432, help='Porta do PostgreSQL')
    parser.add_argument('--user', default='postgres', help='Usuário do PostgreSQL')
    parser.add_argument('--password', default='Jmkjmk.00', help='Senha do PostgreSQL')
    
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
    success = create_database_simple(db_config)
    
    if success:
        logger.info("🎉 Banco configurado com sucesso!")
        logger.info("📋 Tabelas criadas:")
        logger.info("   ✅ veiculos")
        logger.info("   ✅ passagens (com dataHoraUTC)")
        logger.info("   ✅ municipios")
        logger.info("")
        logger.info("🔧 Próximos passos:")
        logger.info("   1. Configure as variáveis de ambiente")
        logger.info("   2. Teste a conexão com o banco")
        logger.info("   3. Importe seus dados para a tabela passagens")
        sys.exit(0)
    else:
        logger.error("❌ Falha ao configurar banco de dados")
        sys.exit(1)

if __name__ == "__main__":
    main()

