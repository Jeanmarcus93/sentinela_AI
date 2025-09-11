# app/__init__.py
"""
Factory function para aplicação Flask com integração completa
Mantém rotas existentes + adiciona sistema de agentes
"""

from flask import Flask, jsonify
from flask_cors import CORS
import os

def create_app():
    """Cria e configura a aplicação Flask"""
    
    app = Flask(__name__)
    
    # Configurações básicas
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    app.config['JSON_SORT_KEYS'] = False
    app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True
    
    # Configurar CORS
    CORS(app, resources={
        r"/api/*": {"origins": "*"},
        r"/consultar/*": {"origins": "*"}
    })
    
    # Registrar blueprints EXISTENTES (mantém tudo funcionando)
    try:
        from app.routes.main_routes import main_bp
        app.register_blueprint(main_bp)
        print("✅ Rotas principais (main_bp) registradas")
    except ImportError as e:
        print(f"⚠️ Erro ao importar main_routes: {e}")
    
    try:
        from app.routes.analise_routes import analise_bp  
        app.register_blueprint(analise_bp)
        print("✅ Rotas de análise (analise_bp) registradas")
    except ImportError as e:
        print(f"⚠️ Erro ao importar analise_routes: {e}")
    
    # Registrar blueprint NOVO do sistema de agentes
    try:
        from app.routes.agent_routes import agent_bp
        app.register_blueprint(agent_bp)
        print("✅ Sistema de Agentes v2.0 (agent_bp) registrado em /api/v2/")
    except ImportError as e:
        print(f"⚠️ Sistema de Agentes não pôde ser registrado: {e}")
        print("   As rotas /api/v2/ não estarão disponíveis")
        print("   Verifique se agent_routes.py foi criado corretamente")
    
    # Handler global de erros
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            "error": "Endpoint não encontrado",
            "available_apis": {
                "legacy_consulta": "/api/consulta_placa/<placa>",
                "legacy_analise": "/api/analise_placa/<placa>", 
                "agents_v2": "/api/v2/ - Sistema de Agentes Especializados"
            },
            "documentation": {
                "agents_info": "/api/v2/",
                "health_check": "/api/v2/health",
                "system_stats": "/api/v2/stats"
            }
        }), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({
            "error": "Erro interno do servidor",
            "message": "Um erro inesperado ocorreu"
        }), 500
    
    # Rota de informações da aplicação
    @app.route('/info')
    def app_info():
        """Informações gerais da aplicação"""
        info = {
            "application": "Sistema de Análise de Placas",
            "version": "2.0.0", 
            "framework": "Flask",
            "status": "operational",
            "apis": {
                "legacy": {
                    "consulta_placa": "/api/consulta_placa/<placa>",
                    "consulta_cpf": "/api/consulta_cpf/<cpf>",
                    "analise": "/api/analise",
                    "analise_placa": "/api/analise_placa/<placa>"
                },
                "v2_agents": {
                    "info": "/api/v2/",
                    "comprehensive": "/api/v2/analyze/<placa>",
                    "fast": "/api/v2/analyze/<placa>/fast",
                    "batch": "/api/v2/analyze/batch",
                    "health": "/api/v2/health",
                    "stats": "/api/v2/stats"
                }
            }
        }
        
        # Tentar obter informações dos agentes
        try:
            from app.services.enhanced_placa_service import get_enhanced_placa_service
            service = get_enhanced_placa_service()
            stats = service.get_orchestrator_stats()
            
            info.update({
                "agents_status": "available",
                "agents": {
                    "registered": stats.get("registered_agents", 0),
                    "total_processed": stats.get("total_processed", 0),
                    "success_rate": f"{stats.get('overall_success_rate', 0):.2%}"
                }
            })
        except Exception as e:
            info.update({
                "agents_status": "not_available",
                "error": str(e)
            })
        
        return jsonify(info)
    
    # Middleware para logging
    @app.before_request
    def log_request():
        """Log básico de requisições"""
        from flask import request
        import time
        request.start_time = time.time()
    
    @app.after_request
    def log_response(response):
        """Log de respostas com tempo de processamento"""
        from flask import request
        import time
        
        if hasattr(request, 'start_time'):
            duration = time.time() - request.start_time
            print(f"📝 {request.method} {request.path} - {response.status_code} - {duration:.3f}s")
            response.headers['X-Process-Time'] = str(duration)
        
        return response
    
    print("🚀 Aplicação Flask criada com sucesso!")
    print("📌 APIs disponíveis:")
    print("   - Legacy: /api/consulta_placa/, /api/analise, etc.")
    print("   - Agentes v2: /api/v2/")
    print("   - Info: /info")
    
    return app