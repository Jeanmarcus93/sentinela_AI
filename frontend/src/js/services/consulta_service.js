// services/consulta-service.js - Serviço especializado para consultas

import api from './api.js';

/**
 * Serviço especializado para funcionalidades de consulta
 * Encapsula lógica de negócio, validações e formatação de dados
 */
class ConsultaService {
    constructor() {
        this.api = api;
        this.cache = new Map();
        this.cacheTimeout = 5 * 60 * 1000; // 5 minutos
    }

    // ===============================================
    // ===== VALIDAÇÕES =============================
    // ===============================================

    /**
     * Valida formato de placa brasileira
     * @param {string} placa - Placa a ser validada
     * @returns {boolean} True se válida
     */
    validarPlaca(placa) {
        if (!placa || typeof placa !== 'string') return false;
        
        // Remove espaços e converte para maiúsculo
        const placaLimpa = placa.trim().toUpperCase();
        
        // Formato antigo: ABC1234
        const formatoAntigo = /^[A-Z]{3}\d{4}$/;
        // Formato Mercosul: ABC1D23
        const formatoMercosul = /^[A-Z]{3}\d[A-Z]\d{2}$/;
        
        return formatoAntigo.test(placaLimpa) || formatoMercosul.test(placaLimpa);
    }

    /**
     * Valida e normaliza CPF/CNPJ
     * @param {string} documento - CPF ou CNPJ
     * @returns {object} {isValid: boolean, normalized: string, type: 'CPF'|'CNPJ'}
     */
    validarDocumento(documento) {
        if (!documento || typeof documento !== 'string') {
            return { isValid: false, normalized: '', type: null };
        }

        // Remove caracteres não numéricos
        const numerico = documento.replace(/\D/g, '');

        if (numerico.length === 11) {
            return {
                isValid: this._validarCPF(numerico),
                normalized: numerico,
                type: 'CPF'
            };
        } else if (numerico.length === 14) {
            return {
                isValid: this._validarCNPJ(numerico),
                normalized: numerico,
                type: 'CNPJ'
            };
        }

        return { isValid: false, normalized: numerico, type: null };
    }

    /**
     * Validação de CPF
     * @private
     */
    _validarCPF(cpf) {
        // Verificar se todos os dígitos são iguais
        if (/^(\d)\1{10}$/.test(cpf)) return false;

        let soma = 0;
        for (let i = 0; i < 9; i++) {
            soma += parseInt(cpf.charAt(i)) * (10 - i);
        }
        let resto = 11 - (soma % 11);
        if (resto === 10 || resto === 11) resto = 0;
        if (resto !== parseInt(cpf.charAt(9))) return false;

        soma = 0;
        for (let i = 0; i < 10; i++) {
            soma += parseInt(cpf.charAt(i)) * (11 - i);
        }
        resto = 11 - (soma % 11);
        if (resto === 10 || resto === 11) resto = 0;
        return resto === parseInt(cpf.charAt(10));
    }

    /**
     * Validação de CNPJ
     * @private
     */
    _validarCNPJ(cnpj) {
        if (/^(\d)\1{13}$/.test(cnpj)) return false;

        const tamanho = cnpj.length - 2;
        let numeros = cnpj.substring(0, tamanho);
        const digitos = cnpj.substring(tamanho);
        let soma = 0;
        let pos = tamanho - 7;

        for (let i = tamanho; i >= 1; i--) {
            soma += numeros.charAt(tamanho - i) * pos--;
            if (pos < 2) pos = 9;
        }

        let resultado = soma % 11 < 2 ? 0 : 11 - soma % 11;
        if (resultado !== parseInt(digitos.charAt(0))) return false;

        tamanho += 1;
        numeros = cnpj.substring(0, tamanho);
        soma = 0;
        pos = tamanho - 7;

        for (let i = tamanho; i >= 1; i--) {
            soma += numeros.charAt(tamanho - i) * pos--;
            if (pos < 2) pos = 9;
        }

        resultado = soma % 11 < 2 ? 0 : 11 - soma % 11;
        return resultado === parseInt(digitos.charAt(1));
    }

    // ===============================================
    // ===== FORMATAÇÃO =============================
    // ===============================================

    /**
     * Formata data para padrão brasileiro
     * @param {string|Date} data - Data a ser formatada
     * @returns {string} Data formatada (dd/mm/aaaa hh:mm)
     */
    formatarData(data) {
        if (!data) return 'N/D';
        
        try {
            const dateObj = (data instanceof Date) ? data : new Date(data);
            if (isNaN(dateObj.getTime())) return 'Data inválida';

            const dia = String(dateObj.getDate()).padStart(2, '0');
            const mes = String(dateObj.getMonth() + 1).padStart(2, '0');
            const ano = dateObj.getFullYear();
            const hora = String(dateObj.getHours()).padStart(2, '0');
            const minuto = String(dateObj.getMinutes()).padStart(2, '0');

            return `${dia}/${mes}/${ano} ${hora}:${minuto}`;
        } catch {
            return String(data);
        }
    }

    /**
     * Formata CPF/CNPJ para exibição
     * @param {string} documento - Documento sem formatação
     * @returns {string} Documento formatado
     */
    formatarDocumento(documento) {
        if (!documento) return 'N/D';
        
        const limpo = documento.replace(/\D/g, '');
        
        if (limpo.length === 11) {
            // CPF: 123.456.789-01
            return limpo.replace(/(\d{3})(\d{3})(\d{3})(\d{2})/, '$1.$2.$3-$4');
        } else if (limpo.length === 14) {
            // CNPJ: 12.345.678/0001-01
            return limpo.replace(/(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})/, '$1.$2.$3/$4-$5');
        }
        
        return limpo;
    }

    /**
     * Formata placa para exibição
     * @param {string} placa - Placa sem formatação
     * @returns {string} Placa formatada
     */
    formatarPlaca(placa) {
        if (!placa) return 'N/D';
        
        const placaLimpa = placa.trim().toUpperCase();
        
        // Formato Mercosul: ABC1D23 → ABC-1D23
        if (/^[A-Z]{3}\d[A-Z]\d{2}$/.test(placaLimpa)) {
            return placaLimpa.replace(/^([A-Z]{3})(\d[A-Z]\d{2})$/, '$1-$2');
        }
        
        // Formato antigo: ABC1234 → ABC-1234
        if (/^[A-Z]{3}\d{4}$/.test(placaLimpa)) {
            return placaLimpa.replace(/^([A-Z]{3})(\d{4})$/, '$1-$2');
        }
        
        return placaLimpa;
    }

    // ===============================================
    // ===== CONSULTAS ==============================
    // ===============================================

    /**
     * Realiza consulta completa por placa com validação e cache
     * @param {string} placa - Placa a ser consultada
     * @returns {Promise<object>} Dados formatados da consulta
     */
    async consultarPlaca(placa) {
        // Validar placa
        if (!this.validarPlaca(placa)) {
            throw new Error('Formato de placa inválido');
        }

        const placaLimpa = placa.trim().toUpperCase();
        const cacheKey = `placa_${placaLimpa}`;

        // Verificar cache
        if (this.cache.has(cacheKey)) {
            const cached = this.cache.get(cacheKey);
            if (Date.now() - cached.timestamp < this.cacheTimeout) {
                return cached.data;
            }
            this.cache.delete(cacheKey);
        }

        try {
            // Buscar dados da API
            const dados = await this.api.consultarPlaca(placaLimpa);
            
            // Processar e formatar dados
            const dadosProcessados = this._processarDadosPlaca(dados);
            
            // Salvar no cache
            this.cache.set(cacheKey, {
                data: dadosProcessados,
                timestamp: Date.now()
            });

            return dadosProcessados;
        } catch (error) {
            if (error.message.includes('404') || error.message.includes('não encontrada')) {
                throw new Error('Placa não encontrada na base de dados');
            }
            throw error;
        }
    }

    /**
     * Realiza consulta completa por CPF com validação e cache
     * @param {string} cpf - CPF a ser consultado
     * @returns {Promise<object>} Dados formatados da consulta
     */
    async consultarCPF(cpf) {
        // Validar CPF
        const validacao = this.validarDocumento(cpf);
        if (!validacao.isValid) {
            throw new Error('CPF inválido');
        }

        const cacheKey = `cpf_${validacao.normalized}`;

        // Verificar cache
        if (this.cache.has(cacheKey)) {
            const cached = this.cache.get(cacheKey);
            if (Date.now() - cached.timestamp < this.cacheTimeout) {
                return cached.data;
            }
            this.cache.delete(cacheKey);
        }

        try {
            // Buscar dados da API
            const dados = await this.api.consultarCPF(validacao.normalized);
            
            // Processar e formatar dados
            const dadosProcessados = this._processarDadosCPF(dados);
            
            // Salvar no cache
            this.cache.set(cacheKey, {
                data: dadosProcessados,
                timestamp: Date.now()
            });

            return dadosProcessados;
        } catch (error) {
            if (error.message.includes('404') || error.message.includes('não encontrado')) {
                throw new Error('CPF não encontrado na base de dados');
            }
            throw error;
        }
    }

    // ===============================================
    // ===== PROCESSAMENTO DE DADOS =================
    // ===============================================

    /**
     * Processa e formata dados de consulta por placa
     * @private
     */
    _processarDadosPlaca(dados) {
        const { veiculos = [], pessoas = [], passagens = [], ocorrencias = [] } = dados;

        return {
            veiculo: veiculos[0] ? {
                ...veiculos[0],
                placa_formatada: this.formatarPlaca(veiculos[0].placa)
            } : null,
            
            pessoas: pessoas.map(pessoa => ({
                ...pessoa,
                cpf_cnpj_formatado: this.formatarDocumento(pessoa.cpf_cnpj)
            })),
            
            passagens: passagens.map(passagem => ({
                ...passagem,
                datahora_formatada: this.formatarData(passagem.datahora),
                placa_formatada: this.formatarPlaca(passagem.placa)
            })),
            
            ocorrencias: ocorrencias.map(ocorrencia => ({
                ...ocorrencia,
                datahora_formatada: this.formatarData(ocorrencia.datahora),
                datahora_fim_formatada: ocorrencia.datahora_fim ? 
                    this.formatarData(ocorrencia.datahora_fim) : null,
                tipo_formatado: ocorrencia.tipo?.replace('Local de Entrega', 'Local de Entrega da Droga') || '',
                apreensoes: ocorrencia.apreensoes || []
            })),
            
            estatisticas: this._calcularEstatisticas(passagens, ocorrencias),
            metadados: {
                consultado_em: new Date().toISOString(),
                total_registros: passagens.length + ocorrencias.length,
                fonte: 'Sentinela IA'
            }
        };
    }

    /**
     * Processa e formata dados de consulta por CPF
     * @private
     */
    _processarDadosCPF(dados) {
        const { veiculos = [], pessoas = [], passagens = [], ocorrencias = [] } = dados;

        return {
            pessoas: pessoas.map(pessoa => ({
                ...pessoa,
                cpf_cnpj_formatado: this.formatarDocumento(pessoa.cpf_cnpj)
            })),
            
            veiculos: veiculos.map(veiculo => ({
                ...veiculo,
                placa_formatada: this.formatarPlaca(veiculo.placa)
            })),
            
            passagens: passagens.map(passagem => ({
                ...passagem,
                datahora_formatada: this.formatarData(passagem.datahora),
                placa_formatada: this.formatarPlaca(passagem.placa)
            })),
            
            ocorrencias: ocorrencias.map(ocorrencia => ({
                ...ocorrencia,
                datahora_formatada: this.formatarData(ocorrencia.datahora),
                tipo_formatado: ocorrencia.tipo?.replace('Local de Entrega', 'Local de Entrega da Droga') || '',
                apreensoes: ocorrencia.apreensoes || []
            })),
            
            estatisticas: this._calcularEstatisticas(passagens, ocorrencias),
            metadados: {
                consultado_em: new Date().toISOString(),
                total_pessoas: pessoas.length,
                total_veiculos: veiculos.length,
                fonte: 'Sentinela IA'
            }
        };
    }

    /**
     * Calcula estatísticas dos dados consultados
     * @private
     */
    _calcularEstatisticas(passagens, ocorrencias) {
        const agora = new Date();
        const umMesAtras = new Date(agora.getFullYear(), agora.getMonth() - 1, agora.getDate());

        return {
            total_passagens: passagens.length,
            total_ocorrencias: ocorrencias.length,
            passagens_recentes: passagens.filter(p => 
                new Date(p.datahora) >= umMesAtras
            ).length,
            ocorrencias_recentes: ocorrencias.filter(o => 
                new Date(o.datahora) >= umMesAtras
            ).length,
            tipos_ocorrencia: this._contarTipos(ocorrencias),
            passagens_ilicitas: {
                ida: passagens.filter(p => p.ilicito_ida).length,
                volta: passagens.filter(p => p.ilicito_volta).length
            }
        };
    }

    /**
     * Conta tipos de ocorrência
     * @private
     */
    _contarTipos(ocorrencias) {
        const contagem = {};
        ocorrencias.forEach(o => {
            const tipo = o.tipo || 'Não especificado';
            contagem[tipo] = (contagem[tipo] || 0) + 1;
        });
        return contagem;
    }

    // ===============================================
    // ===== UTILITÁRIOS ============================
    // ===============================================

    /**
     * Limpa cache de consultas
     */
    limparCache() {
        this.cache.clear();
    }

    /**
     * Remove entradas antigas do cache
     */
    limparCacheAntigo() {
        const agora = Date.now();
        for (const [key, value] of this.cache.entries()) {
            if (agora - value.timestamp >= this.cacheTimeout) {
                this.cache.delete(key);
            }
        }
    }

    /**
     * Obtém estatísticas do cache
     */
    obterEstatisticasCache() {
        return {
            total_entradas: this.cache.size,
            timeout_configurado: this.cacheTimeout,
            memoria_aproximada: this.cache.size * 1024 // Estimativa em bytes
        };
    }

    /**
     * Pré-valida uma consulta sem fazer a requisição
     * @param {string} tipo - 'placa' ou 'cpf'
     * @param {string} valor - Valor a ser validado
     * @returns {object} Resultado da validação
     */
    preValidarConsulta(tipo, valor) {
        if (tipo === 'placa') {
            return {
                valido: this.validarPlaca(valor),
                valor_limpo: valor ? valor.trim().toUpperCase() : '',
                tipo: 'placa'
            };
        } else if (tipo === 'cpf') {
            const validacao = this.validarDocumento(valor);
            return {
                valido: validacao.isValid,
                valor_limpo: validacao.normalized,
                tipo: validacao.type,
                valor_formatado: this.formatarDocumento(validacao.normalized)
            };
        }
        
        return { valido: false, erro: 'Tipo de consulta inválido' };
    }
}

// ===============================================
// ===== INSTÂNCIA E EXPORTAÇÃO =================
// ===============================================

const consultaService = new ConsultaService();

export default consultaService;

// Exportações nomeadas para conveniência
export const {
    validarPlaca,
    validarDocumento,
    formatarData,
    formatarDocumento,
    formatarPlaca,
    consultarPlaca,
    consultarCPF,
    preValidarConsulta,
    limparCache
} = consultaService;