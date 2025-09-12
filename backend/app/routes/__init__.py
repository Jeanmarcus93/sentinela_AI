# app/routes/__init__.py
"""
Módulo de rotas Flask para o Sistema Sentinela IA

Este módulo contém todos os blueprints de rotas da aplicação:
- main_routes: Rotas principais (consulta, nova ocorrência, etc.)
- analise_routes: Rotas de análise e inteligência
- agent_routes: Rotas do sistema de agentes v2.0
"""

# Importar blueprints para facilitar o uso
from .main_routes import main_bp
from .analise_routes import analise_bp

# Tentar importar blueprint dos agentes (pode não estar disponível)
try:
    from .agent_routes import agent_bp
    AGENT_ROUTES_AVAILABLE = True
except ImportError:
    agent_bp = None
    AGENT_ROUTES_AVAILABLE = False

__all__ = ['main_bp', 'analise_bp', 'agent_bp', 'AGENT_ROUTES_AVAILABLE']