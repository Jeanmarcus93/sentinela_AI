# app/routes/agent_routes.py
"""
Rotas Flask para Sistema de Agentes Especializados
"""

from flask import Blueprint, request, jsonify
import asyncio
import time
import json
from functools import wraps

# Criar blueprint para rotas dos agentes
agent_bp = Blueprint('agents', __name__, url_prefix='/api/v2')

def async_route(f):
    """Decorator para permitir funções async em rotas Flask"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(f(*args, **kwargs))
        finally:
            loop.close()
    return wrapper

def get_enhanced_service():
    """Helper para obter serviço com tratamento de erro"""
    try:
        from app.services.enhanced_placa_service import get_enhanced_placa_service
        from app.services.agents import Priority
        return get_enhanced_placa_service(), Priority
    except ImportError:
        return None, None

@agent_bp.route('/')
def home():
    """Endpoint raiz com informações do sistema v2"""
    return jsonify({
        "message": "Sistema de Análise de Placas v2.0 - Agentes Especializados",
        "version": "2.0",
        "framework": "Flask",
        "features": [
            "Análise completa com múltiplos agentes",
            "Análise rápida otimizada", 
            "Processamento em lote",
            "Balanceamento de carga automático",
            "Monitoramento de performance"
        ],
        "endpoints": {
            "analysis": "/api/v2/analyze/<placa>",
            "fast_analysis": "/api/v2/analyze/<placa>/fast",
            "batch_analysis": "/api/v2/analyze/batch",
            "health": "/api/v2/health",
            "stats": "/api/v2/stats"
        }
    })

@agent_bp.route('/analyze/<placa>')
@async_route
async def analyze_placa(placa):
    """Análise completa de uma placa usando todos os agentes especializados"""
    
    service, Priority = get_enhanced_service()
    if not service:
        return jsonify({
            "error": "Sistema de agentes não disponível",
            "placa": placa,
            "success": False
        }), 503
    
    if not placa or len(placa.strip()) < 7:
        return jsonify({
            "error": "Placa inválida", 
            "placa": placa,
            "success": False
        }), 400
    
    # Obter prioridade da query string
    priority_str = request.args.get('priority', 'medium').lower()
    priority_map = {
        "low": Priority.LOW,
        "medium": Priority.MEDIUM, 
        "high": Priority.HIGH,
        "critical": Priority.CRITICAL
    }
    priority = priority_map.get(priority_str, Priority.MEDIUM)
    
    try:
        start_time = time.time()
        result = await service.analyze_placa_comprehensive(placa.upper().strip(), priority)
        
        # Adicionar metadados da requisição
        result["request_info"] = {
            "endpoint": "comprehensive",
            "priority_requested": priority_str,
            "processing_time": time.time() - start_time,
            "framework": "flask"
        }
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            "error": f"Erro na análise da placa {placa}: {str(e)}",
            "placa": placa,
            "success": False
        }), 500

@agent_bp.route('/analyze/<placa>/fast')
@async_route
async def analyze_placa_fast(placa):
    """Análise rápida otimizada de uma placa"""
    
    service, _ = get_enhanced_service()
    if not service:
        return jsonify({
            "error": "Sistema de agentes não disponível",
            "placa": placa,
            "success": False
        }), 503
    
    if not placa or len(placa.strip()) < 7:
        return jsonify({
            "error": "Placa inválida",
            "placa": placa, 
            "success": False
        }), 400
    
    try:
        start_time = time.time()
        result = await service.analyze_placa_fast(placa.upper().strip())
        
        result["request_info"] = {
            "endpoint": "fast",
            "processing_time": time.time() - start_time,
            "framework": "flask"
        }
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            "error": f"Erro na análise rápida da placa {placa}: {str(e)}",
            "placa": placa,
            "success": False
        }), 500

@agent_bp.route('/analyze/batch', methods=['POST'])
@async_route
async def analyze_batch():
    """Análise em lote de múltiplas placas"""
    
    service, Priority = get_enhanced_service()
    if not service:
        return jsonify({
            "error": "Sistema de agentes não disponível",
            "success": False
        }), 503
    
    try:
        data = request.get_json()
        if not data or 'placas' not in data:
            return jsonify({
                "error": "JSON deve conter array 'placas'",
                "success": False
            }), 400
        
        placas = data['placas']
        if not placas or len(placas) == 0:
            return jsonify({
                "error": "Lista de placas não pode estar vazia",
                "success": False
            }), 400
        
        if len(placas) > 50:
            return jsonify({
                "error": "Máximo de 50 placas por lote",
                "success": False
            }), 400
        
        # Validar placas
        placas_validas = []
        for placa in placas:
            placa_clean = placa.strip().upper()
            if len(placa_clean) >= 7:
                placas_validas.append(placa_clean)
        
        if not placas_validas:
            return jsonify({
                "error": "Nenhuma placa válida encontrada",
                "success": False
            }), 400
        
        # Obter prioridade
        priority_str = data.get('priority', 'medium').lower()
        priority_map = {
            "low": Priority.LOW,
            "medium": Priority.MEDIUM,
            "high": Priority.HIGH,
            "critical": Priority.CRITICAL
        }
        priority = priority_map.get(priority_str, Priority.MEDIUM)
        
        start_time = time.time()
        result = await service.analyze_batch(placas_validas, priority)
        
        result["request_info"] = {
            "endpoint": "batch",
            "placas_requested": len(placas),
            "placas_valid": len(placas_validas),
            "priority": priority_str,
            "processing_time": time.time() - start_time,
            "framework": "flask"
        }
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            "error": f"Erro na análise em lote: {str(e)}",
            "success": False
        }), 500

@agent_bp.route('/health')
@async_route
async def health_check():
    """Verificação de saúde do sistema de agentes"""
    
    service, _ = get_enhanced_service()
    if not service:
        return jsonify({
            "system_healthy": False,
            "error": "Sistema de agentes não disponível",
            "timestamp": time.time()
        }), 503
    
    try:
        health_result = await service.health_check()
        
        status_code = 200 if health_result["system_healthy"] else 503
        
        return jsonify(health_result), status_code
        
    except Exception as e:
        return jsonify({
            "system_healthy": False,
            "error": str(e),
            "timestamp": time.time()
        }), 503

@agent_bp.route('/stats')
def get_system_stats():
    """Estatísticas detalhadas do sistema de agentes"""
    
    service, _ = get_enhanced_service()
    if not service:
        return jsonify({
            "error": "Sistema de agentes não disponível",
            "success": False
        }), 503
    
    try:
        stats = service.get_orchestrator_stats()
        
        # Adicionar informações de balanceamento de carga
        load_balancing = service.orchestrator.get_agent_load_balancing_info()
        
        return jsonify({
            "orchestrator_stats": stats,
            "load_balancing": load_balancing,
            "system_info": {
                "agents_available": list(load_balancing.keys()),
                "system_load": sum(info["current_load"] for info in load_balancing.values()) / len(load_balancing) if load_balancing else 0,
                "agents_ready": sum(1 for info in load_balancing.values() if info["can_process"]),
                "timestamp": time.time(),
                "framework": "flask"
            }
        })
        
    except Exception as e:
        return jsonify({
            "error": f"Erro ao obter estatísticas: {str(e)}",
            "success": False
        }), 500

@agent_bp.route('/agents/status')
def get_agents_status():
    """Status individual de cada agente"""
    
    service, _ = get_enhanced_service()
    if not service:
        return jsonify({
            "error": "Sistema de agentes não disponível",
            "success": False
        }), 503
    
    try:
        agents_status = {}
        
        for agent_type, agent in service.orchestrator.agents.items():
            agents_status[agent_type.value] = {
                "active_tasks": agent.active_tasks,
                "max_concurrent_tasks": agent.max_concurrent_tasks,
                "current_load": agent.get_load(),
                "can_process": agent.can_process(),
                "stats": agent.get_stats()
            }
        
        return jsonify({
            "agents": agents_status,
            "total_agents": len(agents_status),
            "timestamp": time.time(),
            "framework": "flask"
        })
        
    except Exception as e:
        return jsonify({
            "error": f"Erro ao obter status dos agentes: {str(e)}",
            "success": False
        }), 500

# Rota para compatibilidade com versão anterior (DEPRECATED)
@agent_bp.route('/consultar/<placa>')
@async_route
async def consultar_placa_legacy(placa):
    """[DEPRECATED] Endpoint para compatibilidade com versão anterior"""
    
    # Adicionar header de depreciação
    result = await analyze_placa_fast(placa)
    
    if isinstance(result, tuple):
        data, status_code = result
        if isinstance(data, str):
            data = json.loads(data)
        data["warning"] = "Este endpoint está depreciado. Use /api/v2/analyze/{placa}/fast"
        return jsonify(data), status_code
    else:
        if isinstance(result, str):
            result = json.loads(result)
        result["warning"] = "Este endpoint está depreciado. Use /api/v2/analyze/{placa}/fast"
        return jsonify(result)

# Error handlers específicos para este blueprint
@agent_bp.errorhandler(404)
def not_found(error):
    return jsonify({
        "error": "Endpoint não encontrado",
        "available_endpoints": [
            "/api/v2/analyze/<placa>",
            "/api/v2/analyze/<placa>/fast",
            "/api/v2/analyze/batch",
            "/api/v2/health",
            "/api/v2/stats",
            "/api/v2/agents/status"
        ]
    }), 404

@agent_bp.errorhandler(500)
def internal_error(error):
    return jsonify({
        "error": "Erro interno do servidor",
        "detail": "Um erro inesperado ocorreu no sistema de agentes"
    }), 500