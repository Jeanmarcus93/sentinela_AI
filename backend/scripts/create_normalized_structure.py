#!/usr/bin/env python3
"""
Script para criar estrutura normalizada do banco
- Tabela veiculos: dados únicos dos veículos
- Tabela passagens: dados das passagens referenciando veículos
"""

import sys
from pathlib import Path

# Adicionar o diretório backend ao path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.models.database import DatabaseConfig, get_db_connection
import psycopg

def create_normalized_tables():
    """Cria estrutura normalizada com tabelas separadas"""
    
    print("🏗️ Criando estrutura normalizada do banco...")
    
    db_config = DatabaseConfig(
        host='localhost',
        port=5432,
        dbname='sentinela_treino',
        user='postgres',
        password='Jmkjmk.00'
    )
    
    try:
        with get_db_connection(db_config) as conn:
            with conn.cursor() as cur:
                # Dropar tabelas existentes
                print("🧹 Limpando estrutura anterior...")
                cur.execute("DROP TABLE IF EXISTS passagens CASCADE")
                cur.execute("DROP TABLE IF EXISTS veiculos CASCADE")
                
                # Criar tabela veiculos (dados únicos dos veículos)
                print("🚗 Criando tabela veiculos...")
                cur.execute("""
                CREATE TABLE veiculos (
                    id SERIAL PRIMARY KEY,
                    placa VARCHAR(10) UNIQUE NOT NULL,
                    marca_modelo VARCHAR(200),
                    cor VARCHAR(50),
                    tipo VARCHAR(100),
                    ano_modelo INTEGER,
                    local_emplacamento VARCHAR(100),
                    primeira_passagem TIMESTAMP,
                    ultima_passagem TIMESTAMP,
                    total_passagens INTEGER DEFAULT 0,
                    cidades_visitadas TEXT[], -- Array de cidades únicas
                    ufs_visitadas TEXT[], -- Array de UFs únicas
                    sistemas_origem TEXT[], -- Array de sistemas origem únicos
                    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """)
                
                # Criar índices para veiculos
                cur.execute("CREATE INDEX idx_veiculos_placa ON veiculos(placa)")
                cur.execute("CREATE INDEX idx_veiculos_marca_modelo ON veiculos(marca_modelo)")
                cur.execute("CREATE INDEX idx_veiculos_tipo ON veiculos(tipo)")
                cur.execute("CREATE INDEX idx_veiculos_primeira_passagem ON veiculos(primeira_passagem)")
                cur.execute("CREATE INDEX idx_veiculos_ultima_passagem ON veiculos(ultima_passagem)")
                cur.execute("CREATE INDEX idx_veiculos_total_passagens ON veiculos(total_passagens)")
                
                print("✅ Tabela veiculos criada com índices")
                
                # Criar tabela passagens (dados das passagens)
                print("📋 Criando tabela passagens...")
                cur.execute("""
                CREATE TABLE passagens (
                    id SERIAL PRIMARY KEY,
                    veiculo_id INTEGER NOT NULL REFERENCES veiculos(id) ON DELETE CASCADE,
                    dataHoraUTC TIMESTAMP NOT NULL,
                    pontoCaptura VARCHAR(500),
                    cidade VARCHAR(200),
                    uf VARCHAR(5),
                    codigoEquipamento VARCHAR(200),
                    codigoRodovia VARCHAR(100),
                    km NUMERIC(15,6),
                    faixa INTEGER,
                    sentido VARCHAR(100),
                    velocidade NUMERIC(10,3),
                    latitude NUMERIC(20,15),
                    longitude NUMERIC(20,15),
                    refImagem1 VARCHAR(1000),
                    refImagem2 VARCHAR(1000),
                    sistemaOrigem VARCHAR(200),
                    ehEquipamentoMovel BOOLEAN DEFAULT FALSE,
                    ehLeituraHumana BOOLEAN DEFAULT FALSE,
                    tipoInferidoIA VARCHAR(200),
                    marcaModeloInferidoIA VARCHAR(500),
                    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """)
                
                # Criar índices para passagens
                cur.execute("CREATE INDEX idx_passagens_veiculo_id ON passagens(veiculo_id)")
                cur.execute("CREATE INDEX idx_passagens_dataHoraUTC ON passagens(dataHoraUTC)")
                cur.execute("CREATE INDEX idx_passagens_cidade ON passagens(cidade)")
                cur.execute("CREATE INDEX idx_passagens_uf ON passagens(uf)")
                cur.execute("CREATE INDEX idx_passagens_codigoRodovia ON passagens(codigoRodovia)")
                cur.execute("CREATE INDEX idx_passagens_codigoEquipamento ON passagens(codigoEquipamento)")
                cur.execute("CREATE INDEX idx_passagens_sistemaOrigem ON passagens(sistemaOrigem)")
                cur.execute("CREATE INDEX idx_passagens_placa_data ON passagens(veiculo_id, dataHoraUTC)")
                cur.execute("CREATE INDEX idx_passagens_coordenadas ON passagens(latitude, longitude) WHERE latitude IS NOT NULL AND longitude IS NOT NULL")
                
                print("✅ Tabela passagens criada com índices")
                
                # Criar tabela municipios (se não existir)
                print("🏙️ Verificando tabela municipios...")
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
                
                print("✅ Tabela municipios verificada")
                
                # Criar função para atualizar estatísticas do veículo
                print("⚙️ Criando funções auxiliares...")
                
                # Primeiro, criar a função
                cur.execute("""
                CREATE OR REPLACE FUNCTION atualizar_estatisticas_veiculo()
                RETURNS TRIGGER AS $$
                DECLARE
                    veiculo_record RECORD;
                BEGIN
                    -- Buscar estatísticas do veículo
                    SELECT 
                        MIN(p.dataHoraUTC) as primeira,
                        MAX(p.dataHoraUTC) as ultima,
                        COUNT(*) as total,
                        ARRAY_AGG(DISTINCT p.cidade) FILTER (WHERE p.cidade IS NOT NULL) as cidades,
                        ARRAY_AGG(DISTINCT p.uf) FILTER (WHERE p.uf IS NOT NULL) as ufs,
                        ARRAY_AGG(DISTINCT p.sistemaOrigem) FILTER (WHERE p.sistemaOrigem IS NOT NULL) as sistemas
                    INTO veiculo_record
                    FROM passagens p
                    WHERE p.veiculo_id = NEW.veiculo_id;
                    
                    -- Atualizar veículo
                    UPDATE veiculos SET
                        primeira_passagem = veiculo_record.primeira,
                        ultima_passagem = veiculo_record.ultima,
                        total_passagens = veiculo_record.total,
                        cidades_visitadas = veiculo_record.cidades,
                        ufs_visitadas = veiculo_record.ufs,
                        sistemas_origem = veiculo_record.sistemas,
                        atualizado_em = CURRENT_TIMESTAMP
                    WHERE id = NEW.veiculo_id;
                    
                    RETURN NEW;
                END;
                $$ LANGUAGE plpgsql;
                """)
                
                # Depois, criar o trigger
                cur.execute("DROP TRIGGER IF EXISTS trigger_atualizar_estatisticas_veiculo ON passagens")
                
                cur.execute("""
                CREATE TRIGGER trigger_atualizar_estatisticas_veiculo
                    AFTER INSERT OR UPDATE OR DELETE ON passagens
                    FOR EACH ROW
                    EXECUTE FUNCTION atualizar_estatisticas_veiculo()
                """)
                
                print("✅ Funções e triggers criados")
                
                # Inserir municípios básicos se não existirem
                cur.execute("SELECT COUNT(*) FROM municipios")
                count = cur.fetchone()[0]
                
                if count == 0:
                    print("📍 Inserindo municípios básicos...")
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
                    
                    print("✅ Municípios básicos inseridos")
                
                conn.commit()
                
                print("\n🎉 Estrutura normalizada criada com sucesso!")
                print("📋 Estrutura criada:")
                print("   🚗 veiculos - Dados únicos dos veículos com estatísticas")
                print("   📋 passagens - Dados das passagens referenciando veículos")
                print("   🏙️ municipios - Municípios do Brasil")
                print("   ⚙️ Triggers automáticos para atualizar estatísticas")
                print("   🔍 Índices otimizados para consultas rápidas")
                
                return True
                
    except Exception as e:
        print(f"❌ Erro ao criar estrutura: {e}")
        return False

def show_structure():
    """Mostra a estrutura criada"""
    
    db_config = DatabaseConfig(
        host='localhost',
        port=5432,
        dbname='sentinela_treino',
        user='postgres',
        password='Jmkjmk.00'
    )
    
    try:
        with get_db_connection(db_config) as conn:
            with conn.cursor() as cur:
                print("\n📊 Estrutura das tabelas:")
                print("=" * 60)
                
                # Mostrar estrutura da tabela veiculos
                print("\n🚗 Tabela VEICULOS:")
                cur.execute("""
                    SELECT column_name, data_type, character_maximum_length, is_nullable, column_default
                    FROM information_schema.columns
                    WHERE table_name = 'veiculos'
                    ORDER BY ordinal_position
                """)
                columns = cur.fetchall()
                
                for col in columns:
                    nullable = "NULL" if col[3] == 'YES' else "NOT NULL"
                    length = f"({col[2]})" if col[2] else ""
                    default = f" DEFAULT {col[4]}" if col[4] else ""
                    print(f"   📝 {col[0]:<25} {col[1]}{length:<15} {nullable}{default}")
                
                # Mostrar estrutura da tabela passagens
                print("\n📋 Tabela PASSAGENS:")
                cur.execute("""
                    SELECT column_name, data_type, character_maximum_length, is_nullable, column_default
                    FROM information_schema.columns
                    WHERE table_name = 'passagens'
                    ORDER BY ordinal_position
                """)
                columns = cur.fetchall()
                
                for col in columns:
                    nullable = "NULL" if col[3] == 'YES' else "NOT NULL"
                    length = f"({col[2]})" if col[2] else ""
                    default = f" DEFAULT {col[4]}" if col[4] else ""
                    print(f"   📝 {col[0]:<25} {col[1]}{length:<15} {nullable}{default}")
                
                # Mostrar índices
                print("\n🔍 Índices criados:")
                cur.execute("""
                    SELECT indexname, tablename, indexdef
                    FROM pg_indexes 
                    WHERE schemaname = 'public' 
                    AND tablename IN ('veiculos', 'passagens')
                    ORDER BY tablename, indexname
                """)
                indexes = cur.fetchall()
                
                for idx in indexes:
                    print(f"   🔍 {idx[0]} ON {idx[1]}")
                
    except Exception as e:
        print(f"❌ Erro ao mostrar estrutura: {e}")

def main():
    """Função principal"""
    print("🏗️ Criador de Estrutura Normalizada - Sentinela Treino")
    print("=" * 60)
    
    if create_normalized_tables():
        show_structure()
        print("\n✅ Estrutura normalizada criada com sucesso!")
        print("\n🔧 Próximos passos:")
        print("   1. Execute o script de importação normalizada")
        print("   2. Os dados serão automaticamente separados em veículos e passagens")
        print("   3. As estatísticas dos veículos serão atualizadas automaticamente")
    else:
        print("❌ Falha ao criar estrutura normalizada")

if __name__ == "__main__":
    main()
