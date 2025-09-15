# test_semantic_feedback.py
"""
Sistema de Teste e Feedback Semântico - Sentinela IA
====================================================

Versão STANDALONE que funciona independente da estrutura do projeto

Usage:
    python test_semantic_feedback.py
"""

import os
import sys
import json
import joblib
import psycopg
import re
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, Tuple, List
from dataclasses import dataclass

# ==========================================
# CONFIGURAÇÕES STANDALONE
# ==========================================

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('sentinela_feedback.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Detectar diretório base automaticamente
SCRIPT_DIR = Path(__file__).parent.absolute()

# Buscar pelo diretório backend ou usar o diretório atual
if SCRIPT_DIR.name == "scripts":
    BASE_DIR = SCRIPT_DIR.parent  # backend/
elif (SCRIPT_DIR / "backend").exists():
    BASE_DIR = SCRIPT_DIR / "backend"
else:
    BASE_DIR = SCRIPT_DIR  # raiz/
    logger.warning(f"Usando diretório atual como base: {BASE_DIR}")

MODELS_DIR = BASE_DIR / "ml_models" / "trained"

# Configuração de banco (pegando do .env ou valores padrão)
def load_env_config():
    """Carrega configuração do arquivo .env"""
    # Tentar primeiro .env, depois env
    env_file = BASE_DIR / ".env"
    if not env_file.exists():
        env_file = BASE_DIR / "env"
    config = {
        'DB_HOST': os.getenv('DB_HOST', 'localhost'),
        'DB_PORT': os.getenv('DB_PORT', '5432'), 
        'DB_NAME': os.getenv('DB_NAME', 'sentinela_teste'),
        'DB_USER': os.getenv('DB_USER', 'postgres'),
        'DB_PASSWORD': os.getenv('DB_PASSWORD', 'postgres')
    }
    
    if env_file.exists():
        try:
            with open(env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if '=' in line and not line.strip().startswith('#'):
                        key, value = line.strip().split('=', 1)
                        if key in config:
                            config[key] = value
            logger.info(f"Configurações carregadas de {env_file}")
        except Exception as e:
            logger.warning(f"Erro ao carregar arquivo {env_file}: {e}")
            # Continua com valores padrão
    
    return config

ENV_CONFIG = load_env_config()

@dataclass
class FeedbackRecord:
    """Registro de feedback do usuário"""
    relato_original: str
    classificacao_ia: str
    confianca_ia: float
    score_suspicao: float
    classificacao_correta: str
    feedback_usuario: str
    timestamp: datetime

# ==========================================
# CLASSIFICADOR STANDALONE
# ==========================================

class SimpleSemanticClassifier:
    """Classificador semântico simplificado"""
    
    def __init__(self):
        self.palavras_criticas = {
            'traficante', 'traficantes', 'tráfico', 'trafico',
            'cocaína', 'cocaina', 'crack', 'droga', 'drogas',
            'pistola', 'revolver', 'arma', 'munição', 'munições',
            'homicídio', 'homicidio', 'assassinato', 'flagrante',
            'foragido', 'procurado', 'mandado', 'fronteira'
        }
        
        self.palavras_suspeitas = {
            'maconha', 'skunk', 'entorpecente', 'pó', 'pedra',
            'rifle', 'fuzil', 'disparo', 'tiro',
            'roubo', 'assalto', 'furto', 'receptação',
            'nervoso', 'agressivo', 'mentiu', 'contradicao',
            'evasão', 'fuga', 'bate volta', 'madrugada'
        }
        
        self.historias_cobertura = {
            'estava passando', 'não sabia de nada', 'só estava dando uma volta',
            'estava indo para casa', 'estava esperando alguém', 'não conhecia ninguém',
            'estava voltando do trabalho', 'por acaso estava ali'
        }
    
    def classify_text(self, texto: str) -> Tuple[str, float, float, Dict[str, Any]]:
        """Classifica texto usando regras simplificadas"""
        # Validação mais robusta
        if not texto:
            return "SEM_ALTERACAO", 0.9, 0.1, {"erro": "Texto vazio"}
        
        texto_clean = texto.strip()
        if len(texto_clean) < 10:
            return "SEM_ALTERACAO", 0.9, 0.1, {"erro": "Texto muito curto"}
        
        # Verificar se tem conteúdo real (não apenas espaços/pontuação)
        if not re.search(r'[a-zA-ZÀ-ÿ]', texto_clean):
            return "SEM_ALTERACAO", 0.9, 0.1, {"erro": "Texto sem conteúdo textual"}
        
        texto_lower = texto.lower()
        score = 0.0
        detalhes = {
            'palavras_criticas_found': [],
            'palavras_suspeitas_found': [],
            'historias_cobertura_found': []
        }
        
        # 1. Palavras críticas (peso alto - 0.4 cada)
        for palavra in self.palavras_criticas:
            if palavra in texto_lower:
                score += 0.4
                detalhes['palavras_criticas_found'].append(palavra)
        
        # 2. Palavras suspeitas (peso médio - 0.15 cada)
        for palavra in self.palavras_suspeitas:
            if palavra in texto_lower:
                score += 0.15
                detalhes['palavras_suspeitas_found'].append(palavra)
        
        # 3. Histórias de cobertura (peso médio - 0.2 cada)
        for historia in self.historias_cobertura:
            if historia in texto_lower:
                score += 0.2
                detalhes['historias_cobertura_found'].append(historia)
        
        # Normalizar score
        score = min(score, 1.0)
        
        # Classificar
        THRESHOLD = 0.35  # Mesmo threshold corrigido
        if score >= THRESHOLD:
            label = "SUSPEITO"
            confidence = score
        else:
            label = "SEM_ALTERACAO"
            confidence = 1.0 - score
        
        return label, confidence, score, detalhes

# ==========================================
# GERENCIADOR DE BANCO DE DADOS
# ==========================================

class DatabaseManager:
    """Gerenciador de banco standalone"""
    
    def __init__(self):
        self.config = ENV_CONFIG
    
    def get_connection(self):
        """Cria conexão com banco"""
        try:
            conn = psycopg.connect(
                host=self.config['DB_HOST'],
                port=int(self.config['DB_PORT']),
                dbname=self.config['DB_NAME'],
                user=self.config['DB_USER'],
                password=self.config['DB_PASSWORD']
            )
            return conn
        except Exception as e:
            logger.error(f"Erro de conexão com banco: {e}")
            logger.info(f"Verifique as configurações em {BASE_DIR}/.env")
            return None
    
    def setup_feedback_table(self):
        """Cria tabela de feedback"""
        conn = self.get_connection()
        if not conn:
            return False
        
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS semantic_feedback (
                        id SERIAL PRIMARY KEY,
                        relato_original TEXT NOT NULL,
                        classificacao_ia VARCHAR(20) NOT NULL,
                        confianca_ia NUMERIC(5,3) NOT NULL,
                        score_suspicao NUMERIC(5,3) NOT NULL,
                        classificacao_correta VARCHAR(20) NOT NULL,
                        feedback_usuario TEXT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        metadados JSONB,
                        usado_retreinamento BOOLEAN DEFAULT FALSE
                    )
                """)
                
                # Índices
                cur.execute("CREATE INDEX IF NOT EXISTS idx_feedback_timestamp ON semantic_feedback(timestamp)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_feedback_classificacao ON semantic_feedback(classificacao_ia, classificacao_correta)")
                
                conn.commit()
                print("✅ Tabela de feedback configurada")
                return True
                
        except Exception as e:
            print(f"❌ Erro ao criar tabela: {e}")
            return False
        finally:
            if conn:
                conn.close()
    
    def save_feedback(self, feedback: FeedbackRecord) -> bool:
        """Salva feedback no banco"""
        conn = self.get_connection()
        if not conn:
            return False
        
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO semantic_feedback (
                        relato_original, classificacao_ia, confianca_ia, score_suspicao,
                        classificacao_correta, feedback_usuario, timestamp
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    feedback.relato_original,
                    feedback.classificacao_ia,
                    feedback.confianca_ia,
                    feedback.score_suspicao,
                    feedback.classificacao_correta,
                    feedback.feedback_usuario,
                    feedback.timestamp
                ))
                
                conn.commit()
                return True
                
        except Exception as e:
            print(f"❌ Erro ao salvar: {e}")
            return False
        finally:
            if conn:
                conn.close()
    
    def get_feedback_stats(self) -> Dict[str, Any]:
        """Obtém estatísticas de feedback"""
        conn = self.get_connection()
        if not conn:
            return {}
        
        stats = {}
        try:
            with conn.cursor() as cur:
                # Total
                cur.execute("SELECT COUNT(*) FROM semantic_feedback")
                stats['total'] = cur.fetchone()[0]
                
                if stats['total'] > 0:
                    # Acurácia
                    cur.execute("""
                        SELECT 
                            COUNT(*) as total,
                            SUM(CASE WHEN classificacao_ia = classificacao_correta THEN 1 ELSE 0 END) as corretos
                        FROM semantic_feedback 
                        WHERE classificacao_correta != 'INCERTO'
                    """)
                    acc_data = cur.fetchone()
                    if acc_data[0] > 0:
                        stats['acuracia'] = (acc_data[1] / acc_data[0]) * 100
                    
                    # Distribuição
                    cur.execute("""
                        SELECT classificacao_correta, COUNT(*) 
                        FROM semantic_feedback 
                        GROUP BY classificacao_correta 
                        ORDER BY COUNT(*) DESC
                    """)
                    stats['distribuicao'] = cur.fetchall()
                
        except Exception as e:
            print(f"❌ Erro ao obter stats: {e}")
        finally:
            if conn:
                conn.close()
        
        return stats

# ==========================================
# SISTEMA PRINCIPAL
# ==========================================

class SemanticFeedbackTester:
    """Sistema principal de teste"""
    
    def __init__(self, offline_mode=False):
        self.classifier = SimpleSemanticClassifier()
        self.offline_mode = offline_mode
        self.db = DatabaseManager() if not offline_mode else None
        self.has_trained_model = False
        self.trained_model = None
    
    def try_load_trained_model(self):
        """Tenta carregar modelo treinado"""
        clf_path = MODELS_DIR / "semantic_agents_clf.joblib"
        
        if clf_path.exists():
            try:
                self.trained_model = joblib.load(clf_path)
                self.has_trained_model = True
                print("✅ Modelo treinado carregado")
                return True
            except Exception as e:
                print(f"⚠️ Não foi possível carregar modelo treinado: {e}")
        
        print("💡 Usando classificador baseado em regras")
        return False
    
    def classify_text(self, texto: str) -> Tuple[str, float, float, Dict[str, Any]]:
        """Classifica usando modelo disponível"""
        # Por enquanto, usar sempre o classificador simples
        # No futuro, aqui você pode integrar o modelo treinado se disponível
        return self.classifier.classify_text(texto)
    
    def collect_feedback(self, relato: str, classification: str, confidence: float, score: float) -> Optional[FeedbackRecord]:
        """Coleta feedback do usuário"""
        print(f"\n{'='*60}")
        print(f"📝 RELATO: \"{relato}\"")
        print(f"\n🤖 ANÁLISE DA IA:")
        emoji = "🔴" if classification == "SUSPEITO" else "🟢"
        print(f"   {emoji} Classificação: {classification}")
        print(f"   📊 Confiança: {confidence:.1%}")
        print(f"   🎯 Score Suspeição: {score:.1%}")
        
        print(f"\n❓ A CLASSIFICAÇÃO ESTÁ CORRETA?")
        print("   1 - ✅ Sim, está correto")
        print("   2 - ❌ Não, deveria ser SUSPEITO")
        print("   3 - ❌ Não, deveria ser SEM_ALTERACAO")
        print("   4 - 🤔 Caso duvidoso")
        print("   0 - ⏭️ Pular")
        
        while True:
            try:
                escolha = input("\n👉 Sua avaliação (1-4, 0 para pular): ").strip()
                
                if escolha == "0":
                    return None
                elif escolha == "1":
                    classificacao_correta = classification
                    feedback = "Classificação correta"
                    break
                elif escolha == "2":
                    classificacao_correta = "SUSPEITO"
                    feedback = "Deveria ser SUSPEITO"
                    break
                elif escolha == "3":
                    classificacao_correta = "SEM_ALTERACAO"
                    feedback = "Deveria ser SEM_ALTERACAO"
                    break
                elif escolha == "4":
                    classificacao_correta = "INCERTO"
                    feedback = "Caso duvidoso"
                    break
                else:
                    print("❌ Opção inválida")
                    continue
                    
            except KeyboardInterrupt:
                return None
        
        # Comentário opcional
        print("\n💬 Comentário adicional (Enter para pular):")
        comentario = input("👉 ").strip()
        if comentario:
            feedback += f" - {comentario}"
        
        return FeedbackRecord(
            relato_original=relato,
            classificacao_ia=classification,
            confianca_ia=confidence,
            score_suspicao=score,
            classificacao_correta=classificacao_correta,
            feedback_usuario=feedback,
            timestamp=datetime.now()
        )
    
    def show_stats(self):
        """Mostra estatísticas"""
        if self.offline_mode:
            print("\n📊 Modo offline - estatísticas não disponíveis")
            return
            
        stats = self.db.get_feedback_stats()
        
        if not stats or stats.get('total', 0) == 0:
            print("\n📊 Nenhum feedback coletado ainda")
            return
        
        print(f"\n📊 ESTATÍSTICAS DE FEEDBACK:")
        print(f"   📝 Total: {stats['total']}")
        
        if 'acuracia' in stats:
            print(f"   🎯 Acurácia: {stats['acuracia']:.1f}%")
        
        if 'distribuicao' in stats:
            print(f"   📊 Distribuição:")
            for classe, count in stats['distribuicao']:
                percentage = (count / stats['total']) * 100
                print(f"      {classe}: {count} ({percentage:.1f}%)")
    
    def run(self):
        """Loop principal"""
        print("🎯 SISTEMA DE TESTE E FEEDBACK SEMÂNTICO - SENTINELA IA")
        print("="*60)
        
        # Setup
        if not self.offline_mode:
            if not self.db.setup_feedback_table():
                print("❌ Erro na configuração do banco")
                print("💡 Execute com --offline para usar sem banco de dados")
                return
        else:
            print("🔌 Modo offline - sem conexão com banco de dados")
        
        self.try_load_trained_model()
        self.show_stats()
        
        print(f"\n🚀 SISTEMA INICIADO")
        print("💡 Digite relatos para análise")
        print("💡 Digite 'stats' para estatísticas") 
        print("💡 Digite 'quit' para sair")
        print("="*60)
        
        test_count = 0
        feedback_count = 0
        
        while True:
            try:
                print(f"\n📝 TESTE #{test_count + 1}")
                relato = input("👉 Digite o relato: ").strip()
                
                if relato.lower() in ['quit', 'sair', 'exit']:
                    break
                elif relato.lower() in ['stats', 'estatísticas']:
                    self.show_stats()
                    continue
                elif not relato:
                    continue
                
                # Classificar
                print("🤖 Analisando...")
                classification, confidence, score, details = self.classify_text(relato)
                
                test_count += 1
                
                # Feedback
                feedback = self.collect_feedback(relato, classification, confidence, score)
                
                if feedback:
                    if not self.offline_mode and self.db.save_feedback(feedback):
                        feedback_count += 1
                        print("✅ Feedback salvo!")
                    elif self.offline_mode:
                        feedback_count += 1
                        print("✅ Feedback coletado (modo offline)")
                    
                    if feedback.classificacao_ia == feedback.classificacao_correta:
                        print("🎯 IA acertou!")
                    else:
                        print("❌ IA errou - dados salvos para melhoria")
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"❌ Erro: {e}")
        
        print(f"\n📋 RESUMO:")
        print(f"   🧪 Testes: {test_count}")
        print(f"   📝 Feedbacks: {feedback_count}")
        print("\n👋 Obrigado! Os dados ajudarão a melhorar o sistema.")

def main():
    """Função principal"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Sistema de Teste e Feedback Semântico')
    parser.add_argument('--offline', action='store_true', 
                       help='Executa em modo offline (sem banco de dados)')
    parser.add_argument('--db-host', default='localhost',
                       help='Host do banco de dados')
    parser.add_argument('--db-port', default='5432',
                       help='Porta do banco de dados')
    parser.add_argument('--db-name', default='sentinela_teste',
                       help='Nome do banco de dados')
    parser.add_argument('--db-user', default='postgres',
                       help='Usuário do banco de dados')
    parser.add_argument('--db-password', default='postgres',
                       help='Senha do banco de dados')
    
    args = parser.parse_args()
    
    # Configurar variáveis de ambiente se fornecidas
    if not args.offline:
        os.environ['DB_HOST'] = args.db_host
        os.environ['DB_PORT'] = args.db_port
        os.environ['DB_NAME'] = args.db_name
        os.environ['DB_USER'] = args.db_user
        os.environ['DB_PASSWORD'] = args.db_password
    
    try:
        tester = SemanticFeedbackTester(offline_mode=args.offline)
        tester.run()
    except Exception as e:
        print(f"❌ Erro crítico: {e}")
        import traceback
        traceback.print_exc()
    
    return 0

if __name__ == "__main__":
    main()