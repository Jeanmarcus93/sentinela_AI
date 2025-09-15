#!/usr/bin/env python3
"""
Teste Automático com Amostra de Relatos Reais
=============================================

Este script testa automaticamente o modelo com uma amostra aleatória
dos relatos do banco veiculos_db.
"""

import os
import sys
import json
import joblib
import psycopg
import pandas as pd
import numpy as np
from pathlib import Path
from typing import List, Tuple, Dict, Any
import warnings
warnings.filterwarnings('ignore')

# Configurações
BASE_DIR = Path(__file__).parent.parent
MODELS_DIR = BASE_DIR / "ml_models" / "trained"

# Configuração do banco veiculos_db
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'dbname': 'veiculos_db',
    'user': 'postgres',
    'password': 'Jmkjmk.00'
}

def load_model():
    """Carrega o modelo treinado"""
    model_path = MODELS_DIR / "semantic_agents_clf.joblib"
    metadata_path = MODELS_DIR / "semantic_agents_metadata.json"
    
    model = None
    threshold = 0.35
    
    try:
        model = joblib.load(model_path)
        print(f"✅ Modelo carregado de: {model_path}")
        
        # Carregar threshold se disponível
        if metadata_path.exists():
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
                if 'optimal_threshold' in metadata:
                    threshold = metadata['optimal_threshold']
                    print(f"🎯 Threshold carregado: {threshold:.3f}")
        
    except Exception as e:
        print(f"❌ Erro ao carregar modelo: {e}")
        return None, 0.35
    
    return model, threshold

def get_connection():
    """Cria conexão com banco"""
    try:
        return psycopg.connect(**DB_CONFIG)
    except Exception as e:
        print(f"❌ Erro de conexão: {e}")
        return None

def load_sample_relatos(limit: int = 100):
    """Carrega uma amostra de relatos reais"""
    print(f"🔄 Carregando {limit} relatos do banco veiculos_db...")
    
    conn = get_connection()
    if not conn:
        return []
    
    relatos = []
    
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT relato, id 
                FROM ocorrencias 
                WHERE relato IS NOT NULL 
                AND relato != '' 
                AND LENGTH(relato) > 50
                ORDER BY RANDOM()
                LIMIT %s
            """, (limit,))
            
            for row in cur.fetchall():
                relato, id_ocorrencia = row
                if relato and len(relato.strip()) > 10:
                    relatos.append((relato.strip(), id_ocorrencia))
            
            print(f"✅ Carregados {len(relatos)} relatos")
            
    except Exception as e:
        print(f"❌ Erro ao carregar dados: {e}")
    finally:
        conn.close()
    
    return relatos

def classify_relato(model, relato: str, threshold: float):
    """Classifica um relato usando o modelo"""
    if not model:
        return "ERRO", 0.0, 0.0
    
    try:
        # Obter probabilidades
        proba = model.predict_proba([relato])[0]
        
        # Assumir que a classe SUSPEITO é o índice 1
        suspeito_prob = proba[1] if len(proba) > 1 else proba[0]
        
        # Classificar baseado no threshold
        if suspeito_prob >= threshold:
            classification = "SUSPEITO"
            confidence = suspeito_prob
        else:
            classification = "SEM_ALTERACAO"
            confidence = 1.0 - suspeito_prob
        
        return classification, confidence, suspeito_prob
        
    except Exception as e:
        print(f"❌ Erro na classificação: {e}")
        return "ERRO", 0.0, 0.0

def test_sample_automatic(limit: int = 50):
    """Testa automaticamente uma amostra de relatos"""
    print(f"\n🧪 TESTE AUTOMÁTICO COM {limit} RELATOS REAIS")
    print("=" * 60)
    
    # Carregar modelo
    model, threshold = load_model()
    if not model:
        print("❌ Não foi possível carregar o modelo")
        return
    
    print(f"🎯 Threshold configurado: {threshold:.3f}")
    
    # Carregar relatos
    relatos = load_sample_relatos(limit)
    
    if not relatos:
        print("❌ Nenhum relato carregado")
        return
    
    # Classificar todos os relatos
    results = []
    suspeitos_count = 0
    
    print(f"\n📊 Classificando {len(relatos)} relatos...")
    
    for i, (relato, id_ocorrencia) in enumerate(relatos):
        classification, confidence, suspeito_prob = classify_relato(model, relato, threshold)
        
        if classification == "SUSPEITO":
            suspeitos_count += 1
        
        results.append({
            'id': id_ocorrencia,
            'relato': relato[:150] + "..." if len(relato) > 150 else relato,
            'classification': classification,
            'confidence': confidence,
            'suspeito_prob': suspeito_prob
        })
        
        # Mostrar progresso
        if (i + 1) % 10 == 0:
            print(f"   Processados: {i + 1}/{len(relatos)}")
    
    # Estatísticas gerais
    print(f"\n📈 ESTATÍSTICAS GERAIS:")
    print(f"   Total de relatos: {len(relatos)}")
    print(f"   Classificados como SUSPEITO: {suspeitos_count} ({suspeitos_count/len(relatos)*100:.1f}%)")
    print(f"   Classificados como SEM_ALTERACAO: {len(relatos)-suspeitos_count} ({(len(relatos)-suspeitos_count)/len(relatos)*100:.1f}%)")
    
    # Mostrar casos mais suspeitos
    suspeitos = [r for r in results if r['classification'] == 'SUSPEITO']
    suspeitos.sort(key=lambda x: x['suspeito_prob'], reverse=True)
    
    print(f"\n🔴 TOP 10 CASOS MAIS SUSPEITOS:")
    for i, caso in enumerate(suspeitos[:10]):
        print(f"   {i+1:2d}. [{caso['suspeito_prob']:.2f}] {caso['relato']}")
    
    # Mostrar casos menos suspeitos
    normais = [r for r in results if r['classification'] == 'SEM_ALTERACAO']
    normais.sort(key=lambda x: x['suspeito_prob'])
    
    print(f"\n🟢 TOP 10 CASOS MENOS SUSPEITOS:")
    for i, caso in enumerate(normais[:10]):
        print(f"   {i+1:2d}. [{caso['suspeito_prob']:.2f}] {caso['relato']}")
    
    # Análise de distribuição de probabilidades
    suspeito_probs = [r['suspeito_prob'] for r in results]
    print(f"\n📊 ANÁLISE DE PROBABILIDADES:")
    print(f"   Média: {np.mean(suspeito_probs):.3f}")
    print(f"   Mediana: {np.median(suspeito_probs):.3f}")
    print(f"   Desvio padrão: {np.std(suspeito_probs):.3f}")
    print(f"   Min: {np.min(suspeito_probs):.3f}")
    print(f"   Max: {np.max(suspeito_probs):.3f}")
    
    return results

def main():
    """Função principal"""
    print("🤖 TESTE AUTOMÁTICO COM DADOS REAIS - veiculos_db")
    print("=" * 60)
    
    # Teste com 100 relatos
    results = test_sample_automatic(100)
    
    if results:
        print(f"\n✅ Teste concluído com sucesso!")
        print(f"📊 {len(results)} relatos analisados")
    else:
        print(f"\n❌ Falha no teste")

if __name__ == "__main__":
    main()

