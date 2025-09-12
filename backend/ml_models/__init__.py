# ml_models/__init__.py
"""
Módulo de Machine Learning para o Sistema Sentinela IA

Este módulo contém:
- Scripts de treinamento para modelos de rotas e análise semântica
- Modelos treinados salvos em formato joblib
- Utilitários para análise de risco e classificação

Estrutura:
- training/: Scripts de treinamento
- trained/: Modelos treinados salvos
"""

__version__ = "1.0.0"
__author__ = "Sistema Sentinela IA"

# Imports opcionais para facilitar o uso
try:
    import joblib
    import numpy as np
    import pandas as pd
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.linear_model import LogisticRegression
    ML_DEPENDENCIES_AVAILABLE = True
except ImportError:
    ML_DEPENDENCIES_AVAILABLE = False

def check_dependencies():
    """Verifica se as dependências de ML estão disponíveis"""
    return ML_DEPENDENCIES_AVAILABLE

def get_model_info():
    """Retorna informações sobre os modelos disponíveis"""
    import os
    
    models_dir = os.path.join(os.path.dirname(__file__), "trained")
    info = {
        "models_directory": models_dir,
        "available_models": [],
        "dependencies_ok": ML_DEPENDENCIES_AVAILABLE
    }
    
    if os.path.exists(models_dir):
        model_files = [f for f in os.listdir(models_dir) if f.endswith('.joblib')]
        info["available_models"] = model_files
    
    return info

# Constantes úteis
MODEL_PATHS = {
    "routes_classifier": "trained/routes_clf.joblib",
    "routes_labels": "trained/routes_labels.joblib", 
    "semantic_classifier": "trained/semantic_clf.joblib",
    "semantic_labels": "trained/semantic_labels.joblib"
}

# Verificação de inicialização
if not ML_DEPENDENCIES_AVAILABLE:
    print("⚠️ Algumas dependências de ML não estão disponíveis.")
    print("   Execute: pip install scikit-learn pandas numpy joblib")
