#!/usr/bin/env python3
# backend/scripts/manage_semantic_training.py
"""
Gerenciador de Treinamento Semântico - Sistema de Agentes
Script utilitário para treinar, testar e gerenciar modelos semânticos binários
"""

import sys
import os
import argparse
import json
import time
import glob
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime, timedelta

# Adicionar path do projeto
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from ml_models.training.train_semantic_agents import (
        AgentSemanticTrainer, 
        AgentTrainingConfig,
        BinarySemanticClassifier,
        check_environment
    )
    from config.agents.semantic_binary_config import (
        create_semantic_config, 
        BinarySemanticConfig,
        print_config_summary,
        PresetConfigurations
    )
    from app.models.database import get_db_connection
    import joblib
    import numpy as np
    print("✅ Imports carregados com sucesso")
except ImportError as e:
    print(f"❌ Erro nos imports: {e}")
    print("Execute este script do diretório raiz do projeto")
    sys.exit(1)

class SemanticTrainingManager:
    """Gerenciador completo para treinamento semântico"""
    
    def __init__(self):
        self.project_root = PROJECT_ROOT
        self.models_dir = PROJECT_ROOT / "ml_models" / "trained"
        self.config_dir = PROJECT_ROOT / "config" / "agents"
        self.logs_dir = PROJECT_ROOT / "logs"
        
        # Criar diretórios se não existirem
        for directory in [self.models_dir, self.config_dir, self.logs_dir]:
            directory.mkdir(parents=True, exist_ok=True)
        
        # Arquivos principais
        self.model_files = {
            'classifier': self.models_dir / 'semantic_agents_clf.joblib',
            'labels': self.models_dir / 'semantic_agents_labels.joblib',
            'metadata': self.models_dir / 'semantic_agents_metadata.json'
        }
        
        self.log_file = self.logs_dir / f"semantic_training_{datetime.now().strftime('%Y%m')}.log"
        
    def log(self, message: str, level: str = "INFO"):
        """Log com timestamp"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}"
        print(log_entry)
        
        # Salvar em arquivo de log
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(log_entry + '\n')
        except Exception:
            pass  # Não falhar por problemas de log
    
    def status(self) -> Dict[str, Any]:
        """Verifica status atual do sistema"""
        self.log("🔍 Verificando status do sistema semântico...")
        
        status_info = {
            'timestamp': time.time(),
            'date': datetime.now().isoformat(),
            'models': {},
            'database': {},
            'dependencies': {},
            'configuration': {},
            'environment': {},
            'performance': {}
        }
        
        # ===== VERIFICAR MODELOS EXISTENTES =====
        self.log("   📊 Verificando modelos...")
        for model_name, model_path in self.model_files.items():
            if model_path.exists():
                stat = model_path.stat()
                status_info['models'][model_name] = {
                    'exists': True,
                    'path': str(model_path),
                    'size_mb': round(stat.st_size / (1024 * 1024), 2),
                    'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    'age_hours': round((time.time() - stat.st_mtime) / 3600, 1)
                }
            else:
                status_info['models'][model_name] = {
                    'exists': False,
                    'path': str(model_path)
                }
        
        # Verificar se temos um modelo completo
        models_complete = all(info['exists'] for info in status_info['models'].values())
        status_info['models']['complete_set'] = models_complete
        
        # ===== VERIFICAR BANCO DE DADOS =====
        self.log("   💾 Verificando banco de dados...")
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    # Contar relatos totais
                    cur.execute("SELECT COUNT(*) FROM ocorrencias WHERE relato IS NOT NULL")
                    total_relatos = cur.fetchone()[0]
                    
                    # Contar por classificação manual
                    cur.execute("""
                        SELECT classificacao_manual, COUNT(*) 
                        FROM ocorrencias 
                        WHERE relato IS NOT NULL 
                        AND classificacao_manual IS NOT NULL
                        GROUP BY classificacao_manual
                    """)
                    manual_classifications = dict(cur.fetchall())
                    
                    # Contar relatos úteis (>50 chars)
                    cur.execute("SELECT COUNT(*) FROM ocorrencias WHERE LENGTH(relato) > 50")
                    useful_relatos = cur.fetchone()[0]
                    
                    # Contar relatos muito úteis (>100 chars)
                    cur.execute("SELECT COUNT(*) FROM ocorrencias WHERE LENGTH(relato) > 100")
                    quality_relatos = cur.fetchone()[0]
                    
                    # Últimas ocorrências
                    cur.execute("""
                        SELECT data_ocorrencia 
                        FROM ocorrencias 
                        WHERE relato IS NOT NULL 
                        ORDER BY data_ocorrencia DESC 
                        LIMIT 1
                    """)
                    last_record = cur.fetchone()
                    
            status_info['database'] = {
                'connected': True,
                'total_relatos': total_relatos,
                'useful_relatos': useful_relatos,
                'quality_relatos': quality_relatos,
                'manual_classifications': manual_classifications,
                'last_record_date': last_record[0].isoformat() if last_record else None,
                'training_ready': useful_relatos >= 100,
                'quality_ready': quality_relatos >= 50
            }
            
        except Exception as e:
            status_info['database'] = {
                'connected': False,
                'error': str(e),
                'training_ready': False
            }
        
        # ===== VERIFICAR DEPENDÊNCIAS =====
        self.log("   📦 Verificando dependências...")
        required_packages = [
            ('sklearn', 'scikit-learn'),
            ('spacy', 'spacy'),
            ('sentence_transformers', 'sentence-transformers'),
            ('yake', 'yake'),
            ('joblib', 'joblib'),
            ('numpy', 'numpy'),
            ('pandas', 'pandas')
        ]
        
        for package, install_name in required_packages:
            try:
                __import__(package)
                status_info['dependencies'][install_name] = True
            except ImportError:
                status_info['dependencies'][install_name] = False
        
        # Verificar modelo spaCy específico
        try:
            import spacy
            spacy.load('pt_core_news_sm')
            status_info['dependencies']['pt_core_news_sm'] = True
        except:
            status_info['dependencies']['pt_core_news_sm'] = False
        
        # ===== VERIFICAR CONFIGURAÇÃO =====
        self.log("   ⚙️ Verificando configuração...")
        try:
            config = create_semantic_config()
            issues = config.validate_configuration()
            status_info['configuration'] = {
                'valid': len(issues) == 0,
                'issues': issues,
                'preset': 'balanced',
                'total_keywords': len(config.critical_keywords),
                'total_patterns': len(config.coverage_patterns)
            }
        except Exception as e:
            status_info['configuration'] = {
                'valid': False,
                'error': str(e)
            }
        
        # ===== VERIFICAR AMBIENTE =====
        self.log("   🌍 Verificando variáveis de ambiente...")
        env_vars = [
            'SPACY_PT_MODEL', 'SENTENCE_EMB_MODEL', 'SEMANTIC_PRESET',
            'SEMANTIC_SUSPICION_THRESHOLD', 'SEMANTIC_MAX_CONCURRENT'
        ]
        
        for var in env_vars:
            value = os.getenv(var)
            status_info['environment'][var] = {
                'set': value is not None,
                'value': value if value else None
            }
        
        # ===== VERIFICAR PERFORMANCE (se modelo existe) =====
        if models_complete:
            self.log("   ⚡ Verificando performance do modelo...")
            try:
                with open(self.model_files['metadata'], 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                
                status_info['performance'] = {
                    'model_version': metadata.get('model_version', 'unknown'),
                    'training_date': metadata.get('training_date', 'unknown'),
                    'f1_score': metadata.get('f1_score', 0),
                    'accuracy': metadata.get('accuracy', 0),
                    'precision': metadata.get('precision', 0),
                    'recall': metadata.get('recall', 0),
                    'training_time': metadata.get('training_time_seconds', 0),
                    'total_samples': metadata.get('total_samples', 0)
                }
            except Exception as e:
                status_info['performance'] = {
                    'error': f'Erro ao carregar metadata: {e}'
                }
        
        return status_info
    
    def print_status(self):
        """Imprime status detalhado formatado"""
        status = self.status()
        
        print("\n" + "="*70)
        print("📊 STATUS DO SISTEMA SEMÂNTICO COM AGENTES")
        print("="*70)
        
        # ===== MODELOS =====
        print("\n🤖 MODELOS:")
        models_info = status['models']
        for model_name, info in models_info.items():
            if model_name == 'complete_set':
                continue
                
            if info['exists']:
                age_info = f"({info['age_hours']:.1f}h atrás)" if info['age_hours'] < 48 else f"({info['age_hours']/24:.1f} dias atrás)"
                print(f"   ✅ {model_name:12s}: {info['size_mb']:6.1f}MB {age_info}")
            else:
                print(f"   ❌ {model_name:12s}: NÃO ENCONTRADO")
        
        if models_info['complete_set']:
            print("   🎯 Status: MODELO COMPLETO DISPONÍVEL")
        else:
            print("   ⚠️ Status: MODELO INCOMPLETO - TREINAMENTO NECESSÁRIO")
        
        # ===== BANCO DE DADOS =====
        print("\n💾 BANCO DE DADOS:")
        db_info = status['database']
        if db_info['connected']:
            print(f"   ✅ Conectado")
            print(f"   📄 Total de relatos: {db_info['total_relatos']:,}")
            print(f"   📝 Relatos úteis (>50 chars): {db_info['useful_relatos']:,}")
            print(f"   ⭐ Relatos de qualidade (>100 chars): {db_info['quality_relatos']:,}")
            
            if db_info['manual_classifications']:
                print(f"   🏷️  Classificações manuais:")
                for classification, count in db_info['manual_classifications'].items():
                    print(f"      {classification}: {count}")
            
            if db_info['last_record_date']:
                last_date = datetime.fromisoformat(db_info['last_record_date'])
                days_ago = (datetime.now() - last_date).days
                print(f"   📅 Último registro: {days_ago} dia(s) atrás")
            
            training_status = "✅ PRONTO" if db_info['training_ready'] else "❌ INSUFICIENTE"
            print(f"   🚀 Status para treino: {training_status}")
        else:
            print(f"   ❌ Erro de conexão: {db_info['error']}")
        
        # ===== DEPENDÊNCIAS =====
        print("\n📦 DEPENDÊNCIAS:")
        deps_info = status['dependencies']
        missing_deps = []
        for dep, available in deps_info.items():
            status_icon = "✅" if available else "❌"
            print(f"   {status_icon} {dep}")
            if not available:
                missing_deps.append(dep)
        
        if missing_deps:
            print(f"   ⚠️ Faltando {len(missing_deps)} dependência(s)")
        
        # ===== CONFIGURAÇÃO =====
        print("\n⚙️ CONFIGURAÇÃO:")
        config_info = status['configuration']
        if config_info['valid']:
            print("   ✅ Configuração válida")
            print(f"   📊 Palavras-chave: {config_info['total_keywords']}")
            print(f"   📋 Padrões: {config_info['total_patterns']}")
        else:
            print("   ❌ Problemas na configuração:")
            for issue in config_info.get('issues', []):
                print(f"      - {issue}")
        
        # ===== PERFORMANCE (se disponível) =====
        if 'performance' in status and 'error' not in status['performance']:
            print("\n📈 PERFORMANCE DO MODELO:")
            perf = status['performance']
            print(f"   🏷️  Versão: {perf['model_version']}")
            print(f"   📅 Treinado em: {perf['training_date']}")
            print(f"   🎯 F1-Score: {perf['f1_score']:.3f}")
            print(f"   📊 Acurácia: {perf['accuracy']:.3f}")
            print(f"   ⚡ Precisão: {perf['precision']:.3f}")
            print(f"   🔍 Recall: {perf['recall']:.3f}")
            print(f"   📋 Amostras de treino: {perf['total_samples']:,}")
            print(f"   ⏱️ Tempo de treino: {perf['training_time']:.1f}s")
        
        # ===== RECOMENDAÇÕES =====
        print("\n💡 RECOMENDAÇÕES:")
        recommendations = []
        
        if not db_info['connected']:
            recommendations.append("🔧 Configurar conexão com banco de dados")
        elif not db_info['training_ready']:
            recommendations.append(f"📝 Coletar mais dados (atual: {db_info['useful_relatos']}, mínimo: 100)")
        
        if missing_deps:
            recommendations.append(f"📦 Instalar dependências: pip install {' '.join(missing_deps)}")
        
        if not models_info['complete_set']:
            recommendations.append("🤖 Treinar modelo semântico")
        elif status.get('performance', {}).get('f1_score', 0) < 0.7:
            recommendations.append("📈 Retreinar modelo (performance baixa)")
        
        if not config_info['valid']:
            recommendations.append("⚙️ Corrigir configuração")
        
        # Verificar idade do modelo
        if models_info['complete_set']:
            oldest_model = max(info.get('age_hours', 0) for info in models_info.values() 
                             if isinstance(info, dict) and 'age_hours' in info)
            if oldest_model > 24 * 7:  # 1 semana
                recommendations.append("🔄 Considerar retreinar modelo (mais de 1 semana)")
        
        if recommendations:
            for i, rec in enumerate(recommendations, 1):
                print(f"   {i}. {rec}")
        else:
            print("   🎉 Sistema está configurado e pronto para uso!")
        
        print("\n" + "="*70)
    
    def train(self, preset: str = "balanced", **kwargs) -> bool:
        """Treina modelo semântico"""
        self.log(f"🚀 Iniciando treinamento com preset '{preset}'...", "INFO")
        
        # Verificar pré-requisitos
        self.log("   🔍 Verificando pré-requisitos...", "INFO")
        status = self.status()
        
        if not status['database']['training_ready']:
            self.log("❌ Dados insuficientes para treinamento", "ERROR")
            self.log(f"   Atual: {status['database']['useful_relatos']} relatos úteis", "ERROR")
            self.log("   Mínimo: 100 relatos úteis", "ERROR")
            return False
        
        missing_deps = [dep for dep, avail in status['dependencies'].items() if not avail]
        if missing_deps:
            self.log(f"❌ Dependências faltando: {', '.join(missing_deps)}", "ERROR")
            return False
        
        # Backup do modelo anterior (se existir)
        self._backup_existing_models()
        
        # Criar configurações
        try:
            training_config = AgentTrainingConfig()
            semantic_config = create_semantic_config(preset, **kwargs)
            
            self.log(f"   ⚙️ Configuração criada:", "INFO")
            self.log(f"      Preset: {preset}", "INFO")
            self.log(f"      Threshold suspeição: {semantic_config.suspicion_threshold}", "INFO")
            self.log(f"      Threshold confiança: {semantic_config.confidence_threshold}", "INFO")
            if kwargs:
                self.log(f"      Overrides: {kwargs}", "INFO")
                
        except Exception as e:
            self.log(f"❌ Erro ao criar configuração: {e}", "ERROR")
            return False
        
        # Executar treinamento
        start_time = time.time()
        try:
            self.log("   🎯 Iniciando processo de treinamento...", "INFO")
            trainer = AgentSemanticTrainer(training_config)
            success = trainer.run_full_training()
            
            total_time = time.time() - start_time
            
            if success:
                self.log(f"✅ Treinamento concluído em {total_time:.1f}s", "INFO")
                
                # Salvar configuração usada
                config_path = self.config_dir / f"last_training_config_{preset}_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
                config_data = {
                    'preset': preset,
                    'overrides': kwargs,
                    'timestamp': time.time(),
                    'datetime': datetime.now().isoformat(),
                    'success': success,
                    'training_time_seconds': total_time,
                    'database_stats': status['database']
                }
                
                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(config_data, f, indent=2, ensure_ascii=False)
                
                self.log(f"   📁 Configuração salva em: {config_path}", "INFO")
                
                # Validar modelo treinado
                if self._validate_trained_model():
                    self.log("✅ Modelo validado com sucesso", "INFO")
                else:
                    self.log("⚠️ Modelo treinado, mas validação falhou", "WARN")
                
            else:
                self.log(f"❌ Treinamento falhou após {total_time:.1f}s", "ERROR")
            
        except Exception as e:
            self.log(f"❌ Erro durante treinamento: {e}", "ERROR")
            import traceback
            self.log(f"   Detalhes: {traceback.format_exc()}", "DEBUG")
            success = False
        
        return success
    
    def test(self, sample_texts: Optional[List[str]] = None) -> bool:
        """Testa modelo treinado"""
        self.log("🧪 Testando modelo semântico...", "INFO")
        
        # Verificar se modelo existe
        if not self.model_files['classifier'].exists():
            self.log("❌ Modelo não encontrado. Execute o treinamento primeiro.", "ERROR")
            return False
        
        # Carregar modelo
        try:
            model = joblib.load(self.model_files['classifier'])
            labels = joblib.load(self.model_files['labels'])
            
            with open(self.model_files['metadata'], 'r', encoding='utf-8') as f:
                metadata = json.load(f)
                
            self.log("✅ Modelo carregado com sucesso", "INFO")
            self.log(f"   Versão: {metadata.get('model_version', 'unknown')}", "INFO")
            self.log(f"   Treinado em: {metadata.get('training_date', 'unknown')}", "INFO")
            self.log(f"   F1-Score: {metadata.get('f1_score', 0):.3f}", "INFO")
            
        except Exception as e:
            self.log(f"❌ Erro ao carregar modelo: {e}", "ERROR")
            return False
        
        # Textos de teste padrão
        if sample_texts is None:
            sample_texts = [
                # Casos claramente suspeitos
                "O indivíduo foi encontrado com 50g de cocaína e uma pistola calibre 380 na cintura durante abordagem policial",
                "Confessou estar traficando drogas há 3 meses na região central da cidade e conhecer outros traficantes",
                "Foi preso em flagrante portando material entorpecente, munições e dinheiro em espécie sem origem comprovada",
                
                # Casos de possível cobertura
                "Estava passando na rua quando vi a abordagem policial. Não sabia de nada sobre drogas no local",
                "Só estava dando uma volta no bairro de madrugada, não conhecia ninguém do local nem sabia do que se tratava",
                "Estava esperando minha namorada na esquina quando a polícia chegou, não sei de nada sobre o material encontrado",
                
                # Casos normais/legítimos  
                "Estava voltando do trabalho, por volta das 22h, apresentou documentos e colaborou plenamente com a investigação",
                "Mora na região há 10 anos, trabalha como pedreiro, nunca teve problemas com a justiça e possui referências",
                "Colaborou com a polícia e forneceu todas as informações solicitadas, demonstrando transparência total"
            ]
        
        self.log(f"📝 Testando {len(sample_texts)} amostras:", "INFO")
        print("\n" + "="*80)
        print("🧪 RESULTADOS DOS TESTES SEMÂNTICOS")
        print("="*80)
        
        # Criar classificador para testes com regras
        config = create_semantic_config("balanced")
        classifier = BinarySemanticClassifier(config)
        
        try:
            classifier.load_nlp_models()
        except Exception as e:
            self.log(f"⚠️ Erro ao carregar modelos NLP para teste: {e}", "WARN")
            print("⚠️ Teste limitado - usando apenas classificação baseada em regras")
        
        results_summary = {"SUSPEITO": 0, "SEM_ALTERACAO": 0}
        confidence_scores = []
        
        for i, texto in enumerate(sample_texts, 1):
            print(f"\n{i:2d}. TEXTO: {texto}")
            print("    " + "-"*76)
            
            try:
                # Classificação usando regras inteligentes
                label, confidence, metadata = classifier.classify_text_binary(texto)
                
                results_summary[label] += 1
                confidence_scores.append(confidence)
                
                # Determinar emoji e cor baseado na classificação
                if label == "SUSPEITO":
                    emoji = "🔴"
                    risk_level = "ALTO" if confidence > 0.8 else "MÉDIO" if confidence > 0.6 else "BAIXO"
                else:
                    emoji = "🟢"
                    risk_level = "BAIXO"
                
                print(f"    {emoji} CLASSIFICAÇÃO: {label}")
                print(f"    📊 CONFIANÇA: {confidence:.3f}")
                print(f"    ⚠️ NÍVEL DE RISCO: {risk_level}")
                print(f"    🎯 SCORE SUSPEIÇÃO: {metadata['suspicion_score']:.3f}")
                
                # Mostrar fatores que contribuíram
                contributing_factors = []
                for category, score in metadata['category_scores'].items():
                    if score > 0.05:  # Apenas fatores significativos
                        contributing_factors.append(f"{category.replace('_', ' ')}: {score:.2f}")
                
                if contributing_factors:
                    factors_str = ", ".join(contributing_factors[:3])  # Limitar a 3 fatores principais
                    print(f"    📈 PRINCIPAIS FATORES: {factors_str}")
                
                # Indicação se precisa revisão humana
                needs_review = config.should_require_human_review(confidence)
                if needs_review:
                    print(f"    👤 REQUER REVISÃO HUMANA: Sim")
                
            except Exception as e:
                print(f"    ❌ ERRO NO TESTE: {e}")
                continue
        
        # Resumo dos resultados
        print(f"\n" + "="*80)
        print("📊 RESUMO DOS RESULTADOS")
        print("="*80)
        print(f"🔴 SUSPEITO: {results_summary['SUSPEITO']} casos ({results_summary['SUSPEITO']/len(sample_texts)*100:.1f}%)")
        print(f"🟢 SEM_ALTERACAO: {results_summary['SEM_ALTERACAO']} casos ({results_summary['SEM_ALTERACAO']/len(sample_texts)*100:.1f}%)")
        
        if confidence_scores:
            avg_confidence = sum(confidence_scores) / len(confidence_scores)
            print(f"📊 CONFIANÇA MÉDIA: {avg_confidence:.3f}")
            print(f"📊 CONFIANÇA MÍNIMA: {min(confidence_scores):.3f}")
            print(f"📊 CONFIANÇA MÁXIMA: {max(confidence_scores):.3f}")
        
        print(f"\n💡 NOTA: Para classificação com modelo ML completo, use:")
        print(f"   python -c \"from app.services.semantic_service import analyze_text; print(analyze_text('seu_texto'))\"")
        
        self.log("✅ Teste concluído com sucesso", "INFO")
        return True
    
    def benchmark(self) -> Dict[str, Any]:
        """Executa benchmark do sistema"""
        self.log("📈 Executando benchmark do sistema...", "INFO")
        
        benchmark_results = {
            'timestamp': time.time(),
            'system_performance': {},
            'model_performance': {},
            'database_performance': {}
        }
        
        # ===== BENCHMARK DO SISTEMA =====
        print("\n⚡ BENCHMARK DE PERFORMANCE DO SISTEMA")
        print("="*50)
        
        # Teste de importação
        import_start = time.time()
        try:
            from app.services.semantic_service import analyze_text
            import_time = time.time() - import_start
            print(f"📦 Tempo de importação: {import_time*1000:.1f}ms")
            benchmark_results['system_performance']['import_time_ms'] = import_time * 1000
        except Exception as e:
            print(f"❌ Erro na importação: {e}")
            benchmark_results['system_performance']['import_error'] = str(e)
        
        # Teste de configuração
        config_start = time.time()
        try:
            for preset in ['balanced', 'high_precision', 'high_recall']:
                config = create_semantic_config(preset)
                issues = config.validate_configuration()
            config_time = time.time() - config_start
            print(f"⚙️ Tempo de configuração (3 presets): {config_time*1000:.1f}ms")
            benchmark_results['system_performance']['config_time_ms'] = config_time * 1000
        except Exception as e:
            print(f"❌ Erro na configuração: {e}")
            benchmark_results['system_performance']['config_error'] = str(e)
        
        # ===== BENCHMARK DO BANCO =====
        try:
            db_start = time.time()
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT COUNT(*) FROM ocorrencias WHERE relato IS NOT NULL LIMIT 1000")
                    count = cur.fetchone()[0]
            db_time = time.time() - db_start
            print(f"💾 Tempo de consulta ao banco: {db_time*1000:.1f}ms")
            print(f"💾 Relatos disponíveis: {count:,}")
            benchmark_results['database_performance'] = {
                'query_time_ms': db_time * 1000,
                'records_available': count
            }
        except Exception as e:
            print(f"❌ Erro no banco: {e}")
            benchmark_results['database_performance']['error'] = str(e)
        
        # ===== BENCHMARK DO MODELO (se existir) =====
        if self.model_files['classifier'].exists():
            try:
                model_start = time.time()
                model = joblib.load(self.model_files['classifier'])
                load_time = time.time() - model_start
                
                print(f"🤖 Tempo de carregamento do modelo: {load_time*1000:.1f}ms")
                
                # Informações do modelo
                with open(self.model_files['metadata'], 'r') as f:
                    metadata = json.load(f)
                
                print(f"🤖 Versão do modelo: {metadata.get('model_version', 'unknown')}")
                print(f"🤖 F1-Score: {metadata.get('f1_score', 0):.3f}")
                print(f"🤖 Amostras de treino: {metadata.get('total_samples', 0):,}")
                
                benchmark_results['model_performance'] = {
                    'load_time_ms': load_time * 1000,
                    'version': metadata.get('model_version'),
                    'f1_score': metadata.get('f1_score', 0),
                    'accuracy': metadata.get('accuracy', 0),
                    'total_samples': metadata.get('total_samples', 0)
                }
                
            except Exception as e:
                print(f"❌ Erro no modelo: {e}")
                benchmark_results['model_performance']['error'] = str(e)
        else:
            print("⚠️ Modelo não encontrado - execute treinamento primeiro")
        
        # ===== ESTIMATIVAS DE THROUGHPUT =====
        print(f"\n📊 ESTIMATIVAS DE THROUGHPUT:")
        
        # Baseado em benchmarks típicos
        estimated_analysis_time = 0.5  # segundos por análise
        max_concurrent = 5
        
        analyses_per_minute = (60 / estimated_analysis_time) * max_concurrent
        analyses_per_hour = analyses_per_minute * 60
        
        print(f"   ⚡ Tempo estimado por análise: ~{estimated_analysis_time}s")
        print(f"   🔄 Análises simultâneas: {max_concurrent}")
        print(f"   📈 Throughput estimado: {analyses_per_minute:.0f} análises/min")
        print(f"   📈 Throughput por hora: {analyses_per_hour:,.0f} análises/h")
        print(f"   💾 Uso estimado de memória: ~300MB")
        
        benchmark_results['system_performance'].update({
            'estimated_analysis_time_s': estimated_analysis_time,
            'max_concurrent': max_concurrent,
            'throughput_per_minute': analyses_per_minute,
            'throughput_per_hour': analyses_per_hour,
            'estimated_memory_mb': 300
        })
        
        self.log("✅ Benchmark concluído", "INFO")
        return benchmark_results
    
    def cleanup(self) -> int:
        """Limpa arquivos antigos e temporários"""
        self.log("🧹 Iniciando limpeza do sistema...", "INFO")
        
        cleanup_count = 0
        total_size_mb = 0
        
        # ===== LIMPAR BACKUPS ANTIGOS =====
        print("\n🗑️ LIMPANDO ARQUIVOS ANTIGOS")
        print("="*40)
        
        backup_patterns = [
            self.models_dir / "*.backup",
            self.models_dir / "*_old.*",
            self.models_dir / "temp_*",
            self.config_dir / "*_temp.*"
        ]
        
        for pattern in backup_patterns:
            for file_path in pattern.parent.glob(pattern.name):
                if file_path.is_file():
                    # Verificar idade (mais de 7 dias)
                    file_age = time.time() - file_path.stat().st_mtime
                    if file_age > (7 * 24 * 3600):  # 7 dias
                        file_size = file_path.stat().st_size / (1024 * 1024)  # MB
                        total_size_mb += file_size
                        
                        file_path.unlink()
                        cleanup_count += 1
                        print(f"   🗑️ Removido: {file_path.name} ({file_size:.1f}MB)")
        
        # ===== LIMPAR LOGS ANTIGOS =====
        log_patterns = [
            self.logs_dir / "semantic_training_*.log"
        ]
        
        for pattern in log_patterns:
            for log_file in pattern.parent.glob(pattern.name):
                if log_file.is_file():
                    # Manter apenas logs dos últimos 30 dias
                    file_age = time.time() - log_file.stat().st_mtime
                    if file_age > (30 * 24 * 3600):  # 30 dias
                        file_size = log_file.stat().st_size / (1024 * 1024)  # MB
                        total_size_mb += file_size
                        
                        log_file.unlink()
                        cleanup_count += 1
                        print(f"   🗑️ Log removido: {log_file.name} ({file_size:.2f}MB)")
        
        # ===== LIMPAR CONFIGURAÇÕES ANTIGAS DE TREINO =====
        config_pattern = self.config_dir / "last_training_config_*"
        config_files = list(config_pattern.parent.glob(config_pattern.name))
        
        # Manter apenas os 5 mais recentes
        config_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        for old_config in config_files[5:]:
            file_size = old_config.stat().st_size / (1024 * 1024)  # MB
            total_size_mb += file_size
            
            old_config.unlink()
            cleanup_count += 1
            print(f"   🗑️ Config antiga removida: {old_config.name} ({file_size:.3f}MB)")
        
        # ===== LIMPEZA DE CACHE (se existir) =====
        cache_dirs = [
            self.project_root / "__pycache__",
            self.models_dir / "__pycache__",
            self.project_root / ".pytest_cache"
        ]
        
        for cache_dir in cache_dirs:
            if cache_dir.exists() and cache_dir.is_dir():
                import shutil
                try:
                    dir_size = sum(f.stat().st_size for f in cache_dir.rglob('*') if f.is_file()) / (1024 * 1024)
                    shutil.rmtree(cache_dir)
                    total_size_mb += dir_size
                    cleanup_count += 1
                    print(f"   🗑️ Cache removido: {cache_dir.name}/ ({dir_size:.1f}MB)")
                except Exception as e:
                    print(f"   ⚠️ Erro ao remover {cache_dir}: {e}")
        
        # ===== RESUMO DA LIMPEZA =====
        print(f"\n📊 RESUMO DA LIMPEZA:")
        if cleanup_count > 0:
            print(f"   ✅ {cleanup_count} arquivo(s) removido(s)")
            print(f"   💾 {total_size_mb:.2f}MB liberados")
        else:
            print("   ✨ Nenhum arquivo antigo encontrado")
        
        self.log(f"✅ Limpeza concluída: {cleanup_count} arquivos, {total_size_mb:.2f}MB", "INFO")
        return cleanup_count
    
    def _backup_existing_models(self):
        """Cria backup dos modelos existentes antes do treinamento"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        for model_name, model_path in self.model_files.items():
            if model_path.exists():
                backup_path = model_path.with_suffix(f'.backup_{timestamp}{model_path.suffix}')
                try:
                    import shutil
                    shutil.copy2(model_path, backup_path)
                    self.log(f"   📋 Backup criado: {backup_path.name}", "INFO")
                except Exception as e:
                    self.log(f"   ⚠️ Erro ao criar backup de {model_name}: {e}", "WARN")
    
    def _validate_trained_model(self) -> bool:
        """Valida modelo recém-treinado"""
        try:
            # Verificar se todos os arquivos existem
            for model_name, model_path in self.model_files.items():
                if not model_path.exists():
                    self.log(f"   ❌ Arquivo faltando: {model_name}", "ERROR")
                    return False
            
            # Tentar carregar modelo
            model = joblib.load(self.model_files['classifier'])
            labels = joblib.load(self.model_files['labels'])
            
            # Verificar metadata
            with open(self.model_files['metadata'], 'r') as f:
                metadata = json.load(f)
            
            # Validações básicas
            required_fields = ['f1_score', 'accuracy', 'total_samples', 'training_date']
            for field in required_fields:
                if field not in metadata:
                    self.log(f"   ❌ Campo faltando em metadata: {field}", "ERROR")
                    return False
            
            # Verificar performance mínima
            f1_score = metadata.get('f1_score', 0)
            if f1_score < 0.5:
                self.log(f"   ⚠️ F1-Score baixo: {f1_score:.3f}", "WARN")
            
            self.log(f"   ✅ Modelo validado - F1: {f1_score:.3f}", "INFO")
            return True
            
        except Exception as e:
            self.log(f"   ❌ Erro na validação: {e}", "ERROR")
            return False
    
    def export_model_info(self, output_path: Optional[Path] = None) -> Path:
        """Exporta informações detalhadas do modelo"""
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = self.models_dir / f"model_report_{timestamp}.json"
        
        self.log(f"📤 Exportando informações do modelo...", "INFO")
        
        report = {
            'export_info': {
                'timestamp': time.time(),
                'datetime': datetime.now().isoformat(),
                'exported_by': 'SemanticTrainingManager'
            },
            'system_status': self.status(),
            'model_files': {}
        }
        
        # Informações dos arquivos
        for model_name, model_path in self.model_files.items():
            if model_path.exists():
                stat = model_path.stat()
                report['model_files'][model_name] = {
                    'exists': True,
                    'path': str(model_path),
                    'size_bytes': stat.st_size,
                    'size_mb': round(stat.st_size / (1024 * 1024), 2),
                    'modified': datetime.fromtimestamp(stat.st_mtime).isoformat()
                }
            else:
                report['model_files'][model_name] = {
                    'exists': False,
                    'path': str(model_path)
                }
        
        # Configurações utilizadas
        try:
            config = create_semantic_config()
            report['configuration'] = config.to_dict()
        except Exception as e:
            report['configuration_error'] = str(e)
        
        # Salvar relatório
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        self.log(f"✅ Relatório exportado: {output_path}", "INFO")
        return output_path
    
    def compare_models(self, model1_metadata: Path, model2_metadata: Path):
        """Compara dois modelos diferentes"""
        try:
            with open(model1_metadata, 'r') as f:
                meta1 = json.load(f)
            with open(model2_metadata, 'r') as f:
                meta2 = json.load(f)
            
            print("\n📊 COMPARAÇÃO DE MODELOS")
            print("="*50)
            
            metrics = ['f1_score', 'accuracy', 'precision', 'recall']
            
            for metric in metrics:
                val1 = meta1.get(metric, 0)
                val2 = meta2.get(metric, 0)
                diff = val2 - val1
                
                arrow = "📈" if diff > 0 else "📉" if diff < 0 else "➡️"
                print(f"{metric:10s}: {val1:.3f} vs {val2:.3f} {arrow} ({diff:+.3f})")
            
        except Exception as e:
            self.log(f"❌ Erro na comparação: {e}", "ERROR")

def main():
    """Função principal do CLI"""
    parser = argparse.ArgumentParser(
        description="Gerenciador de Treinamento Semântico - Agentes Binários",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos de uso:
  # Verificar status do sistema
  python manage_semantic_training.py status
  
  # Treinamento básico
  python manage_semantic_training.py train
  
  # Treinamento com preset específico
  python manage_semantic_training.py train --preset high_precision
  
  # Treinamento com parâmetros customizados
  python manage_semantic_training.py train --preset balanced \\
    --suspicion-threshold 0.6 --confidence-threshold 0.8
  
  # Testar modelo existente
  python manage_semantic_training.py test
  
  # Benchmark de performance
  python manage_semantic_training.py benchmark
  
  # Limpeza de arquivos antigos
  python manage_semantic_training.py cleanup
  
  # Exportar relatório completo
  python manage_semantic_training.py export
        """
    )
    
    # Argumento principal (ação)
    parser.add_argument('action', 
                       choices=['status', 'train', 'test', 'benchmark', 'cleanup', 'export'],
                       help='Ação a ser executada')
    
    # Argumentos para treinamento
    parser.add_argument('--preset', default='balanced', 
                       choices=['balanced', 'high_precision', 'high_recall', 'conservative', 'aggressive', 'forensic'],
                       help='Preset de configuração para treinamento')
    
    parser.add_argument('--suspicion-threshold', type=float, metavar='FLOAT',
                       help='Override para threshold de suspeição (0.0-1.0)')
    
    parser.add_argument('--confidence-threshold', type=float, metavar='FLOAT',
                       help='Override para threshold de confiança (0.0-1.0)')
    
    parser.add_argument('--max-concurrent', type=int, metavar='INT',
                       help='Número máximo de análises simultâneas')
    
    # Argumentos para teste
    parser.add_argument('--test-file', type=str, metavar='PATH',
                       help='Arquivo com textos de teste (um por linha)')
    
    # Argumentos para export
    parser.add_argument('--output', type=str, metavar='PATH',
                       help='Caminho para arquivo de saída')
    
    # Argumentos gerais
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Saída mais detalhada')
    
    parser.add_argument('--quiet', '-q', action='store_true',
                       help='Saída mínima (apenas erros)')
    
    parser.add_argument('--force', action='store_true',
                       help='Forçar execução mesmo com avisos')
    
    args = parser.parse_args()
    
    # Configurar nível de verbosidade
    if args.quiet:
        # Redirecionar stdout para reduzir output
        import sys
        class QuietOutput:
            def write(self, s): pass
            def flush(self): pass
        
        if not args.verbose:  # Só aplicar quiet se não for verbose
            sys.stdout = QuietOutput()
    
    # Criar gerenciador
    try:
        manager = SemanticTrainingManager()
        
        # Header
        if not args.quiet:
            print("🤖 GERENCIADOR DE TREINAMENTO SEMÂNTICO")
            print("Sistema de Agentes com Classificação Binária")
            print("="*55)
        
        success = True
        
        # Executar ação solicitada
        if args.action == 'status':
            manager.print_status()
            
        elif args.action == 'train':
            # Preparar overrides
            overrides = {}
            if args.suspicion_threshold is not None:
                if not 0.0 <= args.suspicion_threshold <= 1.0:
                    print("❌ Suspicion threshold deve estar entre 0.0 e 1.0")
                    sys.exit(1)
                overrides['suspicion_threshold'] = args.suspicion_threshold
                
            if args.confidence_threshold is not None:
                if not 0.0 <= args.confidence_threshold <= 1.0:
                    print("❌ Confidence threshold deve estar entre 0.0 e 1.0")
                    sys.exit(1)
                overrides['confidence_threshold'] = args.confidence_threshold
                
            if args.max_concurrent is not None:
                if args.max_concurrent < 1:
                    print("❌ Max concurrent deve ser maior que 0")
                    sys.exit(1)
                overrides['max_concurrent_analyses'] = args.max_concurrent
            
            # Verificação de pré-requisitos (se não for --force)
            if not args.force:
                if not check_environment():
                    print("\n❌ Use --force para ignorar verificações ou corrija os problemas")
                    sys.exit(1)
            
            success = manager.train(args.preset, **overrides)
            
        elif args.action == 'test':
            # Carregar textos de arquivo se especificado
            sample_texts = None
            if args.test_file:
                try:
                    with open(args.test_file, 'r', encoding='utf-8') as f:
                        sample_texts = [line.strip() for line in f if line.strip()]
                    print(f"📁 Carregados {len(sample_texts)} textos de {args.test_file}")
                except Exception as e:
                    print(f"❌ Erro ao ler arquivo de teste: {e}")
                    sys.exit(1)
            
            success = manager.test(sample_texts)
            
        elif args.action == 'benchmark':
            results = manager.benchmark()
            if args.verbose:
                print(f"\n📋 Resultados detalhados salvos em memória")
                # Aqui poderia salvar em arquivo se necessário
            
        elif args.action == 'cleanup':
            cleaned_files = manager.cleanup()
            if not args.quiet:
                if cleaned_files > 0:
                    print(f"\n✅ Limpeza concluída: {cleaned_files} arquivos removidos")
                else:
                    print("\n✨ Sistema já estava limpo")
            
        elif args.action == 'export':
            output_path = Path(args.output) if args.output else None
            exported_file = manager.export_model_info(output_path)
            if not args.quiet:
                print(f"\n📤 Relatório exportado: {exported_file}")
        
        # Resultado final
        if not args.quiet:
            status_icon = "✅" if success else "❌"
            print(f"\n{status_icon} Operação {'concluída com sucesso' if success else 'falhou'}")
        
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        if not args.quiet:
            print("\n⚠️ Operação cancelada pelo usuário")
        sys.exit(1)
        
    except Exception as e:
        print(f"\n❌ Erro inesperado: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()