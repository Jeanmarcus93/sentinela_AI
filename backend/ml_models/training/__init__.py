# ml_models/training/__init__.py
"""
Scripts de Treinamento para Modelos de Machine Learning

Este módulo contém scripts especializados para treinar diferentes tipos de modelos:

- train_routes.py: Treinamento do classificador de padrões de rotas
- train_inteligente.py: Treinamento do sistema de análise semântica inteligente

Uso típico:
    python ml_models/training/train_routes.py
    python ml_models/training/train_inteligente.py
"""

import os
import sys
from typing import Dict, Any, Optional

__version__ = "1.0.0"

# Adicionar caminho do projeto para imports
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

# Configurações de treinamento
TRAINING_CONFIG = {
    "routes": {
        "script": "train_routes.py",
        "description": "Classificador de padrões de rotas suspeitas",
        "output_models": ["routes_clf.joblib", "routes_labels.joblib"],
        "min_samples": 100
    },
    "semantic": {
        "script": "train_inteligente.py", 
        "description": "Sistema de análise semântica de relatos",
        "output_models": ["semantic_clf.joblib", "semantic_labels.joblib"],
        "min_samples": 50
    }
}

def get_training_info() -> Dict[str, Any]:
    """Retorna informações sobre os scripts de treinamento disponíveis"""
    training_dir = os.path.dirname(__file__)
    
    info = {
        "training_directory": training_dir,
        "available_scripts": [],
        "config": TRAINING_CONFIG
    }
    
    # Verificar quais scripts existem
    for model_type, config in TRAINING_CONFIG.items():
        script_path = os.path.join(training_dir, config["script"])
        if os.path.exists(script_path):
            info["available_scripts"].append({
                "type": model_type,
                "script": config["script"],
                "description": config["description"],
                "path": script_path,
                "exists": True
            })
        else:
            info["available_scripts"].append({
                "type": model_type,
                "script": config["script"],
                "description": config["description"],
                "path": script_path,
                "exists": False
            })
    
    return info

def check_training_dependencies() -> Dict[str, bool]:
    """Verifica se as dependências necessárias para treinamento estão disponíveis"""
    dependencies = {
        "scikit-learn": False,
        "pandas": False,
        "numpy": False,
        "joblib": False,
        "psycopg": False,
        "sentence-transformers": False,
        "spacy": False,
        "yake": False
    }
    
    for lib in dependencies:
        try:
            if lib == "scikit-learn":
                import sklearn
            elif lib == "sentence-transformers":
                import sentence_transformers
            else:
                __import__(lib)
            dependencies[lib] = True
        except ImportError:
            dependencies[lib] = False
    
    return dependencies

def run_training_script(model_type: str, *args) -> bool:
    """
    Executa um script de treinamento
    
    Args:
        model_type: Tipo do modelo ('routes' ou 'semantic')
        *args: Argumentos adicionais para o script
    
    Returns:
        True se o treinamento foi bem-sucedido
    """
    if model_type not in TRAINING_CONFIG:
        print(f"❌ Tipo de modelo '{model_type}' não reconhecido")
        return False
    
    script_name = TRAINING_CONFIG[model_type]["script"]
    script_path = os.path.join(os.path.dirname(__file__), script_name)
    
    if not os.path.exists(script_path):
        print(f"❌ Script '{script_name}' não encontrado")
        return False
    
    print(f"🚀 Executando treinamento: {TRAINING_CONFIG[model_type]['description']}")
    
    try:
        # Importar e executar o módulo
        import subprocess
        cmd = [sys.executable, script_path] + list(args)
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Treinamento concluído com sucesso!")
            return True
        else:
            print(f"❌ Erro no treinamento:")
            print(result.stderr)
            return False
            
    except Exception as e:
        print(f"❌ Erro ao executar treinamento: {e}")
        return False

def validate_training_environment() -> bool:
    """Valida se o ambiente está pronto para treinamento"""
    print("🔍 Validando ambiente de treinamento...")
    
    # Verificar dependências
    deps = check_training_dependencies()
    missing_deps = [lib for lib, available in deps.items() if not available]
    
    if missing_deps:
        print(f"❌ Dependências faltando: {', '.join(missing_deps)}")
        print("   Execute: pip install scikit-learn pandas numpy joblib psycopg sentence-transformers spacy yake")
        return False
    
    # Verificar banco de dados
    try:
        from app.models.database import get_db_connection
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM ocorrencias WHERE relato IS NOT NULL")
                count = cur.fetchone()[0]
        
        if count < 10:
            print(f"❌ Poucos dados para treinamento ({count} relatos)")
            print("   Execute: python scripts/popular_banco.py")
            return False
        
        print(f"✅ Dados disponíveis: {count} relatos")
        
    except Exception as e:
        print(f"❌ Erro de conectividade com banco: {e}")
        return False
    
    # Verificar diretório de saída
    models_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "trained")
    os.makedirs(models_dir, exist_ok=True)
    
    print("✅ Ambiente validado com sucesso!")
    return True

def main():
    """Função principal para execução direta do módulo"""
    print("🎯 Sistema de Treinamento - Sentinela IA")
    print("=" * 45)
    
    # Mostrar informações
    info = get_training_info()
    print("\n📊 Scripts disponíveis:")
    for script_info in info["available_scripts"]:
        status = "✅" if script_info["exists"] else "❌"
        print(f"   {status} {script_info['type']}: {script_info['description']}")
    
    # Validar ambiente
    if validate_training_environment():
        print("\n🚀 Ambiente pronto para treinamento!")
        print("\nComandos disponíveis:")
        print("   python ml_models/training/train_routes.py")
        print("   python ml_models/training/train_inteligente.py")
    else:
        print("\n⚠️ Corrija os problemas acima antes de treinar os modelos")

if __name__ == "__main__":
    main()
