// services/analise-service.js - Serviço especializado para análises

import api from './api.js';

/**
 * Serviço especializado para funcionalidades de análise
 * Gerencia análises agregadas, IA, relatórios e métricas
 */
class AnaliseService {
    constructor() {
        this.api = api;
        this.cache = new Map();
        this.cacheTimeout = 10 * 60 * 1000; // 10 minutos para análises
        this.filtrosCache = null;
        this.filtrosCacheTime = null;
    }

    // ===============================================
    // ===== VALIDAÇÕES DE FILTROS ==================
    // ===============================================

    /**
     * Valida filtros de análise
     * @param {object} filtros - Objeto com filtros de análise
     * @returns {object} Resultado da validação
     */
    validarFiltros(filtros = {}) {
        const erros = [];
        const filtrosValidados = {};

        // Validar placa
        if (filtros.placa) {
            const placa = filtros.placa.trim().toUpperCase();
            if (!/^[A-Z]{3}\d{4}$|^[A-Z]{3}\d[A-Z]\d{2}$/.test(placa)) {
                erros.push('Formato de placa inválido');
            } else {
                filtrosValidados.placa = placa;
            }
        }

        // Validar datas
        if (filtros.dataInicio) {
            const dataInicio = new Date(filtros.dataInicio);
            if (isNaN(dataInicio.getTime())) {
                erros.push('Data de início inválida');
            } else {
                filtrosValidados.dataInicio = filtros.dataInicio;
            }
        }

        if (filtros.dataFim) {
            const dataFim = new Date(filtros.dataFim);
            if (isNaN(dataFim.getTime())) {
                erros.push('Data de fim inválida');
            } else {
                filtrosValidados.dataFim = filtros.dataFim;
            }
        }

        // Validar intervalo de datas
        if (filtrosValidados.dataInicio && filtrosValidados.dataFim) {
            const inicio = new Date(filtrosValidados.dataInicio);
            const fim = new Date(filtrosValidados.dataFim);
            if (inicio > fim) {
                erros.push('Data de início deve ser anterior à data de fim');
            }
        }

        // Validar arrays
        if (filtros.locais && Array.isArray(filtros.locais)) {
            filtrosValidados.locais = filtros.locais.filter(local => 
                typeof local === 'string' && local.trim().length > 0
            );
        }

        if (filtros.apreensoes && Array.isArray(filtros.apreensoes)) {
            const tiposValidos = ['Maconha', 'Skunk', 'Cocaina', 'Crack', 'Sintéticos', 'Arma'];
            filtrosValidados.apreensoes = filtros.apreensoes.filter(tipo =>
                tiposValidos.includes(tipo)
            );
        }

        return {
            valido: erros.length === 0,
            erros,
            filtros: filtrosValidados
        };
    }

    // ===============================================
    // ===== FILTROS E METADADOS ====================
    // ===============================================

    /**
     * Obtém filtros disponíveis com cache
     * @returns {Promise<object>} Filtros disponíveis
     */
    async obterFiltros() {
        // Verificar cache (30 minutos para filtros)
        if (this.filtrosCache && this.filtrosCacheTime && 
            Date.now() - this.filtrosCacheTime < 30 * 60 * 1000) {
            return this.filtrosCache;
        }

        try {
            const filtros = await this.api.obterFiltrosAnalise();
            
            // Processar e enriquecer filtros
            const filtrosProcessados = {
                locais: filtros.locais || [],
                apreensoes: filtros.apreensoes || [],
                estatisticas: {
                    total_locais: filtros.locais?.length || 0,
                    total_tipos_apreensao: filtros.apreensoes?.length || 0
                },
                metadata: {
                    atualizado_em: new Date().toISOString(),
                    fonte: 'Base de dados Sentinela IA'
                }
            };

            // Salvar no cache
            this.filtrosCache = filtrosProcessados;
            this.filtrosCacheTime = Date.now();

            return filtrosProcessados;
        } catch (error) {
            console.error('Erro ao obter filtros:', error);
            throw new Error('Não foi possível carregar os filtros de análise');
        }
    }

    // ===============================================
    // ===== ANÁLISE AGREGADA =======================
    // ===============================================

    /**
     * Gera análise agregada completa
     * @param {object} filtros - Filtros de análise
     * @returns {Promise<object>} Dados de análise processados
     */
    async gerarAnaliseAgregada(filtros = {}) {
        // Validar filtros
        const validacao = this.validarFiltros(filtros);
        if (!validacao.valido) {
            throw new Error(`Filtros inválidos: ${validacao.erros.join(', ')}`);
        }

        const filtrosLimpos = validacao.filtros;
        const cacheKey = this._gerarChaveCache('agregada', filtrosLimpos);

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
            const dadosBrutos = await this.api.gerarAnalise(filtrosLimpos);
            
            // Processar e enriquecer dados
            const dadosProcessados = this._processarAnaliseAgregada(dadosBrutos, filtrosLimpos);
            
            // Salvar no cache
            this.cache.set(cacheKey, {
                data: dadosProcessados,
                timestamp: Date.now()
            });

            return dadosProcessados;
        } catch (error) {
            console.error('Erro na análise agregada:', error);
            throw new Error('Não foi possível gerar a análise agregada');
        }
    }

    // ===============================================
    // ===== ANÁLISE DE IA ==========================
    // ===============================================

    /**
     * Realiza análise de IA para uma placa específica
     * @param {string} placa - Placa a ser analisada
     * @returns {Promise<object>} Análise de IA processada
     */
    async analisarPlacaIA(placa) {
        // Validar placa
        if (!placa || typeof placa !== 'string') {
            throw new Error('Placa é obrigatória');
        }

        const placaLimpa = placa.trim().toUpperCase();
        if (!/^[A-Z]{3}\d{4}$|^[A-Z]{3}\d[A-Z]\d{2}$/.test(placaLimpa)) {
            throw new Error('Formato de placa inválido');
        }

        const cacheKey = `ia_${placaLimpa}`;

        // Verificar cache (5 minutos para IA)
        if (this.cache.has(cacheKey)) {
            const cached = this.cache.get(cacheKey);
            if (Date.now() - cached.timestamp < 5 * 60 * 1000) {
                return cached.data;
            }
            this.cache.delete(cacheKey);
        }

        try {
            // Buscar análise da API
            const analiseIA = await this.api.analisarPlacaIA(placaLimpa);
            
            // Processar dados de IA
            const dadosProcessados = this._processarAnaliseIA(analiseIA, placaLimpa);
            
            // Salvar no cache
            this.cache.set(cacheKey, {
                data: dadosProcessados,
                timestamp: Date.now()
            });

            return dadosProcessados;
        } catch (error) {
            if (error.message.includes('Modelos não encontrados')) {
                throw new Error('Modelos de IA não estão disponíveis. Entre em contato com o administrador.');
            }
            console.error('Erro na análise de IA:', error);
            throw new Error('Não foi possível realizar a análise de IA');
        }
    }

    /**
     * Análise usando sistema v2 de agentes (se disponível)
     * @param {string} placa - Placa a ser analisada
     * @param {string} tipo - 'completa', 'rapida' ou 'lote'
     * @param {object} opcoes - Opções adicionais
     * @returns {Promise<object>} Análise v2 processada
     */
    async analisarPlacaV2(placa, tipo = 'completa', opcoes = {}) {
        const placaLimpa = placa.trim().toUpperCase();
        const { prioridade = 'medium' } = opcoes;

        try {
            let resultado;
            
            switch (tipo) {
                case 'rapida':
                    resultado = await this.api.analisarPlacaRapidaV2(placaLimpa);
                    break;
                case 'lote':
                    const placas = Array.isArray(placa) ? placa : [placaLimpa];
                    resultado = await this.api.analisarLoteV2(placas, prioridade);
                    break;
                default:
                    resultado = await this.api.analisarPlacaV2(placaLimpa, prioridade);
            }

            return this._processarAnaliseV2(resultado, placaLimpa, tipo);
        } catch (error) {
            console.error('Erro na análise v2:', error);
            throw new Error('Sistema de agentes v2 não disponível');
        }
    }

    // ===============================================
    // ===== ANÁLISE DE RELATOS =====================
    // ===============================================

    /**
     * Analisa um relato individual
     * @param {string} relato - Texto do relato
     * @returns {Promise<object>} Análise do relato
     */
    async analisarRelato(relato) {
        if (!relato || typeof relato !== 'string' || relato.trim().length < 10) {
            throw new Error('Relato deve ter pelo menos 10 caracteres');
        }

        try {
            const analise = await this.api.analisarRelato(relato.trim());
            return this._processarAnaliseRelato(analise, relato);
        } catch (error) {
            console.error('Erro na análise de relato:', error);
            throw new Error('Não foi possível analisar o relato');
        }
    }

    /**
     * Analisa múltiplos relatos em lote
     * @param {string[]} relatos - Array de relatos
     * @returns {Promise<object>} Análises dos relatos
     */
    async analisarRelatosLote(relatos) {
        if (!Array.isArray(relatos) || relatos.length === 0) {
            throw new Error('É necessário fornecer pelo menos um relato');
        }

        const relatosValidos = relatos.filter(r => 
            typeof r === 'string' && r.trim().length >= 10
        );

        if (relatosValidos.length === 0) {
            throw new Error('Nenhum relato válido encontrado');
        }

        try {
            const analises = await this.api.analisarRelatosLote(relatosValidos);
            return this._processarAnaliseRelatosLote(analises, relatosValidos);
        } catch (error) {
            console.error('Erro na análise de relatos em lote:', error);
            throw new Error('Não foi possível analisar os relatos');
        }
    }

    // ===============================================
    // ===== PROCESSAMENTO DE DADOS =================
    // ===============================================

    /**
     * Processa dados de análise agregada
     * @private
     */
    _processarAnaliseAgregada(dados, filtros) {
        const { ida = {}, logistica = {}, inteligencia = {} } = dados;

        // Calcular KPIs principais
        const kpis = this._calcularKPIs(dados);
        
        // Processar dados para gráficos
        const graficos = this._prepararDadosGraficos(dados);
        
        // Gerar insights automáticos
        const insights = this._gerarInsights(dados, filtros);

        return {
            kpis,
            graficos,
            insights,
            dados_brutos: dados,
            filtros_aplicados: filtros,
            metadata: {
                gerado_em: new Date().toISOString(),
                total_viagens_ilicitas: inteligencia.total_viagens || 0,
                tempo_medio_permanencia: logistica.tempo_medio || '0.00',
                fonte: 'Sentinela IA - Análise Agregada'
            }
        };
    }

    /**
     * Processa dados de análise de IA
     * @private
     */
    _processarAnaliseIA(dados, placa) {
        const { rotas = {}, relatos = [], risco = {} } = dados;

        // Classificar nível de risco
        const nivelRisco = this._classificarRisco(risco.final || 0);
        
        // Processar análise de rotas
        const rotasProcessadas = this._processarAnaliseRotas(rotas);
        
        // Processar análise de relatos
        const relatosProcessados = this._processarRelatosIA(relatos);
        
        // Gerar recomendações
        const recomendacoes = this._gerarRecomendacoes(dados);

        return {
            placa,
            nivel_risco: nivelRisco,
            indice_risco_global: Math.round((risco.final || 0) * 100),
            componentes_risco: {
                rotas: Math.round((risco.rotas || 0) * 100),
                relatos: Math.round((risco.relatos || 0) * 100)
            },
            analise_rotas: rotasProcessadas,
            analise_relatos: relatosProcessados,
            recomendacoes,
            dados_originais: dados,
            metadata: {
                analisado_em: new Date().toISOString(),
                modelo_ia: 'Sentinela IA v2.0',
                confiabilidade: this._calcularConfiabilidade(dados)
            }
        };
    }

    /**
     * Processa dados de análise v2
     * @private
     */
    _processarAnaliseV2(dados, placa, tipo) {
        const { success, final_assessment = {}, performance = {} } = dados;

        if (!success) {
            throw new Error(dados.error || 'Análise v2 falhou');
        }

        return {
            placa,
            tipo_analise: tipo,
            sucesso: success,
            avaliacao_final: final_assessment,
            performance: {
                tempo_execucao: dados.execution_time || 0,
                agentes_executados: performance.agents_executed || 0,
                taxa_sucesso: performance.success_rate || 0
            },
            dados_completos: dados,
            metadata: {
                analisado_em: new Date().toISOString(),
                sistema: 'Agentes Especializados v2.0',
                modo: tipo
            }
        };
    }

    /**
     * Processa análise de relato individual
     * @private
     */
    _processarAnaliseRelato(analise, relato) {
        return {
            relato_original: relato,
            classificacao: analise.classe || 'OUTROS',
            pontuacao: analise.pontuacao || 0,
            confianca: this._calcularConfiancaRelato(analise),
            palavras_chave: analise.keywords || [],
            entidades: analise.entidades || [],
            indicadores: analise.indicadores || {},
            probabilidades: analise.probs || {},
            metadata: {
                analisado_em: new Date().toISOString(),
                modelo: 'Análise Semântica',
                tamanho_texto: relato.length
            }
        };
    }

    // ===============================================
    // ===== UTILITÁRIOS DE CÁLCULO =================
    // ===============================================

    /**
     * Calcula KPIs principais
     * @private
     */
    _calcularKPIs(dados) {
        const { inteligencia = {}, logistica = {} } = dados;
        
        return {
            viagens_ilicitas: inteligencia.total_viagens || 0,
            tempo_medio_permanencia: parseFloat(logistica.tempo_medio || 0),
            rota_mais_comum: inteligencia.rotas?.labels?.[0] || 'N/D',
            eficiencia_deteccao: this._calcularEficienciaDeteccao(dados),
            tendencia_atividade: this._calcularTendencia(dados)
        };
    }

    /**
     * Prepara dados para gráficos
     * @private
     */
    _prepararDadosGraficos(dados) {
        const { ida = {}, inteligencia = {} } = dados;
        
        return {
            heatmap_temporal: ida.heatmap_temporal || {},
            sankey_rotas: inteligencia.sankey || {},
            distribuicoes: {
                municipios: ida.municipio || {},
                rodovias: ida.rodovia || {},
                veiculos_modelos: inteligencia.veiculos_modelos || {},
                apreensoes: inteligencia.apreensoes || {}
            }
        };
    }

    /**
     * Gera insights automáticos
     * @private
     */
    _gerarInsights(dados, filtros) {
        const insights = [];
        const { inteligencia = {}, ida = {} } = dados;

        // Insight sobre volume de atividade
        if (inteligencia.total_viagens > 100) {
            insights.push({
                tipo: 'alto_volume',
                titulo: 'Alto Volume de Atividade Detectado',
                descricao: `Foram identificadas ${inteligencia.total_viagens} viagens ilícitas, indicando atividade intensa na região.`,
                prioridade: 'alta'
            });
        }

        // Insight sobre padrões temporais
        if (ida.heatmap_temporal?.z) {
            const padroesNoturnos = this._analisarPadroesNoturnos(ida.heatmap_temporal);
            if (padroesNoturnos.alta_atividade_noturna) {
                insights.push({
                    tipo: 'padrao_temporal',
                    titulo: 'Padrão Noturno Identificado',
                    descricao: 'Alta concentração de atividade ilícita durante o período noturno.',
                    prioridade: 'media'
                });
            }
        }

        return insights;
    }

    /**
     * Classifica nível de risco
     * @private
     */
    _classificarRisco(riscoNumerico) {
        if (riscoNumerico >= 0.8) return { nivel: 'CRÍTICO', cor: '#dc2626' };
        if (riscoNumerico >= 0.6) return { nivel: 'ALTO', cor: '#ea580c' };
        if (riscoNumerico >= 0.4) return { nivel: 'MÉDIO', cor: '#d97706' };
        if (riscoNumerico >= 0.2) return { nivel: 'BAIXO', cor: '#65a30d' };
        return { nivel: 'MÍNIMO', cor: '#16a34a' };
    }

    // ===============================================
    // ===== CACHE E UTILITÁRIOS ====================
    // ===============================================

    /**
     * Gera chave única para cache
     * @private
     */
    _gerarChaveCache(tipo, dados) {
        const dadosString = JSON.stringify(dados);
        const hash = this._hashSimples(dadosString);
        return `${tipo}_${hash}`;
    }

    /**
     * Hash simples para cache
     * @private
     */
    _hashSimples(str) {
        let hash = 0;
        for (let i = 0; i < str.length; i++) {
            const char = str.charCodeAt(i);
            hash = ((hash << 5) - hash) + char;
            hash = hash & hash; // 32-bit
        }
        return Math.abs(hash).toString(36);
    }

    /**
     * Limpa cache de análises
     */
    limparCache() {
        this.cache.clear();
        this.filtrosCache = null;
        this.filtrosCacheTime = null;
    }

    /**
     * Obtém estatísticas do cache
     */
    obterEstatisticasCache() {
        return {
            total_entradas: this.cache.size,
            cache_filtros: !!this.filtrosCache,
            timeout_configurado: this.cacheTimeout,
            memoria_aproximada: this.cache.size * 2048 // Estimativa em bytes
        };
    }

    /**
     * Verifica disponibilidade de funcionalidades
     */
    async verificarDisponibilidade() {
        const status = {
            analise_agregada: false,
            analise_ia: false,
            analise_v2: false,
            analise_relatos: false
        };

        try {
            // Testar análise agregada
            await this.api.obterFiltrosAnalise();
            status.analise_agregada = true;
        } catch {}

        try {
            // Testar análise v2
            await this.api.verificarSaudeV2();
            status.analise_v2 = true;
        } catch {}

        // Outras verificações...
        status.analise_ia = true; // Assumir disponível
        status.analise_relatos = true; // Assumir disponível

        return status;
    }
}

// ===============================================
// ===== INSTÂNCIA E EXPORTAÇÃO =================
// ===============================================

const analiseService = new AnaliseService();

export default analiseService;

// Exportações nomeadas para conveniência
export const {
    validarFiltros,
    obterFiltros,
    gerarAnaliseAgregada,
    analisarPlacaIA,
    analisarPlacaV2,
    analisarRelato,
    analisarRelatosLote,
    limparCache,
    verificarDisponibilidade
} = analiseService;