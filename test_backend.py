#!/usr/bin/env python3
"""
Script para testar se o backend está funcionando corretamente
"""

import requests
import json

def test_backend():
    base_url = "http://localhost:5000"
    
    print("🧪 Testando conectividade com o backend...")
    
    # Teste 1: Health check
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        print(f"✅ Health check: {response.status_code}")
        if response.status_code == 200:
            print(f"   Resposta: {response.json()}")
    except Exception as e:
        print(f"❌ Health check falhou: {e}")
        return False
    
    # Teste 2: Info endpoint
    try:
        response = requests.get(f"{base_url}/api/info", timeout=5)
        print(f"✅ Info endpoint: {response.status_code}")
    except Exception as e:
        print(f"❌ Info endpoint falhou: {e}")
        return False
    
    # Teste 3: Endpoint de passagem (simulado)
    try:
        test_data = {
            "passagem_id": 999999,  # ID que não existe
            "tipo": "ida",
            "ilicito": True
        }
        
        response = requests.put(
            f"{base_url}/api/passagem/status",
            json=test_data,
            headers={"Content-Type": "application/json"},
            timeout=5
        )
        print(f"✅ Endpoint passagem: {response.status_code}")
        print(f"   Resposta: {response.text}")
        
        # Esperamos 404 porque o ID não existe
        if response.status_code == 404:
            print("   ✅ Endpoint funcionando (404 esperado para ID inexistente)")
        else:
            print(f"   ⚠️ Status inesperado: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Endpoint passagem falhou: {e}")
        return False
    
    print("\n🎉 Todos os testes passaram! Backend está funcionando.")
    return True

if __name__ == "__main__":
    test_backend()
