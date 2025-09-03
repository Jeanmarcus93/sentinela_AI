// ===============================================
// ===== NAMESPACE GLOBAL =========================
// ===============================================

window.ConsultaApp = window.ConsultaApp || {};

(() => {

// ===== ESTADO GLOBAL ============================
ConsultaApp.state = {
    lastCheckedIda: null,
    lastCheckedVolta: null,
    lastIdaByPlaca: new Map()
};

// ===============================================
// ===== FUNÇÕES AUXILIARES ======================
// ===============================================

function showLoader(element) {
    if (element) {
        element.innerHTML = '<div class="loader"></div>';
    }
}

function safeFormatDate(input) {
    if (!input) return 'N/D';
    try {
        const d = (input instanceof Date) ? input : new Date(input);
        if (!isNaN(d.getTime())) {
            const dd = String(d.getDate()).padStart(2, '0');
            const mm = String(d.getMonth() + 1).padStart(2, '0');
            const yyyy = d.getFullYear();
            const HH = String(d.getHours()).padStart(2, '0');
            const MM = String(d.getMinutes()).padStart(2, '0');
            return `${dd}/${mm}/${yyyy} ${HH}:${MM}`;
        }
        if (typeof input === 'string' && input.includes('T')) {
            const [datePart, timePart = '00:00'] = input.split('T');
            const [year, month, day] = datePart.split('-');
            const time = timePart.substring(0, 5);
            return `${day}/${month}/${year} ${time}`;
        }
        return String(input);
    } catch {
        return String(input);
    }
}

function getRowDataFromTr(tr) {
    const tds = tr.querySelectorAll('td');
    const placa = tds?.[0]?.textContent?.trim() || 'N/D';
    const datahoraText = tds?.[1]?.textContent?.trim() || '';
    const local = tds?.[2]?.textContent?.trim() || '';
    const rodovia = tds?.[3]?.textContent?.trim() || '';
    let parsed = null;
    const m = datahoraText.match(/(\d{2})\/(\d{2})\/(\d{4})\s+(\d{2}):(\d{2})/);
    if (m) {
        const [, dd, mm, yyyy, HH, MM] = m.map(Number);
        parsed = new Date(yyyy, mm - 1, dd, HH, MM);
    }
    return { placa, datahoraText, local, rodovia, dateObj: parsed };
}

function debounce(fn, delay = 350) {
    let t;
    return (...args) => {
        clearTimeout(t);
        t = setTimeout(() => fn(...args), delay);
    };
}

// ===============================================
// ===== FUNÇÕES DA PÁGINA DE CONSULTA ===========
// ===============================================

async function handleConsultaSearch() {
    const searchType = document.getElementById('search-type')?.value;
    const searchValue = document.getElementById('search-input')?.value;
    const resultDiv = document.getElementById('consulta-result');
    if (!searchValue || !searchType || !resultDiv) return;

    showLoader(resultDiv);
    
    try {
        const response = await fetch(`/api/consulta_${searchType}/${encodeURIComponent(searchValue)}`);
        if (!response.ok) {
            let err = 'Valor não encontrado.';
            try {
                const j = await response.json();
                err = j?.error || err;
            } catch {}
            throw new Error(err);
        }
        const data = await response.json();
        displayConsultaResults(data, resultDiv);
    } catch (error) {
        resultDiv.innerHTML = `<p class="text-red-500">❌ ${error.message}</p>`;
    }
}

function displayConsultaResults(data, container) {
    const { veiculos = [], pessoas = [], passagens = [], ocorrencias = [] } = data ?? {};

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
                <thead class="bg-gray-100">
                    <tr><th class="p-2">Placa</th><th class="p-2">Nome</th><th class="p-2">CPF</th><th class="p-2">Ações</th></tr>
                </thead>
                <tbody>${
                    pessoas.length ? pessoas.map(p => {
                        const veiculoAssociado = veiculos.find(v => v.id === p.veiculo_id);
                        return `
                        <tr class="border-b">
                            <td class="p-2">${veiculoAssociado ? veiculoAssociado.placa : 'N/D'}</td>
                            <td class="p-2">${p.nome ?? ''}</td>
                            <td class="p-2">${formatCpfCnpj(p.cpf_cnpj)}</td>
                            <td class="p-2">
                                <button onclick="openEditModal('pessoa', '${escapeData(p)}')" class="action-btn bg-yellow-400 hover:bg-yellow-500">Editar</button>
                                <button onclick="deleteItem('pessoa', ${p.id})" class="action-btn bg-red-500 hover:bg-red-600 text-white">Excluir</button>
                            </td>
                        </tr>`;
                    }).join('') : '<tr><td colspan="4" class="p-2">Nenhuma pessoa encontrada.</td></tr>'
                }
                </tbody>
            </table>
        </div>
        <div class="data-card">
            <h3 class="text-xl font-semibold">🚨 Ocorrências</h3>
            <table class="min-w-full text-sm text-left table-fixed">
                <thead class="bg-gray-100">
                    <tr>
                        <th class="p-2 w-[15%]">Data/Hora</th>
                        <th class="p-2 w-[15%]">Tipo</th>
                        <th class="p-2 w-[55%]">Relato</th>
                        <th class="p-2 w-[15%] text-right">Ações</th>
                    </tr>
                </thead>
                <tbody>${
                    ocorrencias.length ? ocorrencias.map(o => `
                        <tr class="border-b">
                            <td class="p-2 align-top">${safeFormatDate(o.datahora)}</td>
                            <td class="p-2 align-top">${(o.tipo || '').replace('Local de Entrega', 'Droga entregue em:')}</td>
                            <td class="p-2 break-words align-top">${o.relato || ''}</td>
                            <td class="p-2 align-top">
                                <div class="flex flex-col items-end gap-1">
                                    <button onclick="openEditModal('ocorrencia', '${escapeData(o)}')" class="action-btn bg-yellow-400 hover:bg-yellow-500">Editar</button>
                                    <button onclick="deleteItem('ocorrencia', ${o.id})" class="action-btn bg-red-500 hover:bg-red-600 text-white">Excluir</button>
                                </div>
                            </td>
                        </tr>`).join('') : '<tr><td colspan="4" class="p-2">Nenhuma ocorrência encontrada.</td></tr>'
                }
                </tbody>
            </table>
        </div>
        <div class="data-card">
            <div class="flex items-center justify-between">
                <h3 class="text-xl font-semibold">📍 Passagens</h3>
                <div class="text-xs opacity-70 pr-2">Dica: use Shift+Clique para marcar um intervalo.</div>
            </div>
            <table id="passagens-table" class="min-w-full text-sm text-left">
                <thead class="bg-gray-100">
                    <tr>
                        <th class="p-2">Placa</th>
                        <th class="p-2">Data/Hora</th>
                        <th class="p-2">Cidade</th>
                        <th class="p-2">Local</th>
                        <th class="p-2">Ilícito (Ida)</th>
                        <th class="p-2">Ilícito (Volta)</th>
                    </tr>
                </thead>
                <tbody>${
                    passagens.length ? passagens.map(p => `
                        <tr class="border-b">
                            <td class="p-2">${p.placa || 'N/D'}</td>
                            <td class="p-2">${safeFormatDate(p.datahora)}</td>
                            <td class="p-2">${p.municipio}/${p.estado}</td>
                            <td class="p-2">${p.rodovia || ''}</td>
                            <td class="p-2 text-center">
                                <input type="checkbox" 
                                       class="passagem-checkbox" 
                                       data-column="ida" 
                                       data-id="${p.id}" 
                                       ${p.ilicito_ida ? 'checked' : ''}>
                            </td>
                            <td class="p-2 text-center flex items-center justify-center gap-2">
                                <input type="checkbox" 
                                       class="passagem-checkbox" 
                                       data-column="volta" 
                                       data-id="${p.id}" 
                                       ${p.ilicito_volta ? 'checked' : ''}>
                                <span class="text-green-500 text-xs" id="passagem-feedback-${p.id}"></span>
                            </td>
                        </tr>`).join('') : '<tr><td colspan="6" class="p-2">Nenhuma passagem encontrada.</td></tr>'
                }
                </tbody>
            </table>

            <div class="mt-3 text-xs text-gray-600">
                Ao marcar uma passagem de <b>ida</b> e, em seguida, uma de <b>volta</b> (da mesma placa), será sugerido criar uma ocorrência de <i>Local de Entrega</i> para o intervalo.
            </div>
        </div>
    `;

    const passagensTable = document.getElementById('passagens-table');
    if (passagensTable) {
        passagensTable.addEventListener('click', handlePassagemClick);
    }
}

async function handlePassagemClick(e) {
    if (!e.target.matches('.passagem-checkbox')) return;

    const checkbox = e.target;
    const column = checkbox.dataset.column;
    const tr = checkbox.closest('tr');
    const rowData = getRowDataFromTr(tr);

    let lastChecked = (column === 'ida') ? ConsultaApp.state.lastCheckedIda : ConsultaApp.state.lastCheckedVolta;

    if (e.shiftKey && lastChecked) {
        const checkboxes = Array.from(document.querySelectorAll(`.passagem-checkbox[data-column="${column}"]`));
        const start = checkboxes.indexOf(lastChecked);
        const end = checkboxes.indexOf(checkbox);
        const rangeStart = Math.min(start, end);
        const rangeEnd = Math.max(start, end);
        const inBetween = checkboxes.slice(rangeStart, rangeEnd + 1);
        for (const cb of inBetween) {
            cb.checked = checkbox.checked;
            await updatePassagem(cb, cb.dataset.id, cb.dataset.column);
        }
    }

    if (column === 'ida') {
        ConsultaApp.state.lastCheckedIda = checkbox;
        if (rowData.placa) {
            ConsultaApp.state.lastIdaByPlaca.set(rowData.placa, { checkbox, rowData });
        }
    } else {
        ConsultaApp.state.lastCheckedVolta = checkbox;
    }

    if (!e.shiftKey) {
        await updatePassagem(checkbox, checkbox.dataset.id, checkbox.dataset.column);
    }

    if (column === 'volta' && checkbox.checked && rowData?.placa) {
        const idaInfo = ConsultaApp.state.lastIdaByPlaca.get(rowData.placa);
        if (idaInfo?.rowData?.dateObj && rowData?.dateObj) {
            const idaDate = idaInfo.rowData.dateObj;
            const voltaDate = rowData.dateObj;
            if (voltaDate >= idaDate) {
                try {
                    const municipio = prompt('Informe o município/local de entrega (opcional):', idaInfo.rowData.local || '');
                    if (municipio === null) return;

                    await createLocalEntrega({
                        placa: rowData.placa,
                        inicio_iso: idaDate.toISOString(),
                        fim_iso: voltaDate.toISOString(),
                        municipio,
                    });

                    const fbVolta = document.getElementById(`passagem-feedback-${checkbox.dataset.id}`);
                    if (fbVolta) {
                        fbVolta.textContent = 'Local de entrega registrado!';
                        setTimeout(() => (fbVolta.textContent = ''), 3000);
                    }

                    document.dispatchEvent(new CustomEvent('data-changed'));
                } catch (err) {
                    console.error(err);
                    alert('Não foi possível registrar o Local de Entrega.');
                }
            }
        }
    }
}

async function updatePassagem(checkbox, passagemId, field) {
    const value = !!checkbox.checked;
    try {
        const response = await fetch(`/api/passagem/${encodeURIComponent(passagemId)}`, {
            method: 'PUT',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ field: `ilicito_${field}`, value })
        });
        const result = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(result?.error || 'Falha ao atualizar passagem.');

        const feedbackEl = document.getElementById(`passagem-feedback-${passagemId}`);
        if (feedbackEl) {
            feedbackEl.textContent = 'Guardado!';
            setTimeout(() => { feedbackEl.textContent = ''; }, 2000);
        }
    } catch (error) {
        console.error(`Erro ao guardar: ${error.message}`);
        checkbox.checked = !value;
    }
}

async function createLocalEntrega(payload) {
    const response = await fetch('/api/local_entrega', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(payload)
    });
    if (!response.ok) {
        let msg = 'Falha ao registrar Local de Entrega.';
        try {
            const j = await response.json();
            msg = j?.error || msg;
        } catch {}
        throw new Error(msg);
    }
}

// ===============================================
// ===== INICIALIZAÇÃO ===========================
// ===============================================

document.addEventListener('DOMContentLoaded', () => {
    const searchBtn = document.getElementById('search-btn');
    if (searchBtn) {
        searchBtn.addEventListener('click', handleConsultaSearch);
    }

    const searchInput = document.getElementById('search-input');
    if (searchInput) {
        searchInput.addEventListener('keyup', (event) => {
            if (event.key === 'Enter') {
                handleConsultaSearch();
            }
        });
        const debounced = debounce(handleConsultaSearch, 500);
        searchInput.addEventListener('input', () => {
            if (searchInput.value?.length >= 3) debounced();
        });
    }

    const searchTypeSelect = document.getElementById('search-type');
    if (searchTypeSelect) {
        searchTypeSelect.addEventListener('change', (e) => {
            const isPlaca = e.target.value === 'placa';
            const label = document.getElementById('search-label');
            if (label) label.textContent = isPlaca ? 'Digite a Placa:' : 'Digite o CPF:';
            if (searchInput) {
                searchInput.className = isPlaca ? 'w-full px-4 py-2 border rounded-lg uppercase' : 'w-full px-4 py-2 border rounded-lg';
                if (isPlaca) {
                    searchInput.addEventListener('input', () => {
                        searchInput.value = searchInput.value.toUpperCase();
                    }, { once: true });
                }
            }
        });
    }

    document.addEventListener('data-changed', handleConsultaSearch);
});

})(); // fim do namespace isolado

