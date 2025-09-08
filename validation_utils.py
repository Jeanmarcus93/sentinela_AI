# validation_utils.py
import re
import logging
from datetime import datetime
from functools import wraps
from flask import jsonify, request

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ValidationError(Exception):
    """Exceção customizada para erros de validação."""
    pass

class InputValidator:
    """Classe para validação de inputs do sistema."""
    
    @staticmethod
    def validate_placa(placa: str) -> str:
        """Valida formato de placa brasileira."""
        if not placa:
            raise ValidationError("Placa não pode estar vazia")
        
        # Remove espaços e converte para maiúscula
        placa = placa.strip().upper()
        
        # Padrão: ABC1234 ou ABC1D23 (Mercosul)
        if not re.match(r'^[A-Z]{3}\d{4}$|^[A-Z]{3}\d[A-Z]\d{2}$', placa):
            raise ValidationError("Formato de placa inválido. Use ABC1234 ou ABC1D23")
        
        return placa
    
    @staticmethod
    def validate_cpf(cpf: str) -> str:
        """Valida e normaliza CPF."""
        if not cpf:
            raise ValidationError("CPF não pode estar vazio")
        
        # Remove caracteres não numéricos
        cpf = re.sub(r'\D', '', cpf)
        
        if len(cpf) != 11:
            raise ValidationError("CPF deve ter 11 dígitos")
        
        # Validação básica (evita CPFs com todos os dígitos iguais)
        if len(set(cpf)) == 1:
            raise ValidationError("CPF inválido")
        
        return cpf
    
    @staticmethod
    def validate_datetime(datetime_str: str) -> datetime:
        """Valida formato de data/hora."""
        if not datetime_str:
            raise ValidationError("Data/hora não pode estar vazia")
        
        try:
            # Tenta vários formatos comuns
            formats = [
                "%Y-%m-%dT%H:%M",
                "%Y-%m-%d %H:%M:%S",
                "%d/%m/%Y %H:%M",
                "%Y-%m-%d"
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(datetime_str, fmt)
                except ValueError:
                    continue
            
            raise ValueError("Formato não reconhecido")
            
        except ValueError:
            raise ValidationError(f"Formato de data/hora inválido: {datetime_str}")
    
    @staticmethod
    def sanitize_text(text: str, max_length: int = 1000) -> str:
        """Sanitiza texto para evitar XSS e limita tamanho."""
        if not text:
            return ""
        
        # Remove tags HTML básicas
        text = re.sub(r'<[^>]*>', '', text)
        
        # Limita tamanho
        text = text[:max_length]
        
        # Remove caracteres especiais perigosos
        text = re.sub(r'[<>"\']', '', text)
        
        return text.strip()

def validate_json_input(required_fields: list = None, optional_fields: list = None):
    """Decorator para validar entrada JSON em rotas Flask."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                # Verifica se é JSON válido
                data = request.get_json(force=True)
                if data is None:
                    return jsonify({"error": "JSON inválido ou ausente"}), 400
                
                # Valida campos obrigatórios
                if required_fields:
                    missing_fields = [field for field in required_fields if field not in data or not data[field]]
                    if missing_fields:
                        return jsonify({"error": f"Campos obrigatórios faltando: {missing_fields}"}), 400
                
                # Log da operação
                logger.info(f"Validação bem-sucedida para {func.__name__}")
                
                return func(*args, **kwargs)
                
            except ValidationError as e:
                logger.warning(f"Erro de validação em {func.__name__}: {e}")
                return jsonify({"error": str(e)}), 400
            except Exception as e:
                logger.error(f"Erro interno em {func.__name__}: {e}")
                return jsonify({"error": "Erro interno do servidor"}), 500
        
        return wrapper
    return decorator

# Exemplo de uso melhorado para routes.py
def validate_ocorrencia_data(data):
    """Valida dados específicos de ocorrência."""
    validator = InputValidator()
    
    # Valida campos obrigatórios
    if not data.get('veiculo_id'):
        raise ValidationError("ID do veículo é obrigatório")
    
    if not data.get('tipo'):
        raise ValidationError("Tipo de ocorrência é obrigatório")
    
    # Valida data/hora
    if data.get('datahora'):
        data['datahora'] = validator.validate_datetime(data['datahora']).isoformat()
    
    # Sanitiza relato
    if data.get('relato'):
        data['relato'] = validator.sanitize_text(data['relato'], 2000)
    
    return data

# Rate limiting básico
from collections import defaultdict
from time import time

class RateLimiter:
    """Rate limiter simples para proteger APIs."""
    
    def __init__(self, max_requests=100, window_seconds=3600):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = defaultdict(list)
    
    def is_allowed(self, identifier: str) -> bool:
        """Verifica se a requisição é permitida."""
        now = time()
        # Remove requisições antigas
        self.requests[identifier] = [
            req_time for req_time in self.requests[identifier] 
            if now - req_time < self.window_seconds
        ]
        
        # Verifica limite
        if len(self.requests[identifier]) >= self.max_requests:
            return False
        
        # Adiciona requisição atual
        self.requests[identifier].append(now)
        return True

# Instância global do rate limiter
rate_limiter = RateLimiter()

def with_rate_limit(identifier_func=lambda: request.remote_addr):
    """Decorator para rate limiting."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            identifier = identifier_func()
            
            if not rate_limiter.is_allowed(identifier):
                logger.warning(f"Rate limit excedido para {identifier}")
                return jsonify({"error": "Muitas requisições. Tente novamente mais tarde."}), 429
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator