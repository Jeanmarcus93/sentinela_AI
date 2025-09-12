// services/formatters.js - Formatadores centralizados para o Sentinela IA

/**
 * Biblioteca de formatadores para padronizar exibição de dados
 * Centraliza todas as funções de formatação usadas no sistema
 */
class Formatters {
    constructor() {
        // Configurações regionais do Brasil
        this.locale = 'pt-BR';
        this.timezone = 'America/Sao_Paulo';
        
        // Mapas de conversão
        this.estadosMap = new Map([
            ['AC', 'Acre'], ['AL', 'Alagoas'], ['AP', 'Amapá'], ['AM', 'Amazonas'],
            ['BA', 'Bahia'], ['CE', 'Ceará'], ['DF', 'Distrito Federal'], ['ES', 'Espírito Santo'],
            ['GO', 'Goiás'], ['MA', 'Maranhão'], ['MT', 'Mato Grosso'], ['MS', 'Mato Grosso do Sul'],
            ['MG', 'Minas Gerais'], ['PA', 'Pará'], ['PB', 'Paraíba'], ['PR', 'Paraná'],
            ['PE', 'Pernambuco'], ['PI', 'Piauí'], ['RJ', 'Rio de Janeiro'], ['RN', 'Rio Grande do Norte'],
            ['RS', 'Rio Grande do Sul'], ['RO', 'Rondônia'], ['RR', 'Roraima'], ['SC', 'Santa Catarina'],
            ['SP', 'São Paulo'], ['SE', 'Sergipe'], ['TO', 'Tocantins']
        ]);

        this.tiposOcorrenciaMap = new Map([
            ['Abordagem', 'Abordagem Policial'],
            ['BOP', 'Boletim de Ocorrência Policial'],
            ['Local de Entrega', 'Local de Entrega da Droga'],
            ['Fiscalizacao', 'Fiscalização de Rotina'],
            ['Operacao', 'Operação Especial']
        ]);
    }

    // ===============================================
    // ===== FORMATAÇÃO DE DATAS ====================
    // ===============================================

    /**
     * Formata data para padrão brasileiro
     * @param {string|Date} data - Data a ser formatada
     * @param {string} formato - 'completo', 'data', 'hora', 'relativo'
     * @returns {string} Data formatada
     */
    formatarData(data, formato = 'completo') {
        if (!data) return 'N/D';

        try {
            const dateObj = data instanceof Date ? data : new Date(data);
            if (isNaN(dateObj.getTime())) return 'Data inválida';

            switch (formato) {
                case 'data':
                    return dateObj.toLocaleDateString(this.locale);
                
                case 'hora':
                    return dateObj.toLocaleTimeString(this.locale, { 
                        hour: '2-digit', 
                        minute: '2-digit' 
                    });
                
                case 'completo':
                    return dateObj.toLocaleString(this.locale, {
                        day: '2-digit',
                        month: '2-digit', 
                        year: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit'
                    });
                
                case 'relativo':
                    return this._formatarDataRelativa(dateObj);
                
                case 'extenso':
                    return dateObj.toLocaleDateString(this.locale, {
                        weekday: 'long',
                        year: 'numeric',
                        month: 'long',
                        day: 'numeric'
                    });
                
                case 'iso':
                    return dateObj.toISOString();
                
                default:
                    return dateObj.toLocaleString(this.locale);
            }
        } catch (error) {
            console.warn('Erro ao formatar data:', error);
            return String(data);
        }
    }

    /**
     * Formata data relativa (há 2 horas, ontem, etc.)
     * @private
     */
    _formatarDataRelativa(data) {
        const agora = new Date();
        const diffMs = agora.getTime() - data.getTime();
        const diffMinutos = Math.floor(diffMs / (1000 * 60));
        const diffHoras = Math.floor(diffMs / (1000 * 60 * 60));
        const diffDias = Math.floor(diffMs / (1000 * 60 * 60 * 24));

        if (diffMinutos < 1) return 'Agora mesmo';
        if (diffMinutos < 60) return `Há ${diffMinutos} minuto${diffMinutos > 1 ? 's' : ''}`;
        if (diffHoras < 24) return `Há ${diffHoras} hora${diffHoras > 1 ? 's' : ''}`;
        if (diffDias === 1) return 'Ontem';
        if (diffDias < 7) return `Há ${diffDias} dias`;
        if (diffDias < 30) return `Há ${Math.floor(diffDias / 7)} semana${Math.floor(diffDias / 7) > 1 ? 's' : ''}`;
        if (diffDias < 365) return `Há ${Math.floor(diffDias / 30)} mês${Math.floor(diffDias / 30) > 1 ? 'es' : ''}`;
        
        return `Há ${Math.floor(diffDias / 365)} ano${Math.floor(diffDias / 365) > 1 ? 's' : ''}`;
    }

    /**
     * Converte data brasileira para ISO
     * @param {string} dataBrasileira - Data no formato dd/mm/yyyy hh:mm
     * @returns {string} Data no formato ISO
     */
    converterDataBrasileiraParaISO(dataBrasileira) {
        if (!dataBrasileira) return null;
        
        const regex = /^(\d{2})\/(\d{2})\/(\d{4})(?:\s+(\d{2}):(\d{2}))?$/;
        const match = dataBrasileira.match(regex);
        
        if (!match) return null;
        
        const [, dia, mes, ano, hora = '00', minuto = '00'] = match;
        return `${ano}-${mes}-${dia}T${hora}:${minuto}`;
    }

    // ===============================================
    // ===== FORMATAÇÃO DE DOCUMENTOS ===============
    // ===============================================

    /**
     * Formata CPF/CNPJ para exibição
     * @param {string} documento - Documento sem formatação
     * @param {boolean} ocultar - Se deve ocultar parte do documento
     * @returns {string} Documento formatado
     */
    formatarDocumento(documento, ocultar = false) {
        if (!documento) return 'N/D';
        
        const limpo = documento.replace(/\D/g, '');
        
        if (limpo.length === 11) {
            // CPF: 123.456.789-01
            const formatado = limpo.replace(/(\d{3})(\d{3})(\d{3})(\d{2})/, '$1.$2.$3-$4');
            return ocultar ? formatado.replace(/\d{3}\.\d{3}/, '***.***.') : formatado;
        } else if (limpo.length === 14) {
            // CNPJ: 12.345.678/0001-01
            const formatado = limpo.replace(/(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})/, '$1.$2.$3/$4-$5');
            return ocultar ? formatado.replace(/\d{2}\.\d{3}\.\d{3}/, '**.***.***.') : formatado;
        }
        
        return limpo;
    }

    /**
     * Detecta tipo de documento
     * @param {string} documento - Documento a ser analisado
     * @returns {string} 'CPF', 'CNPJ' ou 'INVÁLIDO'
     */
    detectarTipoDocumento(documento) {
        if (!documento) return 'INVÁLIDO';
        
        const limpo = documento.replace(/\D/g, '');
        
        if (limpo.length === 11) return 'CPF';
        if (limpo.length === 14) return 'CNPJ';
        return 'INVÁLIDO';
    }

    // ===============================================
    // ===== FORMATAÇÃO DE PLACAS ===================
    // ===============================================

    /**
     * Formata placa para exibição
     * @param {string} placa - Placa sem formatação
     * @param {boolean} detectarTipo - Se deve detectar o tipo da placa
     * @returns {string|object} Placa formatada ou objeto com detalhes
     */
    formatarPlaca(placa, detectarTipo = false) {
        if (!placa) return detectarTipo ? { formatada: 'N/D', tipo: 'INVÁLIDO' } : 'N/D';
        
        const placaLimpa = placa.trim().toUpperCase().replace(/[^A-Z0-9]/g, '');
        
        let formatada = placaLimpa;
        let tipo = 'INVÁLIDO';
        
        // Formato Mercosul: ABC1D23 → ABC-1D23
        if (/^[A-Z]{3}\d[A-Z]\d{2}$/.test(placaLimpa)) {
            formatada = placaLimpa.replace(/^([A-Z]{3})(\d[A-Z]\d{2})$/, '$1-$2');
            tipo = 'MERCOSUL';
        }
        // Formato antigo: ABC1234 → ABC-1234
        else if (/^[A-Z]{3}\d{4}$/.test(placaLimpa)) {
            formatada = placaLimpa.replace(/^([A-Z]{3})(\d{4})$/, '$1-$2');
            tipo = 'TRADICIONAL';
        }
        
        return detectarTipo ? { formatada, tipo, original: placa } : formatada;
    }

    /**
     * Valida formato de placa
     * @param {string} placa - Placa a ser validada
     * @returns {boolean} True se válida
     */
    validarPlaca(placa) {
        if (!placa) return false;
        
        const placaLimpa = placa.trim().toUpperCase().replace(/[^A-Z0-9]/g, '');
        
        // Formatos válidos
        const formatoTradicional = /^[A-Z]{3}\d{4}$/;
        const formatoMercosul = /^[A-Z]{3}\d[A-Z]\d{2}$/;
        
        return formatoTradicional.test(placaLimpa) || formatoMercosul.test(placaLimpa);
    }

    // ===============================================
    // ===== FORMATAÇÃO DE VALORES ==================
    // ===============================================

    /**
     * Formata valores monetários
     * @param {number|string} valor - Valor a ser formatado
     * @param {string} moeda - Código da moeda (BRL, USD, etc.)
     * @returns {string} Valor formatado
     */
    formatarMoeda(valor, moeda = 'BRL') {
        if (valor === null || valor === undefined || valor === '') return 'N/D';
        
        const numero = typeof valor === 'string' ? parseFloat(valor) : valor;
        if (isNaN(numero)) return 'Valor inválido';
        
        return new Intl.NumberFormat(this.locale, {
            style: 'currency',
            currency: moeda,
            minimumFractionDigits: 2
        }).format(numero);
    }

    /**
     * Formata números com separadores
     * @param {number|string} numero - Número a ser formatado
     * @param {number} decimais - Número de casas decimais
     * @returns {string} Número formatado
     */
    formatarNumero(numero, decimais = 0) {
        if (numero === null || numero === undefined || numero === '') return 'N/D';
        
        const num = typeof numero === 'string' ? parseFloat(numero) : numero;
        if (isNaN(num)) return 'Número inválido';
        
        return new Intl.NumberFormat(this.locale, {
            minimumFractionDigits: decimais,
            maximumFractionDigits: decimais
        }).format(num);
    }

    /**
     * Formata porcentagens
     * @param {number|string} valor - Valor a ser formatado (0-1 ou 0-100)
     * @param {number} decimais - Casas decimais
     * @param {boolean} deZeroAUm - Se o valor está entre 0-1 (true) ou 0-100 (false)
     * @returns {string} Porcentagem formatada
     */
    formatarPorcentagem(valor, decimais = 1, deZeroAUm = true) {
        if (valor === null || valor === undefined || valor === '') return 'N/D';
        
        const num = typeof valor === 'string' ? parseFloat(valor) : valor;
        if (isNaN(num)) return 'Porcentagem inválida';
        
        const percentual = deZeroAUm ? num : num / 100;
        
        return new Intl.NumberFormat(this.locale, {
            style: 'percent',
            minimumFractionDigits: decimais,
            maximumFractionDigits: decimais
        }).format(percentual);
    }

    // ===============================================
    // ===== FORMATAÇÃO DE TEXTO ====================
    // ===============================================

    /**
     * Trunca texto com reticências
     * @param {string} texto - Texto a ser truncado
     * @param {number} limite - Limite de caracteres
     * @param {boolean} quebrarPalavra - Se pode quebrar no meio da palavra
     * @returns {string} Texto truncado
     */
    truncarTexto(texto, limite = 100, quebrarPalavra = false) {
        if (!texto || typeof texto !== 'string') return '';
        if (texto.length <= limite) return texto;
        
        if (quebrarPalavra) {
            return texto.substring(0, limite) + '...';
        }
        
        // Tenta quebrar em espaço mais próximo
        const cortado = texto.substring(0, limite);
        const ultimoEspaco = cortado.lastIndexOf(' ');
        
        if (ultimoEspaco > limite * 0.8) { // Se o espaço não está muito no início
            return cortado.substring(0, ultimoEspaco) + '...';
        }
        
        return cortado + '...';
    }

    /**
     * Capitaliza primeira letra de cada palavra
     * @param {string} texto - Texto a ser capitalizado
     * @returns {string} Texto capitalizado
     */
    capitalizarTexto(texto) {
        if (!texto || typeof texto !== 'string') return '';
        
        return texto
            .toLowerCase()
            .split(' ')
            .map(palavra => palavra.charAt(0).toUpperCase() + palavra.slice(1))
            .join(' ');
    }

    /**
     * Remove acentos do texto
     * @param {string} texto - Texto com acentos
     * @returns {string} Texto sem acentos
     */
    removerAcentos(texto) {
        if (!texto || typeof texto !== 'string') return '';
        
        return texto.normalize('NFD').replace(/[\u0300-\u036f]/g, '');
    }

    // ===============================================
    // ===== FORMATAÇÃO ESPECÍFICA DO SISTEMA =======
    // ===============================================

    /**
     * Formata tipo de ocorrência
     * @param {string} tipo - Tipo bruto da ocorrência
     * @returns {string} Tipo formatado
     */
    formatarTipoOcorrencia(tipo) {
        if (!tipo) return 'Não especificado';
        return this.tiposOcorrenciaMap.get(tipo) || tipo;
    }

    /**
     * Formata nível de risco com cor
     * @param {number|string} risco - Valor do risco (0-1 ou 0-100)
     * @param {boolean} incluirCor - Se deve incluir código de cor
     * @returns {string|object} Risco formatado
     */
    formatarNivelRisco(risco, incluirCor = false) {
        if (risco === null || risco === undefined) {
            return incluirCor ? { texto: 'N/D', cor: '#6b7280' } : 'N/D';
        }
        
        const valor = typeof risco === 'string' ? parseFloat(risco) : risco;
        const percentual = valor > 1 ? valor : valor * 100;
        
        let nivel, cor;
        
        if (percentual >= 80) {
            nivel = 'CRÍTICO';
            cor = '#dc2626'; // Vermelho
        } else if (percentual >= 60) {
            nivel = 'ALTO';
            cor = '#ea580c'; // Laranja escuro
        } else if (percentual >= 40) {
            nivel = 'MÉDIO';
            cor = '#d97706'; // Amarelo escuro
        } else if (percentual >= 20) {
            nivel = 'BAIXO';
            cor = '#65a30d'; // Verde claro
        } else {
            nivel = 'MÍNIMO';
            cor = '#16a34a'; // Verde
        }
        
        const texto = `${nivel} (${percentual.toFixed(0)}%)`;
        
        return incluirCor ? { texto, cor, nivel, percentual } : texto;
    }

    /**
     * Formata estado por sigla
     * @param {string} sigla - Sigla do estado
     * @param {boolean} completo - Se deve retornar nome completo
     * @returns {string} Estado formatado
     */
    formatarEstado(sigla, completo = false) {
        if (!sigla) return 'N/D';
        
        const siglaLimpa = sigla.trim().toUpperCase();
        const nomeCompleto = this.estadosMap.get(siglaLimpa);
        
        if (completo) {
            return nomeCompleto || siglaLimpa;
        }
        
        return nomeCompleto ? `${nomeCompleto} (${siglaLimpa})` : siglaLimpa;
    }

    /**
     * Formata quantidade de apreensão
     * @param {number|string} quantidade - Quantidade
     * @param {string} unidade - Unidade (kg, g, un)
     * @returns {string} Quantidade formatada
     */
    formatarApreensao(quantidade, unidade) {
        if (!quantidade || !unidade) return 'N/D';
        
        const qtd = typeof quantidade === 'string' ? parseFloat(quantidade) : quantidade;
        if (isNaN(qtd)) return 'Quantidade inválida';
        
        const unidadeFormatada = unidade.toLowerCase();
        let textoUnidade;
        
        switch (unidadeFormatada) {
            case 'kg':
                textoUnidade = qtd === 1 ? 'quilograma' : 'quilogramas';
                break;
            case 'g':
                textoUnidade = qtd === 1 ? 'grama' : 'gramas';
                break;
            case 'un':
                textoUnidade = qtd === 1 ? 'unidade' : 'unidades';
                break;
            default:
                textoUnidade = unidade;
        }
        
        return `${this.formatarNumero(qtd, unidadeFormatada === 'kg' ? 2 : 0)} ${textoUnidade}`;
    }

    // ===============================================
    // ===== UTILITÁRIOS ============================
    // ===============================================

    /**
     * Escapa HTML para prevenir XSS
     * @param {string} texto - Texto a ser escapado
     * @returns {string} Texto escapado
     */
    escaparHTML(texto) {
        if (!texto || typeof texto !== 'string') return '';
        
        const div = document.createElement('div');
        div.textContent = texto;
        return div.innerHTML;
    }

    /**
     * Formata lista de itens
     * @param {Array} items - Lista de itens
     * @param {string} separador - Separador padrão
     * @param {string} ultimoSeparador - Separador para último item
     * @returns {string} Lista formatada
     */
    formatarLista(items, separador = ', ', ultimoSeparador = ' e ') {
        if (!Array.isArray(items) || items.length === 0) return '';
        if (items.length === 1) return String(items[0]);
        if (items.length === 2) return items.join(ultimoSeparador);
        
        const iniciais = items.slice(0, -1).join(separador);
        const ultimo = items[items.length - 1];
        
        return iniciais + ultimoSeparador + ultimo;
    }

    /**
     * Valida se um valor está definido e não é vazio
     * @param {any} valor - Valor a ser validado
     * @returns {boolean} True se valor é válido
     */
    temValor(valor) {
        return valor !== null && 
               valor !== undefined && 
               valor !== '' && 
               (!Array.isArray(valor) || valor.length > 0) &&
               (typeof valor !== 'object' || Object.keys(valor).length > 0);
    }
}

// ===============================================
// ===== INSTÂNCIA E EXPORTAÇÃO =================
// ===============================================

const formatters = new Formatters();

export default formatters;

// Exportações nomeadas para conveniência
export const {
    formatarData,
    formatarDocumento,
    formatarPlaca,
    formatarMoeda,
    formatarNumero,
    formatarPorcentagem,
    truncarTexto,
    capitalizarTexto,
    formatarTipoOcorrencia,
    formatarNivelRisco,
    formatarEstado,
    formatarApreensao,
    validarPlaca,
    detectarTipoDocumento,
    removerAcentos,
    escaparHTML,
    formatarLista,
    temValor
} = formatters;