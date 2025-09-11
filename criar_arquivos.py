#!/usr/bin/env python3
# criar_arquivos.py - Cria os arquivos de configuração

import os

# Conteúdo das palavras suspeitas
palavras_suspeitas = """# Palavras e expressões que indicam atividade suspeita
# Uma por linha, use # para comentários

# Drogas
maconha
skunk
cocaina
crack
droga
pó
erva
entorpecente
traficante
trafico

# Armas
arma
revolver
pistola
munição
fuzil
porte ilegal
porte

# Comportamento suspeito
mentiu
contradicao
nervoso
agressivo
entrevista ruim
não soube explicar
historia estranha
atitude suspeita
comportamento hostil
visitar tia
EC ruim
mentiu
tem passagem
tem ocorrências
preso

# Locais/situações
fronteira
bate volta
madrugada
evasão
fuga

# Dinheiro/objetos
dinheiro em espécie
grande quantidade
sem justificativa
origem duvidosa"""

# Conteúdo das palavras normais
palavras_normais = """# Palavras e expressões que indicam situações normais
# Uma por linha, use # para comentários

# Família e relacionamentos
família
ferias
parentes
visitar
passeando
viagem
turismo

# Trabalho
trabalho
emprego
serviço
empresa
reuniao
cliente

# Situações cotidianas
documentação em ordem
sem irregularidade
liberado
rotina
normal
regular
conforme

# Emergências/problemas mecânicos
pane
quebrou
problema mecânico
socorro
emergência
hospital

# Cooperação
colaborou
educado
prestativo
cordial
respeitoso"""

def main():
    # Cria diretório config se não existir
    os.makedirs("config", exist_ok=True)
    
    # Cria arquivo de palavras suspeitas
    with open("config/palavras_suspeitas.txt", "w", encoding="utf-8") as f:
        f.write(palavras_suspeitas)
    
    # Cria arquivo de palavras normais
    with open("config/palavras_normais.txt", "w", encoding="utf-8") as f:
        f.write(palavras_normais)
    
    print("Arquivos criados:")
    print("- config/palavras_suspeitas.txt")
    print("- config/palavras_normais.txt")
    print("\nAgora execute: python train_semantic.py")

if __name__ == "__main__":
    main()
