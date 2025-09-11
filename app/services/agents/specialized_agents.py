# app/services/agents/specialized_agents.py
"""
Implementação dos agentes especializados para análise de placas
"""

import asyncio
import time
import numpy as np
from typing import Dict, List, Any, Optional

from app.services.agents.base_agent import BaseAgent, AgentType, AnalysisTask, AgentResult
from app.models.database import get_db_connection
from psycopg.rows import dict_row

class DataCollectorAgent(BaseAgent):
    """Agente responsável por coletar todos os dados relacionados a uma placa"""
    
    def __init__(self):
        super().__init__(AgentType.DATA_COLLECTOR, max_concurrent_tasks=5)
        
    async def process(self, task: AnalysisTask) -> AgentResult:
        start_time = time.time()
        self.active_tasks += 1
        
        try:
            placa = task.data["placa"]
            
            # Coletar dados básicos
            passagens = await self._fetch_passagens(placa)
            ocorrencias = await self._fetch_ocorrencias(placa)
            veiculo_info = await self._fetch_veiculo_info(placa)
            
            collected_data = {
                "placa": placa,
                "veiculo_info": veiculo_info,
                "passagens": passagens,
                "ocorrencias": ocorrencias,
                "data_quality": self._assess_data_quality(passagens, ocorrencias, veiculo_info),
                "collection_timestamp": time.time()
            }
            
            self.total_processed += 1
            execution_time = time.time() - start_time
            
            return AgentResult(
                agent_type=self.agent_type,
                task_id=task.task_id,
                success=True,
                data=collected_data,
                execution_time=execution_time,
                metadata={"records_collected": len(passagens) + len(ocorrencias)}
            )
            
        except Exception as e:
            self.total_errors += 1
            return AgentResult(
                agent_type=self.agent_type,
                task_id=task.task_id,
                success=False,
                data={},
                execution_time=time.time() - start_time,
                error=str(e)
            )
        finally:
            self.active_tasks -= 1
    
    async def _fetch_passagens(self, placa: str) -> List[Dict]:
        """Busca passagens da placa"""
        sql = """
        SELECT p.id, v.placa, p.datahora, p.municipio, p.rodovia,
               p.ilicito_ida, p.ilicito_volta
        FROM passagens p
        JOIN veiculos v ON v.id = p.veiculo_id
        WHERE v.placa = %s
        ORDER BY p.datahora;
        """
        try:
            with get_db_connection() as conn:
                with conn.cursor(row_factory=dict_row) as cur:
                    cur.execute(sql, (placa,))
                    return cur.fetchall()
        except Exception:
            return []
    
    async def _fetch_ocorrencias(self, placa: str, limit: int = 10) -> List[Dict]:
        """Busca ocorrências da placa"""
        sql = """
        SELECT o.id, o.tipo, o.relato, o.datahora
        FROM ocorrencias o
        JOIN veiculos v ON v.id = o.veiculo_id
        WHERE v.placa = %s AND o.relato IS NOT NULL AND o.relato <> ''
        ORDER BY o.datahora DESC
        LIMIT %s;
        """
        try:
            with get_db_connection() as conn:
                with conn.cursor(row_factory=dict_row) as cur:
                    cur.execute(sql, (placa, limit))
                    return cur.fetchall()
        except Exception:
            return []
    
    async def _fetch_veiculo_info(self, placa: str) -> Dict:
        """Busca informações básicas do veículo"""
        sql = "SELECT * FROM veiculos WHERE placa = %s LIMIT 1"
        try:
            with get_db_connection() as conn:
                with conn.cursor(row_factory=dict_row) as cur:
                    cur.execute(sql, (placa,))
                    result = cur.fetchone()
                    return dict(result) if result else {}
        except Exception:
            return {}
    
    def _assess_data_quality(self, passagens: List, ocorrencias: List, veiculo_info: Dict) -> Dict:
        """Avalia a qualidade dos dados coletados"""
        return {
            "has_vehicle_info": bool(veiculo_info),
            "passagens_count": len(passagens),
            "ocorrencias_count": len(ocorrencias),
            "data_completeness": min(1.0, (len(passagens) + len(ocorrencias)) / 10),
            "quality_score": 0.8 if veiculo_info and (passagens or ocorrencias) else 0.3
        }

class RouteAnalyzerAgent(BaseAgent):
    """Agente especializado em análise de padrões de rotas"""
    
    def __init__(self):
        super().__init__(AgentType.ROUTE_ANALYZER, max_concurrent_tasks=3)
    
    async def process(self, task: AnalysisTask) -> AgentResult:
        start_time = time.time()
        self.active_tasks += 1
        
        try:
            # Obter dados das dependências
            dependency_data = task.data.get("dependency_results", {})
            collected_data = None
            
            for dep_result in dependency_data.values():
                if "passagens" in dep_result:
                    collected_data = dep_result
                    break
            
            if not collected_data:
                raise ValueError("Dados de passagens não encontrados nas dependências")
            
            passagens = collected_data["passagens"]
            
            if not passagens:
                result_data = {
                    "risk_score": 0.0,
                    "classification": "NORMAL",
                    "confidence": 1.0,
                    "patterns": {},
                    "reason": "Nenhuma passagem encontrada"
                }
            else:
                result_data = await self._analyze_route_patterns(passagens)
            
            self.total_processed += 1
            execution_time = time.time() - start_time
            
            return AgentResult(
                agent_type=self.agent_type,
                task_id=task.task_id,
                success=True,
                data=result_data,
                execution_time=execution_time,
                metadata={"passagens_analyzed": len(passagens)}
            )
            
        except Exception as e:
            self.total_errors += 1
            return AgentResult(
                agent_type=self.agent_type,
                task_id=task.task_id,
                success=False,
                data={},
                execution_time=time.time() - start_time,
                error=str(e)
            )
        finally:
            self.active_tasks -= 1
    
    async def _analyze_route_patterns(self, passagens: List[Dict]) -> Dict:
        """Análise rápida de padrões de rotas baseada em heurísticas"""
        if not passagens:
            return {"risk_score": 0.0, "patterns": {}}
        
        risk_factors = []
        patterns = {}
        
        # Análise de padrões noturnos
        night_passages = sum(1 for p in passagens if self._is_night_passage(p))
        night_ratio = night_passages / len(passagens)
        if night_ratio > 0.6:
            risk_factors.append(("high_night_activity", night_ratio))
        patterns["night_activity"] = night_ratio
        
        # Repetição de rotas
        routes = [(p.get("municipio", ""), p.get("rodovia", "")) for p in passagens]
        route_counts = {}
        for route in routes:
            route_counts[route] = route_counts.get(route, 0) + 1
        
        max_repetition = max(route_counts.values()) if route_counts else 0
        repetition_ratio = max_repetition / len(passagens)
        if repetition_ratio > 0.4:
            risk_factors.append(("route_repetition", repetition_ratio))
        patterns["route_repetition"] = repetition_ratio
        
        # Calcular score final
        risk_score = min(1.0, sum(factor[1] for factor in risk_factors) / 2)
        
        return {
            "risk_score": risk_score,
            "patterns": patterns,
            "risk_factors": risk_factors,
            "classification": "SUSPEITO" if risk_score > 0.6 else "NORMAL",
            "confidence": 0.8
        }
    
    def _is_night_passage(self, passagem: Dict) -> bool:
        """Verifica se a passagem ocorreu durante a noite"""
        try:
            hour = passagem["datahora"].hour
            return hour >= 22 or hour <= 6
        except:
            return False

class SemanticAnalyzerAgent(BaseAgent):
    """Agente especializado em análise semântica de relatos"""
    
    def __init__(self):
        super().__init__(AgentType.SEMANTIC_ANALYZER, max_concurrent_tasks=4)
    
    async def process(self, task: AnalysisTask) -> AgentResult:
        start_time = time.time()
        self.active_tasks += 1
        
        try:
            dependency_data = task.data.get("dependency_results", {})
            collected_data = None
            
            for dep_result in dependency_data.values():
                if "ocorrencias" in dep_result:
                    collected_data = dep_result
                    break
            
            if not collected_data:
                raise ValueError("Dados de ocorrências não encontrados nas dependências")
            
            ocorrencias = collected_data["ocorrencias"]
            
            if not ocorrencias:
                result_data = {
                    "overall_risk": 0.0,
                    "analyzed_reports": [],
                    "summary": "Nenhum relato encontrado para análise"
                }
            else:
                result_data = await self._analyze_reports(ocorrencias)
            
            self.total_processed += 1
            execution_time = time.time() - start_time
            
            return AgentResult(
                agent_type=self.agent_type,
                task_id=task.task_id,
                success=True,
                data=result_data,
                execution_time=execution_time,
                metadata={"reports_analyzed": len(ocorrencias)}
            )
            
        except Exception as e:
            self.total_errors += 1
            return AgentResult(
                agent_type=self.agent_type,
                task_id=task.task_id,
                success=False,
                data={},
                execution_time=time.time() - start_time,
                error=str(e)
            )
        finally:
            self.active_tasks -= 1
    
    async def _analyze_reports(self, ocorrencias: List[Dict]) -> Dict:
        """Análise simples de relatos"""
        analyzed_reports = []
        risk_scores = []
        
        for ocorrencia in ocorrencias:
            relato = (ocorrencia.get("relato") or "").strip()
            if not relato:
                continue
            
            # Análise simples por palavras-chave
            risk_score = self._simple_text_analysis(relato)
            risk_scores.append(risk_score)
            
            analyzed_reports.append({
                "ocorrencia_id": ocorrencia["id"],
                "tipo": ocorrencia["tipo"],
                "datahora": str(ocorrencia["datahora"]),
                "relato": relato,
                "risk_score": risk_score
            })
        
        overall_risk = float(np.mean(risk_scores)) if risk_scores else 0.0
        
        return {
            "overall_risk": overall_risk,
            "analyzed_reports": analyzed_reports,
            "summary": f"Analisados {len(analyzed_reports)} relatos. Risco médio: {overall_risk:.2f}"
        }
    
    def _simple_text_analysis(self, texto: str) -> float:
        """Análise simples de texto baseada em palavras-chave"""
        palavras_suspeitas = [
            "droga", "maconha", "cocaina", "crack", "tráfico", "arma", "pistola",
            "suspeito", "nervoso", "mentiu", "contradicao", "fronteira"
        ]
        
        texto_lower = texto.lower()
        matches = sum(1 for palavra in palavras_suspeitas if palavra in texto_lower)
        
        return min(1.0, matches / 5.0)  # Normalizar para 0-1

class RiskCalculatorAgent(BaseAgent):
    """Agente especializado em calcular risco final consolidado"""
    
    def __init__(self):
        super().__init__(AgentType.RISK_CALCULATOR, max_concurrent_tasks=5)
    
    async def process(self, task: AnalysisTask) -> AgentResult:
        start_time = time.time()
        self.active_tasks += 1
        
        try:
            dependency_data = task.data.get("dependency_results", {})
            
            route_analysis = None
            semantic_analysis = None
            
            for dep_result in dependency_data.values():
                if "classification" in dep_result and "patterns" in dep_result:
                    route_analysis = dep_result
                elif "analyzed_reports" in dep_result:
                    semantic_analysis = dep_result
            
            final_risk = await self._calculate_consolidated_risk(route_analysis, semantic_analysis)
            
            self.total_processed += 1
            execution_time = time.time() - start_time
            
            return AgentResult(
                agent_type=self.agent_type,
                task_id=task.task_id,
                success=True,
                data=final_risk,
                execution_time=execution_time
            )
            
        except Exception as e:
            self.total_errors += 1
            return AgentResult(
                agent_type=self.agent_type,
                task_id=task.task_id,
                success=False,
                data={},
                execution_time=time.time() - start_time,
                error=str(e)
            )
        finally:
            self.active_tasks -= 1
    
    async def _calculate_consolidated_risk(self, route_analysis: Dict, semantic_analysis: Dict) -> Dict:
        """Calcula risco final considerando múltiplas análises"""
        
        route_risk = route_analysis.get("risk_score", 0.0) if route_analysis else 0.0
        semantic_risk = semantic_analysis.get("overall_risk", 0.0) if semantic_analysis else 0.0
        
        # Pesos adaptativos
        route_weight = 0.6 if route_analysis else 0.3
        semantic_weight = 0.4 if semantic_analysis else 0.2
        
        # Normalizar pesos
        total_weight = route_weight + semantic_weight
        if total_weight > 0:
            route_weight /= total_weight
            semantic_weight /= total_weight
        else:
            route_weight = semantic_weight = 0.5
        
        final_score = (route_risk * route_weight) + (semantic_risk * semantic_weight)
        
        if final_score > 0.8:
            risk_level = "CRÍTICO"
        elif final_score > 0.6:
            risk_level = "ALTO"
        elif final_score > 0.4:
            risk_level = "MÉDIO"
        else:
            risk_level = "BAIXO"
        
        return {
            "final_risk_score": final_score,
            "risk_level": risk_level,
            "component_scores": {
                "route_risk": route_risk,
                "semantic_risk": semantic_risk
            },
            "weights_used": {
                "route_weight": route_weight,
                "semantic_weight": semantic_weight
            },
            "confidence": 0.8,
            "calculation_timestamp": time.time()
        }