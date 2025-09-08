#!/usr/bin/env python3
# verificar_dados_treino.py - Verifica se há dados suficientes para treinar o modelo semântico

import psycopg
from psycopg.rows import dict_row
from database import DB_CONFIG

def verificar_dados_treino():
    """Verifica a quantidade e qualidade dos dados disponíveis para treino."""
    
    try:
        with psycopg.connect(**DB_CONFIG) as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                # Conta total de relatos
                cur.execute("SELECT COUNT(*) as total FROM ocorrencias WHERE relato IS NOT NULL AND relato <> '';")
                total_relatos = cur.fetchone()['total']
                
                print(f"📊 Total de relatos disponíveis: {total_relatos}")
                
                if total_relatos < 100:
                    print("⚠️  AVISO: Poucos dados para treino. Recomendado pelo menos 100 relatos.")
                    print("   Execute 'python popular_banco.py' para gerar mais dados de treino.")
                    return False
                
                # Verifica distribuição de dados por tipo
                cur.execute("""
                    SELECT tipo, COUNT(*) as count 
                    FROM ocorrencias 
                    WHERE relato IS NOT NULL AND relato <> ''
                    GROUP BY tipo 
                    ORDER BY count DESC;
                """)
                tipos = cur.fetchall()
                
                print("\n📈 Distribuição por tipo de ocorrência:")
                for tipo in tipos:
                    print(f"   {tipo['tipo']}: {tipo['count']} relatos")
                
                # Verifica relatos com apreensões
                cur.execute("""
                    SELECT COUNT(DISTINCT o.id) as count
                    FROM ocorrencias o
                    JOIN apreensoes a ON o.id = a.ocorrencia_id
                    WHERE o.relato IS NOT NULL AND o.relato <> '';
                """)
                com_apreensoes = cur.fetchone()['count']
                
                print(f"\n🔍 Relatos com apreensões: {com_apreensoes}")
                
                # Mostra alguns exemplos de relatos
                cur.execute("""
                    SELECT relato, tipo
                    FROM ocorrencias 
                    WHERE relato IS NOT NULL AND relato <> ''
                    ORDER BY RANDOM()
                    LIMIT 3;
                """)
                exemplos = cur.fetchall()
                
                print("\n📝 Exemplos de relatos:")
                for i, exemplo in enumerate(exemplos, 1):
                    relato_preview = exemplo['relato'][:100] + "..." if len(exemplo['relato']) > 100 else exemplo['relato']
                    print(f"   {i}. [{exemplo['tipo']}] {relato_preview}")
                
                return True
                
    except Exception as e:
        print(f"❌ Erro ao verificar dados: {e}")
        return False

def verificar_dependencias():
    """Verifica se as dependências necessárias estão instaladas."""
    
    dependencias = [
        'spacy', 'sentence_transformers', 'sklearn', 
        'yake', 'numpy', 'pandas', 'joblib'
    ]
    
    print("\n🔧 Verificando dependências:")
    faltando = []
    
    for dep in dependencias:
        try:
            __import__(dep)
            print(f"   ✅ {dep}")
        except ImportError:
            print(f"   ❌ {dep} - NÃO INSTALADO")
            faltando.append(dep)
    
    if faltando:
        print(f"\n⚠️  Instale as dependências faltando:")
        print(f"   pip install {' '.join(faltando)}")
        return False
    
    return True

def verificar_modelo_spacy():
    """Verifica se o modelo de português do spaCy está disponível."""
    
    try:
        import spacy
        nlp = spacy.load("pt_core_news_lg")
        print("✅ Modelo pt_core_news_lg do spaCy disponível")
        return True
    except OSError:
        print("❌ Modelo pt_core_news_lg não encontrado")
        print("   Instale com: python -m spacy download pt_core_news_lg")
        return False

if __name__ == "__main__":
    print("🔍 Verificando ambiente para treino semântico...\n")
    
    dados_ok = verificar_dados_treino()
    deps_ok = verificar_dependencias()
    spacy_ok = verificar_modelo_spacy()
    
    print("\n" + "="*60)
    
    if dados_ok and deps_ok and spacy_ok:
        print("✅ Ambiente pronto para treinar o modelo semântico!")
        print("   Execute: python train_semantic.py")
    else:
        print("⚠️  Corrija os problemas acima antes de treinar.")
