#!/usr/bin/env python3
"""
Exemplo de uso do script de criação de banco
"""

import subprocess
import sys
from pathlib import Path

def exemplo_criar_banco():
    """Exemplo de como criar um banco usando o script"""
    
    # Configurações do banco
    config = {
        'db_name': 'sentinela_exemplo',
        'host': 'localhost',
        'port': 5432,
        'user': 'postgres',
        'password': 'Jmkjmk.00'
    }
    
    print("🚀 Exemplo de criação de banco PostgreSQL")
    print("=" * 50)
    print(f"📊 Banco: {config['db_name']}")
    print(f"🏠 Host: {config['host']}:{config['port']}")
    print(f"👤 Usuário: {config['user']}")
    print()
    
    # Comando para executar
    cmd = [
        sys.executable,  # python
        'scripts/create_database.py',
        '--db-name', config['db_name'],
        '--host', config['host'],
        '--port', str(config['port']),
        '--user', config['user'],
        '--password', config['password']
    ]
    
    print("📋 Comando a ser executado:")
    print(" ".join(cmd))
    print()
    
    # Perguntar se deve executar
    resposta = input("Deseja executar este comando? (s/n): ").lower().strip()
    
    if resposta in ['s', 'sim', 'y', 'yes']:
        try:
            print("🔄 Executando criação do banco...")
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                print("✅ Banco criado com sucesso!")
                print("\n📋 Saída:")
                print(result.stdout)
            else:
                print("❌ Erro ao criar banco:")
                print(result.stderr)
                
        except Exception as e:
            print(f"❌ Erro na execução: {e}")
    else:
        print("❌ Operação cancelada")

def mostrar_estrutura_passagens():
    """Mostra a estrutura da tabela passagens"""
    
    print("\n📋 Estrutura da Tabela Passagens")
    print("=" * 50)
    
    colunas = [
        ("id", "SERIAL PRIMARY KEY", "ID único"),
        ("dataHoraUTC", "TIMESTAMP", "Data e hora em UTC"),
        ("placa", "VARCHAR(10)", "Placa do veículo"),
        ("pontoCaptura", "VARCHAR(200)", "Ponto de captura"),
        ("cidade", "VARCHAR(200)", "Cidade"),
        ("uf", "VARCHAR(5)", "Unidade Federativa"),
        ("codigoEquipamento", "VARCHAR(100)", "Código do equipamento"),
        ("codigoRodovia", "VARCHAR(50)", "Código da rodovia"),
        ("km", "NUMERIC(10,3)", "Quilometragem"),
        ("faixa", "INTEGER", "Faixa da rodovia"),
        ("sentido", "VARCHAR(50)", "Sentido da via"),
        ("velocidade", "NUMERIC(5,2)", "Velocidade registrada"),
        ("latitude", "NUMERIC(10,8)", "Latitude GPS"),
        ("longitude", "NUMERIC(11,8)", "Longitude GPS"),
        ("refImagem1", "VARCHAR(500)", "Referência da imagem 1"),
        ("refImagem2", "VARCHAR(500)", "Referência da imagem 2"),
        ("sistemaOrigem", "VARCHAR(100)", "Sistema de origem"),
        ("ehEquipamentoMovel", "BOOLEAN", "Se é equipamento móvel"),
        ("ehLeituraHumana", "BOOLEAN", "Se é leitura humana"),
        ("tipoInferidoIA", "VARCHAR(100)", "Tipo inferido por IA"),
        ("marcaModeloInferidoIA", "VARCHAR(200)", "Marca/modelo inferido por IA"),
        ("criado_em", "TIMESTAMP", "Data de criação"),
        ("atualizado_em", "TIMESTAMP", "Data de atualização")
    ]
    
    for coluna, tipo, descricao in colunas:
        print(f"{coluna:<25} {tipo:<20} {descricao}")

def mostrar_comandos_uteis():
    """Mostra comandos úteis para trabalhar com o banco"""
    
    print("\n🔧 Comandos Úteis")
    print("=" * 50)
    
    comandos = [
        ("Conectar ao banco", "psql -h localhost -p 5432 -U postgres -d sentinela_exemplo"),
        ("Ver tabelas", "\\dt"),
        ("Ver estrutura da tabela", "\\d passagens"),
        ("Ver índices", "\\di"),
        ("Contar registros", "SELECT COUNT(*) FROM passagens;"),
        ("Ver municípios inseridos", "SELECT * FROM municipios LIMIT 10;"),
        ("Sair do psql", "\\q")
    ]
    
    for descricao, comando in comandos:
        print(f"{descricao:<25} {comando}")

if __name__ == "__main__":
    print("🎯 Exemplo de Uso - Script de Criação de Banco")
    print("=" * 60)
    
    while True:
        print("\n📋 Opções:")
        print("1. Mostrar estrutura da tabela passagens")
        print("2. Executar exemplo de criação de banco")
        print("3. Mostrar comandos úteis")
        print("4. Sair")
        
        opcao = input("\nEscolha uma opção (1-4): ").strip()
        
        if opcao == "1":
            mostrar_estrutura_passagens()
        elif opcao == "2":
            exemplo_criar_banco()
        elif opcao == "3":
            mostrar_comandos_uteis()
        elif opcao == "4":
            print("👋 Até logo!")
            break
        else:
            print("❌ Opção inválida!")

