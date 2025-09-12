// services/api.js - Cliente centralizado para APIs do Sentinela IA

/**
 * Cliente de API centralizado para o sistema Sentinela IA
 * Centraliza todas as chamadas HTTP para o backend
 */
class SentinelaAPIClient {
    constructor(baseURL = '') {
        this.baseURL = baseURL;
        this.defaultHeaders = {
            'Content-Type': 'application/json'
        };
    }

    /**
     * Método base para fazer requisições HTTP
     * @param {string} endpoint - Endpoint da API
     * @param {object} options - Opções da requisição (método, body, headers, etc.)
     * @returns {Promise<object>} Resposta da API
     */
    async request(endpoint, options = {}) {
        const url = `${this.baseURL}${endpoint}`;
        const config = {
            headers: { ...this.defaultHeaders, ...options.headers },
            ...options
        };

        try {
            const response = await fetch(url, config);
            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || `HTTP ${response.status}: ${response.statusText}`);
            }

            return data;
        } catch (error) {
            console.error(`API Error [${endpoint}]:`, error.message);
            throw error;
        }
    }

    // ===============================================
    // ===== CONSULTAS ==============================
    // ===============================================

    /**
     * Consulta dados de uma placa
     * @param {string} placa - Placa do veículo
     * @returns {Promise<object>} Dados do veículo, pessoas, passagens e ocorrências
     */
    async consultarPlaca(placa) {
        return await this.request(`/api/consulta_placa/${encodeURIComponent(placa)}`);
    }

    /**
     * Consulta dados de um CPF
     * @param {string} cpf - CPF a ser consultado
     * @returns {Promise<object>} Dados associados ao CPF
     */
    async consultarCPF(cpf) {
        return await this.request(`/api/consulta_cpf/${encodeURIComponent(cpf)}`);
    }

    /**
     * Busca lista de municípios
     * @returns {Promise<object>} Lista de municípios
     */
    async obterMunicipios() {
        return await this.request('/api/municipios');
    }

    // ===============================================
    // ===== OCORRÊNCIAS =============================
    // ===============================================

    /**
     * Cria uma nova ocorrência
     * @param {object} dadosOcorrencia - Dados da ocorrência
     * @returns {Promise<object>} Resultado da criação
     */
    async criarOcorrencia(dadosOcorrencia) {
        return await this.request('/api/ocorrencia', {
            method: 'POST',
            body: JSON.stringify(dadosOcorrencia)
        });
    }

    /**
     * Atualiza uma ocorrência existente
     * @param {number} id - ID da ocorrência
     * @param {object} dadosAtualizacao - Dados a serem atualizados
     * @returns {Promise<object>} Resultado da atualização
     */
    async atualizarOcorrencia(id, dadosAtualizacao) {
        return await this.request(`/api/ocorrencia/${id}`, {
            method: 'PUT',
            body: JSON.stringify(dadosAtualizacao)
        });
    }

    /**
     * Exclui uma ocorrência
     * @param {number} id - ID da ocorrência
     * @returns {Promise<object>} Resultado da exclusão
     */
    async excluirOcorrencia(id) {
        return await this.request(`/api/ocorrencia/${id}`, {
            method: 'DELETE'
        });
    }

    /**
     * Cria um registro de local de entrega
     * @param {object} dadosEntrega - Dados do local de entrega
     * @returns {Promise<object>} Resultado da criação
     */
    async criarLocalEntrega(dadosEntrega) {
        return await this.request('/api/local_entrega', {
            method: 'POST',
            body: JSON.stringify(dadosEntrega)
        });
    }

    // ===============================================
    // ===== PESSOAS =================================
    // ===============================================

    /**
     * Atualiza dados de uma pessoa
     * @param {number} id - ID da pessoa
     * @param {object} dadosPessoa - Dados da pessoa
     * @returns {Promise<object>} Resultado da atualização
     */
    async atualizarPessoa(id, dadosPessoa) {
        return await this.request(`/api/pessoa/${id}`, {
            method: 'PUT',
            body: JSON.stringify(dadosPessoa)
        });
    }

    /**
     * Exclui uma pessoa
     * @param {number} id - ID da pessoa
     * @returns {Promise<object>} Resultado da exclusão
     */
    async excluirPessoa(id) {
        return await this.request(`/api/pessoa/${id}`, {
            method: 'DELETE'
        });
    }

    // ===============================================
    // ===== PASSAGENS ===============================
    // ===============================================

    /**
     * Atualiza uma passagem (marca como ilícita ou não)
     * @param {number} id - ID da passagem
     * @param {string} field - Campo a ser atualizado ('ilicito_ida' ou 'ilicito_volta')
     * @param {boolean} value - Valor do campo
     * @returns {Promise<object>} Resultado da atualização
     */
    async atualizarPassagem(id, field, value) {
        return await this.request(`/api/passagem/${id}`, {
            method: 'PUT',
            body: JSON.stringify({ field, value })
        });
    }

    // ===============================================
    // ===== ANÁLISES ================================
    // ===============================================

    /**
     * Obtém filtros para análise (locais e tipos de apreensão)
     * @returns {Promise<object>} Filtros disponíveis
     */
    async obterFiltrosAnalise() {
        return await this.request('/api/analise/filtros');
    }

    /**
     * Gera dados de análise com base nos filtros
     * @param {object} filtros - Filtros de análise
     * @returns {Promise<object>} Dados de análise
     */
    async gerarAnalise(filtros = {}) {
        const params = new URLSearchParams();
        
        // Processar arrays de filtros
        if (filtros.locais) {
            filtros.locais.forEach(local => params.append('locais', local));
        }
        if (filtros.apreensoes) {
            filtros.apreensoes.forEach(item => params.append('apreensoes', item));
        }
        
        // Parâmetros simples
        if (filtros.placa) params.append('placa', filtros.placa);
        if (filtros.dataInicio) params.append('data_inicio', filtros.dataInicio);
        if (filtros.dataFim) params.append('data_fim', filtros.dataFim);

        return await this.request(`/api/analise?${params.toString()}`);
    }

    /**
     * Analisa um relato individual
     * @param {string} relato - Texto do relato
     * @returns {Promise<object>} Análise do relato
     */
    async analisarRelato(relato) {
        return await this.request('/api/analise_relato', {
            method: 'POST',
            body: JSON.stringify({ relato })
        });
    }

    /**
     * Analisa múltiplos relatos em lote
     * @param {string[]} relatos - Array de relatos
     * @returns {Promise<object>} Análises dos relatos
     */
    async analisarRelatosLote(relatos) {
        return await this.request('/api/analise_relato/lote', {
            method: 'POST',
            body: JSON.stringify({ relatos })
        });
    }

    // ===============================================
    // ===== ANÁLISE IA ==============================
    // ===============================================

    /**
     * Analisa uma placa usando modelos de IA
     * @param {string} placa - Placa a ser analisada
     * @returns {Promise<object>} Análise de IA da placa
     */
    async analisarPlacaIA(placa) {
        return await this.request(`/api/analise_placa/${encodeURIComponent(placa)}`);
    }

    /**
     * Análise geral de IA (parâmetros via query string)
     * @param {string} placa - Placa a ser analisada
     * @returns {Promise<object>} Análise de IA
     */
    async analisarIA(placa) {
        const params = new URLSearchParams({ placa });
        return await this.request(`/api/analise_IA?${params.toString()}`);
    }

    // ===============================================
    // ===== SISTEMA DE AGENTES V2 (Se disponível) ==
    // ===============================================

    /**
     * Análise completa usando sistema de agentes v2
     * @param {string} placa - Placa a ser analisada
     * @param {string} priority - Prioridade ('low', 'medium', 'high', 'critical')
     * @returns {Promise<object>} Análise completa
     */
    async analisarPlacaV2(placa, priority = 'medium') {
        const params = new URLSearchParams({ priority });
        return await this.request(`/api/v2/analyze/${encodeURIComponent(placa)}?${params.toString()}`);
    }

    /**
     * Análise rápida usando sistema de agentes v2
     * @param {string} placa - Placa a ser analisada
     * @returns {Promise<object>} Análise rápida
     */
    async analisarPlacaRapidaV2(placa) {
        return await this.request(`/api/v2/analyze/${encodeURIComponent(placa)}/fast`);
    }

    /**
     * Análise em lote usando sistema de agentes v2
     * @param {string[]} placas - Array de placas
     * @param {string} priority - Prioridade
     * @returns {Promise<object>} Análise em lote
     */
    async analisarLoteV2(placas, priority = 'medium') {
        return await this.request('/api/v2/analyze/batch', {
            method: 'POST',
            body: JSON.stringify({ placas, priority })
        });
    }

    /**
     * Verifica saúde do sistema de agentes v2
     * @returns {Promise<object>} Status de saúde
     */
    async verificarSaudeV2() {
        return await this.request('/api/v2/health');
    }

    /**
     * Obtém estatísticas do sistema de agentes v2
     * @returns {Promise<object>} Estatísticas detalhadas
     */
    async obterEstatisticasV2() {
        return await this.request('/api/v2/stats');
    }

    /**
     * Obtém status individual dos agentes
     * @returns {Promise<object>} Status dos agentes
     */
    async obterStatusAgentesV2() {
        return await this.request('/api/v2/agents/status');
    }

    // ===============================================
    // ===== UTILITÁRIOS =============================
    // ===============================================

    /**
     * Testa conectividade com a API
     * @returns {Promise<boolean>} True se a API estiver acessível
     */
    async testarConectividade() {
        try {
            await this.request('/api/municipios');
            return true;
        } catch {
            return false;
        }
    }

    /**
     * Obtém informações gerais da aplicação
     * @returns {Promise<object>} Informações da aplicação
     */
    async obterInfoAplicacao() {
        return await this.request('/info');
    }
}

// ===============================================
// ===== INSTÂNCIA GLOBAL =======================
// ===============================================

// Criar instância global da API
const api = new SentinelaAPIClient();

// ===============================================
// ===== FUNÇÕES DE CONVENIÊNCIA ================
// ===============================================

/**
 * Funções de conveniência para uso direto sem instanciar a classe
 */

// Consultas
export const consultarPlaca = (placa) => api.consultarPlaca(placa);
export const consultarCPF = (cpf) => api.consultarCPF(cpf);
export const obterMunicipios = () => api.obterMunicipios();

// Ocorrências
export const criarOcorrencia = (dados) => api.criarOcorrencia(dados);
export const atualizarOcorrencia = (id, dados) => api.atualizarOcorrencia(id, dados);
export const excluirOcorrencia = (id) => api.excluirOcorrencia(id);
export const criarLocalEntrega = (dados) => api.criarLocalEntrega(dados);

// Pessoas
export const atualizarPessoa = (id, dados) => api.atualizarPessoa(id, dados);
export const excluirPessoa = (id) => api.excluirPessoa(id);

// Passagens
export const atualizarPassagem = (id, field, value) => api.atualizarPassagem(id, field, value);

// Análises
export const obterFiltrosAnalise = () => api.obterFiltrosAnalise();
export const gerarAnalise = (filtros) => api.gerarAnalise(filtros);
export const analisarRelato = (relato) => api.analisarRelato(relato);
export const analisarRelatosLote = (relatos) => api.analisarRelatosLote(relatos);

// IA
export const analisarPlacaIA = (placa) => api.analisarPlacaIA(placa);
export const analisarIA = (placa) => api.analisarIA(placa);

// Sistema V2 (se disponível)
export const analisarPlacaV2 = (placa, priority) => api.analisarPlacaV2(placa, priority);
export const analisarPlacaRapidaV2 = (placa) => api.analisarPlacaRapidaV2(placa);
export const analisarLoteV2 = (placas, priority) => api.analisarLoteV2(placas, priority);
export const verificarSaudeV2 = () => api.verificarSaudeV2();
export const obterEstatisticasV2 = () => api.obterEstatisticasV2();

// Utilitários
export const testarConectividade = () => api.testarConectividade();
export const obterInfoAplicacao = () => api.obterInfoAplicacao();

// Exportar instância principal
export default api;

// ===============================================
// ===== COMPATIBILIDADE GLOBAL =================
// ===============================================

// Para compatibilidade com código que não usa ES6 modules
if (typeof window !== 'undefined') {
    window.SentinelaAPI = api;
    window.api = api;
}