# fix_training.py - Corrige o treinamento para reduzir falsos positivos

import re

def fix_auto_label():
    with open("train_semantic.py", "r", encoding="utf-8") as f:
        content = f.read()
    
    # Substitui a função auto_label por uma versão mais rigorosa
    new_auto_label = '''def auto_label(row) -> str:
    """
    Classificação mais rigorosa: só é SUSPEITO se houver múltiplos indicadores.
    """
    relato = (row.get("relato") or "").lower()

    # Verifica apreensões (indício forte)
    if row.get("apreensoes"):
        if any(a["tipo"] in ("Maconha", "Skunk", "Cocaina", "Crack", "Sintéticos", "Arma") for a in row["apreensoes"]):
            return "SUSPEITO"

    # Lista de indicadores FORTES - precisam de pelo menos 2 para ser suspeito
    indicadores_fortes = [
        "maconha", "skunk", "cocaina", "crack", "droga", "traficante",
        "arma", "revólver", "pistola", "munição", "fronteira",
        "mentiu", "contradição", "nervoso", "agressivo", "entrevista ruim"
    ]
    
    # Conta quantos indicadores fortes existem
    count = sum(1 for ind in indicadores_fortes if ind in relato)
    
    # Palavras que NUNCA devem ser suspeitas
    palavras_normais = [
        "família", "férias", "trabalho", "visitar", "parentes", 
        "documentação em ordem", "sem irregularidade", "liberado"
    ]
    
    # Se tem palavras claramente normais, não é suspeito
    if any(palavra in relato for palavra in palavras_normais):
        return "SEM_ALTERACAO"
    
    # Só é suspeito se tem 2+ indicadores fortes OU 1 indicador muito específico
    if count >= 2 or any(palavra in relato for palavra in ["traficante", "maconha", "cocaina", "crack"]):
        return "SUSPEITO"

    return "SEM_ALTERACAO"'''
    
    # Substitui a função antiga
    pattern = r'def auto_label\(row\) -> str:.*?return "SEM_ALTERACAO"'
    content = re.sub(pattern, new_auto_label, content, flags=re.DOTALL)
    
    with open("train_semantic.py", "w", encoding="utf-8") as f:
        f.write(content)
    
    print("Treinamento corrigido! Re-execute: python train_semantic.py")

if __name__ == "__main__":
    fix_auto_label()
