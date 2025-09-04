import joblib
import os
import sys
import numpy as np
import re
import traceback

# Garante que a raiz do projeto esteja no sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# USAR semantic_local ALINHADO
try:
    from semantic_local import embed, CLF_PATH, LBL_PATH, analyze_text
    print("✅ Módulo semantic_local importado com sucesso")
except ImportError as e:
    print(f"❌ Erro ao importar semantic_local: {e}")
    sys.exit(1)

# INDICADORES ALINHADOS COM O MODELO HÍBRIDO
INDICIOS_SUSPEITA = {
    "alto_risco": [
        "apreendido", "encontrado", "portando", "escondido",
        "maconha", "cocaina", "crack", "skunk", "droga",
        "arma", "revolver", "pistola", "municao",
        "fugiu", "resistiu", "tentou escapar", "jogou fora",
        "trafico", "traficante", "receptacao", "roubo", "assalto"
    ],
    "medio_risco": [
        "nervoso", "inquieto", "agitado", "evasivo",
        "contradicao", "mentiu", "nao soube explicar", "nao soube dizer",
        "nao soube justificar", "madrugada", "horario suspeito", 
        "antecedentes", "denuncia", "informacao",
        "fronteira", "bate volta", "bate e volta", "rota conhecida",
        "dinheiro em especie", "quantia elevada",
        "historia estranha", "relato estranho"
    ],
    "baixo_risco": [
        "desconfianca", "suspeita", "atencao", "verificacao",
        "checagem", "consulta", "sem motivo aparente", "nao justificou",
        "historia confusa", "relato inconsistente"
    ],
    "reducao": [
        "liberado", "sem alteracao", "tudo ok", "normal",
        "documentos em ordem", "nada encontrado", "rotina",
        "fiscalizacao de rotina", "abordagem normal", "cooperativo",
        "tranquilo", "justificou adequadamente", "motivo plausivel"
    ]
}

def verificar_arquivos_modelo():
    """Verifica se os arquivos do modelo híbrido existem"""
    print("🔍 Verificando arquivos do modelo híbrido...")
    
    if not os.path.exists(CLF_PATH):
        print(f"❌ Arquivo do modelo não encontrado: {CLF_PATH}")
        print("Execute 'python train_semantic.py' primeiro.")
        return False
        
    if not os.path.exists(LBL_PATH):
        print(f"❌ Arquivo de labels não encontrado: {LBL_PATH}")
        print("Execute 'python train_semantic.py' primeiro.")
        return False
    
    try:
        clf_size = os.path.getsize(CLF_PATH)
        lbl_size = os.path.getsize(LBL_PATH)
        
        print(f"✅ Arquivo do modelo: {clf_size:,} bytes")
        print(f"✅ Arquivo de labels: {lbl_size:,} bytes")
        
        if clf_size < 1000:
            print("⚠️ AVISO: Arquivo do modelo muito pequeno!")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ Erro ao verificar arquivos: {e}")
        return False

def carregar_modelo_hibrido():
    """Carrega o modelo híbrido"""
    
    if not verificar_arquivos_modelo():
        print("\n" + "="*80)
        print("❌ ERRO: Problemas com os arquivos do modelo!")
        print("Execute 'python train_semantic.py' para retreinar o modelo.")
        print("="*80)
        return None, None
    
    try:
        print("\n📦 Carregando modelo híbrido...")
        clf = joblib.load(CLF_PATH)
        print("✅ Modelo carregado com sucesso")
        
        print("📦 Carregando labels...")
        labels = joblib.load(LBL_PATH)
        print("✅ Labels carregados com sucesso")
        
        # Verificar se é modelo híbrido
        if hasattr(clf, 'classify_by_rules'):
            print("🤖 Modelo híbrido detectado (Regras + ML)")
        else:
            print("🧠 Modelo ML tradicional detectado")
        
        print(f"📊 Classes disponíveis: {labels}")
        return clf, labels
        
    except Exception as e:
        print(f"❌ Erro ao carregar modelo: {e}")
        traceback.print_exc()
        return None, None

def encontrar_motivacoes(relato: str) -> dict:
    """Encontra indícios por categoria no relato"""
    motivacoes = {"alto_risco": [], "medio_risco": [], "baixo_risco": [], "reducao": []}
    relato_lower = relato.lower()
    
    for categoria, termos in INDICIOS_SUSPEITA.items():
        for indicio in termos:
            # Busca flexível - palavra completa ou parte da expressão
            if indicio in relato_lower or any(word in relato_lower for word in indicio.split()):
                motivacoes[categoria].append(indicio)
    
    return motivacoes

def calcular_score_manual(relato: str) -> tuple[float, dict]:
    """Calcula score manual baseado nos indícios"""
    motivacoes = encontrar_motivacoes(relato)
    
    score = 0
    pesos = {"alto_risco": 3, "medio_risco": 2, "baixo_risco": 1, "reducao": -2}
    
    for categoria, termos in motivacoes.items():
        score += len(termos) * pesos[categoria]
    
    return score, motivacoes

def classificar_hibrido(clf, labels, relato):
    """Classificação usando modelo híbrido"""
    
    try:
        # Usar análise completa do semantic_local
        resultado = analyze_text(relato)
        
        classificacao = resultado["classe"]
        confianca = resultado["pontuacao"] / 100.0  # Converter para 0-1
        
        # Extrair probabilidades
        probs = resultado.get("probs", {})
        
        # Garantir que temos as probabilidades corretas
        if "SEM_ALTERACAO" not in probs:
            # Fallback se não tiver probabilidades
            if classificacao == "SUSPEITO":
                probs = {"SEM_ALTERACAO": 1-confianca, "SUSPEITO": confianca}
            else:
                probs = {"SEM_ALTERACAO": confianca, "SUSPEITO": 1-confianca}
        
        return classificacao, {
            "SEM_ALTERACAO": probs.get("SEM_ALTERACAO", 0.5),
            "SUSPEITO": probs.get("SUSPEITO", 0.5),
            "confianca": confianca,
            "method": resultado.get("method", "unknown")
        }
        
    except Exception as e:
        print(f"Erro na classificação híbrida: {e}")
        return None, None

def testar_modelo_hibrido(clf, labels):
    """Testa modelo híbrido com casos de validação"""
    print("\n🧪 Executando teste do modelo híbrido...")
    
    exemplos_teste = [
        ("Veículo abordado para fiscalização de rotina. Documentos em ordem.", "SEM_ALTERACAO"),
        ("Durante revista encontrada maconha escondida no painel.", "SUSPEITO"),
        ("Condutor nervoso mentiu sobre destino da viagem.", "SUSPEITO"),
        ("Abordagem normal sem alterações. Liberado após verificação.", "SEM_ALTERACAO"),
        ("Traficante conhecido, faz bate volta na fronteira.", "SUSPEITO"),
        ("História estranha, não soube explicar origem da viagem.", "SUSPEITO")
    ]
    
    try:
        acertos = 0
        print("\nCaso | Esperado      | Predito       | Conf. | Método | Status")
        print("-" * 70)
        
        for i, (exemplo, esperado) in enumerate(exemplos_teste, 1):
            classificacao, resultado = classificar_hibrido(clf, labels, exemplo)
            
            if classificacao is None:
                print(f"{i:2d}   | {esperado:12s} | ERRO         | -     | -      | ❌")
                continue
            
            status = "✅" if classificacao == esperado else "❌"
            if classificacao == esperado:
                acertos += 1
            
            metodo = resultado.get("method", "?")[:6]
            confianca = resultado["confianca"]
            
            print(f"{i:2d}   | {esperado:12s} | {classificacao:12s} | {confianca:.3f} | {metodo:6s} | {status}")
        
        taxa_acerto = acertos / len(exemplos_teste)
        print(f"\n📊 Taxa de acerto: {acertos}/{len(exemplos_teste)} ({taxa_acerto:.1%})")
        
        if taxa_acerto >= 0.83:  # 5/6 ou melhor
            print("✅ Modelo híbrido passou no teste!")
            return True
        else:
            print("⚠️ Modelo com performance baixa no teste")
            return False
            
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        return False

def main():
    """Função principal para teste do modelo híbrido"""
    print("="*80)
    print("🤖 SISTEMA DE ANÁLISE SEMÂNTICA HÍBRIDO 🤖")
    print("="*80)
    
    clf, labels = carregar_modelo_hibrido()
    if not clf or not labels:
        return
    
    # Teste básico
    if not testar_modelo_hibrido(clf, labels):
        print("\n⚠️ Teste básico falhou, mas continuando...")
    
    print("\n" + "="*80)
    print("🔍 MODO DE ANÁLISE INTERATIVA HÍBRIDA")
    print("="*80)
    print("Digite um relato e pressione Enter para análise.")
    print("Comandos especiais:")
    print("  • 'sair' - Encerrar programa")
    print("  • 'exemplo' - Ver exemplos de uso")
    print("  • 'teste' - Executar teste básico")
    print("  • 'analise' - Análise completa com detalhes")

    modo_detalhado = False

    while True:
        try:
            relato_usuario = input("\n> Digite o relato: ").strip()
            
            if relato_usuario.lower() in ['sair', 'exit', 'quit']:
                print("👋 Encerrando...")
                break
                
            if relato_usuario.lower() in ['exemplo', 'exemplos']:
                print("\n📝 EXEMPLOS DE RELATOS:")
                print("1. 'Fiscalização de rotina, documentos em ordem'")
                print("2. 'Encontrada maconha escondida no veículo'") 
                print("3. 'Condutor nervoso, história estranha'")
                print("4. 'Traficante conhecido da região'")
                print("5. 'Abordagem normal, nada encontrado'")
                continue
                
            if relato_usuario.lower() == 'teste':
                testar_modelo_hibrido(clf, labels)
                continue
                
            if relato_usuario.lower() == 'analise':
                modo_detalhado = not modo_detalhado
                print(f"🔧 Modo detalhado: {'ATIVADO' if modo_detalhado else 'DESATIVADO'}")
                continue
                
            if not relato_usuario:
                continue

            # Análise híbrida
            print("\n🔄 Processando com modelo híbrido...")
            
            if modo_detalhado:
                # Análise completa
                resultado_completo = analyze_text(relato_usuario)
                classificacao = resultado_completo["classe"]
                confianca = resultado_completo["pontuacao"] / 100.0
                method = resultado_completo.get("method", "unknown")
                
                # Score manual para comparação
                score_manual, motivacoes = calcular_score_manual(relato_usuario)
                
                # Resultado detalhado
                print("\n" + "="*70)
                print("📊 ANÁLISE HÍBRIDA DETALHADA")
                print("="*70)
                
                cor = "\033[92m" if classificacao == "SEM_ALTERACAO" else "\033[91m"
                print(f"🎯 CLASSIFICAÇÃO: {cor}{classificacao}\033[0m")
                print(f"🔍 CONFIANÇA: {confianca:.1%}")
                print(f"🤖 MÉTODO: {method.upper()}")
                
                if "probs" in resultado_completo:
                    print(f"\n📈 PROBABILIDADES:")
                    for classe, prob in resultado_completo["probs"].items():
                        barra = "█" * int(prob * 20)
                        print(f"  {classe:15}: {prob*100:5.1f}% {barra}")
                
                print(f"\n🔢 SCORE MANUAL: {score_manual} pontos")
                
                # Indicadores detectados
                if resultado_completo.get("indicadores"):
                    print(f"\n🔍 INDICADORES AUTOMÁTICOS:")
                    ind = resultado_completo["indicadores"]
                    for key, value in ind.items():
                        if value > 0:
                            print(f"  • {key}: {value}")
                
                # Palavras-chave se disponíveis
                if resultado_completo.get("keywords"):
                    print(f"\n🔑 PALAVRAS-CHAVE:")
                    for kw in resultado_completo["keywords"][:5]:
                        print(f"  • {kw['term']} (score: {kw['score']:.3f})")
                        
            else:
                # Análise simples
                classificacao, resultado = classificar_hibrido(clf, labels, relato_usuario)
                
                if not classificacao:
                    print("❌ Erro na classificação")
                    continue
                
                score_manual, motivacoes = calcular_score_manual(relato_usuario)
                
                print("\n" + "="*60)
                print("📊 RESULTADO DA ANÁLISE HÍBRIDA")
                print("="*60)
                
                cor = "\033[92m" if classificacao == "SEM_ALTERACAO" else "\033[91m"
                print(f"🎯 CLASSIFICAÇÃO: {cor}{classificacao}\033[0m")
                print(f"🔍 CONFIANÇA: {resultado['confianca']:.1%}")
                print(f"🤖 MÉTODO: {resultado.get('method', 'unknown').upper()}")
                
                print(f"\n📈 PROBABILIDADES:")
                for classe in ["SEM_ALTERACAO", "SUSPEITO"]:
                    prob = resultado[classe]
                    barra = "█" * int(prob * 20)
                    print(f"  {classe:15}: {prob*100:5.1f}% {barra}")
                
                print(f"\n🔢 SCORE MANUAL: {score_manual} pontos")

            # Indícios detectados (comum aos dois modos)
            total_indicios = sum(len(termos) for termos in motivacoes.values())
            if total_indicios > 0:
                print(f"\n🚨 INDÍCIOS DETECTADOS ({total_indicios} total):")
                
                cores = {
                    "alto_risco": "\033[91m",     # Vermelho
                    "medio_risco": "\033[93m",    # Amarelo  
                    "baixo_risco": "\033[96m",    # Ciano
                    "reducao": "\033[92m"         # Verde
                }
                nomes = {
                    "alto_risco": "Alto Risco", 
                    "medio_risco": "Médio Risco", 
                    "baixo_risco": "Baixo Risco",
                    "reducao": "Redução de Suspeita"
                }
                
                for categoria, termos in motivacoes.items():
                    if termos:
                        cor = cores[categoria]
                        nome = nomes[categoria]
                        print(f"  {cor}● {nome}:\033[0m {', '.join(termos[:3])}")
                        if len(termos) > 3:
                            print(f"    ... e mais {len(termos)-3} termos")
            else:
                print("\n📝 ANÁLISE:")
                if classificacao == "SUSPEITO":
                    print("  Modelo híbrido detectou padrão suspeito baseado no contexto geral.")
                else:
                    print("  Nenhum indício de suspeita detectado pelo sistema.")
            
            print("="*(70 if modo_detalhado else 60))

        except KeyboardInterrupt:
            print("\n\n👋 Programa interrompido. Saindo...")
            break
        except Exception as e:
            print(f"\n❌ Erro durante análise: {e}")
            print("Tente novamente ou digite 'sair'.")

if __name__ == "__main__":
    main()