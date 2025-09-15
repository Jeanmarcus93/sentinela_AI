#!/usr/bin/env python3
"""
Script para criar banco PostgreSQL manualmente
Primeiro cria o banco, depois as tabelas
"""

import argparse
import logging
import sys
from pathlib import Path

# Adicionar o diretório backend ao path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

import psycopg
from sqlalchemy import create_engine, text

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_database_manual(db_name, host, port, user, password):
    """Cria o banco de dados manualmente"""
    
    logger.info(f"🚀 Criando banco de dados: {db_name}")
    
    # Tentar diferentes bancos padrão para conectar
    default_databases = ['postgres', 'template1', 'template0']
    
    for default_db in default_databases:
        try:
            logger.info(f"Tentando conectar ao banco padrão: {default_db}")
            
            # Conectar ao banco padrão
            conn = psycopg.connect(
                host=host,
                port=port,
                dbname=default_db,
                user=user,
                password=password,
                autocommit=True
            )
            
            with conn.cursor() as cur:
                # Verificar se o banco já existe
                cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
                
                if cur.fetchone():
                    logger.info(f"✅ Banco {db_name} já existe")
                    conn.close()
                    return True
                
                # Criar o banco
                cur.execute(f'CREATE DATABASE "{db_name}"')
                logger.info(f"✅ Banco {db_name} criado com sucesso!")
                conn.close()
                return True
                
        except Exception as e:
            logger.warning(f"Não foi possível conectar ao banco {default_db}: {e}")
            continue
    
    logger.error("❌ Não foi possível conectar a nenhum banco padrão")
    logger.info("💡 Soluções:")
    logger.info("   1. Verifique se o PostgreSQL está rodando")
    logger.info("   2. Confirme as credenciais (host, porta, usuário, senha)")
    logger.info("   3. Execute manualmente: CREATE DATABASE sentinela_treino;")
    return False

def create_tables(db_name, host, port, user, password):
    """Cria as tabelas no banco"""
    
    logger.info(f"📋 Criando tabelas no banco: {db_name}")
    
    try:
        # Conectar ao banco criado
        conn = psycopg.connect(
            host=host,
            port=port,
            dbname=db_name,
            user=user,
            password=password
        )
        
        with conn.cursor() as cur:
            # Criar tabela veiculos
            cur.execute("""
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
            """)
            
            cur.execute("CREATE INDEX IF NOT EXISTS idx_veiculos_placa ON veiculos(placa)")
            logger.info("✅ Tabela veiculos criada")
            
            # Criar tabela passagens
            cur.execute("""
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
            """)
            
            # Criar índices para passagens
            cur.execute("CREATE INDEX IF NOT EXISTS idx_passagens_dataHoraUTC ON passagens(dataHoraUTC)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_passagens_placa ON passagens(placa)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_passagens_cidade ON passagens(cidade)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_passagens_uf ON passagens(uf)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_passagens_codigoRodovia ON passagens(codigoRodovia)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_passagens_codigoEquipamento ON passagens(codigoEquipamento)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_passagens_sistemaOrigem ON passagens(sistemaOrigem)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_passagens_placa_data ON passagens(placa, dataHoraUTC)")
            logger.info("✅ Tabela passagens criada com índices")
            
            # Criar tabela municipios
            cur.execute("""
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
            """)
            
            cur.execute("CREATE INDEX IF NOT EXISTS idx_municipios_nome ON municipios(nome)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_municipios_uf ON municipios(uf)")
            cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_municipios_nome_uf ON municipios(nome, uf)")
            logger.info("✅ Tabela municipios criada")
            
            # Inserir municípios básicos
            municipios_basicos = [
                ('Foz do Iguaçu', 'PR', True, True),
                ('Ponta Porã', 'MS', True, True), 
                ('Corumbá', 'MS', True, True),
                ('Uruguaiana', 'RS', True, True),
                ('Santana do Livramento', 'RS', True, True),
                ('Jaguarão', 'RS', True, True),
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
            
            for nome, uf, eh_fronteira, eh_suspeito in municipios_basicos:
                cur.execute("""
                INSERT INTO municipios (nome, uf, eh_fronteira, eh_suspeito)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (nome, uf) DO NOTHING
                """, (nome, uf, eh_fronteira, eh_suspeito))
            
            logger.info("✅ Municípios básicos inseridos")
            
            conn.commit()
            conn.close()
            
            return True
            
    except Exception as e:
        logger.error(f"❌ Erro ao criar tabelas: {e}")
        return False

def main():
    """Função principal"""
    parser = argparse.ArgumentParser(description='Criar banco PostgreSQL manualmente')
    
    parser.add_argument('--db-name', default='sentinela_treino', help='Nome do banco de dados')
    parser.add_argument('--host', default='localhost', help='Host do PostgreSQL')
    parser.add_argument('--port', type=int, default=5432, help='Porta do PostgreSQL')
    parser.add_argument('--user', default='postgres', help='Usuário do PostgreSQL')
    parser.add_argument('--password', default='Jmkjmk.00', help='Senha do PostgreSQL')
    
    args = parser.parse_args()
    
    logger.info("🔧 Configuração do banco:")
    logger.info(f"   Host: {args.host}")
    logger.info(f"   Porta: {args.port}")
    logger.info(f"   Banco: {args.db_name}")
    logger.info(f"   Usuário: {args.user}")
    
    # Criar banco
    if create_database_manual(args.db_name, args.host, args.port, args.user, args.password):
        # Criar tabelas
        if create_tables(args.db_name, args.host, args.port, args.user, args.password):
            logger.info("🎉 Banco criado com sucesso!")
            logger.info("📋 Estrutura criada:")
            logger.info("   ✅ Banco: sentinela_treino")
            logger.info("   ✅ Tabela: veiculos")
            logger.info("   ✅ Tabela: passagens (com dataHoraUTC)")
            logger.info("   ✅ Tabela: municipios")
            logger.info("   ✅ Índices otimizados")
            logger.info("   ✅ Dados básicos inseridos")
            logger.info("")
            logger.info("🔧 Próximos passos:")
            logger.info("   1. Configure as variáveis de ambiente")
            logger.info("   2. Teste a conexão com o banco")
            logger.info("   3. Importe seus dados para a tabela passagens")
            sys.exit(0)
        else:
            logger.error("❌ Falha ao criar tabelas")
            sys.exit(1)
    else:
        logger.error("❌ Falha ao criar banco de dados")
        sys.exit(1)

if __name__ == "__main__":
    main()

