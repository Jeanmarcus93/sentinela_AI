# app/services/agents/specialized_agents.py
"""
Implementação dos agentes especializados para análise de placas
"""

import asyncio
import time
import numpy as np
from typing import Dict, List, Any, Optional

from .base_agent import BaseAgent, AgentType, AnalysisTask, AgentResult
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
                    results = cur.fetchall()
                    # Converter para dict padrão para serialização
                    return [dict(row) for row in results]
        except Exception as e:
            print(f"Erro ao buscar passagens para {placa}: {e}")
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
                    results = cur.fetchall()
                    # Converter para dict padrão para serialização
                    return [dict(row) for row in results]
        except Exception as e:
            print(f"Erro ao buscar ocorrências para {placa}: {e}")
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
        except Exception as e:
            print(f"Erro ao buscar veículo {placa}: {e}")
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
        
        # Análise de passagens marcadas como ilícitas
        ilicito_ida = sum(1 for p in passagens if p.get("ilicito_ida"))
        ilicito_volta = sum(1 for p in passagens if p.get("ilicito_volta"))
        ilicito_ratio = (ilicito_ida + ilicito_volta) / (len(passagens) * 2)
        if ilicito_ratio > 0.3:
            risk_factors.append(("marked_illicit", ilicito_ratio))
        patterns["illicit_ratio"] = ilicito_ratio
        
        # Análise de frequência (muitas passagens em pouco tempo)
        if len(passagens) > 1:
            # Ordenar por data
            sorted_passagens = sorted(passagens, key=lambda x: x.get("datahora", ""))
            if len(sorted_passagens) >= 2:
                try:
                    # Calcular span temporal
                    from datetime import datetime
                    first_date = datetime.fromisoformat(str(sorted_passagens[0]["datahora"]).replace('Z', '+00:00'))
                    last_date = datetime.fromisoformat(str(sorted_passagens[-1]["datahora"]).replace('Z', '+00:00'))
                    days_span = max((last_date - first_date).days, 1)
                    
                    passages_per_day = len(passagens) / days_span
                    if passages_per_day > 5:  # Mais de 5 passagens por dia em média
                        risk_factors.append(("high_frequency", passages_per_day))
                    patterns["passages_per_day"] = passages_per_day
                except:
                    patterns["passages_per_day"] = 0
        
        # Calcular score final
        risk_score = min(1.0, sum(factor[1] for factor in risk_factors) / 2)
        
        # Aumentar peso se há passagens marcadas como ilícitas
        if ilicito_ratio > 0:
            risk_score = min(1.0, risk_score + (ilicito_ratio * 0.5))
        
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
            datahora = passagem.get("datahora")
            if isinstance(datahora, str):
                from datetime import datetime
                dt = datetime.fromisoformat(datahora.replace('Z', '+00:00'))
                hour = dt.hour
            else:
                hour = datahora.hour
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
        """Análise de relatos usando análise semântica"""
        analyzed_reports = []
        risk_scores = []
        
        for ocorrencia in ocorrencias:
            relato = (ocorrencia.get("relato") or "").strip()
            if not relato:
                continue
            
            # Usar serviço semântico se disponível
            try:
                from app.services.semantic_service import analyze_text
                analysis = analyze_text(relato)
                
                # Converter pontuação (0-100) para score (0.0-1.0)
                risk_score = min(1.0, analysis.get("pontuacao", 0) / 100.0)
                
                # Ajustar baseado na classe
                classe = analysis.get("classe", "OUTROS")
                if classe in ["TRAFICO", "PORTE_ARMA"]:
                    risk_score = max(risk_score, 0.7)  # Mínimo de 70% para casos críticos
                elif classe == "RECEPTACAO":
                    risk_score = max(risk_score, 0.5)  # Mínimo de 50% para receptação
                
            except ImportError:
                # Fallback para análise simples se serviço semântico não disponível
                risk_score = self._simple_text_analysis(relato)
                analysis = {
                    "classe": "OUTROS",
                    "pontuacao": int(risk_score * 100),
                    "keywords": []
                }
            
            risk_scores.append(risk_score)
            
            analyzed_reports.append({
                "ocorrencia_id": ocorrencia.get("id"),
                "tipo": ocorrencia.get("tipo"),
                "datahora": str(ocorrencia.get("datahora", "")),
                "relato": relato,
                "analysis": analysis,
                "risk_score": risk_score
            })
        
        overall_risk = float(np.mean(risk_scores)) if risk_scores else 0.0
        
        # Classificação baseada na análise semântica
        high_risk_count = sum(1 for score in risk_scores if score > 0.7)
        classification = "SUSPEITO" if high_risk_count > 0 or overall_risk > 0.5 else "NORMAL"
        
        return {
            "overall_risk": overall_risk,
            "analyzed_reports": analyzed_reports,
            "classification": classification,
            "high_risk_reports": high_risk_count,
            "summary": f"Analisados {len(analyzed_reports)} relatos. Risco médio: {overall_risk:.2f}"
        }
    
    def _simple_text_analysis(self, texto: str) -> float:
        """Análise simples de texto baseada em palavras-chave"""
        palavras_suspeitas = [
            "droga", "maconha", "cocaina", "crack", "tráfico", "arma", "pistola",
            "suspeito", "nervoso", "mentiu", "contradicao", "fronteira", "ec ruim"
        ]
        
        palavras_criticas = [
            "traficante", "traficantes", "homicidio", "assassinato", 
            "sequestro", "roubo", "assalto"
        ]
        
        texto_lower = texto.lower()
        
        # Palavras críticas têm peso maior
        critical_matches = sum(1 for palavra in palavras_criticas if palavra in texto_lower)
        normal_matches = sum(1 for palavra in palavras_suspeitas if palavra in texto_lower)
        
        # Score baseado em matches
        score = (critical_matches * 0.3) + (normal_matches * 0.1)
        
        return min(1.0, score)

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
            data_analysis = None
            
            for dep_result in dependency_data.values():
                if "classification" in dep_result and "patterns" in dep_result:
                    route_analysis = dep_result
                elif "analyzed_reports" in dep_result:
                    semantic_analysis = dep_result
                elif "veiculo_info" in dep_result:
                    data_analysis = dep_result
            
            final_risk = await self._calculate_consolidated_risk(
                route_analysis, semantic_analysis, data_analysis
            )
            
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
    
    async def _calculate_consolidated_risk(
        self, 
        route_analysis: Optional[Dict], 
        semantic_analysis: Optional[Dict],
        data_analysis: Optional[Dict]
    ) -> Dict:
        """Calcula risco final considerando múltiplas análises"""
        
        route_risk = route_analysis.get("risk_score", 0.0) if route_analysis else 0.0
        semantic_risk = semantic_analysis.get("overall_risk", 0.0) if semantic_analysis else 0.0
        data_quality = data_analysis.get("data_quality", {}).get("quality_score", 0.5) if data_analysis else 0.5
        
        # Pesos adaptativos baseados na disponibilidade de dados
        route_weight = 0.6 if route_analysis else 0.3
        semantic_weight = 0.4 if semantic_analysis else 0.2
        
        # Ajustar pesos baseado na qualidade dos dados
        if data_quality < 0.3:  # Dados de baixa qualidade
            route_weight *= 0.7
            semantic_weight *= 0.7
        
        # Normalizar pesos
        total_weight = route_weight + semantic_weight
        if total_weight > 0:
            route_weight /= total_weight
            semantic_weight /= total_weight
        else:
            route_weight = semantic_weight = 0.5
        
        # Calcular score final
        final_score = (route_risk * route_weight) + (semantic_risk * semantic_weight)
        
        # Boost adicional se ambas as análises indicam suspeita
        if route_risk > 0.6 and semantic_risk > 0.6:
            final_score = min(1.0, final_score + 0.2)  # Boost de 20%
        
        # Classificação de risco
        if final_score > 0.8:
            risk_level = "CRÍTICO"
        elif final_score > 0.6:
            risk_level = "ALTO"
        elif final_score > 0.4:
            risk_level = "MÉDIO"
        else:
            risk_level = "BAIXO"
        
        # Gerar recomendações
        recommendations = self._generate_recommendations(
            final_score, route_analysis, semantic_analysis
        )
        
        # Calcular confiança
        confidence = self._calculate_confidence(
            route_analysis, semantic_analysis, data_quality
        )
        
        return {
            "final_risk_score": final_score,
            "risk_level": risk_level,
            "component_scores": {
                "route_risk": route_risk,
                "semantic_risk": semantic_risk,
                "data_quality": data_quality
            },
            "weights_used": {
                "route_weight": route_weight,
                "semantic_weight": semantic_weight
            },
            "confidence": confidence,
            "recommendations": recommendations,
            "calculation_timestamp": time.time()
        }
    
    def _generate_recommendations(
        self, 
        final_score: float, 
        route_analysis: Optional[Dict], 
        semantic_analysis: Optional[Dict]
    ) -> List[str]:
        """Gera recomendações baseadas na análise"""
        recommendations = []
        
        if final_score > 0.7:
            recommendations.append("Realizar inspeção física detalhada")
            recommendations.append("Verificar histórico criminal dos ocupantes")
        
        if route_analysis and route_analysis.get("patterns", {}).get("night_activity", 0) > 0.5:
            recommendations.append("Monitorar atividades noturnas")
        
        if route_analysis and route_analysis.get("patterns", {}).get("illicit_ratio", 0) > 0.3:
            recommendations.append("Investigar rotas marcadas como ilícitas")
        
        if semantic_analysis and semantic_analysis.get("high_risk_reports", 0) > 0:
            recommendations.append("Revisar relatos de alto risco")
        
        if final_score > 0.5:
            recommendations.append("Aumentar frequência de fiscalização")
        
        if not recommendations:
            recommendations.append("Manter padrão normal de fiscalização")
        
        return recommendations
    
    def _calculate_confidence(
        self, 
        route_analysis: Optional[Dict], 
        semantic_analysis: Optional[Dict], 
        data_quality: float
    ) -> float:
        """Calcula confiança na análise baseada na disponibilidade e qualidade dos dados"""
        
        confidence_factors = []
        
        # Fator de qualidade dos dados
        confidence_factors.append(data_quality)
        
        # Fator de análise de rotas
        if route_analysis:
            route_confidence = route_analysis.get("confidence", 0.5)
            passagens_count = len(route_analysis.get("patterns", {}).get("passages", []))
            # Mais passagens = maior confiança
            route_factor = min(1.0, route_confidence * (1 + min(passagens_count / 10, 0.5)))
            confidence_factors.append(route_factor)
        
        # Fator de análise semântica
        if semantic_analysis:
            reports_count = len(semantic_analysis.get("analyzed_reports", []))
            # Mais relatos = maior confiança
            semantic_factor = min(1.0, 0.6 + min(reports_count / 5, 0.4))
            confidence_factors.append(semantic_factor)
        
        # Confiança final é a média dos fatores disponíveis
        final_confidence = sum(confidence_factors) / len(confidence_factors) if confidence_factors else 0.5
        
        return min(1.0, max(0.0, final_confidence))