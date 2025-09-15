#!/usr/bin/env python3
"""
Script para testar as APIs do Sentinela Treino
Verifica se todas as rotas estão funcionando corretamente
"""

import sys
import requests
import json
from pathlib import Path

# Adicionar o diretório backend ao path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

def test_api_endpoint(base_url, endpoint, method='GET', data=None, expected_status=200):
    """Testa um endpoint da API"""
    url = f"{base_url}{endpoint}"
    
    try:
        if method == 'GET':
            response = requests.get(url, timeout=10)
        elif method == 'POST':
            response = requests.post(url, json=data, timeout=10)
        else:
            print(f"❌ Método {method} não suportado")
            return False
        
        if response.status_code == expected_status:
            print(f"✅ {method} {endpoint} - Status: {response.status_code}")
            return True
        else:
            print(f"❌ {method} {endpoint} - Status: {response.status_code} (esperado: {expected_status})")
            if response.text:
                print(f"   Resposta: {response.text[:200]}...")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ {method} {endpoint} - Erro de conexão: {e}")
        return False
    except Exception as e:
        print(f"❌ {method} {endpoint} - Erro: {e}")
        return False

def test_sentinela_treino_apis():
    """Testa todas as APIs do Sentinela Treino"""
    
    print("🧪 Testando APIs do Sentinela Treino")
    print("=" * 50)
    
    # URL base da API
    base_url = "http://localhost:5000"
    
    # Lista de endpoints para testar
    endpoints = [
        # Endpoints de sistema
        ("/api/treino/health", "GET", None, 200),
        ("/api/treino/info", "GET", None, 200),
        
        # Endpoints de veículos
        ("/api/treino/vehicles/search?q=ABC", "GET", None, 200),
        ("/api/treino/vehicles/search?q=XYZ123", "GET", None, 200),
        
        # Endpoints de análises
        ("/api/treino/analytics", "GET", None, 200),
        ("/api/treino/dashboard", "GET", None, 200),
        ("/api/treino/passages/analytics", "GET", None, 200),
        
        # Endpoints de municípios
        ("/api/treino/municipios", "GET", None, 200),
        
        # Endpoints de exportação
        ("/api/treino/export/vehicles?limit=10", "GET", None, 200),
    ]
    
    # Testar cada endpoint
    success_count = 0
    total_count = len(endpoints)
    
    for endpoint, method, data, expected_status in endpoints:
        if test_api_endpoint(base_url, endpoint, method, data, expected_status):
            success_count += 1
    
    print("\n" + "=" * 50)
    print(f"📊 Resultados: {success_count}/{total_count} endpoints funcionando")
    
    if success_count == total_count:
        print("🎉 Todos os endpoints estão funcionando!")
        return True
    else:
        print("⚠️ Alguns endpoints apresentaram problemas")
        return False

def test_specific_vehicle():
    """Testa busca por um veículo específico"""
    
    print("\n🔍 Testando busca por veículo específico...")
    
    base_url = "http://localhost:5000"
    
    # Primeiro, buscar veículos para obter um ID válido
    try:
        response = requests.get(f"{base_url}/api/treino/vehicles/search?q=ABC&limit=5", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            veiculos = data.get('veiculos', [])
            
            if veiculos:
                # Pegar o primeiro veículo
                veiculo = veiculos[0]
                veiculo_id = veiculo['id']
                placa = veiculo['placa']
                
                print(f"📋 Testando com veículo: {placa} (ID: {veiculo_id})")
                
                # Testar endpoints específicos do veículo
                endpoints_veiculo = [
                    (f"/api/treino/vehicles/{veiculo_id}", "GET", None, 200),
                    (f"/api/treino/vehicles/{veiculo_id}/passages?limit=10", "GET", None, 200),
                    (f"/api/treino/consulta_placa/{placa}", "GET", None, 200),
                    (f"/api/treino/export/passages/{veiculo_id}", "GET", None, 200),
                ]
                
                success_count = 0
                for endpoint, method, data, expected_status in endpoints_veiculo:
                    if test_api_endpoint(base_url, endpoint, method, data, expected_status):
                        success_count += 1
                
                print(f"📊 Endpoints do veículo: {success_count}/{len(endpoints_veiculo)} funcionando")
                return success_count == len(endpoints_veiculo)
            else:
                print("⚠️ Nenhum veículo encontrado para teste")
                return False
        else:
            print(f"❌ Erro ao buscar veículos: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Erro ao testar veículo específico: {e}")
        return False

def test_api_response_format():
    """Testa se as respostas da API estão no formato correto"""
    
    print("\n🔍 Testando formato das respostas...")
    
    base_url = "http://localhost:5000"
    
    try:
        # Testar endpoint de analytics
        response = requests.get(f"{base_url}/api/treino/analytics", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            # Verificar se tem os campos esperados
            expected_fields = ['estatisticas_gerais', 'top_veiculos', 'distribuicao_uf', 'distribuicao_sistema']
            
            missing_fields = []
            for field in expected_fields:
                if field not in data:
                    missing_fields.append(field)
            
            if missing_fields:
                print(f"❌ Campos ausentes na resposta: {missing_fields}")
                return False
            else:
                print("✅ Formato da resposta está correto")
                return True
        else:
            print(f"❌ Erro ao obter analytics: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Erro ao testar formato: {e}")
        return False

def main():
    """Função principal"""
    
    print("🚀 Iniciando testes das APIs do Sentinela Treino")
    print("=" * 60)
    
    # Verificar se o servidor está rodando
    try:
        response = requests.get("http://localhost:5000/api/health", timeout=5)
        if response.status_code != 200:
            print("❌ Servidor não está respondendo corretamente")
            return False
    except:
        print("❌ Servidor não está rodando em http://localhost:5000")
        print("   Execute: python run.py")
        return False
    
    # Executar testes
    test1 = test_sentinela_treino_apis()
    test2 = test_specific_vehicle()
    test3 = test_api_response_format()
    
    print("\n" + "=" * 60)
    print("📊 RESUMO DOS TESTES:")
    print(f"   - APIs básicas: {'✅' if test1 else '❌'}")
    print(f"   - Veículo específico: {'✅' if test2 else '❌'}")
    print(f"   - Formato de resposta: {'✅' if test3 else '❌'}")
    
    if all([test1, test2, test3]):
        print("\n🎉 Todos os testes passaram! APIs funcionando corretamente.")
        return True
    else:
        print("\n⚠️ Alguns testes falharam. Verifique os logs acima.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

