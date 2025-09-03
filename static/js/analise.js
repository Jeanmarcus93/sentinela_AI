// ===============================================
// ===== FUNÇÕES DA PÁGINA DE ANÁLISE ============
// ===============================================

/**
 * Configura os event listeners para os componentes de dropdown com checkboxes.
 * Esta função gere a abertura, o fecho e a atualização visual dos menus de seleção.
 */
function setupCustomSelects() {
    // Adiciona um listener de clique global para gerir os dropdowns.
    // Usar 'event delegation' é mais eficiente do que adicionar um listener a cada botão.
    document.addEventListener('click', e => {
        const button = e.target.closest('.custom-select-button');
        
        // Se o elemento clicado for um botão de dropdown
        if (button) {
            const targetId = button.dataset.target;
            const options = document.getElementById(targetId);
            if (options) {
                // Fecha todos os outros dropdowns que possam estar abertos para evitar sobreposição.
                document.querySelectorAll('.custom-select-options.show').forEach(openSelect => {
                    if (openSelect.id !== targetId) {
                        openSelect.classList.remove('show');
                    }
                });
                // Alterna a visibilidade (abre/fecha) do dropdown que foi clicado.
                options.classList.toggle('show');
            }
        } else if (!e.target.closest('.custom-select-options')) {
            // Se o clique ocorrer fora de qualquer menu de opções, fecha todos os que estiverem abertos.
            document.querySelectorAll('.custom-select-options.show').forEach(openSelect => {
                openSelect.classList.remove('show');
            });
        }
    });

    /**
     * Função interna para atualizar o texto do botão do dropdown com base nos itens selecionados.
     * @param {HTMLElement} optionsContainer - O container das checkboxes (ex: 'analise-locais-options').
     */
    const updateButtonText = (optionsContainer) => {
        const selectedCheckboxes = optionsContainer.querySelectorAll('input[type="checkbox"]:checked');
        const button = optionsContainer.previousElementSibling; // O botão é o elemento irmão anterior.
        const textElement = button.querySelector('.selected-items-text');

        if (selectedCheckboxes.length === 0) {
            // Se nada estiver selecionado, mostra o texto do placeholder.
            textElement.textContent = button.dataset.placeholder || 'Selecione...';
            textElement.style.color = '#6b7280'; // Cor cinza para o placeholder.
        } else if (selectedCheckboxes.length === 1) {
            // Se um item estiver selecionado, mostra o nome desse item.
            textElement.textContent = selectedCheckboxes[0].value;
            textElement.style.color = '#111827'; // Cor de texto normal.
        } else {
            // Se vários itens estiverem selecionados, mostra a contagem.
            textElement.textContent = `${selectedCheckboxes.length} itens selecionados`;
            textElement.style.color = '#111827';
        }
    };
    
    /**
     * Função interna para configurar o listener de 'change' para um container de checkboxes.
     * @param {string} containerId - O ID do container das checkboxes.
     * @param {string} placeholder - O texto a ser exibido no botão quando nada estiver selecionado.
     */
    const setupChangeListener = (containerId, placeholder) => {
        const optionsContainer = document.getElementById(containerId);
        if (optionsContainer) {
            // Ouve o evento 'change' que ocorre quando uma checkbox é marcada ou desmarcada.
            optionsContainer.addEventListener('change', () => updateButtonText(optionsContainer));
            // Guarda o texto do placeholder no próprio botão para referência futura.
            optionsContainer.previousElementSibling.dataset.placeholder = placeholder;
        }
    };

    // Configura os listeners para cada um dos dropdowns da página.
    setupChangeListener('analise-locais-options', 'Selecione os locais...');
    setupChangeListener('analise-apreensoes-options', 'Selecione os tipos...');
}


/**
 * Carrega os filtros (locais e tipos de apreensão) da API e preenche os dropdowns com as checkboxes.
 */
async function loadAnaliseFilters() {
    try {
        const response = await fetch('/api/analise/filtros');
        if (!response.ok) {
            throw new Error('Falha ao carregar filtros do servidor.');
        }
        const data = await response.json();
        
        /**
         * Função interna para popular um container de dropdown com checkboxes a partir de uma lista de itens.
         * @param {string} containerId - O ID do container onde as checkboxes serão inseridas.
         * @param {string[]} items - Uma lista de strings, onde cada string será uma opção.
         */
        const populateCustomSelect = (containerId, items) => {
            const container = document.getElementById(containerId);
            if (!container) return; // Sai se o container não for encontrado.
            
            container.innerHTML = ''; // Limpa quaisquer opções antigas para evitar duplicação.
            
            items.forEach(item => {
                const label = document.createElement('label');
                // **CORREÇÃO CRÍTICA**: Adiciona um listener de clique na label.
                // `e.stopPropagation()` impede que o evento de clique "borbulhe" para o document,
                // o que faria com que o menu se fechasse imediatamente após um clique.
                label.addEventListener('click', e => e.stopPropagation());
                label.innerHTML = `<input type="checkbox" value="${item}"> ${item}`;
                container.appendChild(label);
            });
        };
        
        populateCustomSelect('analise-locais-options', data.locais);
        populateCustomSelect('analise-apreensoes-options', data.apreensoes);

    } catch (error) {
        console.error('Erro ao carregar filtros de análise:', error);
        document.getElementById('analise-resultados').innerHTML = `<p class="text-red-500">❌ Erro ao carregar filtros. Verifique a conexão com o servidor.</p>`;
    }
}

/**
 * Coleta todos os filtros selecionados pelo utilizador, envia o pedido para a API de análise e inicia a renderização dos resultados.
 */
async function handleAnaliseGeneration() {
    const resultadosContainer = document.getElementById('analise-resultados');
    
    /**
     * Função interna para obter os valores de todas as checkboxes marcadas dentro de um container.
     * @param {string} containerId - O ID do container das checkboxes.
     * @returns {string[]} Uma lista com os valores selecionados.
     */
    const getSelectedValues = (containerId) => {
        return Array.from(document.querySelectorAll(`#${containerId} input[type="checkbox"]:checked`))
                    .map(cb => cb.value);
    };

    // Obtém os valores de todos os campos de filtro.
    const locais = getSelectedValues('analise-locais-options');
    const apreensoes = getSelectedValues('analise-apreensoes-options');
    const placa = document.getElementById('analise-placa').value.toUpperCase();
    const dataInicio = document.getElementById('analise-data-inicio').value;
    const dataFim = document.getElementById('analise-data-fim').value;

    showLoader(resultadosContainer); // Mostra o loader enquanto os dados são processados.

    // Constrói os parâmetros da URL para o pedido à API.
    const params = new URLSearchParams();
    locais.forEach(local => params.append('locais', local));
    apreensoes.forEach(item => params.append('apreensoes', item));
    if (placa) params.append('placa', placa);
    if (dataInicio) params.append('data_inicio', dataInicio);
    if (dataFim) params.append('data_fim', dataFim);
    
    try {
        const response = await fetch(`/api/analise?${params.toString()}`);
        const data = await response.json();
        if (response.ok) {
            displayAnaliseResults(data, resultadosContainer); // Se o pedido for bem-sucedido, mostra os resultados.
        } else {
            throw new Error(data.error); // Se houver um erro, lança-o para ser capturado pelo catch.
        }
    } catch (error) {
        resultadosContainer.innerHTML = `<p class="text-red-500">❌ Ocorreu um erro ao gerar a análise: ${error.message}</p>`;
        console.error('Erro na requisição da análise:', error);
    }
}

/**
 * Renderiza os KPIs (Key Performance Indicators) e prepara os containers para os gráficos de análise.
 * @param {object} data - Os dados de análise retornados pela API.
 * @param {HTMLElement} container - O elemento HTML onde os resultados serão exibidos.
 */
function displayAnaliseResults(data, container) {
    const kpisHtml = `
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
            <div class="kpi-box"><div class="kpi-value">${data.inteligencia.total_viagens}</div><div class="kpi-label">Viagens Ilícitas Detectadas</div></div>
            <div class="kpi-box"><div class="kpi-value">${data.logistica.tempo_medio}h</div><div class="kpi-label">Tempo Médio de Permanência</div></div>
            <div class="kpi-box"><div class="kpi-value">${data.inteligencia.rotas.labels.length > 0 ? data.inteligencia.rotas.labels[0] : 'N/D'}</div><div class="kpi-label">Rota Mais Comum</div></div>
        </div>
    `;

    // **NOVO**: Adiciona os placeholders para os novos gráficos
    const chartsHtml = `
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div class="chart-container md:col-span-2"><h3 class="text-lg">Fluxo de Rotas (Origem / Destino)</h3><div id="chart-sankey" class="flex-grow"></div></div>
            <div class="chart-container"><h3 class="text-lg">Heatmap de Atividade (Dia vs. Hora)</h3><div id="chart-heatmap-temporal" class="flex-grow"></div></div>
            <div class="chart-container"><h3 class="text-lg">Mapa de Atividade Geográfica</h3><div id="chart-geo-map" class="flex-grow"></div></div>
            
            <div class="chart-container"><h3 class="text-lg">Rotas Mais Comuns</h3><div id="chart-rotas" class="flex-grow"></div></div>
            <div class="chart-container"><h3 class="text-lg">Localizações Mais Comuns (Ida)</h3><div id="chart-ida-locais" class="flex-grow"></div></div>
            <div class="chart-container"><h3 class="text-lg">Rodovias Mais Comuns (Ida)</h3><div id="chart-ida-rodovias" class="flex-grow"></div></div>
            <div class="chart-container"><h3 class="text-lg">Apreensões Mais Frequentes</h3><div id="chart-apreensoes" class="flex-grow"></div></div>
            <div class="chart-container"><h3 class="text-lg">Modelos de Veículos (Viagens Ilícitas)</h3><div id="chart-veiculos" class="flex-grow"></div></div>
            <div class="chart-container"><h3 class="text-lg">Cores de Veículos (Viagens Ilícitas)</h3><div id="chart-cores" class="flex-grow"></div></div>
        </div>
    `;

    container.innerHTML = kpisHtml + chartsHtml;

    // **NOVO**: Chama as funções para renderizar os novos gráficos
    if (data.inteligencia.sankey && data.inteligencia.sankey.source && data.inteligencia.sankey.source.length > 0) {
        renderSankeyDiagram('chart-sankey', data.inteligencia.sankey);
    }
     if (data.ida.heatmap_temporal && data.ida.heatmap_temporal.z && data.ida.heatmap_temporal.z.length > 0) {
        renderTemporalHeatmap('chart-heatmap-temporal', data.ida.heatmap_temporal);
    }
    // A função do mapa é chamada, mas precisa de coordenadas para funcionar
    renderGeoMap('chart-geo-map', data.ida.pontos_geograficos, data.inteligencia.rotas_geograficas);
    
    // Chama a função para renderizar cada gráfico, verificando se há dados para ele.
    if (data.ida.municipio && data.ida.municipio.labels.length > 0) {
        renderPlotlyChart('chart-ida-locais', data.ida.municipio, 'bar', 'h');
    }
    if (data.ida.rodovia && data.ida.rodovia.labels.length > 0) {
        renderPlotlyChart('chart-ida-rodovias', data.ida.rodovia, 'bar', 'h');
    }
    if (data.inteligencia.rotas && data.inteligencia.rotas.labels.length > 0) {
        renderPlotlyChart('chart-rotas', data.inteligencia.rotas, 'bar', 'h');
    }
    if (data.inteligencia.veiculos_modelos && data.inteligencia.veiculos_modelos.labels.length > 0) {
        renderPlotlyChart('chart-veiculos', data.inteligencia.veiculos_modelos, 'pie');
    }
    if (data.inteligencia.veiculos_cores && data.inteligencia.veiculos_cores.labels.length > 0) {
        renderPlotlyChart('chart-cores', data.inteligencia.veiculos_cores, 'pie');
    }
    if (data.inteligencia.apreensoes && data.inteligencia.apreensoes.labels.length > 0) {
        renderPlotlyChart('chart-apreensoes', data.inteligencia.apreensoes, 'bar', 'h');
    }
}

/**
 * Renderiza um gráfico usando a biblioteca Plotly.js.
 * @param {string} elementId - O ID do elemento HTML onde o gráfico será renderizado.
 * @param {object} chartData - Objeto com 'labels' e 'data' para o gráfico.
 * @param {string} type - O tipo de gráfico ('bar' ou 'pie').
 * @param {string} [orientation='v'] - A orientação do gráfico de barras ('v' para vertical, 'h' para horizontal).
 */
function renderPlotlyChart(elementId, chartData, type, orientation = 'v') {
    const element = document.getElementById(elementId);
    if (!element) return; // Sai se o elemento não existir.
    
    // Se não houver dados, exibe uma mensagem.
    if (!chartData || !chartData.labels || !chartData.data || chartData.data.length === 0) {
        element.innerHTML = '<p class="text-gray-500 text-center mt-4">Sem dados para exibir.</p>';
        return;
    }

    let data;
    let layout;

    if (type === 'pie') {
        data = [{
            values: chartData.data,
            labels: chartData.labels,
            type: 'pie',
            hole: .4,
            textinfo: 'label+percent',
            hoverinfo: 'label+percent+value',
        }];
        layout = {
            margin: { t: 10, b: 10, l: 10, r: 10 },
            showlegend: true,
            legend: { x: 0.5, y: -0.2, xanchor: 'center', orientation: 'h' }
        };
    } else { // bar chart
        data = [{
            x: orientation === 'h' ? chartData.data : chartData.labels,
            y: orientation === 'h' ? chartData.labels : chartData.data,
            type: 'bar',
            orientation: orientation,
            marker: { color: '#4f46e5' }
        }];
        layout = {
            margin: { t: 20, b: 40, l: orientation === 'h' ? 120 : 40, r: 20 },
            xaxis: { title: orientation === 'h' ? 'Quantidade' : '' },
            yaxis: { title: orientation === 'v' ? 'Quantidade' : '' }
        };
    }

    Plotly.newPlot(element, data, layout, { responsive: true, displayModeBar: false });
}

// ===============================================
// ===== NOVAS FUNÇÕES DE GRÁFICOS AVANÇADOS =====
// ===============================================

/**
 * NOVO: Renderiza um heatmap de atividade por dia da semana vs. hora.
 */
function renderTemporalHeatmap(elementId, chartData) {
    const element = document.getElementById(elementId);
    if (!element) return;
    if (!chartData || chartData.z.length === 0) {
        element.innerHTML = '<p class="text-gray-500 text-center mt-4">Sem dados para exibir.</p>';
        return;
    }

    const data = [{
        z: chartData.z,
        x: chartData.x,
        y: chartData.y,
        type: 'heatmap',
        colorscale: 'Viridis',
        reversescale: true
    }];

    const layout = {
        title: 'Picos de Atividade Ilícita',
        margin: { t: 40, b: 50, l: 50, r: 20 },
        xaxis: { title: 'Hora do Dia' },
        yaxis: { title: 'Dia da Semana' }
    };

    Plotly.newPlot(element, data, layout, { responsive: true, displayModeBar: false });
}

/**
 * NOVO: Renderiza um Diagrama de Sankey para fluxos de rotas.
 */
function renderSankeyDiagram(elementId, chartData) {
    const element = document.getElementById(elementId);
    if (!element) return;
     if (!chartData || chartData.source.length === 0) {
        element.innerHTML = '<p class="text-gray-500 text-center mt-4">Sem dados para exibir.</p>';
        return;
    }
    
    const data = [{
        type: "sankey",
        orientation: "h",
        node: {
            pad: 15,
            thickness: 20,
            line: { color: "black", width: 0.5 },
            label: chartData.labels,
            color: "#4f46e5"
        },
        link: {
            source: chartData.source,
            target: chartData.target,
            value: chartData.value
        }
    }];

    const layout = {
        title: "Fluxo das Principais Rotas Ilícitas",
        margin: { t: 40, b: 10, l: 10, r: 10 }
    };

    Plotly.newPlot(element, data, layout, { responsive: true, displayModeBar: false });
}

/**
 * NOVO: Template para renderizar um mapa geográfico.
 * ATENÇÃO: Esta função requer uma forma de obter coordenadas (lat/lon) para os municípios.
 * E também um TOKEN DE ACESSO do Mapbox.
 */
async function renderGeoMap(elementId, pontosData, rotasData) {
    const element = document.getElementById(elementId);
    if (!element) return;

    element.innerHTML = '<p class="text-gray-500 text-center mt-4">Funcionalidade de mapa requer configuração de geolocalização.</p>';

    // --- CÓDIGO ABAIXO É UM EXEMPLO FUNCIONAL SE VOCÊ TIVER OS DADOS ---
    // Para funcionar, você precisa de:
    // 1. Um token do Mapbox. Crie uma conta em https://www.mapbox.com/
    // 2. Um jeito de transformar nome de cidade em [longitude, latitude].
    //    Ex: ter uma tabela no banco de dados ou usar uma API de Geocoding.
    /*
    const MAPBOX_TOKEN = 'SEU_TOKEN_AQUI'; 
    if (MAPBOX_TOKEN === 'SEU_TOKEN_AQUI') return;

    // Função de exemplo para buscar coordenadas (substitua pela sua lógica)
    const getCoords = async (municipio) => {
        // Exemplo: fetch(`https://api.mapbox.com/geocoding/v5/mapbox.places/${municipio}.json?access_token=${MAPBOX_TOKEN}`)
        // Esta é uma simulação. NÃO USE EM PRODUÇÃO.
        const cityCoords = { "CIDADE A": [-46.6, -23.5], "CIDADE B": [-43.2, -22.9] };
        return cityCoords[municipio] || [0,0];
    };
    
    // Processar pontos
    const lons = [], lats = [], texts = [], sizes = [];
    for (const municipio in pontosData) {
        const coords = await getCoords(municipio);
        lons.push(coords[0]);
        lats.push(coords[1]);
        texts.push(`${municipio}: ${pontosData[municipio]}`);
        sizes.push(pontosData[municipio]);
    }

    const pontosTrace = {
        type: 'scattermapbox',
        lon: lons, lat: lats, text: texts,
        mode: 'markers',
        marker: {
            size: sizes.map(s => Math.sqrt(s) * 10), // Ajuste o tamanho
            color: '#e53e3e',
            opacity: 0.7
        }
    };

    const layout = {
        mapbox: {
            style: 'streets',
            center: { lon: -54, lat: -29 }, // Centralizar no RS
            zoom: 4,
            accesstoken: MAPBOX_TOKEN
        },
        margin: { t: 0, b: 0, l: 0, r: 0 },
        showlegend: false
    };

    Plotly.newPlot(element, [pontosTrace], layout, { responsive: true, displayModeBar: false });
    */
}


// --- INICIALIZAÇÃO DA PÁGINA DE ANÁLISE ---
// Este código é executado assim que o conteúdo da página é totalmente carregado.
document.addEventListener('DOMContentLoaded', () => {
    loadAnaliseFilters(); // Carrega as opções dos filtros.
    setupCustomSelects(); // Configura a interatividade dos novos dropdowns.
    
    const analiseBtn = document.getElementById('analise-btn-gerar');
    if (analiseBtn) {
        analiseBtn.addEventListener('click', handleAnaliseGeneration);
    }
});