// static/js/analise_IA.js

/**
 * Exibe uma animação de carregamento dentro de um elemento container.
 * @param {HTMLElement} container - O elemento onde o loader será exibido.
 */
function showLoader(container) {
    container.innerHTML = '<div class="loader"></div>';
}

/**
 * Renderiza os resultados da análise de IA na página.
 * @param {object} data - Os dados retornados pela API de análise.
 * @param {HTMLElement} container - O elemento onde os resultados serão exibidos.
 */
function displayResults(data, container) {
    // Verifica se há dados para exibir
    if (!data || (!data.rotas || !data.rotas.labels) && (!data.relatos || data.relatos.length === 0)) {
        container.innerHTML = '<p class="text-center text-gray-500">Nenhum dado de rota ou relato encontrado para a placa informada.</p>';
        return;
    }

    // --- Card do Índice de Risco Global ---
    const riscoFinalHtml = `
        <div class="kpi-box text-center bg-indigo-50 border-l-4 border-indigo-500 p-6 mb-8 rounded-lg">
            <div class="kpi-label text-indigo-800 font-semibold">Índice de Risco Global</div>
            <div class="kpi-value text-indigo-900">${(data.risco.final * 100).toFixed(0)}%</div>
            <div class="text-xs text-indigo-700 mt-2">
                (Risco Rotas: ${(data.risco.rotas * 100).toFixed(0)}% | Risco Relatos: ${(data.risco.relatos * 100).toFixed(0)}%)
            </div>
        </div>
    `;

    // --- Card de Análise de Rotas ---
    let rotasHtml = '';
    if (data.rotas && data.rotas.labels) {
        const probsHtml = data.rotas.labels.map((label, i) => `
            <div class="flex justify-between items-center py-1">
                <span class="font-medium text-gray-600">${label}</span>
                <span class="font-bold text-gray-800">${(data.rotas.probs[i] * 100).toFixed(1)}%</span>
            </div>
        `).join('');

        rotasHtml = `
            <div class="data-card mb-6">
                <h3 class="text-xl font-semibold">📍 Análise de Padrão de Rotas</h3>
                <div class="mt-4 text-sm space-y-1">
                    ${probsHtml}
                </div>
            </div>
        `;
    }

    // --- Card de Análise de Relatos ---
    let relatosHtml = '';
    if (data.relatos && data.relatos.length > 0) {
        const relatosCardsHtml = data.relatos.map(relato => {
            const probsRelatoHtml = relato.labels.map((label, i) => `
                 <div class="flex justify-between items-center py-1 text-xs">
                    <span class="text-gray-600">${label}</span>
                    <span class="font-semibold text-gray-700">${(relato.probs[i] * 100).toFixed(1)}%</span>
                </div>
            `).join('');

            return `
                <div class="border-t pt-4 mt-4 first:mt-0 first:pt-0 first:border-t-0">
                    <p class="font-bold text-gray-700">Ocorrência #${relato.id} (${relato.tipo})</p>
                    <p class="text-xs text-gray-500 mb-2">Data: ${new Date(relato.datahora).toLocaleDateString('pt-BR')}</p>
                    <blockquote class="border-l-4 border-gray-200 pl-4 italic text-gray-800 text-sm">
                        "${relato.texto}"
                    </blockquote>
                    <div class="mt-3 text-xs">
                        <p class="font-semibold mb-1">Análise Semântica:</p>
                        ${probsRelatoHtml}
                    </div>
                </div>
            `;
        }).join('');

        relatosHtml = `
            <div class="data-card">
                <h3 class="text-xl font-semibold">📝 Análise Semântica de Relatos</h3>
                <div class="mt-4">${relatosCardsHtml}</div>
            </div>
        `;
    }

    container.innerHTML = riscoFinalHtml + rotasHtml + relatosHtml;
}


/**
 * Função principal que configura os eventos da página.
 */
document.addEventListener('DOMContentLoaded', () => {
    const analisarBtn = document.getElementById('analisar-btn');
    const placaInput = document.getElementById('placa-input');
    const resultadosContainer = document.getElementById('analise-resultados');

    const handleAnalise = async () => {
        const placa = placaInput.value.trim().toUpperCase();
        if (!placa) {
            resultadosContainer.innerHTML = '<p class="text-center text-red-500">Por favor, digite uma placa para analisar.</p>';
            return;
        }

        showLoader(resultadosContainer);

        try {
            // A rota da API foi definida em routes.py
            const response = await fetch(`/api/analise_placa/${placa}`);
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || 'Ocorreu um erro desconhecido ao analisar a placa.');
            }
            
            displayResults(data, resultadosContainer);

        } catch (error) {
            resultadosContainer.innerHTML = `<p class="text-center text-red-500">❌ Erro: ${error.message}</p>`;
        }
    };

    if (analisarBtn && placaInput && resultadosContainer) {
        analisarBtn.addEventListener('click', handleAnalise);
        placaInput.addEventListener('keyup', (event) => {
            if (event.key === 'Enter') {
                handleAnalise();
            }
        });
    }
});