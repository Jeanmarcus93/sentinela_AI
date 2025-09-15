#!/usr/bin/env python3
"""
Script de Teste com Dados Reais do Banco veiculos_db
====================================================

Este script testa o modelo treinado com relatos reais do banco de dados.
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
from sklearn.metrics import classification_report, confusion_matrix
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

class RealDataTester:
    """Testador com dados reais do banco"""
    
    def __init__(self):
        self.model = None
        self.threshold = 0.35  # Threshold padrão
        self.load_model()
        
    def load_model(self):
        """Carrega o modelo treinado"""
        model_path = MODELS_DIR / "semantic_agents_clf.joblib"
        metadata_path = MODELS_DIR / "semantic_agents_metadata.json"
        
        try:
            self.model = joblib.load(model_path)
            print(f"✅ Modelo carregado de: {model_path}")
            
            # Carregar threshold se disponível
            if metadata_path.exists():
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                    if 'optimal_threshold' in metadata:
                        self.threshold = metadata['optimal_threshold']
                        print(f"🎯 Threshold carregado: {self.threshold:.3f}")
            
        except Exception as e:
            print(f"❌ Erro ao carregar modelo: {e}")
            return False
        
        return True
    
    def get_connection(self):
        """Cria conexão com banco"""
        try:
            return psycopg.connect(**DB_CONFIG)
        except Exception as e:
            print(f"❌ Erro de conexão: {e}")
            return None
    
    def load_sample_relatos(self, limit: int = 100) -> List[Tuple[str, int]]:
        """Carrega uma amostra de relatos reais"""
        print(f"🔄 Carregando {limit} relatos do banco...")
        
        conn = self.get_connection()
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
    
    def classify_relato(self, relato: str) -> Tuple[str, float, float]:
        """Classifica um relato usando o modelo"""
        if not self.model:
            return "ERRO", 0.0, 0.0
        
        try:
            # Obter probabilidades
            proba = self.model.predict_proba([relato])[0]
            
            # Assumir que a classe SUSPEITO é o índice 1
            suspeito_prob = proba[1] if len(proba) > 1 else proba[0]
            
            # Classificar baseado no threshold
            if suspeito_prob >= self.threshold:
                classification = "SUSPEITO"
                confidence = suspeito_prob
            else:
                classification = "SEM_ALTERACAO"
                confidence = 1.0 - suspeito_prob
            
            return classification, confidence, suspeito_prob
            
        except Exception as e:
            print(f"❌ Erro na classificação: {e}")
            return "ERRO", 0.0, 0.0
    
    def test_sample(self, limit: int = 50):
        """Testa uma amostra de relatos"""
        print(f"\n🧪 TESTANDO MODELO COM {limit} RELATOS REAIS")
        print("=" * 60)
        
        relatos = self.load_sample_relatos(limit)
        
        if not relatos:
            print("❌ Nenhum relato carregado")
            return
        
        # Classificar todos os relatos
        results = []
        suspeitos_count = 0
        
        print(f"\n📊 Classificando {len(relatos)} relatos...")
        
        for i, (relato, id_ocorrencia) in enumerate(relatos):
            classification, confidence, suspeito_prob = self.classify_relato(relato)
            
            if classification == "SUSPEITO":
                suspeitos_count += 1
            
            results.append({
                'id': id_ocorrencia,
                'relato': relato[:100] + "..." if len(relato) > 100 else relato,
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
        
        print(f"\n🔴 TOP 5 CASOS MAIS SUSPEITOS:")
        for i, caso in enumerate(suspeitos[:5]):
            print(f"   {i+1}. [{caso['suspeito_prob']:.2f}] {caso['relato']}")
        
        # Mostrar casos menos suspeitos
        normais = [r for r in results if r['classification'] == 'SEM_ALTERACAO']
        normais.sort(key=lambda x: x['suspeito_prob'])
        
        print(f"\n🟢 TOP 5 CASOS MENOS SUSPEITOS:")
        for i, caso in enumerate(normais[:5]):
            print(f"   {i+1}. [{caso['suspeito_prob']:.2f}] {caso['relato']}")
        
        return results
    
    def interactive_test(self):
        """Teste interativo com relatos específicos"""
        print(f"\n🎮 TESTE INTERATIVO")
        print("=" * 30)
        
        while True:
            print(f"\nOpções:")
            print("1. Testar relato específico")
            print("2. Testar amostra aleatória")
            print("3. Buscar relatos por palavra-chave")
            print("0. Sair")
            
            escolha = input("\n👉 Escolha uma opção: ").strip()
            
            if escolha == "0":
                break
            elif escolha == "1":
                relato = input("Digite o relato: ").strip()
                if relato:
                    classification, confidence, suspeito_prob = self.classify_relato(relato)
                    print(f"\n📊 RESULTADO:")
                    print(f"   Classificação: {classification}")
                    print(f"   Confiança: {confidence:.2f}")
                    print(f"   Probabilidade Suspeição: {suspeito_prob:.2f}")
            
            elif escolha == "2":
                limit = int(input("Quantos relatos testar? (padrão 10): ") or "10")
                self.test_sample(limit)
            
            elif escolha == "3":
                keyword = input("Digite palavra-chave: ").strip()
                if keyword:
                    self.search_and_test(keyword)
    
    def search_and_test(self, keyword: str, limit: int = 10):
        """Busca e testa relatos com palavra-chave específica"""
        print(f"\n🔍 BUSCANDO RELATOS COM '{keyword}'")
        print("=" * 40)
        
        conn = self.get_connection()
        if not conn:
            return
        
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT relato, id 
                    FROM ocorrencias 
                    WHERE relato ILIKE %s
                    AND relato IS NOT NULL 
                    AND relato != ''
                    LIMIT %s
                """, (f'%{keyword}%', limit))
                
                relatos = cur.fetchall()
                
                if not relatos:
                    print(f"❌ Nenhum relato encontrado com '{keyword}'")
                    return
                
                print(f"✅ Encontrados {len(relatos)} relatos")
                
                for i, (relato, id_ocorrencia) in enumerate(relatos):
                    classification, confidence, suspeito_prob = self.classify_relato(relato)
                    
                    print(f"\n📝 RELATO {i+1} (ID: {id_ocorrencia}):")
                    print(f"   {relato[:200]}...")
                    print(f"   🎯 Classificação: {classification} ({suspeito_prob:.2f})")
                
        except Exception as e:
            print(f"❌ Erro na busca: {e}")
        finally:
            conn.close()

def main():
    """Função principal"""
    print("🤖 TESTE DO MODELO COM DADOS REAIS - veiculos_db")
    print("=" * 60)
    
    tester = RealDataTester()
    
    if not tester.model:
        print("❌ Não foi possível carregar o modelo")
        return
    
    print(f"🎯 Threshold configurado: {tester.threshold:.3f}")
    
    # Teste inicial com amostra
    print(f"\n🚀 Executando teste inicial...")
    results = tester.test_sample(50)
    
    # Teste interativo
    tester.interactive_test()
    
    print(f"\n✅ Teste concluído!")

if __name__ == "__main__":
    main()

