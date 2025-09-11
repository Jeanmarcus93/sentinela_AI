#!/usr/bin/env python3
"""
Script para migrar a estrutura atual para a nova organização em pastas
Execute este script a partir do diretório raiz do projeto
"""

import os
import shutil
from pathlib import Path

def create_directory_structure():
    """Cria a estrutura de diretórios"""
    directories = [
        "app",
        "app/models",
        "app/routes", 
        "app/services",
        "app/utils",
        "app/templates",
        "static",
        "static/css",
        "static/js",
        "static/images",
        "config",
        "ml_models",
        "ml_models/trained",
        "ml_models/training",
        "scripts",
        "tests"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        # Criar __init__.py em diretórios Python
        if not directory.startswith('static') and not directory.startswith('app/templates'):
            init_file = Path(directory) / "__init__.py"
            if not init_file.exists():
                init_file.touch()
    
    print("✅ Estrutura de diretórios criada")

def move_files():
    """Move os arquivos para suas novas localizações"""
    file_moves = {
        # Backend Python files
        "config.py": "config/settings.py",
        "database.py": "app/models/database.py", 
        "routes.py": "app/routes/main_routes.py",
        "analise.py": "app/routes/analise_routes.py",
        "analisar_placa.py": "app/services/placa_service.py",
        "semantic_local.py": "app/services/semantic_service.py",
        "train_inteligente.py": "ml_models/training/train_inteligente.py",
        "train_routes.py": "ml_models/training/train_routes.py",
        "popular_banco.py": "scripts/popular_banco.py",
        
        # Frontend JavaScript files
        "main.js": "static/js/main.js",
        "consulta.js": "static/js/consulta.js", 
        "analise.js": "static/js/analise.js",
        "analise_IA.js": "static/js/analise_IA.js",
        "nova_ocorrencia.js": "static/js/nova_ocorrencia.js",
        
        # ML Models (se existirem)
        "models/semantic_clf.joblib": "ml_models/trained/semantic_clf.joblib",
        "models/semantic_labels.joblib": "ml_models/trained/semantic_labels.joblib",
        "models/routes_clf.joblib": "ml_models/trained/routes_clf.joblib",
        "models/routes_labels.joblib": "ml_models/trained/routes_labels.joblib",
    }
    
    for old_path, new_path in file_moves.items():
        if os.path.exists(old_path):
            try:
                # Criar diretório de destino se não existir
                dest_dir = os.path.dirname(new_path)
                Path(dest_dir).mkdir(parents=True, exist_ok=True)
                
                shutil.move(old_path, new_path)
                print(f"✅ Movido: {old_path} → {new_path}")
            except Exception as e:
                print(f"❌ Erro ao mover {old_path}: {e}")
        else:
            print(f"⚠️  Arquivo não encontrado: {old_path}")

def create_new_files():
    """Cria novos arquivos necessários para a nova estrutura"""
    
    # app/__init__.py (Factory Pattern)
    app_init = """from flask import Flask
from config.settings import Config

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Registrar blueprints
    from app.routes.main_routes import main_bp
    from app.routes.analise_routes import analise_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(analise_bp)
    
    return app
"""
    
    # run.py (Novo ponto de entrada)
    run_py = """#!/usr/bin/env python3
from app import create_app
from config.settings import criar_tabelas

app = create_app()

# Função de migração (mantida do app.py original)
def migrar_apreensoes_para_tabela_normalizada():
    \"\"\"
    Migra dados da coluna JSON 'apreensoes' para a nova tabela normalizada 'apreensoes'.
    \"\"\"
    print("Iniciando migração de apreensões para tabela normalizada...")
    try:
        from app.models.database import get_db_connection
        import json
        
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Verifica se a migração já foi executada
                cur.execute("SELECT COUNT(*) FROM apreensoes;")
                if cur.fetchone()[0] > 0:
                    print("A tabela 'apreensoes' já contém dados. A migração não será executada novamente.")
                    return

                # Busca todas as ocorrências que possuem dados de apreensões
                cur.execute("SELECT id, apreensoes FROM ocorrencias WHERE apreensoes IS NOT NULL AND apreensoes::text != '[]';")
                ocorrencias = cur.fetchall()

                if not ocorrencias:
                    print("Nenhum dado de apreensão para migrar.")
                    return

                print(f"Encontrados {len(ocorrencias)} ocorrências com dados de apreensões para migrar.")
                
                for occ_id, apreensoes_data in ocorrencias:
                    apreensoes_list = []
                    if isinstance(apreensoes_data, str):
                        try:
                            apreensoes_list = json.loads(apreensoes_data)
                        except json.JSONDecodeError:
                            print(f"AVISO: Não foi possível decodificar o JSON para a ocorrência ID {occ_id}.")
                            continue
                    elif isinstance(apreensoes_data, list):
                        apreensoes_list = apreensoes_data

                    for item in apreensoes_list:
                        tipo = item.get('tipo')
                        if tipo == 'Armas':
                            tipo = 'Arma'
                        
                        quantidade = item.get('quantidade')
                        unidade = item.get('unidade')
                        
                        if not all([tipo, quantidade, unidade]):
                            print(f"AVISO: Item de apreensão incompleto para ocorrência ID {occ_id}.")
                            continue
                        
                        cur.execute(
                            "INSERT INTO apreensoes (ocorrencia_id, tipo, quantidade, unidade) VALUES (%s, %s, %s, %s)",
                            (occ_id, tipo, quantidade, unidade)
                        )
                conn.commit()
                print("Migração de apreensões concluída com sucesso.")

    except Exception as e:
        print(f"Erro durante a migração de apreensões: {e}")

if __name__ == '__main__':
    try:
        criar_tabelas()
        migrar_apreensoes_para_tabela_normalizada()
    except Exception as e:
        print(f"Erro ao inicializar: {e}")
    
    app.run(debug=True, use_reloader=False)
"""
    
    # requirements.txt
    requirements = """Flask==2.3.3
psycopg==3.1.10
SQLAlchemy==2.0.21
pandas==2.1.1
numpy==1.24.3
scikit-learn==1.3.0
joblib==1.3.2
sentence-transformers==2.2.2
spacy==3.6.1
yake==0.4.8
Faker==19.6.2
"""
    
    # .env.example
    env_example = """# Configurações do Banco de Dados
DB_HOST=localhost
DB_PORT=5432
DB_NAME=sentinela_teste
DB_USER=postgres
DB_PASSWORD=Jmkjmk.00

# Banco de Veículos
VEICULOS_DB_NAME=veiculos_db
VEICULOS_DB_USER=postgres
VEICULOS_DB_PASSWORD=Jmkjmk.00

# Configurações Flask
FLASK_ENV=development
SECRET_KEY=sua_chave_secreta_aqui

# Modelos de ML
SPACY_PT_MODEL=pt_core_news_lg
SENTENCE_EMB_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
"""
    
    # .gitignore
    gitignore = """# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
ENV/
.venv/

# Flask
instance/
.webassets-cache

# Environment variables
.env

# ML Models (large files)
ml_models/trained/*.joblib

# Database
*.db
*.sqlite

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Logs
*.log
"""
    
    files_to_create = {
        "app/__init__.py": app_init,
        "run.py": run_py, 
        "requirements.txt": requirements,
        ".env.example": env_example,
        ".gitignore": gitignore
    }
    
    for filepath, content in files_to_create.items():
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✅ Criado: {filepath}")

def update_imports_in_file(filepath, import_updates):
    """Atualiza imports em um arquivo específico"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        for old_import, new_import in import_updates.items():
            content = content.replace(old_import, new_import)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✅ Imports atualizados em: {filepath}")
    except Exception as e:
        print(f"❌ Erro ao atualizar imports em {filepath}: {e}")

def update_imports():
    """Atualiza imports nos arquivos movidos"""
    import_updates = {
        # Atualizações comuns
        "from database import": "from app.models.database import",
        "from semantic_local import": "from app.services.semantic_service import", 
        "from analisar_placa import": "from app.services.placa_service import",
        "from config import": "from config.settings import",
        "from routes import": "from app.routes.main_routes import",
        "from analise import": "from app.routes.analise_routes import",
        # Para os scripts de treinamento
        "sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))\nfrom database import": "sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))\nfrom app.models.database import",
    }
    
    # Lista de arquivos para atualizar
    files_to_update = [
        "app/routes/main_routes.py",
        "app/routes/analise_routes.py", 
        "app/services/placa_service.py",
        "app/services/semantic_service.py",
        "ml_models/training/train_inteligente.py",
        "ml_models/training/train_routes.py",
        "scripts/popular_banco.py"
    ]
    
    for filepath in files_to_update:
        if os.path.exists(filepath):
            update_imports_in_file(filepath, import_updates)

def main():
    print("🚀 Iniciando migração da estrutura do projeto...")
    
    # Fazer backup do app.py original antes de qualquer coisa
    if os.path.exists("app.py"):
        shutil.copy2("app.py", "app.py.backup")
        print("✅ Backup do app.py criado")
    
    create_directory_structure()
    move_files()
    create_new_files()
    update_imports()
    
    # Mover app.py para app/main.py por último
    if os.path.exists("app.py"):
        shutil.move("app.py", "app/main.py")
        print("✅ app.py movido para app/main.py")
    
    print("\n🎉 Migração concluída!")
    print("\nPróximos passos:")
    print("1. Revisar e ajustar imports se necessário")
    print("2. Testar a aplicação com: python run.py")
    print("3. Configurar variáveis de ambiente (.env)")
    print("4. Executar testes")

if __name__ == "__main__":
    main()