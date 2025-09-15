# training_routes.py
"""
Rotas para treinamento de modelos de IA
"""

from flask import Blueprint, request, jsonify
import os
import sys
import subprocess
import json
from datetime import datetime
from typing import Dict, Any, List

# Adicionar caminho do projeto
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from app.models.database import get_db_connection

# Criar blueprint
training_bp = Blueprint('training', __name__, url_prefix='/api/training')

# Configurações de treinamento
TRAINING_CONFIGS = {
    'semantic': {
        'script': 'ml_models/training/train_semantic.py',
        'description': 'Modelo de Análise Semântica',
        'min_samples': 50,
        'output_dir': 'ml_models/trained'
    },
    'routes': {
        'script': 'scripts/train_route_analysis.py', 
        'description': 'Modelo de Análise de Rotas',
        'min_samples': 100,
        'output_dir': 'ml_models/trained'
    },
    'hybrid': {
        'script': 'scripts/train_hybrid_model.py',
        'description': 'Modelo Híbrido',
        'min_samples': 75,
        'output_dir': 'ml_models/trained'
    }
}

@training_bp.route('/status', methods=['GET'])
def get_training_status():
    """Retorna status dos modelos e dados de treinamento"""
    try:
        status = {
            'models': {},
            'feedback_stats': {},
            'training_ready': False
        }
        
        # Verificar status dos modelos
        for model_type, config in TRAINING_CONFIGS.items():
            model_status = check_model_status(model_type, config)
            status['models'][model_type] = model_status
        
        # Obter estatísticas de feedback
        status['feedback_stats'] = get_feedback_stats()
        
        # Verificar se está pronto para treinamento
        total_feedbacks = status['feedback_stats'].get('total', 0)
        status['training_ready'] = total_feedbacks >= 50
        
        return jsonify(status)
        
    except Exception as e:
        return jsonify({"error": f"Erro ao obter status: {str(e)}"}), 500

@training_bp.route('/models', methods=['GET'])
def list_available_models():
    """Lista modelos disponíveis para treinamento"""
    try:
        models = []
        
        for model_type, config in TRAINING_CONFIGS.items():
            model_info = {
                'type': model_type,
                'name': config['description'],
                'min_samples': config['min_samples'],
                'script': config['script'],
                'status': check_model_status(model_type, config)
            }
            models.append(model_info)
        
        return jsonify({'models': models})
        
    except Exception as e:
        return jsonify({"error": f"Erro ao listar modelos: {str(e)}"}), 500

@training_bp.route('/train/<model_type>', methods=['POST'])
def train_model(model_type):
    """Executa treinamento de um modelo específico"""
    try:
        if model_type not in TRAINING_CONFIGS:
            return jsonify({"error": f"Tipo de modelo '{model_type}' não suportado"}), 400
        
        config = TRAINING_CONFIGS[model_type]
        
        # Verificar se há dados suficientes
        feedback_stats = get_feedback_stats()
        if feedback_stats.get('total', 0) < config['min_samples']:
            return jsonify({
                "error": f"Dados insuficientes para treinamento. Necessário: {config['min_samples']}, Disponível: {feedback_stats.get('total', 0)}"
            }), 400
        
        # Executar treinamento
        training_result = execute_training(model_type, config)
        
        if training_result['success']:
            return jsonify({
                "success": True,
                "message": f"Treinamento do modelo {config['description']} concluído com sucesso",
                "details": training_result
            })
        else:
            return jsonify({
                "success": False,
                "error": f"Falha no treinamento: {training_result.get('error', 'Erro desconhecido')}"
            }), 500
            
    except Exception as e:
        return jsonify({"error": f"Erro no treinamento: {str(e)}"}), 500

@training_bp.route('/feedback/prepare', methods=['POST'])
def prepare_training_data():
    """Prepara dados de feedback para treinamento"""
    try:
        data = request.get_json()
        model_type = data.get('model_type', 'semantic')
        
        if model_type not in TRAINING_CONFIGS:
            return jsonify({"error": f"Tipo de modelo '{model_type}' não suportado"}), 400
        
        # Obter dados de feedback
        training_data = get_training_data_from_feedback(model_type)
        
        return jsonify({
            "success": True,
            "data_prepared": True,
            "samples": len(training_data.get('textos', [])),
            "labels": training_data.get('labels', []),
            "model_type": model_type
        })
        
    except Exception as e:
        return jsonify({"error": f"Erro ao preparar dados: {str(e)}"}), 500

@training_bp.route('/feedback/validate', methods=['POST'])
def validate_training_data():
    """Valida qualidade dos dados de treinamento"""
    try:
        data = request.get_json()
        model_type = data.get('model_type', 'semantic')
        
        validation_result = validate_training_data_quality(model_type)
        
        return jsonify({
            "success": True,
            "validation": validation_result
        })
        
    except Exception as e:
        return jsonify({"error": f"Erro na validação: {str(e)}"}), 500

@training_bp.route('/history', methods=['GET'])
def get_training_history():
    """Retorna histórico de treinamentos"""
    try:
        history = get_training_history_from_db()
        return jsonify({'history': history})
        
    except Exception as e:
        return jsonify({"error": f"Erro ao obter histórico: {str(e)}"}), 500

# ========================================
# ===== FUNÇÕES AUXILIARES =============
# ========================================

def check_model_status(model_type: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """Verifica status de um modelo"""
    try:
        output_dir = os.path.join(PROJECT_ROOT, config['output_dir'])
        
        # Verificar arquivos do modelo
        model_files = {
            'semantic': ['semantic_agents_clf.joblib', 'semantic_agents_labels.joblib', 'semantic_agents_metadata.json'],
            'routes': ['routes_clf.joblib', 'routes_labels.joblib'],
            'hybrid': ['hybrid_clf.joblib', 'hybrid_labels.joblib']
        }
        
        files_exist = []
        for filename in model_files.get(model_type, []):
            filepath = os.path.join(output_dir, filename)
            files_exist.append(os.path.exists(filepath))
        
        # Verificar metadados se disponível
        metadata = {}
        metadata_file = os.path.join(output_dir, f'{model_type}_metadata.json')
        if os.path.exists(metadata_file):
            try:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
            except:
                pass
        
        return {
            'exists': all(files_exist),
            'files_status': dict(zip(model_files.get(model_type, []), files_exist)),
            'metadata': metadata,
            'last_trained': metadata.get('trained_at', 'N/A'),
            'accuracy': metadata.get('accuracy', 'N/A')
        }
        
    except Exception as e:
        return {
            'exists': False,
            'error': str(e),
            'files_status': {},
            'metadata': {}
        }

def get_feedback_stats() -> Dict[str, Any]:
    """Obtém estatísticas dos feedbacks"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Contar total de feedbacks
                cur.execute("SELECT COUNT(*) FROM feedback")
                total = cur.fetchone()[0]
                
                # Contar por tipo de feedback
                cur.execute("""
                    SELECT feedback_usuario, COUNT(*) 
                    FROM feedback 
                    GROUP BY feedback_usuario
                """)
                feedback_counts = dict(cur.fetchall())
                
                # Contar por classificação
                cur.execute("""
                    SELECT classificacao_usuario, COUNT(*) 
                    FROM feedback 
                    GROUP BY classificacao_usuario
                """)
                classification_counts = dict(cur.fetchall())
                
                return {
                    'total': total,
                    'feedback_counts': feedback_counts,
                    'classification_counts': classification_counts,
                    'ready_for_training': total >= 50
                }
                
    except Exception as e:
        return {
            'total': 0,
            'error': str(e),
            'feedback_counts': {},
            'classification_counts': {},
            'ready_for_training': False
        }

def execute_training(model_type: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """Executa treinamento de um modelo"""
    try:
        script_path = os.path.join(PROJECT_ROOT, 'scripts', config['script'])
        
        if not os.path.exists(script_path):
            return {
                'success': False,
                'error': f"Script de treinamento não encontrado: {script_path}"
            }
        
        # Executar script de treinamento
        result = subprocess.run(
            [sys.executable, script_path],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=300  # 5 minutos timeout
        )
        
        if result.returncode == 0:
            return {
                'success': True,
                'output': result.stdout,
                'model_type': model_type,
                'trained_at': datetime.now().isoformat()
            }
        else:
            return {
                'success': False,
                'error': result.stderr,
                'output': result.stdout
            }
            
    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'error': 'Timeout no treinamento (5 minutos)'
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

def get_training_data_from_feedback(model_type: str) -> Dict[str, Any]:
    """Prepara dados de feedback para treinamento"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT texto_relato, classificacao_usuario, feedback_usuario
                    FROM feedback 
                    WHERE texto_relato IS NOT NULL 
                    AND texto_relato != ''
                    AND classificacao_usuario IS NOT NULL
                    ORDER BY id DESC
                """)
                
                rows = cur.fetchall()
                
                textos = []
                labels = []
                
                for row in rows:
                    texto, classificacao, feedback = row
                    if texto and classificacao:
                        textos.append(texto)
                        labels.append(classificacao)
                
                return {
                    'textos': textos,
                    'labels': labels,
                    'total_samples': len(textos)
                }
                
    except Exception as e:
        return {
            'textos': [],
            'labels': [],
            'total_samples': 0,
            'error': str(e)
        }

def validate_training_data_quality(model_type: str) -> Dict[str, Any]:
    """Valida qualidade dos dados de treinamento"""
    try:
        training_data = get_training_data_from_feedback(model_type)
        
        textos = training_data.get('textos', [])
        labels = training_data.get('labels', [])
        
        if not textos:
            return {
                'valid': False,
                'issues': ['Nenhum dado de treinamento encontrado']
            }
        
        issues = []
        
        # Verificar tamanho mínimo
        if len(textos) < TRAINING_CONFIGS[model_type]['min_samples']:
            issues.append(f"Dados insuficientes: {len(textos)} < {TRAINING_CONFIGS[model_type]['min_samples']}")
        
        # Verificar balanceamento de classes
        from collections import Counter
        label_counts = Counter(labels)
        if len(label_counts) < 2:
            issues.append("Apenas uma classe presente nos dados")
        
        # Verificar textos muito curtos
        short_texts = sum(1 for texto in textos if len(texto.strip()) < 10)
        if short_texts > len(textos) * 0.5:
            issues.append(f"Muitos textos muito curtos: {short_texts}/{len(textos)}")
        
        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'stats': {
                'total_samples': len(textos),
                'classes': dict(label_counts),
                'short_texts': short_texts,
                'avg_text_length': sum(len(t) for t in textos) / len(textos) if textos else 0
            }
        }
        
    except Exception as e:
        return {
            'valid': False,
            'issues': [f"Erro na validação: {str(e)}"]
        }

def get_training_history_from_db() -> List[Dict[str, Any]]:
    """Obtém histórico de treinamentos do banco"""
    try:
        # Por enquanto retorna histórico vazio
        # Em uma implementação completa, seria salvo no banco
        return []
        
    except Exception as e:
        return []
