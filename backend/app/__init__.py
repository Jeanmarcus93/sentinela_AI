# backend/app/__init__.py
"""
Factory Flask para Sentinela IA v2.0
Integra sistema legacy com nova arquitetura frontend/backend + agentes especializados
"""

from flask import Flask, jsonify
from flask_cors import CORS
import os
import time
import logging

def create_app(config_name=None):
    """
    Factory para criar aplicação Flask
    
    Args:
        config_name: Nome da configuração (development, production, testing)
    
    Returns:
        Flask: Instância configurada da aplicação
    """
    
    app = Flask(__name__)
    
    # ==========================================
    # CONFIGURAÇÕES BÁSICAS
    # ==========================================
    
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    app.config['JSON_SORT_KEYS'] = False
    app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True
    
    # Configurar ambiente
    flask_env = os.environ.get('FLASK_ENV', 'development')
    app.config['ENV'] = flask_env
    app.config['DEBUG'] = flask_env == 'development'
    
    # ==========================================
    # CORS - FRONTEND SEPARADO
    # ==========================================
    
    # Permitir requisições do frontend
    allowed_origins = [
        "http://localhost:3000",    # Frontend dev (webpack dev server)
        "http://127.0.0.1:3000",   # Frontend dev alt
        "http://localhost:8080",    # Frontend prod local
        "http://127.0.0.1:8080",   # Frontend prod alt
        "http://localhost:3001",    # Frontend dev alternativo
        "http://127.0.0.1:3001"    # Frontend dev alternativo alt
    ]
    
    # Em produção, adicionar domínios específicos
    if flask_env == 'production':
        production_origins = os.environ.get('ALLOWED_ORIGINS', '').split(',')
        allowed_origins.extend([origin.strip() for origin in production_origins if origin.strip()])
    
    # Configuração CORS mais flexível para desenvolvimento
    cors_config = {
        r"/api/*": {
            "origins": allowed_origins,
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization", "X-Requested-With", "Accept"],
            "supports_credentials": True
        },
        r"/health": {
            "origins": allowed_origins,
            "methods": ["GET", "OPTIONS"],
            "allow_headers": ["Content-Type", "X-Requested-With"]
        },
        r"/info": {
            "origins": allowed_origins,
            "methods": ["GET", "OPTIONS"],
            "allow_headers": ["Content-Type", "X-Requested-With"]
        }
    }
    
    # Em desenvolvimento, permitir todas as origins para facilitar testes
    if flask_env == 'development':
        cors_config = {
            r"/*": {
                "origins": "*",
                "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                "allow_headers": ["Content-Type", "Authorization", "X-Requested-With", "Accept"],
                "supports_credentials": False
            }
        }
    
    CORS(app, resources=cors_config)
    
    # ==========================================
    # LOGGING
    # ==========================================
    
    if not app.debug and not app.testing:
        # Configurar logging para produção
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s %(levelname)s: %(message)s',
            handlers=[logging.StreamHandler()]
        )
        app.logger.setLevel(logging.INFO)
        app.logger.info('Sentinela IA Backend iniciado')
    
    # ==========================================
    # REGISTRO DE BLUEPRINTS
    # ==========================================
    
    # Blueprint PRINCIPAL (rotas legacy + CRUD)
    try:
        from app.routes.main_routes import main_bp
        app.register_blueprint(main_bp)
        print("✅ Rotas principais (main_bp) registradas")
    except ImportError as e:
        print(f"⚠️ Erro ao importar main_routes: {e}")
        app.logger.warning(f"main_routes não pôde ser carregado: {e}")
    
    # Blueprint ANÁLISE (dashboard, filtros, ML)
    try:
        from app.routes.analise_routes import analise_bp  
        app.register_blueprint(analise_bp)
        print("✅ Rotas de análise (analise_bp) registradas")
    except ImportError as e:
        print(f"⚠️ Erro ao importar analise_routes: {e}")
        app.logger.warning(f"analise_routes não pôde ser carregado: {e}")
    
    # Blueprint AGENTS v2 (sistema de agentes especializados)
    try:
        from app.routes.agent_routes import agent_bp
        app.register_blueprint(agent_bp)
        print("✅ Sistema de Agentes v2.0 (agent_bp) registrado em /api/v2/")
        app.config['AGENTS_AVAILABLE'] = True
    except ImportError as e:
        print(f"⚠️ Sistema de Agentes não disponível: {e}")
        print("   As rotas /api/v2/ não estarão disponíveis")
        app.logger.warning(f"Sistema de agentes não pôde ser carregado: {e}")
        app.config['AGENTS_AVAILABLE'] = False
    
    # Blueprint TREINAMENTO (sistema de treinamento de modelos)
    try:
        from app.routes.training_routes import training_bp
        app.register_blueprint(training_bp)
        print("✅ Sistema de Treinamento (training_bp) registrado em /api/training/")
        app.config['TRAINING_AVAILABLE'] = True
    except ImportError as e:
        print(f"⚠️ Sistema de Treinamento não disponível: {e}")
        print("   As rotas /api/training/ não estarão disponíveis")
        app.logger.warning(f"Sistema de treinamento não pôde ser carregado: {e}")
        app.config['TRAINING_AVAILABLE'] = False
    
    # Blueprint SENTINELA TREINO (banco de dados de treino normalizado)
    try:
        from app.routes.sentinela_treino_routes import sentinela_treino_bp
        app.register_blueprint(sentinela_treino_bp)
        print("✅ Sistema Sentinela Treino (sentinela_treino_bp) registrado em /api/treino/")
        app.config['SENTINELA_TREINO_AVAILABLE'] = True
    except ImportError as e:
        print(f"⚠️ Sistema Sentinela Treino não disponível: {e}")
        print("   As rotas /api/treino/ não estarão disponíveis")
        app.logger.warning(f"Sistema sentinela treino não pôde ser carregado: {e}")
        app.config['SENTINELA_TREINO_AVAILABLE'] = False
    
    # ==========================================
    # ERROR HANDLERS
    # ==========================================
    
    @app.errorhandler(404)
    def not_found(error):
        """Handler para recursos não encontrados"""
        return jsonify({
            "error": "Endpoint não encontrado",
            "message": "Verifique a URL e tente novamente",
            "available_apis": {
                "info": "/api/info",
                "legacy_consulta": "/api/consulta_placa/<placa>",
                "legacy_analise": "/api/analise_placa/<placa>",
                "agents_v2": "/api/v2/" if app.config.get('AGENTS_AVAILABLE') else "indisponível"
            },
            "documentation": {
                "health_check": "/api/v2/health" if app.config.get('AGENTS_AVAILABLE') else None,
                "system_stats": "/api/v2/stats" if app.config.get('AGENTS_AVAILABLE') else None
            }
        }), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        """Handler para erros internos do servidor"""
        app.logger.error(f'Erro interno: {str(error)}')
        return jsonify({
            "error": "Erro interno do servidor",
            "message": "Um erro inesperado ocorreu. Tente novamente mais tarde.",
            "support": "Verifique os logs para mais detalhes"
        }), 500
    
    @app.errorhandler(400)
    def bad_request(error):
        """Handler para requisições malformadas"""
        return jsonify({
            "error": "Requisição inválida",
            "message": "Verifique os dados enviados e tente novamente"
        }), 400
    
    # ==========================================
    # ROTAS DE SISTEMA
    # ==========================================
    
    @app.route('/health')
    @app.route('/api/health')
    def health_check():
        """Health check básico da aplicação"""
        try:
            # Testar conexão com banco
            from app.models.database import get_db_connection
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    cur.fetchone()
            db_status = "healthy"
        except Exception as e:
            db_status = f"error: {str(e)}"
            app.logger.error(f"Database health check failed: {e}")
        
        return jsonify({
            "status": "healthy" if db_status == "healthy" else "degraded",
            "timestamp": time.time(),
            "version": "2.0.0",
            "environment": app.config['ENV'],
            "services": {
                "database": db_status,
                "agents_system": "available" if app.config.get('AGENTS_AVAILABLE') else "unavailable",
                "sentinela_treino": "available" if app.config.get('SENTINELA_TREINO_AVAILABLE') else "unavailable"
            }
        }), 200 if db_status == "healthy" else 503
    
    @app.route('/info')
    @app.route('/api/info')
    def app_info():
        """Informações gerais da aplicação"""
        try:
            # Tentar obter stats dos agentes se disponível
            agents_info = {}
            if app.config.get('AGENTS_AVAILABLE'):
                try:
                    from app.services.enhanced_placa_service import get_enhanced_placa_service
                    service = get_enhanced_placa_service()
                    stats = service.get_orchestrator_stats()
                    agents_info = {
                        "status": "available",
                        "registered_agents": stats.get("registered_agents", 0),
                        "total_processed": stats.get("total_processed", 0),
                        "success_rate": f"{stats.get('overall_success_rate', 0):.2%}"
                    }
                except Exception as e:
                    agents_info = {
                        "status": "error", 
                        "error": str(e)
                    }
            else:
                agents_info = {"status": "not_available"}
        
        except Exception:
            agents_info = {"status": "unknown"}
        
        return jsonify({
            "application": "Sistema Sentinela IA",
            "version": "2.0.0",
            "architecture": "Frontend/Backend Separado", 
            "framework": "Flask",
            "environment": app.config['ENV'],
            "debug": app.config['DEBUG'],
            "status": "operational",
            "timestamp": time.time(),
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
                } if app.config.get('AGENTS_AVAILABLE') else "not_available",
                "training": {
                    "status": "/api/training/status",
                    "models": "/api/training/models",
                    "train": "/api/training/train/<model_type>",
                    "prepare_data": "/api/training/feedback/prepare",
                    "validate_data": "/api/training/feedback/validate",
                    "history": "/api/training/history"
                } if app.config.get('TRAINING_AVAILABLE') else "not_available",
                "sentinela_treino": {
                    "health": "/api/treino/health",
                    "info": "/api/treino/info",
                    "search_vehicles": "/api/treino/vehicles/search",
                    "vehicle_details": "/api/treino/vehicles/<id>",
                    "vehicle_passages": "/api/treino/vehicles/<id>/passages",
                    "analytics": "/api/treino/analytics",
                    "dashboard": "/api/treino/dashboard",
                    "consulta_placa": "/api/treino/consulta_placa/<placa>",
                    "municipios": "/api/treino/municipios",
                    "export_vehicles": "/api/treino/export/vehicles",
                    "export_passages": "/api/treino/export/passages/<id>"
                } if app.config.get('SENTINELA_TREINO_AVAILABLE') else "not_available"
            },
            "agents_system": agents_info,
            "frontend_urls": allowed_origins if app.debug else ["configured_in_production"]
        })
    
    @app.route('/')
    def root():
        """Rota raiz - redireciona para info"""
        return jsonify({
            "message": "Backend Sentinela IA v2.0 funcionando",
            "info": "/api/info",
            "health": "/api/health",
            "frontend": "http://localhost:3000" if app.debug else "configured_separately"
        })
    
    # ==========================================
    # MIDDLEWARE
    # ==========================================
    
    @app.before_request
    def before_request():
        """Middleware executado antes de cada requisição"""
        from flask import request, g
        
        # Timestamp para medir tempo de processamento
        g.start_time = time.time()
        
        # Log da requisição (apenas em debug)
        if app.debug:
            app.logger.debug(f"Request: {request.method} {request.path}")
    
    @app.after_request
    def after_request(response):
        """Middleware executado após cada requisição"""
        from flask import request, g
        
        # Adicionar headers de resposta
        response.headers['X-API-Version'] = '2.0.0'
        
        # Calcular tempo de processamento
        if hasattr(g, 'start_time'):
            duration = time.time() - g.start_time
            response.headers['X-Process-Time'] = f"{duration:.3f}"
            
            # Log apenas em desenvolvimento
            if app.debug and not request.path.startswith('/static'):
                status_icon = "✅" if response.status_code < 400 else "❌"
                app.logger.info(f"{status_icon} {request.method} {request.path} - {response.status_code} - {duration:.3f}s")
        
        # Headers de segurança básicos
        if not app.debug:
            response.headers['X-Content-Type-Options'] = 'nosniff'
            response.headers['X-Frame-Options'] = 'DENY'
            response.headers['X-XSS-Protection'] = '1; mode=block'
        
        return response
    
    # ==========================================
    # INICIALIZAÇÃO FINAL
    # ==========================================
    
    print("🚀 Aplicação Flask criada com sucesso!")
    print("📌 Arquitetura: Frontend/Backend Separado")
    print("📌 APIs disponíveis:")
    print("   - Legacy: /api/consulta_placa/, /api/analise, etc.")
    if app.config.get('AGENTS_AVAILABLE'):
        print("   - Agentes v2: /api/v2/")
    if app.config.get('SENTINELA_TREINO_AVAILABLE'):
        print("   - Sentinela Treino: /api/treino/")
    print("   - Sistema: /api/info, /api/health")
    print("   - CORS habilitado para:", allowed_origins[:2], "...")
    
    return app


# ==========================================
# FUNÇÕES AUXILIARES
# ==========================================

def init_database():
    """Inicializa o banco de dados (chamada externa)"""
    try:
        from config.settings import criar_tabelas
        criar_tabelas()
        print("✅ Banco de dados inicializado")
        return True
    except Exception as e:
        print(f"❌ Erro ao inicializar banco: {e}")
        return False

def check_ml_models():
    """Verifica se os modelos de ML estão disponíveis"""
    import os
    models_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'ml_models', 'trained')
    
    required_models = [
        'semantic_clf.joblib',
        'semantic_labels.joblib',
        'routes_clf.joblib', 
        'routes_labels.joblib'
    ]
    
    missing_models = []
    for model in required_models:
        model_path = os.path.join(models_dir, model)
        if not os.path.exists(model_path):
            missing_models.append(model)
    
    if missing_models:
        print(f"⚠️ Modelos ML não encontrados: {missing_models}")
        print("   Execute os scripts de treinamento em ml_models/training/")
        return False
    else:
        print("✅ Todos os modelos ML encontrados")
        return True


# Para compatibilidade com importações diretas
if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)