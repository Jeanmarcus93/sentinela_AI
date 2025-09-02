// --- FUNÇÕES GLOBAIS, DO MODAL E SHIFT-CLICK ---

/**
 * Exibe uma animação de carregamento dentro de um elemento container.
 * @param {HTMLElement} container - O elemento onde o loader será exibido.
 */
function showLoader(container) {
    container.innerHTML = '<div class="loader"></div>';
}

/**
 * Abre e preenche o modal de edição para um item (pessoa ou ocorrência).
 * @param {string} type - O tipo de item ('pessoa' ou 'ocorrencia').
 * @param {string} dataString - Os dados do item em formato JSON, codificados como URI.
 */
function openEditModal(type, dataString) {
    const data = JSON.parse(decodeURIComponent(dataString));
    const modal = document.getElementById('edit-modal');
    const form = document.getElementById('modal-form');
    const title = document.getElementById('modal-title');
    document.getElementById('modal-feedback').innerHTML = '';

    title.textContent = `Editar ${type === 'pessoa' ? 'Pessoa' : 'Ocorrência'}`;
    
    if (type === 'pessoa') {
        form.innerHTML = `
            <input type="hidden" name="id" value="${data.id}">
            <div><label class="block">Nome</label><input type="text" name="nome" value="${data.nome || ''}" class="modal-input"></div>
            <div><label class="block">CPF</label><input type="text" name="cpf_cnpj" value="${data.cpf_cnpj || ''}" class="modal-input"></div>
        `;
    } else if (type === 'ocorrencia') {
        const datahora_str = data.datahora ? data.datahora.split('T')[0] : '';
        const hora_str = data.datahora ? data.datahora.split('T')[1].substring(0, 5) : '';
        const datahora_fim_str = data.datahora_fim ? data.datahora_fim.split('T')[0] : '';
        const hora_fim_str = data.datahora_fim ? data.datahora_fim.split('T')[1].substring(0, 5) : '';

        let formHtml = `
            <input type="hidden" name="id" value="${data.id}">
            <input type="hidden" name="tipo" value="${data.tipo}">
            <div><label class="block">Tipo</label><input type="text" value="${data.tipo.replace('Local de Entrega', 'Local de Entrega da Droga') || ''}" class="modal-input" readonly></div>
            <div>
                <label class="block">Data/Hora de Início</label>
                <input type="date" name="datahora_date" value="${datahora_str}" class="modal-input inline-block w-1/2">
                <input type="time" name="datahora_time" value="${hora_str}" class="modal-input inline-block w-1/2">
            </div>
        `;

        if (data.tipo === 'Local de Entrega') {
            formHtml += `
                <div>
                    <label class="block">Relato</label><textarea name="relato" class="modal-input h-24">${data.relato || ''}</textarea>
                </div>
                <div>
                    <label class="block">Data/Hora Final</label>
                    <input type="date" name="datahora_fim_date" value="${datahora_fim_str}" class="modal-input inline-block w-1/2">
                    <input type="time" name="datahora_fim_time" value="${hora_fim_str}" class="modal-input inline-block w-1/2">
                </div>
            `;
        } else if (data.tipo === 'Abordagem') {
             const ocupantes = data.ocupantes ? JSON.parse(data.ocupantes) : [];
             formHtml += `
                 <div><label class="block">Relato</label><textarea name="relato" class="modal-input h-24">${data.relato || ''}</textarea></div>
                 <div id="ocupantes-container" class="space-y-4">
                     <label class="block text-gray-700 font-semibold mb-2">Ocupantes</label>
                     ${ocupantes.map(o => `
                         <div class="ocupante-campo-group border-b pb-4 flex items-center gap-2">
                             <div class="grid grid-cols-1 md:grid-cols-2 gap-2 flex-grow">
                                 <div><label class="block text-sm text-gray-600">CPF</label><input type="text" name="ocupante-cpf" value="${o.cpf_cnpj || ''}" class="w-full px-2 py-1 border rounded-lg" placeholder="CPF do ocupante"></div>
                                 <div><label class="block text-sm text-gray-600">Nome</label><input type="text" name="ocupante-nome" value="${o.nome || ''}" class="w-full px-2 py-1 border rounded-lg" placeholder="Nome do ocupante"></div>
                             </div>
                             <button type="button" onclick="this.parentNode.remove()" class="text-red-500 hover:text-red-700 font-bold text-lg">X</button>
                         </div>
                     `).join('')}
                 </div>
                 <button type="button" onclick="addDynamicField('ocupantes')" class="mt-2 px-4 py-2 bg-gray-200 text-gray-800 rounded-lg hover:bg-gray-300">Adicionar Ocupante</button>
             `;
        } else if (data.tipo === 'BOP') {
            const apreensoes = Array.isArray(data.apreensoes) ? data.apreensoes : [];
            const presos = data.presos ? JSON.parse(data.presos) : [];
            const veiculos = data.veiculos ? JSON.parse(data.veiculos) : [];
            
            formHtml += `
                <div><label class="block">Relato</label><textarea name="relato" class="modal-input h-24">${data.relato || ''}</textarea></div>
                <div id="apreensoes-container" class="space-y-4">
                    <label class="block text-gray-700 font-semibold mb-2">Apreensões</label>
                    ${apreensoes.map(a => `
                        <div class="apreensao-campo-group border-b pb-4 flex items-center gap-2">
                            <div class="grid grid-cols-1 md:grid-cols-3 gap-2 flex-grow">
                                <div>
                                    <label class="block text-sm text-gray-600">Tipo</label>
                                    <select name="apreensao-tipo" class="w-full px-2 py-1 border rounded-lg">
                                        <option value="Maconha" ${a.tipo === 'Maconha' ? 'selected' : ''}>Maconha</option>
                                        <option value="Skunk" ${a.tipo === 'Skunk' ? 'selected' : ''}>Skunk</option>
                                        <option value="Cocaina" ${a.tipo === 'Cocaina' ? 'selected' : ''}>Cocaína</option>
                                        <option value="Crack" ${a.tipo === 'Crack' ? 'selected' : ''}>Crack</option>
                                        <option value="Sintéticos" ${a.tipo === 'Sintéticos' ? 'selected' : ''}>Sintéticos</option>
                                        <option value="Arma" ${a.tipo === 'Arma' || a.tipo === 'Armas' ? 'selected' : ''}>Arma</option>
                                    </select>
                                </div>
                                <div>
                                    <label class="block text-sm text-gray-600">Quantidade</label>
                                    <input type="text" inputmode="decimal" name="apreensao-qtd" value="${a.quantidade || ''}" class="w-full px-2 py-1 border rounded-lg" placeholder="Ex: 5">
                                </div>
                                <div>
                                    <label class="block text-sm text-gray-600">Unidade</label>
                                    <select name="apreensao-unidade" class="w-full px-2 py-1 border rounded-lg">
                                        <option value="kg" ${a.unidade && a.unidade.toLowerCase() === 'kg' ? 'selected' : ''}>Kg</option>
                                        <option value="g" ${a.unidade && (a.unidade.toLowerCase() === 'g' || a.unidade.toLowerCase() === 'gramas') ? 'selected' : ''}>Gramas</option>
                                        <option value="un" ${a.unidade && (a.unidade.toLowerCase() === 'un' || a.unidade.toLowerCase() === 'unidades') ? 'selected' : ''}>Unidades</option>
                                    </select>
                                </div>
                            </div>
                            <button type="button" onclick="this.parentNode.remove()" class="text-red-500 hover:text-red-700 font-bold text-lg">X</button>
                        </div>
                    `).join('')}
                </div>
                <button type="button" onclick="addDynamicField('apreensoes')" class="mt-2 px-4 py-2 bg-gray-200 text-gray-800 rounded-lg hover:bg-gray-300">Adicionar Apreensão</button>

                <div id="presos-container" class="space-y-4">
                    <label class="block text-gray-700 font-semibold mb-2">Presos</label>
                    ${presos.map(p => `
                        <div class="preso-campo-group border-b pb-4 flex items-center gap-2">
                            <div class="grid grid-cols-1 md:grid-cols-2 gap-2 flex-grow">
                                <div><label class="block text-sm text-gray-600">CPF</label><input type="text" name="preso-cpf" value="${p.cpf_cnpj || ''}" class="w-full px-2 py-1 border rounded-lg" placeholder="CPF do preso"></div>
                                <div><label class="block text-sm text-gray-600">Nome</label><input type="text" name="preso-nome" value="${p.nome || ''}" class="w-full px-2 py-1 border rounded-lg" placeholder="Nome do preso"></div>
                            </div>
                            <button type="button" onclick="this.parentNode.remove()" class="text-red-500 hover:text-red-700 font-bold text-lg">X</button>
                        </div>
                    `).join('')}
                </div>
                <button type="button" onclick="addDynamicField('presos')" class="mt-2 px-4 py-2 bg-gray-200 text-gray-800 rounded-lg hover:bg-gray-300">Adicionar Preso</button>

                <div id="veiculos-envolvidos-container" class="space-y-4">
                    <label class="block text-gray-700 font-semibold mb-2">Veículos Envolvidos</label>
                    ${veiculos.map(v => `
                        <div class="veiculo-campo-group border-b pb-4 flex items-center gap-2">
                            <div class="grid grid-cols-1 md:grid-cols-2 gap-2 flex-grow">
                                <div><label class="block text-sm text-gray-600">Placa</label><input type="text" name="veiculo-placa" value="${v.placa || ''}" class="w-full px-2 py-1 border rounded-lg" placeholder="Placa do veículo"></div>
                                <div><label class="block text-sm text-gray-600">Modelo</label><input type="text" name="veiculo-modelo" value="${v.modelo || ''}" class="w-full px-2 py-1 border rounded-lg" placeholder="Modelo do veículo"></div>
                            </div>
                            <button type="button" onclick="this.parentNode.remove()" class="text-red-500 hover:text-red-700 font-bold text-lg">X</button>
                        </div>
                    `).join('')}
                </div>
                <button type="button" onclick="addDynamicField('veiculos')" class="mt-2 px-4 py-2 bg-gray-200 text-gray-800 rounded-lg hover:bg-gray-300">Adicionar Veículo</button>
            `;
        }
        form.innerHTML = formHtml;
    }
    modal.classList.remove('hidden');
}

/**
 * Fecha o modal de edição.
 */
function closeModal() {
    document.getElementById('edit-modal').classList.add('hidden');
}

/**
 * Lida com o clique no botão "Guardar" do modal, enviando os dados para a API.
 */
async function handleModalSave() {
    const modalTitle = document.getElementById('modal-title').textContent;
    const type = modalTitle.includes('Pessoa') ? 'pessoa' : 'ocorrencia';
    const form = document.getElementById('modal-form');
    const feedbackEl = document.getElementById('modal-feedback');
    const id = form.querySelector('input[name="id"]').value;

    let payloadData = {};
    if (type === 'pessoa') {
        payloadData = {
            nome: form.querySelector('input[name="nome"]').value,
            cpf_cnpj: form.querySelector('input[name="cpf_cnpj"]').value
        };
    } else if (type === 'ocorrencia') {
        const tipo = form.querySelector('input[name="tipo"]').value;
        const relato = form.querySelector('textarea[name="relato"]').value;

        const dataInicio = form.querySelector('input[name="datahora_date"]').value;
        const horaInicio = form.querySelector('input[name="datahora_time"]').value;
        let datahora_inicio = null;
        if (dataInicio && horaInicio) {
            datahora_inicio = `${dataInicio}T${horaInicio}`;
        }
        let datahora_fim = null;
        const dataFimInput = form.querySelector('input[name="datahora_fim_date"]');
        if (dataFimInput) {
            const dataFim = dataFimInput.value;
            const horaFim = form.querySelector('input[name="datahora_fim_time"]').value;
            if (dataFim && horaFim) datahora_fim = `${dataFim}T${horaFim}`;
        }

        payloadData = {
            datahora: datahora_inicio,
            relato: relato,
            datahora_fim: datahora_fim
        };

        if (tipo === 'Abordagem') {
            const ocupantesList = Array.from(form.querySelectorAll('.ocupante-campo-group')).map(group => ({
                nome: group.querySelector('input[name="ocupante-nome"]').value,
                cpf_cnpj: group.querySelector('input[name="ocupante-cpf"]').value
            })).filter(o => o.nome || o.cpf_cnpj);
            payloadData.ocupantes = JSON.stringify(ocupantesList);
        } else if (tipo === 'BOP') {
             const apreensoesList = Array.from(form.querySelectorAll('.apreensao-campo-group')).map(group => ({
                 tipo: group.querySelector('select[name="apreensao-tipo"]').value,
                 quantidade: group.querySelector('input[name="apreensao-qtd"]').value,
                 unidade: group.querySelector('select[name="apreensao-unidade"]').value
             })).filter(p => p.tipo && p.quantidade);
             payloadData.apreensoes = JSON.stringify(apreensoesList);
             const presosList = Array.from(form.querySelectorAll('.preso-campo-group')).map(group => ({
                 nome: group.querySelector('input[name="preso-nome"]').value,
                 cpf_cnpj: group.querySelector('input[name="preso-cpf"]').value
             })).filter(p => p.nome || p.cpf_cnpj);
             payloadData.presos = JSON.stringify(presosList);
             const veiculosList = Array.from(form.querySelectorAll('.veiculo-campo-group')).map(group => ({
                 placa: group.querySelector('input[name="veiculo-placa"]').value,
                 modelo: group.querySelector('input[name="veiculo-modelo"]').value
             })).filter(v => v.placa || v.modelo);
             payloadData.veiculos = JSON.stringify(veiculosList);
        }
    }
    feedbackEl.innerHTML = 'A guardar...';

    try {
        const response = await fetch(`/api/${type}/${id}`, {
            method: 'PUT',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payloadData)
        });
        const result = await response.json();
        if (!response.ok) throw new Error(result.error);
        feedbackEl.innerHTML = `<p class="text-green-500">${result.message}</p>`;
        setTimeout(() => {
            closeModal();
            // Dispara um evento para que a página de consulta saiba que precisa de ser atualizada.
            document.dispatchEvent(new CustomEvent('data-changed'));
        }, 1500);
    } catch (error) {
        feedbackEl.innerHTML = `<p class="text-red-500">Erro ao guardar: ${error.message}</p>`;
    }
}

/**
 * Adiciona um novo conjunto de campos dinâmicos a um formulário (ex: adicionar novo ocupante, apreensão).
 * @param {string} containerId - O prefixo do ID do container (ex: 'ocupantes', 'apreensoes').
 */
function addDynamicField(containerId) {
    const container = document.getElementById(containerId + '-container');
    if (!container) return;
    const newGroup = document.createElement('div');
    newGroup.className = 'border-b pb-4 flex items-center gap-2';

    if (containerId === 'ocupantes' || containerId === 'presos') {
        newGroup.innerHTML = `
            <div class="grid grid-cols-1 md:grid-cols-2 gap-2 flex-grow">
                <div><label class="block text-sm text-gray-600">CPF</label><input type="text" name="${containerId.slice(0, -1)}-cpf" class="w-full px-2 py-1 border rounded-lg" placeholder="CPF"></div>
                <div><label class="block text-sm text-gray-600">Nome</label><input type="text" name="${containerId.slice(0, -1)}-nome" class="w-full px-2 py-1 border rounded-lg" placeholder="Nome"></div>
            </div>
            <button type="button" onclick="this.parentNode.remove()" class="text-red-500 hover:text-red-700 font-bold text-lg">X</button>
        `;
    } else if (containerId === 'veiculos') {
        newGroup.className = 'veiculo-campo-group border-b pb-4 flex items-center gap-2';
        newGroup.innerHTML = `
            <div class="grid grid-cols-1 md:grid-cols-2 gap-2 flex-grow">
                <div><label class="block text-sm text-gray-600">Placa</label><input type="text" name="veiculo-placa" class="w-full px-2 py-1 border rounded-lg" placeholder="Placa do veículo"></div>
                <div><label class="block text-sm text-gray-600">Modelo</label><input type="text" name="veiculo-modelo" class="w-full px-2 py-1 border rounded-lg" placeholder="Modelo do veículo"></div>
            </div>
            <button type="button" onclick="this.parentNode.remove()" class="text-red-500 hover:text-red-700 font-bold text-lg">X</button>
         `;
    } else if (containerId === 'apreensoes') {
        newGroup.className = 'apreensao-campo-group border-b pb-4 flex items-center gap-2';
        newGroup.innerHTML = `
            <div class="grid grid-cols-1 md:grid-cols-3 gap-2 flex-grow">
                <div>
                    <label class="block text-sm text-gray-600">Tipo</label>
                    <select name="apreensao-tipo" class="w-full px-2 py-1 border rounded-lg">
                        <option value="" disabled selected>Selecione</option>
                        <option value="Maconha">Maconha</option>
                        <option value="Skunk">Skunk</option>
                        <option value="Cocaina">Cocaína</option>
                        <option value="Crack">Crack</option>
                        <option value="Sintéticos">Sintéticos</option>
                        <option value="Arma">Arma</option>
                    </select>
                </div>
                <div>
                    <label class="block text-sm text-gray-600">Quantidade</label>
                    <input type="number" name="apreensao-qtd" class="w-full px-2 py-1 border rounded-lg" placeholder="Ex: 5">
                </div>
                <div>
                    <label class="block text-sm text-gray-600">Unidade</label>
                    <select name="apreensao-unidade" class="w-full px-2 py-1 border rounded-lg">
                        <option value="" disabled selected>Selecione</option>
                        <option value="kg">Kg</option>
                        <option value="g">Gramas</option>
                        <option value="un">Unidades</option>
                    </select>
                </div>
            </div>
            <button type="button" onclick="this.parentNode.remove()" class="text-red-500 hover:text-red-700 font-bold text-lg">X</button>
        `;
    }
    container.appendChild(newGroup);
}

/**
 * Exclui um item (pessoa ou ocorrência) através da API.
 * @param {string} type - O tipo de item ('pessoa' ou 'ocorrencia').
 * @param {number} id - O ID do item a ser excluído.
 */
async function deleteItem(type, id) {
    if (!confirm(`Tem a certeza que deseja excluir este item? A ação não pode ser desfeita.`)) return;
    try {
        const response = await fetch(`/api/${type}/${id}`, { method: 'DELETE' });
        const result = await response.json();
        if (!response.ok) throw new Error(result.error);
        // Dispara um evento para que a página de consulta saiba que precisa de ser atualizada.
        document.dispatchEvent(new CustomEvent('data-changed'));
    } catch (error) {
        alert(`Erro ao excluir: ${error.message}`);
    }
}

// --- LÓGICA PARA SHIFT-CLICK NAS CHECKBOXES ---
let lastCheckedIda = null;
let lastCheckedVolta = null;
document.addEventListener('click', function(e) {
    if (e.target.matches('.passagem-checkbox')) {
        const checkbox = e.target;
        const column = checkbox.dataset.column;
        let lastChecked = (column === 'ida') ? lastCheckedIda : lastCheckedVolta;
        if (e.shiftKey && lastChecked) {
            const checkboxesInColumn = document.querySelectorAll(`.passagem-checkbox[data-column="${column}"]`);
            const allCheckboxesArray = Array.from(checkboxesInColumn);
            const start = allCheckboxesArray.indexOf(lastChecked);
            const end = allCheckboxesArray.indexOf(checkbox);
            const range = allCheckboxesArray.slice(Math.min(start, end), Math.max(start, end) + 1);
            range.forEach(cb => {
                if (cb.checked !== checkbox.checked) {
                    cb.checked = checkbox.checked;
                    updatePassagem(cb, cb.dataset.id, column);
                }
            });
        }
        if (column === 'ida') {
            lastCheckedIda = checkbox;
        } else {
            lastCheckedVolta = checkbox;
        }
    }
});


// --- LÓGICA DE INICIALIZAÇÃO GLOBAL ---
document.addEventListener('DOMContentLoaded', () => {
    // Ativa o link de navegação da página atual
    const currentPath = window.location.pathname;
    const navLinks = {
        'nav-consulta': ['/', '/consulta'],
        'nav-nova-ocorrencia': ['/nova_ocorrencia'],
        'nav-analise': ['/analise']
    };

    for (const [navId, paths] of Object.entries(navLinks)) {
        const navElement = document.getElementById(navId);
        if (navElement && paths.some(path => currentPath.endsWith(path))) {
            navElement.classList.replace('inactive', 'active');
        }
    }

    // Adiciona o listener para o botão de guardar do modal
    const modalSaveBtn = document.getElementById('modal-save-btn');
    if (modalSaveBtn) {
        modalSaveBtn.addEventListener('click', handleModalSave);
    }
});
