# app.py
from flask import Flask
from config import criar_tabelas
from routes import main_bp
from analise import analise_bp

# Cria a instância da aplicação Flask
app = Flask(__name__)

# Registra os Blueprints (módulos de rotas)
app.register_blueprint(main_bp)
app.register_blueprint(analise_bp)

# Bloco de execução principal
if __name__ == '__main__':
    try:
        # Garante que as tabelas existam no banco de dados ao iniciar
        criar_tabelas()
        print("Tabelas do banco de dados verificadas/criadas com sucesso.")
    except Exception as e:
        print(f"ERRO CRÍTICO ao conectar ao banco ou criar tabelas: {e}")
        # Encerra a aplicação se não conseguir conectar ao DB
        exit()

    # Inicia o servidor Flask em modo de depuração
    app.run(debug=True)