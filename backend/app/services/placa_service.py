# app/services/placa_service.py
"""
Serviço de Análise de Placas - Nova Arquitetura
Integra sistema de agentes especializados com compatibilidade para sistema legado
"""

import asyncio
import time
import json
from typing import Dict, Any, List, Optional
from dataclasses import asdict

# Imports do banco e serviços
from app.models.database import get_db_connection
from app.services.semantic_service import analyze_text
from psycopg.rows import dict_row

# Sistema de agentes (com fallback se não disponível)
AGENTS_AVAILABLE = False
try:
    from app.services.enhanced_placa_service import get_enhanced_placa_service
    from app.services.agents import Priority
    AGENTS_AVAILABLE = True
    print("✅ Sistema de agentes especialistas carregado")
except ImportError as e:
    print(f"⚠️ Sistema de agentes não disponível: {e}")
    print("   Usando sistema de análise clássico")

class PlacaAnalysisService:
    """Serviço principal de análise de placas com sistema híbrido"""
    
    def __init__(self):
        self.enhanced_service = None
        if AGENTS_AVAILABLE:
            try:
                self.enhanced_service = get_enhanced_placa_service()
                print("🤖 Agentes especializados inicializados")
            except Exception as e:
                print(f"❌ Erro ao inicializar agentes: {e}")
                self.enhanced_service = None
    
    def analyze_placa(self, placa: str, use_agents: bool = True) -> Dict[str, Any]:
        """
        Análise principal de uma placa com sistema híbrido
        
        Args:
            placa: Placa do veículo
            use_agents: Se deve usar sistema de agentes (fallback automático se indisponível)
        
        Returns:
            Resultado da análise no formato padrão
        """
        try:
            # Tentar usar sistema de agentes primeiro
            if use_agents and self.enhanced_service:
                return self._analyze_with_agents(placa)
            else:
                return self._analyze_classic(placa)
                
        except Exception as e:
            print(f"Erro na análise primária: {e}")
            # Fallback para análise clássica
            return self._analyze_classic(placa)
    
    def _analyze_with_agents(self, placa: str) -> Dict[str, Any]:
        """Análise usando sistema de agentes especializados"""
        try:
            # Executar análise completa com agentes
            result = self.enhanced_service.analisar_placa_sync(placa)
            
            # Adicionar metadados
            result["analysis_method"] = "agents"
            result["agents_used"] = True
            
            return result
            
        except Exception as e:
            print(f"Erro no sistema de agentes: {e}")
            raise
    
    def _analyze_classic(self, placa: str) -> Dict[str, Any]:
        """Análise clássica sem agentes (fallback)"""
        start_time = time.time()
        
        try:
            # Coleta de dados
            data = self._collect_basic_data(placa)
            
            # Análises
            route_analysis = self._analyze_routes_classic(data["passagens"])
            semantic_analysis = self._analyze_reports_classic(data["ocorrencias"])
            risk_analysis = self._calculate_risk_classic(route_analysis, semantic_analysis)
            
            # Formato de retorno compatível
            return {
                "placa": placa,
                "success": True,
                "analysis_method": "classic",
                "agents_used": False,
                "execution_time": time.time() - start_time,
                
                # Dados coletados
                "data_quality": {
                    "passagens_count": len(data["passagens"]),
                    "ocorrencias_count": len(data["ocorrencias"]),
                    "quality_score": 0.8 if data["passagens"] or data["ocorrencias"] else 0.3
                },
                
                # Análises (formato compatível)
                "rotas": route_analysis,
                "relatos": semantic_analysis,
                "risco": risk_analysis,
                
                # Metadados
                "timestamp": time.time()
            }
            
        except Exception as e:
            return {
                "placa": placa,
                "success": False,
                "error": str(e),
                "analysis_method": "classic",
                "agents_used": False,
                "execution_time": time.time() - start_time
            }
    
    def _collect_basic_data(self, placa: str) -> Dict[str, Any]:
        """Coleta dados básicos do banco"""
        try:
            with get_db_connection() as conn:
                with conn.cursor(row_factory=dict_row) as cur:
                    # Buscar passagens
                    cur.execute("""
                        SELECT p.id, v.placa, p.datahora, p.municipio, p.rodovia,
                               p.ilicito_ida, p.ilicito_volta
                        FROM passagens p
                        JOIN veiculos v ON v.id = p.veiculo_id
                        WHERE v.placa = %s
                        ORDER BY p.datahora
                        LIMIT 1000;
                    """, (placa,))
                    passagens = cur.fetchall()
                    
                    # Buscar ocorrências com relatos
                    cur.execute("""
                        SELECT o.id, o.tipo, o.relato, o.datahora
                        FROM ocorrencias o
                        JOIN veiculos v ON v.id = o.veiculo_id
                        WHERE v.placa = %s AND o.relato IS NOT NULL AND o.relato <> ''
                        ORDER BY o.datahora DESC
                        LIMIT 20;
                    """, (placa,))
                    ocorrencias = cur.fetchall()
                    
                    # Dados do veículo
                    cur.execute("SELECT * FROM veiculos WHERE placa = %s LIMIT 1", (placa,))
                    veiculo = cur.fetchone()
            
            return {
                "passagens": passagens,
                "ocorrencias": ocorrencias, 
                "veiculo": dict(veiculo) if veiculo else {}
            }
            
        except Exception as e:
            print(f"Erro na coleta de dados: {e}")
            return {"passagens": [], "ocorrencias": [], "veiculo": {}}
    
    def _analyze_routes_classic(self, passagens: List[Dict]) -> Dict[str, Any]:
        """Análise clássica de rotas"""
        if not passagens:
            return {
                "labels": ["NORMAL"],
                "probs": [1.0],
                "classe": "NORMAL"
            }
        
        # Análise simples por heurísticas
        risk_factors = 0
        
        # Passagens noturnas
        night_count = sum(1 for p in passagens if self._is_night_time(p.get("datahora")))
        night_ratio = night_count / len(passagens)
        if night_ratio > 0.6:
            risk_factors += 1
        
        # Repetição de rotas
        routes = [(p.get("municipio", ""), p.get("rodovia", "")) for p in passagens]
        route_counts = {}
        for route in routes:
            route_counts[route] = route_counts.get(route, 0) + 1
        
        max_repetition = max(route_counts.values()) if route_counts else 0
        if max_repetition > len(passagens) * 0.4:
            risk_factors += 1
        
        # Passagens marcadas como ilícitas
        ilicit_count = sum(1 for p in passagens if p.get("ilicito_ida") or p.get("ilicito_volta"))
        if ilicit_count > 0:
            risk_factors += 2
        
        # Classificação
        if risk_factors >= 2:
            return {
                "labels": ["NORMAL", "ILICITO"],
                "probs": [0.3, 0.7],
                "classe": "ILICITO"
            }
        else:
            return {
                "labels": ["NORMAL", "ILICITO"],
                "probs": [0.8, 0.2], 
                "classe": "NORMAL"
            }
    
    def _analyze_reports_classic(self, ocorrencias: List[Dict]) -> List[Dict[str, Any]]:
        """Análise clássica de relatos"""
        if not ocorrencias:
            return []
        
        analyzed_reports = []
        
        for ocorrencia in ocorrencias:
            relato = str(ocorrencia.get("relato", "")).strip()
            if not relato:
                continue
            
            # Usar análise semântica existente
            try:
                analysis = analyze_text(relato)
                
                # Converter para formato esperado
                classe = analysis.get("classe", "OUTROS")
                pontuacao = analysis.get("pontuacao", 50)
                
                # Simular distribuição de probabilidades
                if classe == "TRAFICO":
                    probs = [0.1, 0.1, 0.7, 0.1]
                    labels = ["OUTROS", "PORTE_ARMA", "TRAFICO", "RECEPTACAO"]
                elif classe == "PORTE_ARMA":
                    probs = [0.1, 0.7, 0.1, 0.1]
                    labels = ["OUTROS", "PORTE_ARMA", "TRAFICO", "RECEPTACAO"]
                elif classe == "RECEPTACAO":
                    probs = [0.1, 0.1, 0.1, 0.7]
                    labels = ["OUTROS", "PORTE_ARMA", "TRAFICO", "RECEPTACAO"]
                else:
                    probs = [0.7, 0.1, 0.1, 0.1]
                    labels = ["OUTROS", "PORTE_ARMA", "TRAFICO", "RECEPTACAO"]
                
                analyzed_reports.append({
                    "id": ocorrencia["id"],
                    "tipo": ocorrencia["tipo"],
                    "datahora": str(ocorrencia["datahora"]),
                    "texto": relato,
                    "labels": labels,
                    "probs": probs,
                    "classe": classe,
                    "pontuacao": pontuacao
                })
                
            except Exception as e:
                print(f"Erro na análise do relato {ocorrencia['id']}: {e}")
                continue
        
        return analyzed_reports
    
    def _calculate_risk_classic(self, route_analysis: Dict, semantic_analysis: List[Dict]) -> Dict[str, Any]:
        """Cálculo clássico de risco final"""
        # Risco de rotas
        route_risk = 0.7 if route_analysis.get("classe") == "ILICITO" else 0.2
        
        # Risco de relatos
        semantic_risk = 0.0
        if semantic_analysis:
            suspicious_reports = sum(1 for r in semantic_analysis if r.get("classe") in ["TRAFICO", "PORTE_ARMA", "RECEPTACAO"])
            semantic_risk = min(1.0, suspicious_reports / len(semantic_analysis))
        
        # Risco final (média ponderada)
        final_risk = (route_risk * 0.6) + (semantic_risk * 0.4)
        
        return {
            "rotas": route_risk,
            "relatos": semantic_risk,
            "final": final_risk,
            "nivel": self._get_risk_level(final_risk)
        }
    
    def _get_risk_level(self, risk_score: float) -> str:
        """Converte score numérico para nível textual"""
        if risk_score > 0.8:
            return "CRÍTICO"
        elif risk_score > 0.6:
            return "ALTO"
        elif risk_score > 0.4:
            return "MÉDIO"
        else:
            return "BAIXO"
    
    def _is_night_time(self, datetime_obj) -> bool:
        """Verifica se é horário noturno"""
        try:
            if hasattr(datetime_obj, 'hour'):
                hour = datetime_obj.hour
                return hour >= 22 or hour <= 6
        except:
            pass
        return False
    
    def get_analysis_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do serviço de análise"""
        stats = {
            "service_type": "hybrid",
            "agents_available": AGENTS_AVAILABLE,
            "enhanced_service_ready": self.enhanced_service is not None
        }
        
        if self.enhanced_service:
            try:
                agent_stats = self.enhanced_service.get_performance_metrics()
                stats["agent_performance"] = agent_stats
            except:
                pass
        
        return stats

# Instância global
_service_instance = None

def get_placa_service() -> PlacaAnalysisService:
    """Retorna instância singleton do serviço"""
    global _service_instance
    if _service_instance is None:
        _service_instance = PlacaAnalysisService()
    return _service_instance

# Função de compatibilidade para API existente
def analisar_placa_json(placa: str) -> Dict[str, Any]:
    """
    Função principal de análise - compatível com API existente
    Utiliza sistema de agentes quando disponível, com fallback automático
    """
    service = get_placa_service()
    return service.analyze_placa(placa)

# Funções específicas para diferentes tipos de análise
def quick_analysis(placa: str) -> Dict[str, Any]:
    """Análise rápida focada em risco básico"""
    service = get_placa_service()
    
    if service.enhanced_service:
        # Usar análise rápida com agentes
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                from app.services.enhanced_placa_service import quick_risk_analysis
                result = loop.run_until_complete(quick_risk_analysis(placa))
                return result
            finally:
                loop.close()
        except Exception as e:
            print(f"Erro na análise rápida com agentes: {e}")
    
    # Fallback para análise clássica rápida
    return service._analyze_classic(placa)

def route_analysis_only(placa: str) -> Dict[str, Any]:
    """Análise focada apenas em rotas"""
    service = get_placa_service()
    
    if service.enhanced_service:
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                from app.services.enhanced_placa_service import route_analysis_only
                result = loop.run_until_complete(route_analysis_only(placa))
                return result
            finally:
                loop.close()
        except Exception as e:
            print(f"Erro na análise de rotas com agentes: {e}")
    
    # Análise clássica apenas de rotas
    data = service._collect_basic_data(placa)
    route_result = service._analyze_routes_classic(data["passagens"])
    
    return {
        "placa": placa,
        "success": True,
        "rotas": route_result,
        "relatos": [],
        "risco": {"rotas": 0.5 if route_result.get("classe") == "ILICITO" else 0.2, "relatos": 0.0, "final": 0.25}
    }

def semantic_analysis_only(placa: str) -> Dict[str, Any]:
    """Análise focada apenas em relatos"""
    service = get_placa_service()
    
    if service.enhanced_service:
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                from app.services.enhanced_placa_service import semantic_analysis_only
                result = loop.run_until_complete(semantic_analysis_only(placa))
                return result
            finally:
                loop.close()
        except Exception as e:
            print(f"Erro na análise semântica com agentes: {e}")
    
    # Análise clássica apenas de relatos
    data = service._collect_basic_data(placa)
    semantic_result = service._analyze_reports_classic(data["ocorrencias"])
    
    semantic_risk = 0.0
    if semantic_result:
        suspicious_count = sum(1 for r in semantic_result if r.get("classe") in ["TRAFICO", "PORTE_ARMA", "RECEPTACAO"])
        semantic_risk = min(1.0, suspicious_count / len(semantic_result))
    
    return {
        "placa": placa,
        "success": True,
        "rotas": {"labels": ["NORMAL"], "probs": [1.0], "classe": "NORMAL"},
        "relatos": semantic_result,
        "risco": {"rotas": 0.0, "relatos": semantic_risk, "final": semantic_risk * 0.4}
    }

# Funções de utilidade
def health_check() -> Dict[str, Any]:
    """Verifica saúde do sistema de análise"""
    service = get_placa_service()
    
    health_info = {
        "service_healthy": True,
        "agents_available": AGENTS_AVAILABLE,
        "enhanced_service_ready": service.enhanced_service is not None,
        "timestamp": time.time()
    }
    
    # Teste rápido
    try:
        test_result = service.analyze_placa("TEST123")
        health_info["test_analysis"] = test_result.get("success", False)
    except Exception as e:
        health_info["service_healthy"] = False
        health_info["error"] = str(e)
    
    return health_info

def get_service_info() -> Dict[str, Any]:
    """Informações sobre o serviço"""
    service = get_placa_service()
    
    info = {
        "version": "2.0",
        "service_type": "hybrid",
        "features": [
            "Análise clássica (sempre disponível)",
            "Sistema de agentes especializados (quando disponível)",
            "Fallback automático",
            "Análises específicas (rotas, semântica, risco)"
        ],
        "agents_system": {
            "available": AGENTS_AVAILABLE,
            "ready": service.enhanced_service is not None
        }
    }
    
    if service.enhanced_service:
        try:
            stats = service.get_analysis_stats()
            info["performance"] = stats
        except:
            pass
    
    return info

# Migração e compatibilidade
def migrate_from_old_service():
    """Utilitário para migração do sistema antigo"""
    print("🔄 Migrando para novo sistema de análise...")
    
    # Testar novo sistema
    service = get_placa_service()
    
    test_placas = ["ABC1234", "XYZ5678", "TEST123"]
    migration_results = []
    
    for placa in test_placas:
        try:
            # Teste com agentes
            result_agents = service.analyze_placa(placa, use_agents=True)
            
            # Teste sem agentes
            result_classic = service.analyze_placa(placa, use_agents=False)
            
            migration_results.append({
                "placa": placa,
                "agents_success": result_agents.get("success", False),
                "classic_success": result_classic.get("success", False),
                "agents_time": result_agents.get("execution_time", 0),
                "classic_time": result_classic.get("execution_time", 0)
            })
            
        except Exception as e:
            migration_results.append({
                "placa": placa,
                "error": str(e),
                "success": False
            })
    
    print("✅ Migração concluída")
    for result in migration_results:
        if "error" in result:
            print(f"   {result['placa']}: ❌ {result['error']}")
        else:
            agents_status = "✅" if result["agents_success"] else "❌"
            classic_status = "✅" if result["classic_success"] else "❌"
            print(f"   {result['placa']}: Agentes {agents_status} ({result.get('agents_time', 0):.2f}s) | Clássico {classic_status} ({result.get('classic_time', 0):.2f}s)")
    
    return migration_results

if __name__ == "__main__":
    # Teste do sistema
    print("🧪 Testando sistema de análise de placas...")
    
    # Info do sistema
    info = get_service_info()
    print(f"📊 Sistema: {info['service_type']} v{info['version']}")
    print(f"🤖 Agentes disponíveis: {info['agents_system']['available']}")
    
    # Health check
    health = health_check()
    print(f"🏥 Saúde do sistema: {'✅' if health['service_healthy'] else '❌'}")
    
    # Teste de análise
    print("\n🔍 Teste de análise:")
    result = analisar_placa_json("TEST123")
    print(f"   Placa TEST123: {'✅' if result['success'] else '❌'}")
    print(f"   Método: {result.get('analysis_method', 'unknown')}")
    print(f"   Tempo: {result.get('execution_time', 0):.2f}s")
    
    print("\n🎉 Sistema pronto para uso!")
