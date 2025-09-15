# test_feedback.py - SISTEMA DE TESTE
import json
from pathlib import Path
from datetime import datetime

class SimpleClassifier:
    def __init__(self):
        self.threshold = 0.35
        self.palavras_criticas = {'traficante', 'cocaina', 'cocaína', 'crack', 'arma', 'pistola', 'homicidio', 'homicídio', 'flagrante', 'fronteira'}
        self.palavras_suspeitas = {'maconha', 'droga', 'drogas', 'municao', 'munição', 'roubo', 'furto', 'nervoso', 'mentiu'}
    
    def classify(self, texto):
        if not texto:
            return "SEM_ALTERACAO", 0.9
            
        texto_lower = texto.lower()
        score = 0.0
        palavras_encontradas = []
        
        # Palavras críticas (peso 0.4)
        for palavra in self.palavras_criticas:
            if palavra in texto_lower:
                score += 0.4
                palavras_encontradas.append(palavra)
        
        # Palavras suspeitas (peso 0.15)
        for palavra in self.palavras_suspeitas:
            if palavra in texto_lower:
                score += 0.15
                palavras_encontradas.append(palavra)
        
        score = min(score, 1.0)
        
        if score >= self.threshold:
            return "SUSPEITO", score, palavras_encontradas
        else:
            return "SEM_ALTERACAO", 1.0 - score, palavras_encontradas

def main():
    classifier = SimpleClassifier()
    feedbacks = []
    
    print("🎯 SISTEMA DE TESTE SEMÂNTICO - SENTINELA IA")
    print("=" * 55)
    print(f"🔧 Threshold corrigido: {classifier.threshold}")
    print("💡 Digite 'quit' para sair")
    print("=" * 55)
    
    test_count = 0
    
    while True:
        test_count += 1
        print(f"\n📝 TESTE #{test_count}")
        relato = input("👉 Digite o relato para análise: ").strip()
        
        if relato.lower() in ['quit', 'sair', 'exit']:
            break
        if not relato:
            test_count -= 1
            continue
            
        # Classificar
        print("🤖 Analisando...")
        classificacao, confianca, palavras = classifier.classify(relato)
        
        # Mostrar resultado
        emoji = "🔴" if classificacao == "SUSPEITO" else "🟢"
        print(f"\n{'='*60}")
        print(f"📝 RELATO: \"{relato}\"")
        print(f"\n🤖 RESULTADO DA IA:")
        print(f"   {emoji} Classificação: {classificacao}")
        print(f"   📊 Confiança: {confianca:.1%}")
        print(f"   🎯 Score: {confianca:.3f}")
        
        if palavras:
            print(f"   🔍 Palavras detectadas: {', '.join(palavras)}")
        
        # Feedback
        print(f"\n❓ A CLASSIFICAÇÃO ESTÁ CORRETA?")
        print("   1 - ✅ Sim, está correto")
        print("   2 - ❌ Deveria ser SUSPEITO") 
        print("   3 - ❌ Deveria ser SEM_ALTERACAO")
        print("   0 - ⏭️ Pular feedback")
        
        feedback = input("👉 Sua avaliação (1-3, 0 para pular): ").strip()
        
        if feedback == "0":
            print("⏭️ Feedback pulado")
        elif feedback == "1":
            print("🎯 IA ACERTOU!")
            classificacao_correta = classificacao
        elif feedback == "2":
            print("❌ IA ERROU - Deveria ser SUSPEITO")
            classificacao_correta = "SUSPEITO"
        elif feedback == "3":
            print("❌ IA ERROU - Deveria ser SEM_ALTERACAO") 
            classificacao_correta = "SEM_ALTERACAO"
        else:
            print("⚠️ Opção inválida, pulando feedback")
            continue
        
        # Salvar feedback
        if feedback != "0":
            feedbacks.append({
                'relato': relato,
                'ia_classificacao': classificacao,
                'ia_confianca': confianca,
                'classificacao_correta': classificacao_correta,
                'acertou': classificacao == classificacao_correta,
                'palavras_detectadas': palavras,
                'timestamp': datetime.now().isoformat()
            })
            print("✅ Feedback registrado!")
    
    # Resumo final
    if feedbacks:
        total = len(feedbacks)
        acertos = sum(1 for f in feedbacks if f['acertou'])
        acuracia = (acertos / total) * 100
        
        print(f"\n📋 RESUMO DA SESSÃO:")
        print(f"   🧪 Testes realizados: {test_count - 1}")
        print(f"   📝 Feedbacks coletados: {total}")
        print(f"   🎯 Acurácia: {acuracia:.1f}% ({acertos}/{total})")
        
        # Salvar em arquivo
        try:
            with open('feedbacks_semantic.json', 'w', encoding='utf-8') as f:
                json.dump(feedbacks, f, indent=2, ensure_ascii=False)
            print(f"   💾 Feedbacks salvos em: feedbacks_semantic.json")
        except Exception as e:
            print(f"   ❌ Erro ao salvar: {e}")
    
    print("\n👋 Sistema encerrado. Obrigado pelos feedbacks!")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Sistema interrompido pelo usuário")
    except Exception as e:
        print(f"\n❌ Erro: {e}")