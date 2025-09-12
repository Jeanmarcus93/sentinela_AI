// src/js/components/consulta.js - Componente de Consulta Sentinela IA
// ===============================================================================

/**
 * Componente responsável pela funcionalidade de consulta de placas/CPF
 * Inclui busca, exibição de resultados, edição e operações CRUD
 */
export default class ConsultaComponent {
    constructor(app) {
        this.app = app;
        this.eventBus = app.getEventBus();
        
        this.state = {
            lastCheckedIda: null,
            lastCheckedVolta: null,
            lastIdaByPlaca: new Map(),
            currentSearchType: 'placa',
            currentSearchValue: '',
            searchTimeout: null,
            isLoading: false,
            lastResults: null
        };
        
        this.elements = {};
        this.config = {
            searchDebounceMs: 500,
            minSearchLength: 3,
            autoSearchEnabled: true
        };
    }
    
    /**
     * Inicialização do componente
     */
    async init() {
        this.app.log('🔍 Inicializando componente de consulta...');
        
        this.findElements();
        this.setupEventListeners();
        this.setupAutoSearch();
        this.restoreSearchState();
        
        this.app.log('✅ Componente de consulta inicializado');
    }
    
    /**
     * Encontrar elementos DOM necessários
     */
    findElements() {
        this.elements = {
            searchType: document.getElementById('search-type'),
            searchInput: document.getElementById('search-input'),
            searchBtn: document.getElementById('search-btn'),
            searchLabel: document.getElementById('search-label'),
            resultContainer: document.getElementById('consulta-result'),
            passagensTable: null // Será encontrado dinamicamente
        };
        
        // Verificar elementos essenciais
        if (!this.elements.searchInput || !this.elements.resultContainer) {
            throw new Error('Elementos essenciais da página de consulta não encontrados');
        }
    }
    
    /**
     * Configurar event listeners
     */
    setupEventListeners() {
        // Busca manual
        if (this.elements.searchBtn) {
            this.elements.searchBtn.addEventListener('click', this.handleSearch.bind(this));
        }
        
        // Enter no input
        this.elements.searchInput.addEventListener('keyup', (event) => {
            if (event.key === 'Enter') {
                this.handleSearch();
            }
        });
        
        // Mudança do tipo de busca
        if (this.elements.searchType) {
            this.elements.searchType.addEventListener('change', this.handleSearchTypeChange.bind(this));
        }
        
        // Event bus listeners
        this.eventBus.addEventListener('open-modal', this.handleOpenModal.bind(this));
        this.eventBus.addEventListener('modal-save', this.handleModalSave.bind(this));
        this.eventBus.addEventListener('delete-item', this.handleDeleteItem.bind(this));
        this.eventBus.addEventListener('data-changed', this.handleDataChanged.bind(this));
        this.eventBus.addEventListener('refresh-data', this.refreshCurrentSearch.bind(this));
        
        // Passagens checkboxes (delegated event)
        document.addEventListener('click', this.handlePassagemClick.bind(this));
    }
    
    /**
     * Configurar busca automática
     */
    setupAutoSearch() {
        if (!this.config.autoSearchEnabled) return;
        
        this.elements.searchInput.addEventListener('input', this.app.debounce(() => {
            const value = this.elements.searchInput.value?.trim();
            if (value && value.length >= this.config.minSearchLength) {
                this.handleSearch();
            } else if (!value) {
                this.clearResults();
            }
        }, this.config.searchDebounceMs));
    }
    
    /**
     * Restaurar estado da busca (se houver)
     */
    restoreSearchState() {
        const urlParams = new URLSearchParams(window.location.search);
        const searchValue = urlParams.get('q');
        const searchType = urlParams.get('type') || 'placa';
        
        if (searchValue) {
            if (this.elements.searchType) {
                this.elements.searchType.value = searchType;
            }
            this.elements.searchInput.value = searchValue;
            this.state.currentSearchType = searchType;
            this.state.currentSearchValue = searchValue;
            this.updateSearchLabel();
            this.handleSearch();
        }
    }
    
    /**
     * Manipular mudança do tipo de busca
     */
    handleSearchTypeChange(event) {
        const newType = event.target.value;
        this.state.currentSearchType = newType;
        this.updateSearchLabel();
        this.updateInputFormat();
        
        // Limpar e dar foco no input
        this.elements.searchInput.value = '';
        this.elements.searchInput.focus();
        this.clearResults();
    }
    
    /**
     * Atualizar label do input baseado no tipo
     */
    updateSearchLabel() {
        if (this.elements.searchLabel) {
            const isPlaca = this.state.currentSearchType === 'placa';
            this.elements.searchLabel.textContent = isPlaca ? 'Digite a Placa:' : 'Digite o CPF:';
        }
    }
    
    /**
     * Atualizar formato do input
     */
    updateInputFormat() {
        const isPlaca = this.state.currentSearchType === 'placa';
        
        if (isPlaca) {
            this.elements.searchInput.classList.add('placa-input', 'uppercase');
            this.elements.searchInput.placeholder = 'Ex: ABC1234';
            this.elements.searchInput.maxLength = 7;
        } else {
            this.elements.searchInput.classList.remove('placa-input', 'uppercase');
            this.elements.searchInput.placeholder = 'Ex: 12345678901';
            this.elements.searchInput.maxLength = 14;
        }
    }
    
    /**
     * Manipular busca
     */
    async handleSearch() {
        const searchValue = this.elements.searchInput.value?.trim();
        const searchType = this.elements.searchType?.value || this.state.currentSearchType;
        
        if (!searchValue) {
            this.showError('Por favor, digite um valor para buscar.');
            return;
        }
        
        // Validação básica
        if (!this.validateSearchValue(searchValue, searchType)) {
            return;
        }
        
        this.state.currentSearchValue = searchValue;
        this.state.currentSearchType = searchType;
        
        // Atualizar URL
        this.updateURL(searchValue, searchType);
        
        // Executar busca
        await this.performSearch(searchValue, searchType);
    }
    
    /**
     * Validar valor da busca
     */
    validateSearchValue(value, type) {
        if (type === 'placa') {
            const cleanValue = value.toUpperCase();
            if (!this.app.isValidPlaca(cleanValue)) {
                this.showError('Formato de placa inválido. Use ABC1234 ou ABC1D23.');
                return false;
            }
        } else if (type === 'cpf') {
            const cleanCPF = value.replace(/\D/g, '');
            if (cleanCPF.length !== 11 && cleanCPF.length !== 14) {
                this.showError('CPF deve ter 11 dígitos ou CNPJ 14 dígitos.');
                return false;
            }
        }
        
        return true;
    }
    
    /**
     * Executar busca na API
     */
    async performSearch(searchValue, searchType) {
        if (this.state.isLoading) return;
        
        this.state.isLoading = true;
        this.showLoading();
        
        try {
            const endpoint = `/api/consulta_${searchType}/${encodeURIComponent(searchValue)}`;
            const data = await this.app.apiRequest(endpoint);
            
            this.state.lastResults = data;
            this.displayResults(data);
            
        } catch (error) {
            this.app.error('Erro na busca:', error);
            
            if (error.message.includes('404')) {
                this.showError(`${searchType === 'placa' ? 'Placa' : 'CPF'} não encontrado nos registros.`);
            } else if (error.message.includes('400')) {
                this.showError('Formato inválido. Verifique os dados e tente novamente.');
            } else {
                this.showError('Erro ao buscar dados. Tente novamente em alguns instantes.');
            }
        } finally {
            this.state.isLoading = false;
        }
    }
    
    /**
     * Exibir resultados da busca
     */
    displayResults(data) {
        const { veiculos = [], pessoas = [], passagens = [], ocorrencias = [] } = data;
        
        let html = '';
        
        // Seção de Veículos
        if (veiculos.length > 0) {
            html += this.renderVeiculosSection(veiculos);
        }
        
        // Seção de Pessoas
        html += this.renderPessoasSection(pessoas, veiculos);
        
        // Seção de Ocorrências
        html += this.renderOcorrenciasSection(ocorrencias);
        
        // Seção de Passagens
        html += this.renderPassagensSection(passagens);
        
        this.elements.resultContainer.innerHTML = html;
        
        // Configurar tabela de passagens
        this.setupPassagensTable();
        
        // Resetar estado de seleção
        this.resetSelectionState();
        
        this.app.log('📊 Resultados exibidos:', { 
            veiculos: veiculos.length, 
            pessoas: pessoas.length, 
            passagens: passagens.length, 
            ocorrencias: ocorrencias.length 
        });
    }
    
    /**
     * Renderizar seção de veículos
     */
    renderVeiculosSection(veiculos) {
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
        
        return veiculosHtml;
    }
    
    /**
     * Renderizar seção de pessoas
     */
    renderPessoasSection(pessoas, veiculos) {
        const escapeData = (data) => encodeURIComponent(JSON.stringify(data));
        
        const pessoasRows = pessoas.length ? pessoas.map(pessoa => {
            const veiculoAssociado = veiculos.find(v => v.id === pessoa.veiculo_id);
            return `
                <tr class="border-b hover:bg-gray-50">
                    <td class="p-2">${veiculoAssociado ? veiculoAssociado.placa : 'N/D'}</td>
                    <td class="p-2">${pessoa.nome || ''}</td>
                    <td class="p-2">${this.formatCpfCnpj(pessoa.cpf_cnpj)}</td>
                    <td class="p-2">
                        <div class="flex gap-1">
                            <button onclick="window.openEditModal('pessoa', '${escapeData(pessoa)}')" 
                                    class="action-btn bg-warning-500 hover:bg-warning-600 text-white">
                                Editar
                            </button>
                            <button onclick="window.deleteItem('pessoa', ${pessoa.id})" 
                                    class="action-btn bg-error-500 hover:bg-error-600 text-white">
                                Excluir
                            </button>
                        </div>
                    </td>
                </tr>
            `;
        }).join('') : '<tr><td colspan="4" class="p-4 text-center text-gray-500">Nenhuma pessoa encontrada.</td></tr>';
        
        return `
            <div class="data-card">
                <h3 class="text-xl font-semibold">👥 Pessoas Relacionadas</h3>
                <div class="table-container">
                    <table class="table">
                        <thead>
                            <tr>
                                <th class="p-2">Placa</th>
                                <th class="p-2">Nome</th>
                                <th class="p-2">CPF/CNPJ</th>
                                <th class="p-2">Ações</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${pessoasRows}
                        </tbody>
                    </table>
                </div>
            </div>
        `;
    }
    
    /**
     * Renderizar seção de ocorrências
     */
    renderOcorrenciasSection(ocorrencias) {
        const escapeData = (data) => encodeURIComponent(JSON.stringify(data));
        
        const ocorrenciasRows = ocorrencias.length ? ocorrencias.map(ocorrencia => `
            <tr class="border-b hover:bg-gray-50">
                <td class="p-2 align-top">${this.app.formatDate(ocorrencia.datahora)}</td>
                <td class="p-2 align-top">
                    <span class="status-badge ${this.getOcorrenciaBadgeClass(ocorrencia.tipo)}">
                        ${this.formatOcorrenciaTipo(ocorrencia.tipo)}
                    </span>
                </td>
                <td class="p-2 break-words align-top max-w-md">
                    ${this.formatRelato(ocorrencia.relato || '')}
                    ${this.renderApreensoes(ocorrencia.apreensoes || [])}
                </td>
                <td class="p-2 align-top">
                    <div class="flex flex-col gap-1">
                        <button onclick="window.openEditModal('ocorrencia', '${escapeData(ocorrencia)}')" 
                                class="action-btn bg-warning-500 hover:bg-warning-600 text-white">
                            Editar
                        </button>
                        <button onclick="window.deleteItem('ocorrencia', ${ocorrencia.id})" 
                                class="action-btn bg-error-500 hover:bg-error-600 text-white">
                            Excluir
                        </button>
                    </div>
                </td>
            </tr>
        `).join('') : '<tr><td colspan="4" class="p-4 text-center text-gray-500">Nenhuma ocorrência encontrada.</td></tr>';
        
        return `
            <div class="data-card">
                <h3 class="text-xl font-semibold">🚨 Ocorrências</h3>
                <div class="table-container">
                    <table class="table table-fixed">
                        <thead>
                            <tr>
                                <th class="p-2 w-[15%]">Data/Hora</th>
                                <th class="p-2 w-[15%]">Tipo</th>
                                <th class="p-2 w-[55%]">Relato</th>
                                <th class="p-2 w-[15%] text-right">Ações</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${ocorrenciasRows}
                        </tbody>
                    </table>
                </div>
            </div>
        `;
    }
    
    /**
     * Renderizar seção de passagens
     */
    renderPassagensSection(passagens) {
        const passagensRows = passagens.length ? passagens.map(passagem => `
            <tr class="border-b hover:bg-gray-50" data-passagem-id="${passagem.id}">
                <td class="p-2">
                    <span class="placa-display placa-display--small">${passagem.placa || 'N/D'}</span>
                </td>
                <td class="p-2">${this.app.formatDate(passagem.datahora)}</td>
                <td class="p-2">${passagem.municipio || 'N/D'}/${passagem.estado || 'N/D'}</td>
                <td class="p-2">${passagem.rodovia || 'N/D'}</td>
                <td class="p-2 text-center">
                    <input type="checkbox" 
                           class="passagem-checkbox" 
                           data-column="ida" 
                           data-id="${passagem.id}"
                           data-placa="${passagem.placa || ''}"
                           data-municipio="${passagem.municipio || ''}"
                           data-datahora="${passagem.datahora || ''}"
                           ${passagem.ilicito_ida ? 'checked' : ''}>
                </td>
                <td class="p-2 text-center">
                    <div class="flex items-center justify-center gap-2">
                        <input type="checkbox" 
                               class="passagem-checkbox" 
                               data-column="volta" 
                               data-id="${passagem.id}"
                               data-placa="${passagem.placa || ''}"
                               data-municipio="${passagem.municipio || ''}"
                               data-datahora="${passagem.datahora || ''}"
                               ${passagem.ilicito_volta ? 'checked' : ''}>
                        <span class="text-success-500 text-xs font-medium" id="passagem-feedback-${passagem.id}"></span>
                    </div>
                </td>
            </tr>
        `).join('') : '<tr><td colspan="6" class="p-4 text-center text-gray-500">Nenhuma passagem encontrada.</td></tr>';
        
        return `
            <div class="data-card">
                <div class="flex items-center justify-between mb-4">
                    <h3 class="text-xl font-semibold">📍 Passagens</h3>
                    <div class="text-xs text-gray-500">
                        💡 Dica: use Shift+Clique para marcar um intervalo
                    </div>
                </div>
                <div class="table-container">
                    <table id="passagens-table" class="table">
                        <thead>
                            <tr>
                                <th class="p-2">Placa</th>
                                <th class="p-2">Data/Hora</th>
                                <th class="p-2">Cidade</th>
                                <th class="p-2">Local</th>
                                <th class="p-2 text-center">Ilícito (Ida)</th>
                                <th class="p-2 text-center">Ilícito (Volta)</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${passagensRows}
                        </tbody>
                    </table>
                </div>
                <div class="mt-3 text-xs text-gray-600 bg-gray-50 p-3 rounded">
                    <strong>ℹ️ Como usar:</strong> Marque uma passagem de <strong>ida</strong> e depois uma de <strong>volta</strong> (da mesma placa) 
                    para criar automaticamente uma ocorrência de <em>Local de Entrega</em> para o período.
                </div>
            </div>
        `;
    }
    
    /**
     * Configurar tabela de passagens
     */
    setupPassagensTable() {
        this.elements.passagensTable = document.getElementById('passagens-table');
    }
    
    /**
     * Manipular clique em checkbox de passagem
     */
    async handlePassagemClick(event) {
        if (!event.target.matches('.passagem-checkbox')) return;
        
        const checkbox = event.target;
        const column = checkbox.dataset.column;
        const passagemId = checkbox.dataset.id;
        const placa = checkbox.dataset.placa;
        const municipio = checkbox.dataset.municipio;
        const datahora = checkbox.dataset.datahora;
        
        // Shift+Click para seleção múltipla
        if (event.shiftKey) {
            await this.handleShiftClickSelection(checkbox, column);
        } else {
            await this.updatePassagem(checkbox, passagemId, column);
        }
        
        // Atualizar estado de seleção
        if (column === 'ida') {
            this.state.lastCheckedIda = checkbox;
            if (checkbox.checked && placa) {
                this.state.lastIdaByPlaca.set(placa, {
                    checkbox,
                    passagemId,
                    municipio,
                    datahora
                });
            }
        } else if (column === 'volta') {
            this.state.lastCheckedVolta = checkbox;
            
            // Verificar se pode criar Local de Entrega
            if (checkbox.checked && placa) {
                await this.checkCreateLocalEntrega(placa, passagemId, municipio, datahora);
            }
        }
    }
    
    /**
     * Manipular seleção Shift+Click
     */
    async handleShiftClickSelection(checkbox, column) {
        const lastChecked = column === 'ida' ? this.state.lastCheckedIda : this.state.lastCheckedVolta;
        
        if (!lastChecked) {
            await this.updatePassagem(checkbox, checkbox.dataset.id, column);
            return;
        }
        
        const checkboxes = Array.from(document.querySelectorAll(`.passagem-checkbox[data-column="${column}"]`));
        const start = checkboxes.indexOf(lastChecked);
        const end = checkboxes.indexOf(checkbox);
        const rangeStart = Math.min(start, end);
        const rangeEnd = Math.max(start, end);
        const inBetween = checkboxes.slice(rangeStart, rangeEnd + 1);
        
        // Atualizar todas as checkboxes no range
        for (const cb of inBetween) {
            cb.checked = checkbox.checked;
            await this.updatePassagem(cb, cb.dataset.id, cb.dataset.column);
        }
    }
    
    /**
     * Atualizar passagem na API
     */
    async updatePassagem(checkbox, passagemId, field) {
        const value = checkbox.checked;
        
        try {
            await this.app.apiRequest(`/api/passagem/${passagemId}`, {
                method: 'PUT',
                body: JSON.stringify({ 
                    field: `ilicito_${field}`, 
                    value: value 
                })
            });
            
            // Feedback visual
            this.showPassagemFeedback(passagemId, 'Salvo!');
            
        } catch (error) {
            this.app.error('Erro ao atualizar passagem:', error);
            
            // Reverter checkbox
            checkbox.checked = !value;
            
            this.app.showToast('Erro ao salvar alteração', 'error');
        }
    }
    
    /**
     * Verificar e criar Local de Entrega
     */
    async checkCreateLocalEntrega(placa, voltaPassagemId, voltaMunicipio, voltaDatahora) {
        const idaInfo = this.state.lastIdaByPlaca.get(placa);
        
        if (!idaInfo) return;
        
        try {
            const idaDate = new Date(idaInfo.datahora);
            const voltaDate = new Date(voltaDatahora);
            
            if (voltaDate <= idaDate) {
                this.app.showToast('Data de volta deve ser posterior à ida', 'warning');
                return;
            }
            
            // Confirmar com usuário
            const municipio = prompt(
                `Criar "Local de Entrega" de ${idaInfo.municipio} para ${voltaMunicipio}?\n\nInforme o município/local de entrega:`, 
                voltaMunicipio
            );
            
            if (municipio === null) return; // Usuário cancelou
            
            // Criar Local de Entrega
            await this.createLocalEntrega({
                placa: placa,
                inicio_iso: idaDate.toISOString(),
                fim_iso: voltaDate.toISOString(),
                municipio: municipio.trim() || voltaMunicipio
            });
            
            this.showPassagemFeedback(voltaPassagemId, 'Local de entrega criado!');
            
            // Limpar estado de ida para esta placa
            this.state.lastIdaByPlaca.delete(placa);
            
        } catch (error) {
            this.app.error('Erro ao criar Local de Entrega:', error);
            this.app.showToast('Erro ao criar Local de Entrega', 'error');
        }
    }
    
    /**
     * Criar Local de Entrega na API
     */
    async createLocalEntrega(payload) {
        await this.app.apiRequest('/api/local_entrega', {
            method: 'POST',
            body: JSON.stringify(payload)
        });
    }
    
    /**
     * Mostrar feedback na passagem
     */
    showPassagemFeedback(passagemId, message) {
        const feedbackEl = document.getElementById(`passagem-feedback-${passagemId}`);
        if (feedbackEl) {
            feedbackEl.textContent = message;
            feedbackEl.classList.add('animate-fade-in');
            setTimeout(() => {
                feedbackEl.textContent = '';
                feedbackEl.classList.remove('animate-fade-in');
            }, 3000);
        }
    }
    
    /**
     * Manipular abertura de modal
     */
    handleOpenModal(event) {
        const { type, dataString } = event.detail;
        
        try {
            const data = JSON.parse(decodeURIComponent(dataString));
            this.openEditModal(type, data);
        } catch (error) {
            this.app.error('Erro ao abrir modal:', error);
            this.app.showToast('Erro ao abrir formulário de edição', 'error');
        }
    }
    
    /**
     * Abrir modal de edição
     */
    openEditModal(type, data) {
        const modal = document.getElementById('edit-modal');
        const form = document.getElementById('modal-form');
        const title = document.getElementById('modal-title');
        
        if (!modal || !form || !title) {
            this.app.error('Elementos do modal não encontrados');
            return;
        }
        
        // Limpar feedback anterior
        const feedback = document.getElementById('modal-feedback');
        if (feedback) feedback.innerHTML = '';
        
        // Configurar título
        title.textContent = `Editar ${type === 'pessoa' ? 'Pessoa' : 'Ocorrência'}`;
        
        // Gerar formulário
        if (type === 'pessoa') {
            form.innerHTML = this.generatePessoaForm(data);
        } else if (type === 'ocorrencia') {
            form.innerHTML = this.generateOcorrenciaForm(data);
        }
        
        // Mostrar modal
        modal.classList.remove('hidden');
        
        // Focar no primeiro input
        const firstInput = form.querySelector('input, textarea, select');
        if (firstInput) {
            setTimeout(() => firstInput.focus(), 100);
        }
    }
    
    /**
     * Gerar formulário de pessoa
     */
    generatePessoaForm(data) {
        return `
            <input type="hidden" name="id" value="${data.id}">
            <input type="hidden" name="type" value="pessoa">
            
            <div class="form-group">
                <label class="form-label">Nome</label>
                <input type="text" name="nome" value="${data.nome || ''}" 
                       class="form-input" placeholder="Nome completo">
            </div>
            
            <div class="form-group">
                <label class="form-label">CPF/CNPJ</label>
                <input type="text" name="cpf_cnpj" value="${data.cpf_cnpj || ''}" 
                       class="form-input" placeholder="Apenas números">
            </div>
        `;
    }
    
    /**
     * Gerar formulário de ocorrência
     */
    generateOcorrenciaForm(data) {
        const datahora = data.datahora ? new Date(data.datahora) : null;
        const datahoraFim = data.datahora_fim ? new Date(data.datahora_fim) : null;
        
        const datahoraStr = datahora ? 
            `${datahora.getFullYear()}-${String(datahora.getMonth() + 1).padStart(2, '0')}-${String(datahora.getDate()).padStart(2, '0')}T${String(datahora.getHours()).padStart(2, '0')}:${String(datahora.getMinutes()).padStart(2, '0')}` : '';
        
        const datahoraFimStr = datahoraFim ? 
            `${datahoraFim.getFullYear()}-${String(datahoraFim.getMonth() + 1).padStart(2, '0')}-${String(datahoraFim.getDate()).padStart(2, '0')}T${String(datahoraFim.getHours()).padStart(2, '0')}:${String(datahoraFim.getMinutes()).padStart(2, '0')}` : '';
        
        let formHtml = `
            <input type="hidden" name="id" value="${data.id}">
            <input type="hidden" name="type" value="ocorrencia">
            
            <div class="form-group">
                <label class="form-label">Tipo</label>
                <input type="text" value="${this.formatOcorrenciaTipo(data.tipo)}" 
                       class="form-input" readonly>
            </div>
            
            <div class="form-group">
                <label class="form-label">Data/Hora de Início</label>
                <input type="datetime-local" name="datahora" value="${datahoraStr}" 
                       class="form-input" required>
            </div>
        `;
        
        // Campos específicos por tipo
        if (data.tipo === 'Local de Entrega') {
            formHtml += `
                <div class="form-group">
                    <label class="form-label">Local de Entrega</label>
                    <input type="text" name="relato" value="${data.relato || ''}" 
                           class="form-input" placeholder="Município/Local">
                </div>
                
                <div class="form-group">
                    <label class="form-label">Data/Hora Final</label>
                    <input type="datetime-local" name="datahora_fim" value="${datahoraFimStr}" 
                           class="form-input">
                </div>
            `;
        } else {
            formHtml += `
                <div class="form-group">
                    <label class="form-label">Relato</label>
                    <textarea name="relato" class="form-textarea" rows="4" 
                              placeholder="Descrição da ocorrência">${data.relato || ''}</textarea>
                </div>
            `;
            
            // Apreensões para BOP
            if (data.tipo === 'BOP' && data.apreensoes) {
                formHtml += this.generateApreensoesDynamicFields(data.apreensoes);
            }
        }
        
        return formHtml;
    }
    
    /**
     * Gerar campos dinâmicos de apreensões
     */
    generateApreensoesDynamicFields(apreensoes) {
        const apreensoesList = Array.isArray(apreensoes) ? apreensoes : [];
        
        const apreensaesHtml = apreensoesList.map(apreensao => `
            <div class="apreensao-campo-group border border-gray-200 p-3 rounded mb-2">
                <div class="grid grid-cols-1 md:grid-cols-3 gap-2">
                    <div>
                        <label class="form-label text-xs">Tipo</label>
                        <select name="apreensao-tipo" class="form-select">
                            <option value="Maconha" ${apreensao.tipo === 'Maconha' ? 'selected' : ''}>Maconha</option>
                            <option value="Skunk" ${apreensao.tipo === 'Skunk' ? 'selected' : ''}>Skunk</option>
                            <option value="Cocaina" ${apreensao.tipo === 'Cocaina' ? 'selected' : ''}>Cocaína</option>
                            <option value="Crack" ${apreensao.tipo === 'Crack' ? 'selected' : ''}>Crack</option>
                            <option value="Sintéticos" ${apreensao.tipo === 'Sintéticos' ? 'selected' : ''}>Sintéticos</option>
                            <option value="Arma" ${(apreensao.tipo === 'Arma' || apreensao.tipo === 'Armas') ? 'selected' : ''}>Arma</option>
                        </select>
                    </div>
                    <div>
                        <label class="form-label text-xs">Quantidade</label>
                        <input type="number" step="any" name="apreensao-qtd" value="${apreensao.quantidade || ''}" 
                               class="form-input" placeholder="Ex: 5.5">
                    </div>
                    <div>
                        <label class="form-label text-xs">Unidade</label>
                        <select name="apreensao-unidade" class="form-select">
                            <option value="kg" ${apreensao.unidade === 'kg' ? 'selected' : ''}>kg</option>
                            <option value="g" ${apreensao.unidade === 'g' ? 'selected' : ''}>g</option>
                            <option value="un" ${apreensao.unidade === 'un' ? 'selected' : ''}>un</option>
                        </select>
                    </div>
                </div>
                <button type="button" onclick="this.parentNode.remove()" 
                        class="btn btn-sm btn-danger mt-2">
                    Remover
                </button>
            </div>
        `).join('');
        
        return `
            <div class="form-group">
                <label class="form-label">Apreensões</label>
                <div id="apreensoes-container">${apreensaesHtml}</div>
                <button type="button" id="add-apreensao-btn" class="btn btn-sm btn-secondary mt-2">
                    Adicionar Apreensão
                </button>
            </div>
        `;
    }
    
    /**
     * Manipular salvamento do modal
     */
    async handleModalSave(event) {
        const form = document.getElementById('modal-form');
        const feedback = document.getElementById('modal-feedback');
        
        if (!form || !feedback) return;
        
        const formData = new FormData(form);
        const data = Object.fromEntries(formData.entries());
        const type = data.type;
        const id = data.id;
        
        feedback.innerHTML = '<div class="text-blue-600">Salvando...</div>';
        
        try {
            // Preparar dados para envio
            const payload = this.prepareModalPayload(data, type);
            
            // Enviar para API
            await this.app.apiRequest(`/api/${type}/${id}`, {
                method: 'PUT',
                body: JSON.stringify(payload)
            });
            
            feedback.innerHTML = '<div class="text-success-600">✅ Salvo com sucesso!</div>';
            
            // Fechar modal após delay
            setTimeout(() => {
                this.app.closeModal();
                this.handleDataChanged();
            }, 1500);
            
        } catch (error) {
            this.app.error('Erro ao salvar:', error);
            feedback.innerHTML = `<div class="text-error-600">❌ Erro ao salvar: ${error.message}</div>`;
        }
    }
    
    /**
     * Preparar payload do modal
     */
    prepareModalPayload(data, type) {
        if (type === 'pessoa') {
            return {
                nome: data.nome?.trim(),
                cpf_cnpj: data.cpf_cnpj?.replace(/\D/g, '')
            };
        } else if (type === 'ocorrencia') {
            const payload = {
                datahora: data.datahora,
                relato: data.relato?.trim()
            };
            
            if (data.datahora_fim) {
                payload.datahora_fim = data.datahora_fim;
            }
            
            // Processar apreensões se existirem
            const apreensoesList = this.extractApreensoes();
            if (apreensoesList.length > 0) {
                payload.apreensoes = JSON.stringify(apreensoesList);
            }
            
            return payload;
        }
        
        return data;
    }
    
    /**
     * Extrair apreensões do formulário
     */
    extractApreensoes() {
        const apreensaoGroups = document.querySelectorAll('.apreensao-campo-group');
        const apreensoes = [];
        
        apreensaoGroups.forEach(group => {
            const tipo = group.querySelector('select[name="apreensao-tipo"]')?.value;
            const quantidade = group.querySelector('input[name="apreensao-qtd"]')?.value;
            const unidade = group.querySelector('select[name="apreensao-unidade"]')?.value;
            
            if (tipo && quantidade && unidade) {
                apreensoes.push({ tipo, quantidade, unidade });
            }
        });
        
        return apreensoes;
    }
    
    /**
     * Manipular exclusão de item
     */
    async handleDeleteItem(event) {
        const { type, id } = event.detail;
        
        if (!confirm(`Tem certeza que deseja excluir este ${type}? Esta ação não pode ser desfeita.`)) {
            return;
        }
        
        try {
            await this.app.apiRequest(`/api/${type}/${id}`, {
                method: 'DELETE'
            });
            
            this.app.showToast(`${type} excluído com sucesso`, 'success');
            this.handleDataChanged();
            
        } catch (error) {
            this.app.error('Erro ao excluir:', error);
            this.app.showToast(`Erro ao excluir ${type}`, 'error');
        }
    }
    
    /**
     * Manipular mudança de dados
     */
    handleDataChanged() {
        // Recarregar busca atual se houver
        if (this.state.currentSearchValue) {
            this.performSearch(this.state.currentSearchValue, this.state.currentSearchType);
        }
    }
    
    /**
     * Atualizar URL com parâmetros de busca
     */
    updateURL(searchValue, searchType) {
        const url = new URL(window.location);
        url.searchParams.set('q', searchValue);
        url.searchParams.set('type', searchType);
        window.history.replaceState({}, '', url);
    }
    
    /**
     * Utilitários de formatação
     */
    formatCpfCnpj(doc) {
        if (!doc) return 'N/D';
        const cleaned = String(doc).replace(/\D/g, '');
        if (cleaned.length === 11) {
            return cleaned.replace(/(\d{3})(\d{3})(\d{3})(\d{2})/, '$1.$2.$3-$4');
        }
        if (cleaned.length === 14) {
            return cleaned.replace(/(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})/, '$1.$2.$3/$4-$5');
        }
        return cleaned;
    }
    
    formatOcorrenciaTipo(tipo) {
        if (tipo === 'Local de Entrega') {
            return 'Local de Entrega da Droga';
        }
        return tipo || 'N/D';
    }
    
    getOcorrenciaBadgeClass(tipo) {
        switch (tipo) {
            case 'BOP': return 'status-badge--suspeito';
            case 'Abordagem': return 'status-badge--ativo';
            case 'Local de Entrega': return 'status-badge--processando';
            default: return 'status-badge--inativo';
        }
    }
    
    formatRelato(relato) {
        if (!relato) return '<em class="text-gray-400">Nenhum relato</em>';
        if (relato.length > 150) {
            return relato.substring(0, 150) + '...';
        }
        return relato;
    }
    
    renderApreensoes(apreensoes) {
        if (!apreensoes || apreensoes.length === 0) return '';
        
        const apreensoesList = apreensoes.map(a => 
            `<span class="inline-block bg-red-100 text-red-800 text-xs px-2 py-1 rounded mr-1 mt-1">
                ${a.tipo}: ${a.quantidade}${a.unidade}
            </span>`
        ).join('');
        
        return `<div class="mt-2">${apreensoesList}</div>`;
    }
    
    /**
     * Estados e utilitários
     */
    showLoading() {
        this.app.showLoader(this.elements.resultContainer);
    }
    
    showError(message) {
        this.elements.resultContainer.innerHTML = `
            <div class="alert alert--error">
                <div class="alert__content">
                    <p class="alert__message">${message}</p>
                </div>
            </div>
        `;
    }
    
    clearResults() {
        this.elements.resultContainer.innerHTML = `
            <p class="text-center text-gray-500">
                Digite uma placa ou CPF para buscar informações.
            </p>
        `;
        this.resetSelectionState();
    }
    
    resetSelectionState() {
        this.state.lastCheckedIda = null;
        this.state.lastCheckedVolta = null;
        this.state.lastIdaByPlaca.clear();
    }
    
    refreshCurrentSearch() {
        if (this.state.currentSearchValue) {
            this.performSearch(this.state.currentSearchValue, this.state.currentSearchType);
        }
    }
    
    /**
     * Cleanup
     */
    destroy() {
        // Remover event listeners específicos se necessário
        this.resetSelectionState();
        this.clearResults();
    }
}