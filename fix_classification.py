# fix_classification.py - Corrige o problema de classificação

def fix_auto_label():
    with open("train_semantic.py", "r", encoding="utf-8") as f:
        content = f.read()
    
    # Substitui a função auto_label por uma versão mais agressiva
    new_auto_label = '''def auto_label_configuravel(row, config, palavras_suspeitas, palavras_normais):
    """Classificação mais agressiva para capturar suspeitos"""
    relato = (row.get("relato") or "").lower()
    
    # Verifica apreensões
    if row.get("apreensoes"):
        if any(a["tipo"] in ("Maconha", "Skunk", "Cocaina", "Crack", "Sintéticos", "Arma") 
               for a in row["apreensoes"]):
            return "SUSPEITO"
    
    # PALAVRAS CRÍTICAS - sempre suspeito
    criticas = ["traficante", "traficantes", "maconha", "cocaina", "crack", "arma", "revolver", "pistola"]
    for critica in criticas:
        if critica in relato:
            return "SUSPEITO"
    
    # COMBINAÇÕES SUSPEITAS - sempre suspeito  
    combinacoes = [
        ("fronteira", "viaj"), ("mentiu", "motivo"), ("ec ruim", ""), 
        ("nervoso", "viagem"), ("contradicao", ""), ("agressivo", ""),
        ("entrevista ruim", ""), ("atitude suspeita", "")
    ]
    
    for palavra1, palavra2 in combinacoes:
        if palavra1 in relato and (not palavra2 or palavra2 in relato):
            return "SUSPEITO"
    
    # PALAVRAS PROTEGIDAS - sempre normal
    protegidas = ["família", "ferias", "trabalho", "documentação em ordem", "sem irregularidade"]
    for protegida in protegidas:
        if protegida in relato:
            return "SEM_ALTERACAO"
    
    # Conta indicadores suspeitos
    score_suspeito = 0
    for palavra in palavras_suspeitas:
        if palavra.lower() in relato:
            score_suspeito += 1
    
    # Conta indicadores normais
    score_normal = 0
    for palavra in palavras_normais:
        if palavra.lower() in relato:
            score_normal += 1
    
    # DECISÃO FINAL - mais agressiva
    if score_suspeito >= 1 and score_normal == 0:
        return "SUSPEITO"
    elif score_suspeito >= 2:
        return "SUSPEITO"
    elif score_normal > score_suspeito:
        return "SEM_ALTERACAO"
    else:
        return "SEM_ALTERACAO"'''
    
    import re
    # Substitui a função antiga
    pattern = r'def auto_label_configuravel\(row, config, palavras_suspeitas, palavras_normais\):.*?return "SEM_ALTERACAO"'
    content = re.sub(pattern, new_auto_label, content, flags=re.DOTALL)
    
    with open("train_semantic.py", "w", encoding="utf-8") as f:
        f.write(content)
    
    print("Classificação corrigida! Execute: python train_semantic.py")

if __name__ == "__main__":
    fix_auto_label()
