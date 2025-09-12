#!/usr/bin/env python3
"""
WSGI Entry Point para Sistema Sentinela IA

Este arquivo é usado para servir a aplicação em ambientes de produção
com servidores WSGI como Gunicorn, uWSGI, Apache mod_wsgi, etc.

Uso com Gunicorn:
    gunicorn --bind 0.0.0.0:5000 --workers 4 wsgi:application

Uso com uWSGI:
    uwsgi --http :5000 --module wsgi:application --processes 4

Uso com Apache mod_wsgi:
    WSGIScriptAlias / /path/to/wsgi.py
"""

import os
import sys
import logging
from logging.handlers import RotatingFileHandler

# Adicionar o diretório do projeto ao path Python
project_dir = os.path.dirname(os.path.abspath(__file__))
if project_dir not in sys.path:
    sys.path.insert(0, project_dir)

def create_production_app():
    """
    Cria e configura a aplicação para produção
    """
    try:
        # Importar e criar aplicação
        from app import create_app
        from config.settings import criar_tabelas
        
        app = create_app()
        
        # Configurações específicas de produção
        app.config.update(
            DEBUG=False,
            TESTING=False,
            SECRET_KEY=os.environ.get('SECRET_KEY', 'change-this-in-production'),
            WTF_CSRF_ENABLED=True
        )
        
        # Configurar logging para produção
        if not app.debug and not app.testing:
            # Criar diretório de logs se não existir
            logs_dir = os.path.join(project_dir, 'logs')
            os.makedirs(logs_dir, exist_ok=True)
            
            # Configurar handler de arquivo com rotação
            file_handler = RotatingFileHandler(
                os.path.join(logs_dir, 'sentinela.log'),
                maxBytes=10240000,  # 10MB
                backupCount=10
            )
            
            # Formato detalhado para logs
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s %(levelname)s: %(message)s '
                '[in %(pathname)s:%(lineno)d]'
            ))
            
            file_handler.setLevel(logging.INFO)
            app.logger.addHandler(file_handler)
            app.logger.setLevel(logging.INFO)
            app.logger.info('Sistema Sentinela IA iniciado')
        
        # Tentar inicializar banco de dados
        try:
            criar_tabelas()
            app.logger.info("Tabelas do banco verificadas/criadas com sucesso")
        except Exception as e:
            app.logger.error(f"Erro ao inicializar banco de dados: {e}")
            # Não falhar completamente se o banco não estiver disponível
        
        # Tentar inicializar sistema de agentes
        try:
            from app.services.enhanced_placa_service import get_enhanced_placa_service
            service = get_enhanced_placa_service()
            app.logger.info("Sistema de agentes especializados inicializado")
        except Exception as e:
            app.logger.warning(f"Sistema de agentes não disponível: {e}")
            # Sistema continua funcionando sem agentes
        
        return app
        
    except Exception as e:
        # Log crítico se a aplicação não puder ser criada
        logging.critical(f"FALHA CRÍTICA: Não foi possível criar aplicação: {e}")
        raise

def handle_exception(exc_type, exc_value, exc_traceback):
    """Handler global para exceções não tratadas"""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    
    logging.critical("Exceção não tratada", exc_info=(exc_type, exc_value, exc_traceback))

# Configurar handler global de exceções
sys.excepthook = handle_exception

# Criar aplicação
application = create_production_app()

# Para compatibilidade com alguns servidores WSGI
app = application

@application.before_first_request
def initialize_production_features():
    """Inicializa recursos específicos de produção na primeira requisição"""
    application.logger.info("Primeira requisição recebida - aplicação em produção")

@application.after_request
def after_request(response):
    """Headers de segurança e logging para produção"""
    # Headers de segurança
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    
    # Log de requisições (apenas erros em produção)
    if response.status_code >= 400:
        application.logger.warning(
            f'Erro {response.status_code}: {request.method} {request.url}'
        )
    
    return response

@application.errorhandler(500)
def internal_error(error):
    """Handler para erros internos"""
    application.logger.error(f'Erro interno: {error}')
    return "Erro interno do servidor", 500

@application.errorhandler(404)
def not_found(error):
    """Handler para páginas não encontradas"""
    return "Página não encontrada", 404

# Verificação de saúde para load balancers
@application.route('/health')
def health_check():
    """Endpoint de verificação de saúde para load balancers"""
    try:
        # Verificar se a aplicação está respondendo
        from app.models.database import get_db_connection
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
        
        return {
            "status": "healthy",
            "timestamp": __import__('time').time(),
            "version": "2.0"
        }, 200
        
    except Exception as e:
        application.logger.error(f"Health check falhou: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": __import__('time').time()
        }, 503

if __name__ == "__main__":
    # Para desenvolvimento/teste local
    print("⚠️  Este é o arquivo WSGI para produção.")
    print("   Para desenvolvimento, use: python run.py")
    print("   Para produção com Gunicorn: gunicorn --bind 0.0.0.0:5000 wsgi:application")
    
    # Executar em modo desenvolvimento se chamado diretamente
    application.run(
        host='127.0.0.1',
        port=5000,
        debug=False,
        use_reloader=False
    )