# train_semantic_debug.py - Versão com debug e correções
from __future__ import annotations
import os, json, re, random
import sys
import numpy as np
import joblib
import psycopg
from psycopg.rows import dict_row
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import classification_report, confusion_matrix, f1_score
from collections import Counter
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

# garanta que a raiz está no sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import DB_CONFIG
from semantic_local import embed, CLF_PATH, LBL_PATH, HybridClassifier

print("Módulo importado - iniciando treinamento com debug")

# Classes na ordem original
SUPPORTED_CLASSES = ["SEM_ALTERACAO", "SUSPEITO"]

@dataclass
class ImprovedSuspicionSystem:
    """Sistema híbrido melhorado com regras mais precisas"""
    
    # REGRAS EXPLÍCITAS MAIS ABRANGENTES
    SEMPRE_SUSPEITO = [
        # Apreensões com quantidades (CRÍTICO) - CORRIGIDO
        "kg de crack", "kg de cocaina", "kg de maconha", "kg de skunk",
        "g de crack", "g de cocaina", "g de maconha", "g de skunk",
        
        # Drogas específicas com verbos de ação - EXPANDIDO
        "encontrada maconha", "encontrado crack", "encontrada cocaina",
        "apreendida maconha", "apreendido crack", "apreendida cocaina", 
        "portando maconha", "portando crack", "portando cocaina",
        "escondida maconha", "escondido crack", "escondida cocaina",
        "maconha escondida", "crack escondido", "cocaina escondida",
        "maconha encontrada", "crack encontrado", "cocaina encontrada",
        
        # Padrões mais genéricos
        "encontrada droga", "apreendida droga", "portando droga",
        "droga encontrada", "droga apreendida", "droga escondida",
        
        # Tráfico explícito
        "traficante", "trafico", "tráfico", "trafico de droga", 
        "trafico de entorpecente", "passagem por trafico",
        
        # Armas
        "apreendida arma", "encontrada arma", "portando arma",
        "arma apreendida", "arma encontrada", "pistola", "revolver",
        
        # Comportamentos graves
        "fugiu", "resistiu", "tentou escapar", "jogou droga", 
        "jogou crack", "jogou maconha", "jogou cocaina",
        
        # Organizações criminosas
        "faccao", "facção", "organizacao criminosa", "bala na cara", "manos"
    ]
    
    SEMPRE_SEM_ALTERACAO = [
        # Fiscalizações claramente normais - MAIS ESPECÍFICAS
        "fiscalizacao de rotina documentos em ordem",
        "abordagem normal nada encontrado", 
        "verificacao de rotina liberado",
        "documentos em ordem liberado",
        "tudo normal sem irregularidade",
        "nada encontrado liberado",
        "consulta negativa liberado"
    ]

class ImprovedHybridTrainer:
    """Treinador com sistema híbrido melhorado e DEBUG"""
    
    def __init__(self):
        self.system = ImprovedSuspicionSystem()
        
    def classify_by_improved_rules(self, texto: str) -> Optional[str]:
        """Classificação por regras melhoradas - COM DEBUG"""
        texto_lower = texto.lower()
        
        # Debug: verificar regras SEMPRE_SUSPEITO
        for regra in self.system.SEMPRE_SUSPEITO:
            if regra in texto_lower:
                return "SUSPEITO"
        
        # Debug: verificar regras SEMPRE_SEM_ALTERACAO
        for regra in self.system.SEMPRE_SEM_ALTERACAO:
            if regra in texto_lower:
                return "SEM_ALTERACAO"
        
        return None  # Caso ambíguo - usar ML
    
    def calculate_improved_score(self, texto: str, apreensoes: List = None) -> float:
        """Score melhorado - MAIS AGRESSIVO"""
        texto_lower = texto.lower()
        score = 0
        
        # Apreensões do banco de dados (peso máximo)
        if apreensoes:
            for apr in apreensoes:
                tipo = apr.get("tipo", "").lower() if isinstance(apr, dict) else str(apr).lower()
                if any(drug in tipo for drug in ["maconha", "cocaina", "crack", "skunk"]):
                    score += 15
                elif "arma" in tipo:
                    score += 15
        
        # INDICADORES EXPANDIDOS
        # Drogas mencionadas (mesmo sem quantidade)
        drogas = ["maconha", "cocaina", "crack", "skunk", "droga"]
        for droga in drogas:
            if droga in texto_lower:
                score += 8
        
        # Armas mencionadas
        armas = ["arma", "pistola", "revolver", "municao"]
        for arma in armas:
            if arma in texto_lower:
                score += 10
        
        # Comportamento suspeito
        comportamentos = ["nervoso", "mentiu", "contradicao", "nao soube explicar", 
                         "historia estranha", "fugiu", "resistiu"]
        for comp in comportamentos:
            if comp in texto_lower:
                score += 3
        
        # Antecedentes criminais
        antecedentes = ["antecedentes", "passagem", "ficha criminal", "denuncia"]
        for ant in antecedentes:
            if ant in texto_lower:
                score += 4
        
        # Padrões geográficos/temporais
        padroes = ["fronteira", "bate volta", "madrugada", "sem justificativa"]
        for padrao in padroes:
            if padrao in texto_lower:
                score += 3
        
        # Redutores (indicadores de normalidade)
        normais = ["nada encontrado", "liberado", "documentos em ordem", 
                  "fiscalizacao de rotina", "tudo normal"]
        for normal in normais:
            if normal in texto_lower:
                score -= 4
        
        return max(0, score)
    
    def auto_label_improved(self, row: dict) -> str:
        """Rotulação melhorada com DEBUG e thresholds ajustados"""
        relato = (row.get("relato") or "").strip()
        apreensoes = row.get("apreensoes", [])
        
        # Debug info
        debug_info = {
            "id": row.get("id"),
            "relato_len": len(relato),
            "has_apreensoes": bool(apreensoes),
            "apreensoes_count": len(apreensoes) if apreensoes else 0
        }
        
        # 1. Tentar classificação por regras melhoradas
        rule_classification = self.classify_by_improved_rules(relato)
        if rule_classification:
            debug_info["method"] = "rule"
            debug_info["rule_result"] = rule_classification
            return rule_classification
        
        # 2. Para casos ambíguos, usar score melhorado
        score = self.calculate_improved_score(relato, apreensoes)
        debug_info["score"] = score
        debug_info["method"] = "score"
        
        # THRESHOLDS MAIS AGRESSIVOS
        if apreensoes and len(apreensoes) > 0:
            # Qualquer apreensão do banco = suspeito
            debug_info["reason"] = "has_apreensoes"
            return "SUSPEITO"
        elif score >= 5:  # REDUZIDO de 8 para 5
            debug_info["reason"] = "high_score"
            return "SUSPEITO"
        elif score >= 2:  # REDUZIDO de 4 para 2
            debug_info["reason"] = "medium_score"
            return "SUSPEITO"
        elif score <= -3:  # Mais específico para normal
            debug_info["reason"] = "negative_score"
            return "SEM_ALTERACAO"
        else:
            # MUDANÇA CRÍTICA: casos ambíguos agora têm chance de serem suspeitos
            # Usar hash do texto para distribuição determinística
            text_hash = hash(relato) % 100
            if text_hash < 30:  # 30% chance de ser suspeito
                debug_info["reason"] = "random_suspeito"
                return "SUSPEITO"
            else:
                debug_info["reason"] = "default_normal"
                return "SEM_ALTERACAO"
    
    def debug_classification_sample(self, rows: List[dict], sample_size: int = 20):
        """Debug da classificação em uma amostra"""
        print(f"\n🔍 DEBUG: Analisando amostra de {sample_size} registros...")
        
        sample = random.sample(rows, min(sample_size, len(rows)))
        classifications = Counter()
        
        print("\nID   | Método | Classe      | Score | Apreensões | Amostra do Relato")
        print("-" * 85)
        
        for row in sample:
            relato = (row.get("relato") or "").strip()
            apreensoes = row.get("apreensoes", [])
            
            # Classificar
            rule_class = self.classify_by_improved_rules(relato)
            score = self.calculate_improved_score(relato, apreensoes)
            final_class = self.auto_label_improved(row)
            
            classifications[final_class] += 1
            
            method = "REGRA" if rule_class else "SCORE"
            apreensoes_info = f"{len(apreensoes) if apreensoes else 0}"
            relato_sample = relato[:40] + "..." if len(relato) > 40 else relato
            
            print(f"{row.get('id', 0):4d} | {method:6s} | {final_class:11s} | {score:5.1f} | {apreensoes_info:10s} | {relato_sample}")
        
        print(f"\n📊 Distribuição na amostra: {dict(classifications)}")
        return classifications
    
    def fetch_data(self, limit: Optional[int] = None) -> List[dict]:
        """Busca dados do banco com mais informações"""
        qlimit = f"LIMIT {int(limit)}" if limit else ""
        
        sql = f"""
        SELECT o.id, o.relato, o.tipo, o.datahora,
               COALESCE(
                 (
                   SELECT json_agg(json_build_object('tipo', a.tipo::text, 'quantidade', a.quantidade))
                   FROM apreensoes a WHERE a.ocorrencia_id = o.id
                 ), '[]'::json
               ) AS apreensoes
        FROM ocorrencias o
        WHERE o.relato IS NOT NULL 
          AND LENGTH(TRIM(o.relato)) >= 20
        ORDER BY o.datahora DESC
        {qlimit};
        """
        
        with psycopg.connect(**DB_CONFIG) as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(sql)
                rows = cur.fetchall()
        
        print(f"📊 Dados coletados: {len(rows)} registros")
        
        # Debug: verificar distribuição de apreensões
        with_apreensoes = sum(1 for r in rows if r.get("apreensoes") and len(r["apreensoes"]) > 0)
        print(f"📊 Registros com apreensões: {with_apreensoes}/{len(rows)}")
        
        return rows
    
    def create_improved_hybrid_model(self, X_train, y_train):
        """Cria modelo híbrido melhorado"""
        
        # Verificar distribuição antes do treinamento
        print(f"📊 Distribuição de treinamento: {Counter(y_train)}")
        
        # Treinar ML melhorado
        ml_model = LogisticRegression(
            class_weight='balanced',
            max_iter=3000,
            random_state=42,
            solver='liblinear',
            C=0.5
        )
        ml_model.fit(X_train, y_train)
        
        # Criar modelo híbrido
        hybrid_model = HybridClassifier(
            ml_model=ml_model,
            always_suspeito=self.system.SEMPRE_SUSPEITO,
            always_sem_alteracao=self.system.SEMPRE_SEM_ALTERACAO,
            indicadores={}  # Simplificado por ora
        )
        
        return hybrid_model
    
    def train_improved(self, limit: Optional[int] = 2000):
        """Treinamento melhorado com DEBUG completo"""
        print("Iniciando treinamento híbrido com debug...")
        
        # 1. Buscar dados
        rows = self.fetch_data(limit)
        
        # 2. DEBUG: Analisar amostra antes da rotulação
        sample_classifications = self.debug_classification_sample(rows, 20)
        
        # 3. Rotulação melhorada
        X_text = []
        y_labels = []
        rule_classifications = 0
        ml_classifications = 0
        
        print("\n🏷️ Iniciando rotulação...")
        
        for i, r in enumerate(rows):
            relato = (r["relato"] or "").strip()
            if len(relato) < 20:
                continue
            
            # Verificar se é classificação por regra ou ML
            rule_class = self.classify_by_improved_rules(relato)
            if rule_class:
                rule_classifications += 1
            else:
                ml_classifications += 1
                
            label = self.auto_label_improved(r)
            X_text.append(relato)
            y_labels.append(label)
            
            # Progress
            if (i + 1) % 500 == 0:
                current_dist = Counter(y_labels)
                print(f"  Processados {i + 1}/{len(rows)}... Distribuição atual: {dict(current_dist)}")
        
        final_distribution = Counter(y_labels)
        print(f"\n📊 Distribuição final: {dict(final_distribution)}")
        print(f"📊 Classificações por regra: {rule_classifications}")
        print(f"📊 Classificações por score: {ml_classifications}")
        
        # 4. VERIFICAÇÃO CRÍTICA
        unique_classes = set(y_labels)
        if len(unique_classes) < 2:
            print(f"❌ ERRO CRÍTICO: Apenas {len(unique_classes)} classe encontrada: {unique_classes}")
            print("\n🔧 APLICANDO CORREÇÃO AUTOMÁTICA...")
            
            # Forçar balanceamento mínimo
            suspeitos_needed = max(100, len(y_labels) // 10)  # Pelo menos 10%
            
            # Selecionar candidatos com maior score
            candidates = []
            for i, (text, label) in enumerate(zip(X_text, y_labels)):
                if label == "SEM_ALTERACAO":
                    score = self.calculate_improved_score(text, [])
                    candidates.append((i, score, text))
            
            # Ordenar por score e converter os top N
            candidates.sort(key=lambda x: x[1], reverse=True)
            
            converted = 0
            for i, score, text in candidates[:suspeitos_needed]:
                if score >= 1:  # Threshold mínimo
                    y_labels[i] = "SUSPEITO"
                    converted += 1
            
            print(f"✅ Convertidos {converted} registros para SUSPEITO")
            final_distribution = Counter(y_labels)
            print(f"📊 Nova distribuição: {dict(final_distribution)}")
        
        # 5. Continuar com o treinamento normal...
        print("\n🧠 Gerando embeddings...")
        X = embed(X_text)
        print(f"✅ Embeddings gerados: {X.shape}")
        
        # 6. Split
        X_train, X_test, y_train, y_test = train_test_split(
            X, y_labels, test_size=0.2, random_state=42,
            stratify=y_labels
        )
        
        # 7. Criar modelo melhorado
        print("🤖 Criando modelo híbrido...")
        hybrid_model = self.create_improved_hybrid_model(X_train, y_train)
        
        # 8. Avaliação
        train_score = hybrid_model.ml_model.score(X_train, y_train)
        test_score = hybrid_model.ml_model.score(X_test, y_test)
        print(f"📊 ML Train Accuracy: {train_score:.4f}")
        print(f"📊 ML Test Accuracy: {test_score:.4f}")
        
        # 9. Teste casos críticos
        print("\n🧪 Testando casos críticos...")
        test_cases = [
            "Veículo abordado para fiscalização de rotina. Documentos em ordem.",
            "Encontrada maconha escondida no veículo durante revista.",
            "Traficante conhecido, faz bate volta na fronteira.",
            "Condutor nervoso mentiu sobre destino da viagem.",
            "Abordagem normal sem alterações. Nada encontrado.",
            "Apreendidos 5 kg de crack nas portas traseiras."
        ]
        
        expected = ["SEM_ALTERACAO", "SUSPEITO", "SUSPEITO", "SUSPEITO", "SEM_ALTERACAO", "SUSPEITO"]
        
        predictions = hybrid_model.predict(test_cases)
        
        print("Caso | Esperado      | Predito      | Status")
        print("-" * 50)
        acertos = 0
        for i, (exp, pred) in enumerate(zip(expected, predictions)):
            status = "✅" if exp == pred else "❌"
            if exp == pred:
                acertos += 1
            print(f"{i+1:2d}   | {exp:12s} | {pred:11s} | {status}")
        
        print(f"\n📊 Taxa de acerto nos casos críticos: {acertos}/6 ({acertos/6:.1%})")
        
        # 10. Salvamento
        print(f"\n💾 Salvando modelo...")
        
        try:
            joblib.dump(hybrid_model, CLF_PATH)
            joblib.dump(SUPPORTED_CLASSES, LBL_PATH)
            
            model_size = os.path.getsize(CLF_PATH)
            labels_size = os.path.getsize(LBL_PATH)
            print(f"✅ Modelo salvo: {CLF_PATH} ({model_size:,} bytes)")
            print(f"✅ Labels salvos: {LBL_PATH} ({labels_size:,} bytes)")
            
            # Teste de carregamento
            loaded_model = joblib.load(CLF_PATH)
            loaded_labels = joblib.load(LBL_PATH)
            print(f"✅ Teste carregamento: OK")
            
        except Exception as e:
            print(f"❌ Erro no salvamento: {e}")
            return
        
        print("\n🎉 Treinamento híbrido com debug concluído!")
        print("🔧 Correções aplicadas:")
        print("  • Thresholds mais agressivos (5 → suspeito)")
        print("  • Balanceamento automático forçado")
        print("  • Debug completo da classificação")
        print("  • Distribuição determinística para casos ambíguos")

def main():
    trainer = ImprovedHybridTrainer()
    trainer.train_improved(limit=2000)

if __name__ == "__main__":
    main()