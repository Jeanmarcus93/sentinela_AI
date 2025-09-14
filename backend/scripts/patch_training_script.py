#!/usr/bin/env python3
# backend/scripts/patch_semantic_training.py
"""
Script para corrigir rapidamente o treinamento semântico
Remove dependência da coluna classificacao_manual
"""

import os
from pathlib import Path

def patch_training_file():
    """Aplica correção no arquivo de treinamento"""
    
    project_root = Path(__file__).parent.parent
    training_file = project_root / "ml_models" / "training" / "train_semantic_agents.py"
    
    if not training_file.exists():
        print(f"❌ Arquivo não encontrado: {training_file}")
        return False
    
    print(f"🔧 Aplicando correção em: {training_file}")
    
    # Ler arquivo original
    with open(training_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Encontrar e substituir o método load_training_data
    old_method_start = 'def load_training_data(self) -> Tuple[List[str], List[str]]:'
    old_method_end = 'return textos, labels'
    
    # Novo método corrigido
    new_method = '''def load_training_data(self) -> Tuple[List[str], List[str]]:
        """
        Carrega dados de treinamento do banco de dados
        Versão adaptada - trabalha sem classificacao_manual (será implementada no futuro)
        """
        print("🔄 Carregando dados de treinamento...")
        
        textos = []
        labels = []
        
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    # Query adaptada - sem classificacao_manual por enquanto
                    cur.execute("""
                        SELECT relato 
                        FROM ocorrencias 
                        WHERE relato IS NOT NULL 
                        AND LENGTH(TRIM(relato)) > 20
                        ORDER BY data_ocorrencia DESC
                        LIMIT 5000
                    """)
                    
                    rows = cur.fetchall()
                    
            print(f"📊 Encontrados {len(rows)} registros")
            
            # Processar dados com classificação automática inteligente
            print("🤖 Aplicando classificação automática baseada em regras...")
            print("   (No futuro, classificacao_manual será usada para feedback)")
            
            for i, (relato,) in enumerate(rows):
                if not relato or len(relato.strip()) < 20:
                    continue
                    
                texto_limpo = relato.strip()
                textos.append(texto_limpo)
                
                # Classificação automática usando regras inteligentes
                label, confidence, metadata = self.classifier.classify_text_binary(texto_limpo)
                labels.append(label)
                    
                # Mostrar progresso a cada 500 registros
                if (i + 1) % 500 == 0:
                    current_suspicious = sum(1 for l in labels if l == "SUSPEITO")
                    current_normal = len(labels) - current_suspicious
                    print(f"   Processados {i + 1}/{len(rows)} | "
                          f"SUSPEITO: {current_suspicious} | "
                          f"SEM_ALTERACAO: {current_normal}")
                    
        except Exception as e:
            print(f"❌ Erro ao carregar dados: {e}")
            import traceback
            traceback.print_exc()
            return [], []
            
        # Estatísticas finais
        from collections import Counter
        label_counts = Counter(labels)
        print(f"\\n📈 Distribuição das classes (classificação automática):")
        for label, count in label_counts.items():
            percentage = (count / len(labels)) * 100
            print(f"   {label}: {count} ({percentage:.1f}%)")
        
        # Verificar qualidade dos dados
        total_samples = len(labels)
        if total_samples < 50:
            print("⚠️ Poucos dados para treinamento")
            return textos, labels
            
        # Verificar balanceamento
        min_class_size = min(label_counts.values()) if label_counts else 0
        
        if min_class_size < 10:
            print("⚠️ Classe minoritária com poucos exemplos, adicionando casos sintéticos...")
            textos, labels = self._balance_with_synthetic_examples(textos, labels, label_counts)
            
            # Atualizar estatísticas
            label_counts = Counter(labels)
            print(f"📊 Distribuição após balanceamento:")
            for label, count in label_counts.items():
                percentage = (count / len(labels)) * 100
                print(f"   {label}: {count} ({percentage:.1f}%)")
        
        print(f"✅ Dataset preparado: {len(labels)} amostras totais")
        return textos, labels
    
    def _balance_with_synthetic_examples(self, textos: List[str], labels: List[str], 
                                       current_counts: Counter) -> Tuple[List[str], List[str]]:
        """
        Adiciona exemplos sintéticos para balancear classes
        Serão substituídos por feedback real no futuro
        """
        print("   🔧 Balanceando dataset com exemplos sintéticos...")
        
        # Determinar classe minoritária
        minority_class = min(current_counts, key=current_counts.get)
        minority_count = current_counts[minority_class]
        majority_count = max(current_counts.values())
        
        # Calcular quantos exemplos adicionar (máximo 30% do dataset)
        target_minority = min(majority_count // 2, minority_count + 50)
        examples_needed = max(0, target_minority - minority_count)
        
        print(f"   📊 Classe minoritária: {minority_class} ({minority_count} exemplos)")
        print(f"   📊 Adicionando {examples_needed} exemplos sintéticos")
        
        if minority_class == "SUSPEITO":
            synthetic_examples = [
                "O indivíduo foi encontrado com substância entorpecente durante abordagem policial na região central",
                "Confessou estar envolvido com tráfico de drogas há alguns meses na comunidade local",
                "Foi preso em flagrante portando arma de fogo sem documentação legal",
                "Portava material entorpecente dividido em pequenas porções características de venda",
                "Assumiu a participação em crimes contra o patrimônio na região",
                "Foi encontrado com grande quantidade de dinheiro sem comprovação de origem lícita",
                "Portava arma branca e demonstrou atitude agressiva durante abordagem",
                "Confessou participação em esquema criminoso envolvendo outros indivíduos",
                "Estava em posse de objetos com indícios de origem criminosa",
                "Demonstrou conhecimento detalhado sobre atividades ilícitas locais"
            ]
        else:
            synthetic_examples = [
                "Estava retornando do trabalho quando foi abordado pela equipe policial",
                "Colaborou plenamente com a investigação e forneceu todas as informações solicitadas",
                "Apresentou documentação completa e comprovou sua identificação",
                "Reside na região há vários anos e possui referências na comunidade",
                "Trabalha regularmente e não possui antecedentes criminais",
                "Demonstrou transparência total durante todo o procedimento policial",
                "Estava acompanhado de familiares no momento da abordagem",
                "Forneceu informações precisas sobre sua rotina e atividades",
                "Demonstrou cooperação e respeito durante toda a ocorrência",
                "Possui emprego formal e comprovou sua situação profissional"
            ]
        
        # Adicionar exemplos necessários
        examples_to_add = []
        labels_to_add = []
        
        for i in range(examples_needed):
            example = synthetic_examples[i % len(synthetic_examples)]
            if i >= len(synthetic_examples):
                example = f"{example} durante procedimento de rotina"
            
            examples_to_add.append(example)
            labels_to_add.append(minority_class)
        
        # Adicionar ao dataset
        textos.extend(examples_to_add)
        labels.extend(labels_to_add)
        
        print(f"   ✅ {len(examples_to_add)} exemplos sintéticos adicionados")
        print("   💡 No futuro, estes serão substituídos por feedback manual dos usuários")
        
        return textos, labels'''
    
    # Encontrar posição do método antigo
    start_pos = content.find(old_method_start)
    if start_pos == -1:
        print("❌ Método load_training_data não encontrado")
        return False
    
    # Encontrar o final do método (próximo def ou fim da classe)
    lines = content[start_pos:].split('\n')
    method_lines = []
    indent_level = None
    
    for i, line in enumerate(lines):
        if i == 0:  # Primeira linha (def load_training_data)
            method_lines.append(line)
            # Determinar nível de indentação
            indent_level = len(line) - len(line.lstrip())
            continue
            
        # Se linha não está vazia e não tem indentação maior que o método, terminou
        if line.strip() and len(line) - len(line.lstrip()) <= indent_level and line.strip().startswith('def '):
            break
            
        method_lines.append(line)
        
        # Se chegou no return final, incluir e parar
        if 'return textos, labels' in line:
            break
    
    old_method_full = '\n'.join(method_lines)
    end_pos = start_pos + len(old_method_full)
    
    # Substituir método
    new_content = content[:start_pos] + new_method + content[end_pos:]
    
    # Fazer backup
    backup_file = training_file.with_suffix('.py.backup')
    with open(backup_file, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"📋 Backup criado: {backup_file}")
    
    # Escrever arquivo corrigido
    with open(training_file, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print("✅ Correção aplicada com sucesso!")
    print("💡 O arquivo agora funciona sem classificacao_manual")
    print("🔮 No futuro, quando implementarmos feedback do usuário,")
    print("   a coluna classificacao_manual será adicionada e utilizada")
    
    return True

if __name__ == "__main__":
    print("🔧 CORREÇÃO DO SISTEMA DE TREINAMENTO SEMÂNTICO")
    print("="*50)
    print("Adaptando para trabalhar sem classificacao_manual")
    print("(Preparando para implementação futura de feedback)")
    print("="*50)
    
    if patch_training_file():
        print("\n🎉 Correção aplicada! Agora você pode executar:")
        print("   python ml_models/training/train_semantic_agents.py")
    else:
        print("\n❌ Falha na correção. Verifique o arquivo manualmente.")
