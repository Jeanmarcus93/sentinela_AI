// ===============================================
// ===== FUNÇÕES DA PÁGINA DE NOVA OCORRÊNCIA ====
// ===============================================

/**
 * Converte uma string de data e hora no formato brasileiro (dd/mm/aaaa hh:mm)
 * para o formato ISO (aaaa-mm-ddThh:mm) usado por inputs datetime-local e APIs.
 * @param {string} dataHoraString - A data e hora no formato "dd/mm/aaaa hh:mm".
 * @returns {string|null} A data no formato ISO ou null se o formato for inválido.
 */
function converterDataHoraBrasileiraParaISO(dataHoraString) {
    if (!dataHoraString) return null;
    const regex = /^(\d{2})\/(\d{2})\/(\d{4}) (\d{2}):(\d{2})$/;
    const parts = dataHoraString.match(regex);
    if (!parts) return null;
    const [, dia, mes, ano, hora, minuto] = parts;
    return `${ano}-${mes}-${dia}T${hora}:${minuto}`;
}

/**
 * Adiciona um grupo de campos dinâmicos a um container na tela.
 * @param {string} type - O tipo de campo a ser adicionado ('ocupantes', 'apreensoes', 'presos', 'veiculos').
 */
function addDynamicField(type) {
    let container, newFieldHTML, groupClass;

    const createRemoveButton = () => {
        const removeBtn = document.createElement('button');
        removeBtn.type = 'button';
        removeBtn.innerText = 'Remover';
        removeBtn.className = 'mt-1 px-3 py-1 bg-red-500 text-white rounded-lg text-sm';
        removeBtn.onclick = (e) => e.target.closest('.dynamic-field-group').remove();
        return removeBtn;
    };

    switch (type) {
        case 'apreensoes':
            container = document.getElementById('apreensoes-container');
            groupClass = 'apreensao-campo-group';
            newFieldHTML = `
                <div class="grid grid-cols-1 md:grid-cols-3 gap-2">
                    <div>
                        <label class="text-sm">Tipo de Apreensão</label>
                        <select name="apreensao-tipo" class="mt-1 block w-full rounded-lg border-gray-300">
                            <option value="Maconha">Maconha</option>
                            <option value="Skunk">Skunk</option>
                            <option value="Cocaina">Cocaína</option>
                            <option value="Crack">Crack</option>
                            <option value="Sintéticos">Sintéticos</option>
                            <option value="Arma">Arma</option>
                        </select>
                    </div>
                    <div>
                        <label class="text-sm">Quantidade</label>
                        <input type="number" step="any" name="apreensao-qtd" placeholder="Ex: 10.5" class="mt-1 block w-full rounded-lg border-gray-300" />
                    </div>
                    <div>
                        <label class="text-sm">Unidade</label>
                        <select name="apreensao-unidade" class="mt-1 block w-full rounded-lg border-gray-300">
                            <option value="kg">kg</option>
                            <option value="g">g</option>
                            <option value="un">un</option>
                        </select>
                    </div>
                </div>
            `;
            break;
        case 'ocupantes':
        case 'presos':
            container = type === 'ocupantes' ? document.getElementById('ocupantes-container') : document.getElementById('presos-container');
            groupClass = type === 'ocupantes' ? 'ocupante-campo-group' : 'preso-campo-group';
            newFieldHTML = `
                <div class="grid grid-cols-1 md:grid-cols-2 gap-2">
                    <div>
                        <label class="text-sm">Nome</label>
                        <input type="text" name="${type.slice(0, -1)}-nome" placeholder="Nome Completo" class="mt-1 block w-full rounded-lg border-gray-300" />
                    </div>
                    <div>
                        <label class="text-sm">CPF/CNPJ</label>
                        <input type="text" name="${type.slice(0, -1)}-cpf" placeholder="CPF ou CNPJ" class="mt-1 block w-full rounded-lg border-gray-300" />
                    </div>
                </div>
            `;
            break;
        case 'veiculos':
            container = document.getElementById('veiculos-envolvidos-container');
            groupClass = 'veiculo-campo-group';
            newFieldHTML = `
                <div class="grid grid-cols-1 md:grid-cols-2 gap-2">
                    <div>
                        <label class="text-sm">Placa</label>
                        <input type="text" name="veiculo-placa" placeholder="Placa do Veículo" class="mt-1 block w-full rounded-lg border-gray-300" />
                    </div>
                    <div>
                        <label class="text-sm">Modelo</label>
                        <input type="text" name="veiculo-modelo" placeholder="Modelo do Veículo" class="mt-1 block w-full rounded-lg border-gray-300" />
                    </div>
                </div>
            `;
            break;
        default:
            return;
    }

    if (container) {
        const div = document.createElement('div');
        div.className = `p-2 border rounded-lg bg-gray-50 dynamic-field-group ${groupClass}`;
        div.innerHTML = newFieldHTML;
        div.appendChild(createRemoveButton());
        container.appendChild(div);
    }
}

/**
 * Busca os dados de um veículo pela placa e, se encontrado, monta o formulário de ocorrência.
 * @param {string} placa - A placa do veículo a ser buscado.
 */
async function handleNovaOcorrenciaSearch(placa) {
    const formContainer = document.getElementById('nova-ocorrencia-form-container');
    if (!placa) {
        formContainer.innerHTML = `<p class="text-red-500">Por favor, digite a placa do veículo.</p>`;
        return;
    }
    
    try {
        const response = await fetch(`/api/consulta_placa/${placa}`);
        const data = await response.json();
        if (response.status === 404) {
            throw new Error("Matrícula não encontrada.");
        }
        if (!response.ok) {
            throw new Error(data.error || 'Erro ao buscar veículo.');
        }
        
        const veiculo = data.veiculos[0];
        setupOcorrenciaForm(veiculo.id);

    } catch (error) {
        formContainer.innerHTML = `<p class="text-red-500">❌ ${error.message}</p>`;
    }
}

/**
 * Monta e insere o formulário de nova ocorrência na página.
 * @param {number} veiculoId - O ID do veículo ao qual a ocorrência será associada.
 */
async function setupOcorrenciaForm(veiculoId) {
    const formContainer = document.getElementById('nova-ocorrencia-form-container');
    if (!formContainer) return;
    formContainer.innerHTML = `
        <div class="data-card">
            <h3 class="text-xl font-semibold">✍️ Inserir Nova Ocorrência</h3>
            <form id="ocorrencia-form" class="mt-4 space-y-4"></form>
        </div>
    `;
    const form = document.getElementById('ocorrencia-form');

    form.innerHTML = `
        <input type="hidden" id="veiculo-id" value="${veiculoId}">
        <div>
            <label for="tipo-ocorrencia" class="block text-gray-700">Tipo</label>
            <select id="tipo-ocorrencia" class="mt-1 block w-full rounded-lg border-gray-300">
                <option value="Abordagem">Abordagem</option>
                <option value="BOP">BOP</option>
                <option value="Local de Entrega">Local de Entrega da Droga</option>
            </select>
        </div>
        
        <div>
            <label for="datahora-inicio" class="block text-gray-700">Data e Hora Inicial</label>
            <input type="text" id="datahora-inicio" placeholder="dd/mm/aaaa hh:mm" class="date-input mt-1 block w-full rounded-lg border-gray-300" />
        </div>

        <div id="data-fim-group" class="hidden">
            <label for="datahora-fim" class="block text-gray-700">Data e Hora Final</label>
            <input type="text" id="datahora-fim" placeholder="dd/mm/aaaa hh:mm" class="date-input mt-1 block w-full rounded-lg border-gray-300" />
        </div>
        
        <div id="cidade-entrega-group" class="hidden">
             <label for="cidade-entrega-select" class="block text-gray-700">Cidade da Entrega</label>
             <select id="cidade-entrega-select" class="mt-1 block w-full rounded-lg border-gray-300"></select>
        </div>

        <div id="relato-group"><label for="relato" class="block text-gray-700">Relato</label><textarea id="relato" rows="3" class="mt-1 block w-full rounded-lg border-gray-300"></textarea></div>
        
        <div id="ocupantes-group" class="hidden">
            <label class="block text-gray-700 font-semibold mb-2">Ocupantes</label>
            <div id="ocupantes-container" class="space-y-4"></div>
            <button type="button" id="add-ocupante-btn" class="mt-2 px-4 py-2 bg-gray-200 text-gray-800 rounded-lg hover:bg-gray-300">Adicionar Ocupante</button>
        </div>

        <!-- Veículos Envolvidos agora é um grupo independente -->
        <div id="veiculos-envolvidos-group" class="hidden space-y-4">
             <label class="block text-gray-700 font-semibold mb-2">Veículos Envolvidos</label>
             <div id="veiculos-envolvidos-container" class="space-y-4"></div>
             <button type="button" id="add-veiculo-btn" class="mt-2 px-4 py-2 bg-gray-200 text-gray-800 rounded-lg hover:bg-gray-300">Adicionar Veículo</button>
        </div>
        
        <div id="bop-group" class="hidden space-y-4">
            <div>
                <label class="block text-gray-700 font-semibold mb-2">Apreensões</label>
                <div id="apreensoes-container" class="space-y-4"></div>
                <button type="button" id="add-apreensao-btn" class="mt-2 px-4 py-2 bg-gray-200 text-gray-800 rounded-lg hover:bg-gray-300">Adicionar Apreensão</button>
            </div>
            <div>
                <label class="block text-gray-700 font-semibold mb-2">Presos</label>
                <div id="presos-container" class="space-y-4"></div>
                <button type="button" id="add-preso-btn" class="mt-2 px-4 py-2 bg-gray-200 text-gray-800 rounded-lg hover:bg-gray-300">Adicionar Preso</button>
            </div>
        </div>

        <button type="submit" class="px-4 py-2 bg-green-600 text-white rounded-lg">Guardar Ocorrência</button>
        <div id="form-feedback" class="mt-4"></div>
    `;
    
    const selectTipo = document.getElementById('tipo-ocorrencia');
    const dataFimGroup = document.getElementById('data-fim-group');
    const ocupantesGroup = document.getElementById('ocupantes-group');
    const relatoGroup = document.getElementById('relato-group');
    const cidadeEntregaGroup = document.getElementById('cidade-entrega-group');
    const bopGroup = document.getElementById('bop-group');
    const veiculosEnvolvidosGroup = document.getElementById('veiculos-envolvidos-group');

    const ocupantesContainer = document.getElementById('ocupantes-container');
    const addOcupanteBtn = document.getElementById('add-ocupante-btn');
    const veiculosEnvolvidosContainer = document.getElementById('veiculos-envolvidos-container');
    const addVeiculoBtn = document.getElementById('add-veiculo-btn');
    const apreensoesContainer = document.getElementById('apreensoes-container');
    const addApreensaoBtn = document.getElementById('add-apreensao-btn');
    const presosContainer = document.getElementById('presos-container');
    const addPresoBtn = document.getElementById('add-preso-btn');

    const toggleFields = () => {
        const tipo = selectTipo.value;
        const isEntrega = tipo === 'Local de Entrega';
        const isBOP = tipo === 'BOP';
        const isAbordagem = tipo === 'Abordagem';

        dataFimGroup.classList.toggle('hidden', !isEntrega);
        cidadeEntregaGroup.classList.toggle('hidden', !isEntrega);
        relatoGroup.classList.toggle('hidden', isEntrega);
        ocupantesGroup.classList.toggle('hidden', !isAbordagem);
        bopGroup.classList.toggle('hidden', !isBOP);
        // Exibe o grupo de veículos se for Abordagem OU BOP
        veiculosEnvolvidosGroup.classList.toggle('hidden', !isAbordagem && !isBOP);
        
        ocupantesContainer.innerHTML = '';
        apreensoesContainer.innerHTML = '';
        presosContainer.innerHTML = '';
        veiculosEnvolvidosContainer.innerHTML = '';
    };

    const addOccupantField = () => addDynamicField('ocupantes');
    const addVeiculoField = () => addDynamicField('veiculos');
    const addApreensaoField = () => addDynamicField('apreensoes');
    const addPresoField = () => addDynamicField('presos');

    const cidadeSelect = document.getElementById('cidade-entrega-select');
    try {
        const response = await fetch('/api/municipios');
        const { municipios } = await response.json();
        cidadeSelect.innerHTML = '<option value="">Selecione a cidade...</option>';
        municipios.forEach(m => cidadeSelect.add(new Option(m, m)));
    } catch (error) {
        cidadeSelect.innerHTML = '<option value="">Erro ao carregar cidades</option>';
    }

    selectTipo.addEventListener('change', toggleFields);
    addOcupanteBtn.addEventListener('click', addOccupantField);
    addVeiculoBtn.addEventListener('click', addVeiculoField);
    addApreensaoBtn.addEventListener('click', addApreensaoField);
    addPresoBtn.addEventListener('click', addPresoField);
    
    toggleFields(); // Chamada inicial para configurar os campos

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const feedback = document.getElementById('form-feedback');
        feedback.innerHTML = '';

        const datahoraInicioInput = document.getElementById('datahora-inicio').value;
        const datahoraInicioISO = converterDataHoraBrasileiraParaISO(datahoraInicioInput);

        if (!datahoraInicioISO) {
            feedback.innerHTML = '<p class="text-red-500">Data e Hora inicial são obrigatórias e devem estar no formato dd/mm/aaaa hh:mm.</p>';
            return;
        }
        
        const tipoSelecionado = selectTipo.value;
        const veiculoId = document.getElementById('veiculo-id').value;
        let relatoFinal = null;
        let ocupantes = null;
        let presos = null;
        let apreensoes = null;
        let veiculos = null;
        
        if (tipoSelecionado === 'Local de Entrega') {
            relatoFinal = document.getElementById('cidade-entrega-select').value;
            if (!relatoFinal) {
                 feedback.innerHTML = '<p class="text-red-500">A cidade da entrega é obrigatória.</p>';
                 return;
            }
        } else if (tipoSelecionado === 'Abordagem') {
             const ocupantesList = Array.from(document.querySelectorAll('.ocupante-campo-group')).map(group => ({
                nome: group.querySelector('input[name="ocupante-nome"]').value,
                cpf_cnpj: group.querySelector('input[name="ocupante-cpf"]').value
            })).filter(o => o.nome || o.cpf_cnpj);
             ocupantes = JSON.stringify(ocupantesList);

             const veiculosList = Array.from(document.querySelectorAll('.veiculo-campo-group')).map(group => ({
                placa: group.querySelector('input[name="veiculo-placa"]').value,
                modelo: group.querySelector('input[name="veiculo-modelo"]').value
            })).filter(v => v.placa || v.modelo);
             veiculos = JSON.stringify(veiculosList);

             relatoFinal = document.getElementById('relato').value;
        } else if (tipoSelecionado === 'BOP') {
            const apreensoesList = Array.from(document.querySelectorAll('.apreensao-campo-group')).map(group => ({
                tipo: group.querySelector('select[name="apreensao-tipo"]').value,
                quantidade: group.querySelector('input[name="apreensao-qtd"]').value,
                unidade: group.querySelector('select[name="apreensao-unidade"]').value
            })).filter(a => a.tipo && a.quantidade);
            apreensoes = JSON.stringify(apreensoesList);
            
            const presosList = Array.from(document.querySelectorAll('.preso-campo-group')).map(group => ({
                nome: group.querySelector('input[name="preso-nome"]').value,
                cpf_cnpj: group.querySelector('input[name="preso-cpf"]').value
            })).filter(p => p.nome || p.cpf_cnpj);
            presos = JSON.stringify(presosList);
            
            const veiculosList = Array.from(document.querySelectorAll('.veiculo-campo-group')).map(group => ({
                placa: group.querySelector('input[name="veiculo-placa"]').value,
                modelo: group.querySelector('input[name="veiculo-modelo"]').value
            })).filter(v => v.placa || v.modelo);
             veiculos = JSON.stringify(veiculosList);
             
            relatoFinal = document.getElementById('relato').value;
        }

        const payload = {
            veiculo_id: veiculoId,
            tipo: tipoSelecionado,
            datahora: datahoraInicioISO,
            datahora_fim: null,
            relato: relatoFinal,
            ocupantes: ocupantes,
            presos: presos,
            apreensoes: apreensoes,
            veiculos: veiculos
        };
        
        if (tipoSelecionado === 'Local de Entrega') {
            const datahoraFimInput = document.getElementById('datahora-fim').value;
            if (datahoraFimInput) {
                const datahoraFimISO = converterDataHoraBrasileiraParaISO(datahoraFimInput);
                if(!datahoraFimISO) {
                    feedback.innerHTML = '<p class="text-red-500">O formato da Data e Hora Final é inválido. Use dd/mm/aaaa hh:mm.</p>';
                    return;
                }
                payload.datahora_fim = datahoraFimISO;
            }
        }
        
        try {
            const response = await fetch('/api/ocorrencia', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(payload)
            });
            const result = await response.json();
            if (!response.ok) throw new Error(result.error || 'Erro.');
            feedback.innerHTML = `<p class="text-green-500">${result.message}</p>`;
            document.getElementById('ocorrencia-form').reset();
            toggleFields();
        } catch (error) {
            feedback.innerHTML = `<p class="text-red-500">Erro ao guardar: ${error.message}</p>`;
        }
    });
}

// --- INICIALIZAÇÃO DA PÁGINA DE NOVA OCORRÊNCIA ---
document.addEventListener('DOMContentLoaded', () => {
    const novaOcorrenciaSearchBtn = document.getElementById('nova-ocorrencia-search-btn');
    if (novaOcorrenciaSearchBtn) {
        novaOcorrenciaSearchBtn.addEventListener('click', () => {
            const placaInput = document.getElementById('nova-ocorrencia-search-input');
            if (placaInput) {
                handleNovaOcorrenciaSearch(placaInput.value);
            }
        });
    }

    const placaInput = document.getElementById('nova-ocorrencia-search-input');
    if (placaInput) {
        placaInput.addEventListener('keyup', (event) => {
            if (event.key === 'Enter') {
                handleNovaOcorrenciaSearch(placaInput.value);
            }
        });
    }
});