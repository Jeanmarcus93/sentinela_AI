// ===============================================
// ===== FUNÇÕES DA PÁGINA DE CONSULTA ===========
// ===============================================

/**
 * Executa a busca na API com base no tipo e valor de pesquisa e exibe os resultados.
 */
async function handleConsultaSearch() {
    const searchType = document.getElementById('search-type').value;
    const searchValue = document.getElementById('search-input').value;
    const resultDiv = document.getElementById('consulta-result');
    if (!searchValue) return;

    showLoader(resultDiv);
    
    try {
        const response = await fetch(`/api/consulta_${searchType}/${searchValue}`);
        if (!response.ok) throw new Error((await response.json()).error || 'Valor não encontrado.');
        const data = await response.json();
        displayConsultaResults(data, resultDiv);
    } catch (error) {
        resultDiv.innerHTML = `<p class="text-red-500">❌ ${error.message}</p>`;
    }
}

/**
 * Renderiza os resultados da consulta no container especificado.
 * @param {object} data - O objeto de dados retornado pela API.
 * @param {HTMLElement} container - O elemento onde os resultados serão renderizados.
 */
function displayConsultaResults(data, container) {
    const { veiculos, pessoas, passagens, ocorrencias } = data;
    const formatDate = (d) => {
        if (!d) return 'N/D';
        const [datePart, timePart] = d.split('T');
        const [year, month, day] = datePart.split('-');
        const time = timePart.substring(0, 5);
        return `${day}/${month}/${year} ${time}`;
    };
    const formatCpfCnpj = (doc) => {
        if (!doc) return 'N/D';
        const cleaned = String(doc).replace(/\D/g, '');
        if (cleaned.length === 11) {
            return cleaned.replace(/(\d{3})(\d{3})(\d{3})(\d{2})/, '$1.$2.$3-$4');
        }
        if (cleaned.length === 14) {
            return cleaned.replace(/(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})/, '$1.$2.$3/$4-$5');
        }
        return cleaned; 
    };
    const escapeData = (d) => encodeURIComponent(JSON.stringify(d));

    const veiculosHtml = veiculos.map(veiculo => `
        <div class="data-card">
            <h3 class="text-xl font-semibold">🚘 Dados do Veículo</h3>
            <div class="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
                <p><strong>Placa:</strong> <span class="placa-display">${veiculo.placa || 'N/D'}</span></p>
                <p><strong>Marca/Modelo:</strong> ${veiculo.marca_modelo || 'N/D'}</p>
                <p><strong>Tipo:</strong> ${veiculo.tipo || 'N/D'}</p>
                <p><strong>Ano/Modelo:</strong> ${veiculo.ano_modelo || 'N/D'}</p>
                <p><strong>Cor:</strong> ${veiculo.cor || 'N/D'}</p>
                <p><strong>Local da Placa:</strong> ${veiculo.local_emplacamento || 'N/D'}</p>
            </div>
        </div>
    `).join('');

    container.innerHTML = `
        ${veiculos.length > 0 ? veiculosHtml : ''}
        <div class="data-card">
            <h3 class="text-xl font-semibold">👥 Pessoas Relacionadas</h3>
            <table class="min-w-full text-sm text-left">
                <thead class="bg-gray-100"><tr><th class="p-2">Placa</th><th class="p-2">Nome</th><th class="p-2">CPF</th><th class="p-2">Ações</th></tr></thead>
                <tbody>${pessoas.map(p => {
                    const veiculoAssociado = veiculos.find(v => v.id === p.veiculo_id);
                    return `
                    <tr class="border-b">
                        <td class="p-2">${veiculoAssociado ? veiculoAssociado.placa : 'N/D'}</td>
                        <td class="p-2">${p.nome}</td>
                        <td class="p-2">${formatCpfCnpj(p.cpf_cnpj)}</td>
                        <td class="p-2">
                            <button onclick="openEditModal('pessoa', '${escapeData(p)}')" class="action-btn bg-yellow-400 hover:bg-yellow-500">Editar</button>
                            <button onclick="deleteItem('pessoa', ${p.id})" class="action-btn bg-red-500 hover:bg-red-600 text-white">Excluir</button>
                        </td>
                    </tr>`;
                }).join('') || '<tr><td colspan="4" class="p-2">Nenhuma pessoa encontrada.</td></tr>'}
                </tbody>
            </table>
        </div>
        <div class="data-card">
            <h3 class="text-xl font-semibold">🚨 Ocorrências</h3>
            <table class="min-w-full text-sm text-left">
                 <thead class="bg-gray-100"><tr><th class="p-2">Placa</th><th class="p-2">Tipo</th><th class="p-2">Data/Hora</th><th class="p-2">Relato</th><th class="p-2">Ações</th></tr></thead>
                 <tbody>${ocorrencias.map(o => `
                    <tr class="border-b">
                        <td class="p-2">${o.placa || 'N/D'}</td>
                        <td class="p-2">${o.tipo.replace('Local de Entrega', 'Local de Entrega da Droga')}</td>
                        <td class="p-2">${formatDate(o.datahora)}</td>
                        <td class="p-2">${o.relato || ''}</td>
                        <td class="p-2">
                            <button onclick="openEditModal('ocorrencia', '${escapeData(o)}')" class="action-btn bg-yellow-400 hover:bg-yellow-500">Editar</button>
                            <button onclick="deleteItem('ocorrencia', ${o.id})" class="action-btn bg-red-500 hover:bg-red-600 text-white">Excluir</button>
                        </td>
                    </tr>`).join('') || '<tr><td colspan="5" class="p-2">Nenhuma ocorrência encontrada.</td></tr>'}
                 </tbody>
            </table>
        </div>
        <div class="data-card">
            <h3 class="text-xl font-semibold">📍 Passagens</h3>
            <table class="min-w-full text-sm text-left">
                 <thead class="bg-gray-100"><tr><th class="p-2">Placa</th><th class="p-2">Data/Hora</th><th class="p-2">Local</th><th class="p-2">Autoestrada</th><th class="p-2">Ilícito (Ida)</th><th class="p-2">Ilícito (Volta)</th></tr></thead>
                 <tbody>${passagens.map(p => `
                    <tr class="border-b">
                        <td class="p-2">${p.placa || 'N/D'}</td>
                        <td class="p-2">${formatDate(p.datahora)}</td>
                        <td class="p-2">${p.municipio}/${p.estado}</td>
                        <td class="p-2">${p.rodovia || ''}</td>
                        <td class="p-2 text-center">
                            <input type="checkbox" 
                                   class="passagem-checkbox" 
                                   data-column="ida" 
                                   data-id="${p.id}" 
                                   onchange="updatePassagem(this, ${p.id}, 'ida')" 
                                   ${p.ilicito_ida ? 'checked' : ''}>
                        </td>
                        <td class="p-2 text-center flex items-center justify-center gap-2">
                            <input type="checkbox" 
                                   class="passagem-checkbox" 
                                   data-column="volta" 
                                   data-id="${p.id}" 
                                   onchange="updatePassagem(this, ${p.id}, 'volta')" 
                                   ${p.ilicito_volta ? 'checked' : ''}>
                            <span class="text-green-500 text-xs" id="passagem-feedback-${p.id}"></span>
                        </td>
                    </tr>`).join('') || '<tr><td colspan="6" class="p-2">Nenhuma passagem encontrada.</td></tr>'}
                 </tbody>
            </table>
        </div>
    `;
}

/**
 * Atualiza o estado de uma passagem (ilícito ida/volta) na base de dados.
 * @param {HTMLInputElement} checkbox - A checkbox que foi alterada.
 * @param {number} passagemId - O ID da passagem.
 * @param {string} field - O campo a ser atualizado ('ida' ou 'volta').
 */
async function updatePassagem(checkbox, passagemId, field) {
    const value = checkbox.checked;
    try {
        const response = await fetch(`/api/passagem/${passagemId}`, {
            method: 'PUT',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ field: `ilicito_${field}`, value: value })
        });
        const result = await response.json();
        if (!response.ok) throw new Error(result.error);
        
        const feedbackEl = document.getElementById(`passagem-feedback-${passagemId}`);
        feedbackEl.textContent = 'Guardado!';
        setTimeout(() => { feedbackEl.textContent = ''; }, 2000);

    } catch (error) {
        alert(`Erro ao guardar: ${error.message}`);
        checkbox.checked = !value;
    }
}

// --- INICIALIZAÇÃO DA PÁGINA DE CONSULTA ---
document.addEventListener('DOMContentLoaded', () => {
    const searchBtn = document.getElementById('search-btn');
    if(searchBtn) {
        searchBtn.addEventListener('click', handleConsultaSearch);
    }

    const searchInput = document.getElementById('search-input');
    if (searchInput) {
        searchInput.addEventListener('keyup', (event) => {
            if (event.key === 'Enter') {
                handleConsultaSearch();
            }
        });
    }

    const searchTypeSelect = document.getElementById('search-type');
    if(searchTypeSelect) {
        searchTypeSelect.addEventListener('change', (e) => {
            const isPlaca = e.target.value === 'placa';
            document.getElementById('search-label').textContent = isPlaca ? 'Digite a Placa:' : 'Digite o CPF:';
            const searchInput = document.getElementById('search-input');
            if (searchInput) {
                searchInput.className = isPlaca ? 'w-full px-4 py-2 border rounded-lg uppercase' : 'w-full px-4 py-2 border rounded-lg';
            }
        });
    }

    // Listener para o evento personalizado que recarrega a busca após uma exclusão/edição
    document.addEventListener('data-changed', handleConsultaSearch);
});
