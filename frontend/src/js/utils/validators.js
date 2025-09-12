// static/js/validators.js
// ===============================================
// ===== SISTEMA DE VALIDAÇÕES CENTRALIZADAS ====
// ===============================================

/**
 * Utilitários de validação para o Sistema Sentinela IA
 * Centraliza todas as validações utilizadas na aplicação
 */

const Validators = {
    // ===============================================
    // ===== VALIDAÇÕES DE PLACA ====================
    // ===============================================
    
    /**
     * Valida formato de placa brasileira (Mercosul e antiga)
     * @param {string} placa - Placa a ser validada
     * @returns {object} - {valid: boolean, message: string, normalized: string}
     */
    validatePlaca(placa) {
        if (!placa || typeof placa !== 'string') {
            return { valid: false, message: 'Placa é obrigatória', normalized: '' };
        }

        // Remove espaços e converte para maiúsculo
        const normalized = placa.trim().toUpperCase().replace(/[^A-Z0-9]/g, '');
        
        // Formato antigo: ABC1234
        const formatoAntigo = /^[A-Z]{3}[0-9]{4}$/;
        // Formato Mercosul: ABC1D23
        const formatoMercosul = /^[A-Z]{3}[0-9][A-Z][0-9]{2}$/;
        
        if (normalized.length < 7) {
            return { valid: false, message: 'Placa deve ter pelo menos 7 caracteres', normalized };
        }
        
        if (normalized.length > 7) {
            return { valid: false, message: 'Placa deve ter no máximo 7 caracteres', normalized };
        }
        
        if (!formatoAntigo.test(normalized) && !formatoMercosul.test(normalized)) {
            return { valid: false, message: 'Formato de placa inválido', normalized };
        }
        
        return { valid: true, message: 'Placa válida', normalized };
    },

    /**
     * Formata placa para exibição
     * @param {string} placa - Placa para formatar
     * @returns {string} - Placa formatada (ABC-1234 ou ABC1D23)
     */
    formatPlaca(placa) {
        const validation = this.validatePlaca(placa);
        if (!validation.valid) return placa;
        
        const normalized = validation.normalized;
        
        // Formato antigo: ABC-1234
        if (/^[A-Z]{3}[0-9]{4}$/.test(normalized)) {
            return `${normalized.slice(0, 3)}-${normalized.slice(3)}`;
        }
        
        // Formato Mercosul: ABC1D23 (sem hífen por padrão)
        return normalized;
    },

    // ===============================================
    // ===== VALIDAÇÕES DE CPF/CNPJ =================
    // ===============================================
    
    /**
     * Normaliza CPF/CNPJ removendo caracteres especiais
     * @param {string} documento - CPF ou CNPJ
     * @returns {string} - Documento normalizado
     */
    normalizeCpfCnpj(documento) {
        if (!documento) return '';
        return documento.toString().replace(/\D/g, '');
    },

    /**
     * Valida CPF
     * @param {string} cpf - CPF a ser validado
     * @returns {object} - {valid: boolean, message: string}
     */
    validateCpf(cpf) {
        const normalizedCpf = this.normalizeCpfCnpj(cpf);
        
        if (!normalizedCpf) {
            return { valid: false, message: 'CPF é obrigatório' };
        }
        
        if (normalizedCpf.length !== 11) {
            return { valid: false, message: 'CPF deve ter 11 dígitos' };
        }
        
        // Verifica sequências inválidas
        if (/^(\d)\1{10}$/.test(normalizedCpf)) {
            return { valid: false, message: 'CPF inválido' };
        }
        
        // Validação dos dígitos verificadores
        let soma = 0;
        for (let i = 0; i < 9; i++) {
            soma += parseInt(normalizedCpf.charAt(i)) * (10 - i);
        }
        
        let resto = (soma * 10) % 11;
        if (resto === 10 || resto === 11) resto = 0;
        
        if (resto !== parseInt(normalizedCpf.charAt(9))) {
            return { valid: false, message: 'CPF inválido' };
        }
        
        soma = 0;
        for (let i = 0; i < 10; i++) {
            soma += parseInt(normalizedCpf.charAt(i)) * (11 - i);
        }
        
        resto = (soma * 10) % 11;
        if (resto === 10 || resto === 11) resto = 0;
        
        if (resto !== parseInt(normalizedCpf.charAt(10))) {
            return { valid: false, message: 'CPF inválido' };
        }
        
        return { valid: true, message: 'CPF válido' };
    },

    /**
     * Valida CNPJ
     * @param {string} cnpj - CNPJ a ser validado
     * @returns {object} - {valid: boolean, message: string}
     */
    validateCnpj(cnpj) {
        const normalizedCnpj = this.normalizeCpfCnpj(cnpj);
        
        if (!normalizedCnpj) {
            return { valid: false, message: 'CNPJ é obrigatório' };
        }
        
        if (normalizedCnpj.length !== 14) {
            return { valid: false, message: 'CNPJ deve ter 14 dígitos' };
        }
        
        // Verifica sequências inválidas
        if (/^(\d)\1{13}$/.test(normalizedCnpj)) {
            return { valid: false, message: 'CNPJ inválido' };
        }
        
        // Validação dos dígitos verificadores
        const pesos1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2];
        const pesos2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2];
        
        let soma = 0;
        for (let i = 0; i < 12; i++) {
            soma += parseInt(normalizedCnpj.charAt(i)) * pesos1[i];
        }
        
        let resto = soma % 11;
        const dv1 = resto < 2 ? 0 : 11 - resto;
        
        if (dv1 !== parseInt(normalizedCnpj.charAt(12))) {
            return { valid: false, message: 'CNPJ inválido' };
        }
        
        soma = 0;
        for (let i = 0; i < 13; i++) {
            soma += parseInt(normalizedCnpj.charAt(i)) * pesos2[i];
        }
        
        resto = soma % 11;
        const dv2 = resto < 2 ? 0 : 11 - resto;
        
        if (dv2 !== parseInt(normalizedCnpj.charAt(13))) {
            return { valid: false, message: 'CNPJ inválido' };
        }
        
        return { valid: true, message: 'CNPJ válido' };
    },

    /**
     * Valida CPF ou CNPJ automaticamente
     * @param {string} documento - CPF ou CNPJ
     * @returns {object} - {valid: boolean, message: string, type: string}
     */
    validateCpfCnpj(documento) {
        const normalized = this.normalizeCpfCnpj(documento);
        
        if (normalized.length === 11) {
            const cpfResult = this.validateCpf(normalized);
            return { ...cpfResult, type: 'cpf' };
        } else if (normalized.length === 14) {
            const cnpjResult = this.validateCnpj(normalized);
            return { ...cnpjResult, type: 'cnpj' };
        } else {
            return { valid: false, message: 'Documento deve ter 11 (CPF) ou 14 (CNPJ) dígitos', type: 'unknown' };
        }
    },

    /**
     * Formata CPF/CNPJ para exibição
     * @param {string} documento - CPF ou CNPJ
     * @returns {string} - Documento formatado
     */
    formatCpfCnpj(documento) {
        const normalized = this.normalizeCpfCnpj(documento);
        
        if (normalized.length === 11) {
            // CPF: 123.456.789-10
            return normalized.replace(/(\d{3})(\d{3})(\d{3})(\d{2})/, '$1.$2.$3-$4');
        } else if (normalized.length === 14) {
            // CNPJ: 12.345.678/0001-90
            return normalized.replace(/(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})/, '$1.$2.$3/$4-$5');
        }
        
        return documento; // Retorna original se não conseguir formatar
    },

    // ===============================================
    // ===== VALIDAÇÕES DE DATA/HORA ================
    // ===============================================
    
    /**
     * Valida data no formato DD/MM/AAAA
     * @param {string} data - Data a ser validada
     * @returns {object} - {valid: boolean, message: string, date: Date}
     */
    validateDate(data) {
        if (!data) {
            return { valid: false, message: 'Data é obrigatória', date: null };
        }
        
        const regex = /^(\d{2})\/(\d{2})\/(\d{4})$/;
        const match = data.match(regex);
        
        if (!match) {
            return { valid: false, message: 'Data deve estar no formato DD/MM/AAAA', date: null };
        }
        
        const [, dia, mes, ano] = match.map(Number);
        const date = new Date(ano, mes - 1, dia);
        
        // Verifica se a data é válida
        if (date.getDate() !== dia || date.getMonth() !== mes - 1 || date.getFullYear() !== ano) {
            return { valid: false, message: 'Data inválida', date: null };
        }
        
        return { valid: true, message: 'Data válida', date };
    },

    /**
     * Valida data e hora no formato DD/MM/AAAA HH:MM
     * @param {string} dataHora - Data e hora a serem validadas
     * @returns {object} - {valid: boolean, message: string, date: Date, iso: string}
     */
    validateDateTime(dataHora) {
        if (!dataHora) {
            return { valid: false, message: 'Data e hora são obrigatórias', date: null, iso: null };
        }
        
        const regex = /^(\d{2})\/(\d{2})\/(\d{4}) (\d{2}):(\d{2})$/;
        const match = dataHora.match(regex);
        
        if (!match) {
            return { valid: false, message: 'Data/hora deve estar no formato DD/MM/AAAA HH:MM', date: null, iso: null };
        }
        
        const [, dia, mes, ano, hora, minuto] = match.map(Number);
        
        // Valida hora e minuto
        if (hora < 0 || hora > 23) {
            return { valid: false, message: 'Hora deve estar entre 00 e 23', date: null, iso: null };
        }
        
        if (minuto < 0 || minuto > 59) {
            return { valid: false, message: 'Minuto deve estar entre 00 e 59', date: null, iso: null };
        }
        
        const date = new Date(ano, mes - 1, dia, hora, minuto);
        
        // Verifica se a data é válida
        if (date.getDate() !== dia || date.getMonth() !== mes - 1 || date.getFullYear() !== ano ||
            date.getHours() !== hora || date.getMinutes() !== minuto) {
            return { valid: false, message: 'Data/hora inválida', date: null, iso: null };
        }
        
        const iso = `${ano}-${mes.toString().padStart(2, '0')}-${dia.toString().padStart(2, '0')}T${hora.toString().padStart(2, '0')}:${minuto.toString().padStart(2, '0')}`;
        
        return { valid: true, message: 'Data/hora válida', date, iso };
    },

    /**
     * Converte data/hora brasileira para ISO
     * @param {string} dataHoraBr - Data no formato DD/MM/AAAA HH:MM
     * @returns {string|null} - Data no formato ISO ou null se inválida
     */
    convertToISO(dataHoraBr) {
        const validation = this.validateDateTime(dataHoraBr);
        return validation.valid ? validation.iso : null;
    },

    /**
     * Formata data ISO para formato brasileiro
     * @param {string} isoDate - Data no formato ISO
     * @returns {string} - Data no formato DD/MM/AAAA HH:MM
     */
    formatFromISO(isoDate) {
        if (!isoDate) return '';
        
        try {
            const date = new Date(isoDate);
            const dia = date.getDate().toString().padStart(2, '0');
            const mes = (date.getMonth() + 1).toString().padStart(2, '0');
            const ano = date.getFullYear();
            const hora = date.getHours().toString().padStart(2, '0');
            const minuto = date.getMinutes().toString().padStart(2, '0');
            
            return `${dia}/${mes}/${ano} ${hora}:${minuto}`;
        } catch (error) {
            return isoDate; // Retorna original se não conseguir converter
        }
    },

    // ===============================================
    // ===== VALIDAÇÕES GERAIS ======================
    // ===============================================
    
    /**
     * Valida se um campo obrigatório está preenchido
     * @param {any} value - Valor a ser validado
     * @param {string} fieldName - Nome do campo
     * @returns {object} - {valid: boolean, message: string}
     */
    validateRequired(value, fieldName = 'Campo') {
        if (value === null || value === undefined || value === '') {
            return { valid: false, message: `${fieldName} é obrigatório` };
        }
        
        if (typeof value === 'string' && value.trim() === '') {
            return { valid: false, message: `${fieldName} é obrigatório` };
        }
        
        return { valid: true, message: `${fieldName} válido` };
    },

    /**
     * Valida email
     * @param {string} email - Email a ser validado
     * @returns {object} - {valid: boolean, message: string}
     */
    validateEmail(email) {
        if (!email) {
            return { valid: false, message: 'Email é obrigatório' };
        }
        
        const regex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        
        if (!regex.test(email)) {
            return { valid: false, message: 'Email inválido' };
        }
        
        return { valid: true, message: 'Email válido' };
    },

    /**
     * Valida número de telefone brasileiro
     * @param {string} telefone - Telefone a ser validado
     * @returns {object} - {valid: boolean, message: string, normalized: string}
     */
    validateTelefone(telefone) {
        if (!telefone) {
            return { valid: false, message: 'Telefone é obrigatório', normalized: '' };
        }
        
        const normalized = telefone.replace(/\D/g, '');
        
        // Celular: 11987654321 ou Fixo: 1134567890
        if (normalized.length < 10 || normalized.length > 11) {
            return { valid: false, message: 'Telefone deve ter 10 ou 11 dígitos', normalized };
        }
        
        // Verifica se começa com código de área válido
        const ddd = parseInt(normalized.substring(0, 2));
        const ddsValidos = [11, 12, 13, 14, 15, 16, 17, 18, 19, 21, 22, 24, 27, 28, 31, 32, 33, 34, 35, 37, 38, 41, 42, 43, 44, 45, 46, 47, 48, 49, 51, 53, 54, 55, 61, 62, 63, 64, 65, 66, 67, 68, 69, 71, 73, 74, 75, 77, 79, 81, 82, 83, 84, 85, 86, 87, 88, 89, 91, 92, 93, 94, 95, 96, 97, 98, 99];
        
        if (!ddsValidos.includes(ddd)) {
            return { valid: false, message: 'Código de área inválido', normalized };
        }
        
        return { valid: true, message: 'Telefone válido', normalized };
    },

    /**
     * Formata telefone para exibição
     * @param {string} telefone - Telefone para formatar
     * @returns {string} - Telefone formatado
     */
    formatTelefone(telefone) {
        const validation = this.validateTelefone(telefone);
        if (!validation.valid) return telefone;
        
        const normalized = validation.normalized;
        
        if (normalized.length === 10) {
            // Telefone fixo: (11) 3456-7890
            return `(${normalized.slice(0, 2)}) ${normalized.slice(2, 6)}-${normalized.slice(6)}`;
        } else if (normalized.length === 11) {
            // Celular: (11) 98765-4321
            return `(${normalized.slice(0, 2)}) ${normalized.slice(2, 7)}-${normalized.slice(7)}`;
        }
        
        return telefone;
    },

    // ===============================================
    // ===== VALIDAÇÕES ESPECÍFICAS DO SISTEMA ======
    // ===============================================
    
    /**
     * Valida dados de uma ocorrência
     * @param {object} ocorrencia - Dados da ocorrência
     * @returns {object} - {valid: boolean, errors: array}
     */
    validateOcorrencia(ocorrencia) {
        const errors = [];
        
        // Validações obrigatórias
        if (!ocorrencia.veiculo_id) {
            errors.push('Veículo é obrigatório');
        }
        
        if (!ocorrencia.tipo) {
            errors.push('Tipo de ocorrência é obrigatório');
        }
        
        if (!ocorrencia.datahora) {
            errors.push('Data e hora são obrigatórias');
        } else {
            // Se é uma string no formato brasileiro, valida
            if (typeof ocorrencia.datahora === 'string' && ocorrencia.datahora.includes('/')) {
                const dateValidation = this.validateDateTime(ocorrencia.datahora);
                if (!dateValidation.valid) {
                    errors.push(dateValidation.message);
                }
            }
        }
        
        // Validações específicas por tipo
        if (ocorrencia.tipo === 'Local de Entrega') {
            if (!ocorrencia.relato) {
                errors.push('Local de entrega é obrigatório');
            }
            
            if (ocorrencia.datahora_fim) {
                const dateValidation = this.validateDateTime(ocorrencia.datahora_fim);
                if (!dateValidation.valid) {
                    errors.push('Data/hora final inválida');
                }
            }
        }
        
        if (ocorrencia.tipo === 'Abordagem' && !ocorrencia.relato) {
            errors.push('Relato da abordagem é obrigatório');
        }
        
        if (ocorrencia.tipo === 'BOP' && !ocorrencia.relato) {
            errors.push('Relato do BOP é obrigatório');
        }
        
        return {
            valid: errors.length === 0,
            errors
        };
    },

    /**
     * Valida dados de uma apreensão
     * @param {object} apreensao - Dados da apreensão
     * @returns {object} - {valid: boolean, errors: array}
     */
    validateApreensao(apreensao) {
        const errors = [];
        const tiposValidos = ['Maconha', 'Skunk', 'Cocaina', 'Crack', 'Sintéticos', 'Arma'];
        const unidadesValidas = ['kg', 'g', 'un'];
        
        if (!apreensao.tipo || !tiposValidos.includes(apreensao.tipo)) {
            errors.push('Tipo de apreensão inválido');
        }
        
        if (!apreensao.quantidade || isNaN(parseFloat(apreensao.quantidade)) || parseFloat(apreensao.quantidade) <= 0) {
            errors.push('Quantidade deve ser um número positivo');
        }
        
        if (!apreensao.unidade || !unidadesValidas.includes(apreensao.unidade)) {
            errors.push('Unidade inválida');
        }
        
        return {
            valid: errors.length === 0,
            errors
        };
    }
};

// ===============================================
// ===== FUNÇÕES DE UTILIDADE ===================
// ===============================================

/**
 * Aplica validação em tempo real a um campo de input
 * @param {HTMLElement} input - Elemento input
 * @param {function} validator - Função de validação
 * @param {function} onValidation - Callback chamado após validação
 */
function applyRealTimeValidation(input, validator, onValidation = null) {
    if (!input || typeof validator !== 'function') return;
    
    const validateField = () => {
        const result = validator(input.value);
        
        // Remove classes antigas
        input.classList.remove('border-red-500', 'border-green-500', 'border-gray-300');
        
        // Aplica nova classe baseada no resultado
        if (result.valid) {
            input.classList.add('border-green-500');
        } else {
            input.classList.add('border-red-500');
        }
        
        // Chama callback se fornecido
        if (onValidation) {
            onValidation(result, input);
        }
    };
    
    // Aplica validação em vários eventos
    input.addEventListener('blur', validateField);
    input.addEventListener('input', debounce(validateField, 500));
}

/**
 * Debounce para otimizar validações em tempo real
 * @param {function} func - Função a ser executada
 * @param {number} delay - Delay em milissegundos
 * @returns {function} - Função com debounce aplicado
 */
function debounce(func, delay) {
    let timeoutId;
    return function (...args) {
        clearTimeout(timeoutId);
        timeoutId = setTimeout(() => func.apply(this, args), delay);
    };
}

/**
 * Exibe mensagem de validação próximo ao campo
 * @param {HTMLElement} input - Campo de input
 * @param {string} message - Mensagem a ser exibida
 * @param {string} type - Tipo da mensagem ('error' ou 'success')
 */
function showValidationMessage(input, message, type = 'error') {
    // Remove mensagem anterior se existir
    const existingMessage = input.parentNode.querySelector('.validation-message');
    if (existingMessage) {
        existingMessage.remove();
    }
    
    if (!message) return;
    
    // Cria nova mensagem
    const messageElement = document.createElement('div');
    messageElement.className = `validation-message text-xs mt-1 ${type === 'error' ? 'text-red-500' : 'text-green-500'}`;
    messageElement.textContent = message;
    
    // Insere após o input
    input.parentNode.insertBefore(messageElement, input.nextSibling);
}

// Exporta para uso global
if (typeof window !== 'undefined') {
    window.Validators = Validators;
    window.applyRealTimeValidation = applyRealTimeValidation;
    window.showValidationMessage = showValidationMessage;
}

// Exporta para Node.js se disponível
if (typeof module !== 'undefined' && module.exports) {
    module.exports = Validators;
}