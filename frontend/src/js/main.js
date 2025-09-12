// main.js - Sistema Principal Sentinela IA
// ==========================================

/**
 * Aplicação Principal do Sentinela IA
 * Sistema de Análise de Placas com IA e Agentes Especializados
 */
class SentinelaApp {
    constructor() {
        this.config = {
            version: '2.0.0',
            debug: window.location.hostname === 'localhost',
            apiBaseUrl: window.location.origin,
            features: {
                pwa: true,
                offline: true,
                notifications: true,
                backgroundSync: true
            }
        };
        
        this.state = {
            isOnline: navigator.onLine,
            currentPage: this.getCurrentPage(),
            user: null,
            cache: new Map(),
            pendingRequests: new Map(),
            lastActivity: Date.now()
        };
        
        this.components = new Map();
        this.eventBus = new EventTarget();
        
        this.init();
    }
    
    /**
     * Inicialização da aplicação
     */
    async init() {
        try {
            this.log('🚀 Inicializando Sentinela IA...');
            
            // Configurações básicas
            this.setupErrorHandling();
            this.setupNetworkMonitoring();
            this.setupActivityTracking();
            
            // DOM ready
            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', () => this.onDOMReady());
            } else {
                await this.onDOMReady();
            }
            
            this.log('✅ Sentinela IA inicializado com sucesso');
            
        } catch (error) {
            this.error('❌ Erro na inicialização:', error);
        }
    }
    
    /**
     * Quando o DOM estiver pronto
     */
    async onDOMReady() {
        // Componentes principais
        this.initializeNavigation();
        this.initializeModals();
        this.initializeToasts();
        this.initializeForms();
        this.initializeCustomSelects();
        this.initializeShiftClick();
        
        // PWA Features
        if (this.config.features.pwa) {
            await this.initializePWA();
        }
        
        // Interface updates
        this.updateConnectionStatus();
        this.updatePageState();
        
        // Event listeners globais
        this.setupGlobalEventListeners();
        
        // Componentes específicos da página
        await this.initializePageComponents();
        
        // Cache warming
        this.warmupCache();
    }
    
    /**
     * Configurar tratamento de erros globais
     */
    setupErrorHandling() {
        window.addEventListener('error', (event) => {
            this.error('JavaScript Error:', event.error);
            this.showToast('Erro inesperado na aplicação', 'error');
        });
        
        window.addEventListener('unhandledrejection', (event) => {
            this.error('Promise Rejection:', event.reason);
            this.showToast('Erro de conexão ou processamento', 'error');
        });
    }
    
    /**
     * Monitoramento de conexão de rede
     */
    setupNetworkMonitoring() {
        window.addEventListener('online', () => {
            this.state.isOnline = true;
            this.updateConnectionStatus();
            this.syncOfflineData();
            this.showToast('Conexão restabelecida', 'success');
        });
        
        window.addEventListener('offline', () => {
            this.state.isOnline = false;
            this.updateConnectionStatus();
            this.showToast('Modo offline ativo', 'warning');
        });
    }
    
    /**
     * Rastreamento de atividade do usuário
     */
    setupActivityTracking() {
        const updateActivity = () => {
            this.state.lastActivity = Date.now();
        };
        
        ['click', 'keypress', 'scroll', 'mousemove'].forEach(event => {
            document.addEventListener(event, updateActivity, { passive: true });
        });
    }
    
    /**
     * Inicializar navegação
     */
    initializeNavigation() {
        const currentPath = window.location.pathname;
        const navLinks = {
            'nav-consulta': ['/', '/consulta'],
            'nav-nova-ocorrencia': ['/nova_ocorrencia'],
            'nav-analise': ['/analise'],
            'nav-analise-ia': ['/analise_IA']
        };
        
        // Ativar link atual
        Object.entries(navLinks).forEach(([navId, paths]) => {
            const navElement = document.getElementById(navId);
            if (!navElement) return;
            
            const isActive = paths.some(path => 
                currentPath.endsWith(path) || (path === '/' && currentPath === '/')
            );
            
            if (isActive) {
                navElement.classList.remove('nav-link--inactive');
                navElement.classList.add('nav-link--active');
            } else {
                navElement.classList.remove('nav-link--active');
                navElement.classList.add('nav-link--inactive');
            }
        });
        
        // Sidebar mobile toggle
        this.initializeSidebarToggle();
    }
    
    /**
     * Toggle da sidebar para mobile
     */
    initializeSidebarToggle() {
        const sidebar = document.querySelector('.sidebar');
        const toggleBtn = document.getElementById('sidebar-toggle');
        
        if (toggleBtn && sidebar) {
            toggleBtn.addEventListener('click', () => {
                sidebar.classList.toggle('sidebar--open');
            });
            
            // Fechar ao clicar fora
            document.addEventListener('click', (e) => {
                if (!sidebar.contains(e.target) && !toggleBtn.contains(e.target)) {
                    sidebar.classList.remove('sidebar--open');
                }
            });
        }
    }
    
    /**
     * Inicializar sistema de modais
     */
    initializeModals() {
        // Modal principal
        const modal = document.getElementById('edit-modal');
        const modalSaveBtn = document.getElementById('modal-save-btn');
        const modalCloseBtn = document.querySelector('[onclick="closeModal()"]');
        
        if (modalSaveBtn) {
            modalSaveBtn.addEventListener('click', this.handleModalSave.bind(this));
        }
        
        // Fechar modal com ESC
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && modal && !modal.classList.contains('hidden')) {
                this.closeModal();
            }
        });
        
        // Fechar modal clicando no backdrop
        if (modal) {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    this.closeModal();
                }
            });
        }
    }
    
    /**
     * Inicializar sistema de toast notifications
     */
    initializeToasts() {
        // Container para toasts
        if (!document.getElementById('toast-container')) {
            const container = document.createElement('div');
            container.id = 'toast-container';
            container.className = 'fixed top-4 right-4 z-50 space-y-2';
            document.body.appendChild(container);
        }
    }
    
    /**
     * Inicializar formulários
     */
    initializeForms() {
        // Auto uppercase para inputs de placa
        document.querySelectorAll('.placa-input, .form-input.uppercase').forEach(input => {
            input.addEventListener('input', (e) => {
                e.target.value = e.target.value.toUpperCase();
            });
        });
        
        // Validação em tempo real
        document.querySelectorAll('.form-input[required]').forEach(input => {
            input.addEventListener('blur', this.validateField.bind(this));
            input.addEventListener('input', this.clearFieldError.bind(this));
        });
        
        // Submit com prevenção de double-click
        document.querySelectorAll('form').forEach(form => {
            form.addEventListener('submit', this.handleFormSubmit.bind(this));
        });
    }
    
    /**
     * Inicializar custom selects com checkboxes
     */
    initializeCustomSelects() {
        document.addEventListener('click', (e) => {
            const button = e.target.closest('.custom-select-button');
            
            if (button) {
                const targetId = button.dataset.target;
                const options = document.getElementById(targetId);
                
                if (options) {
                    // Fechar outros selects
                    document.querySelectorAll('.custom-select-options.show').forEach(openSelect => {
                        if (openSelect.id !== targetId) {
                            openSelect.classList.remove('show');
                            openSelect.previousElementSibling.classList.remove('open');
                        }
                    });
                    
                    // Toggle atual
                    options.classList.toggle('show');
                    button.classList.toggle('open');
                }
            } else if (!e.target.closest('.custom-select-options')) {
                // Fechar todos se clicou fora
                document.querySelectorAll('.custom-select-options.show').forEach(openSelect => {
                    openSelect.classList.remove('show');
                    openSelect.previousElementSibling.classList.remove('open');
                });
            }
        });
        
        // Update button text on checkbox change
        document.addEventListener('change', (e) => {
            if (e.target.type === 'checkbox' && e.target.closest('.custom-select-options')) {
                this.updateCustomSelectText(e.target.closest('.custom-select-options'));
            }
        });
    }
    
    /**
     * Atualizar texto do custom select
     */
    updateCustomSelectText(optionsContainer) {
        const selectedCheckboxes = optionsContainer.querySelectorAll('input[type="checkbox"]:checked');
        const button = optionsContainer.previousElementSibling;
        const textElement = button.querySelector('.selected-items-text');
        
        if (!textElement) return;
        
        const placeholder = button.dataset.placeholder || 'Selecione...';
        
        if (selectedCheckboxes.length === 0) {
            textElement.textContent = placeholder;
            textElement.style.color = '#6b7280';
        } else if (selectedCheckboxes.length === 1) {
            textElement.textContent = selectedCheckboxes[0].value;
            textElement.style.color = '#111827';
        } else {
            textElement.textContent = `${selectedCheckboxes.length} itens selecionados`;
            textElement.style.color = '#111827';
        }
    }
    
    /**
     * Inicializar funcionalidade Shift+Click
     */
    initializeShiftClick() {
        let lastCheckedIda = null;
        let lastCheckedVolta = null;
        
        document.addEventListener('click', async (e) => {
            if (!e.target.matches('.passagem-checkbox')) return;
            
            const checkbox = e.target;
            const column = checkbox.dataset.column;
            
            let lastChecked = (column === 'ida') ? lastCheckedIda : lastCheckedVolta;
            
            if (e.shiftKey && lastChecked) {
                const checkboxes = Array.from(document.querySelectorAll(`.passagem-checkbox[data-column="${column}"]`));
                const start = checkboxes.indexOf(lastChecked);
                const end = checkboxes.indexOf(checkbox);
                const rangeStart = Math.min(start, end);
                const rangeEnd = Math.max(start, end);
                const inBetween = checkboxes.slice(rangeStart, rangeEnd + 1);
                
                for (const cb of inBetween) {
                    cb.checked = checkbox.checked;
                    await this.updatePassagem(cb, cb.dataset.id, cb.dataset.column);
                }
            }
            
            if (column === 'ida') {
                lastCheckedIda = checkbox;
            } else {
                lastCheckedVolta = checkbox;
            }
            
            if (!e.shiftKey) {
                await this.updatePassagem(checkbox, checkbox.dataset.id, checkbox.dataset.column);
            }
        });
    }
    
    /**
     * Configurar event listeners globais
     */
    setupGlobalEventListeners() {
        // Atalhos de teclado
        document.addEventListener('keydown', this.handleKeyboardShortcuts.bind(this));
        
        // Data change events
        document.addEventListener('data-changed', this.handleDataChange.bind(this));
        
        // Resize events
        window.addEventListener('resize', this.debounce(this.handleResize.bind(this), 250));
        
        // Visibility change
        document.addEventListener('visibilitychange', this.handleVisibilityChange.bind(this));
    }
    
    /**
     * Inicializar componentes específicos da página
     */
    async initializePageComponents() {
        const page = this.state.currentPage;
        
        try {
            switch (page) {
                case 'consulta':
                    await this.loadPageComponent('consulta');
                    break;
                case 'nova_ocorrencia':
                    await this.loadPageComponent('nova-ocorrencia');
                    break;
                case 'analise':
                    await this.loadPageComponent('analise');
                    break;
                case 'analise_IA':
                    await this.loadPageComponent('analise-ia');
                    break;
            }
        } catch (error) {
            this.error(`Erro ao carregar componente da página ${page}:`, error);
        }
    }
    
    /**
     * Carregar componente específico da página
     */
    async loadPageComponent(componentName) {
        if (this.components.has(componentName)) {
            return this.components.get(componentName);
        }
        
        try {
            const module = await import(`./components/${componentName}.js`);
            const component = new module.default(this);
            this.components.set(componentName, component);
            
            if (typeof component.init === 'function') {
                await component.init();
            }
            
            return component;
        } catch (error) {
            this.warn(`Componente ${componentName} não encontrado ou erro no carregamento:`, error);
            return null;
        }
    }
    
    /**
     * Inicializar PWA
     */
    async initializePWA() {
        try {
            // Service Worker
            if ('serviceWorker' in navigator) {
                await this.registerServiceWorker();
            }
            
            // Install prompt
            this.setupInstallPrompt();
            
            // Background sync
            if ('serviceWorker' in navigator && 'sync' in window.ServiceWorkerRegistration.prototype) {
                this.setupBackgroundSync();
            }
            
        } catch (error) {
            this.error('Erro ao inicializar PWA:', error);
        }
    }
    
    /**
     * Registrar Service Worker
     */
    async registerServiceWorker() {
        try {
            const registration = await navigator.serviceWorker.register('/service-worker.js');
            this.log('✅ Service Worker registrado:', registration.scope);
            
            // Listen for updates
            registration.addEventListener('updatefound', () => {
                const newWorker = registration.installing;
                newWorker.addEventListener('statechange', () => {
                    if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
                        this.showUpdateNotification();
                    }
                });
            });
            
        } catch (error) {
            this.error('❌ Falha ao registrar Service Worker:', error);
        }
    }
    
    /**
     * Setup install prompt
     */
    setupInstallPrompt() {
        let deferredPrompt;
        
        window.addEventListener('beforeinstallprompt', (e) => {
            e.preventDefault();
            deferredPrompt = e;
            this.showInstallButton();
        });
        
        window.addEventListener('appinstalled', () => {
            this.hideInstallButton();
            this.showToast('App instalado com sucesso!', 'success');
        });
        
        // Install button
        const installBtn = this.createInstallButton();
        installBtn.addEventListener('click', async () => {
            if (deferredPrompt) {
                deferredPrompt.prompt();
                const { outcome } = await deferredPrompt.userChoice;
                this.log('Install prompt result:', outcome);
                deferredPrompt = null;
                this.hideInstallButton();
            }
        });
    }
    
    /**
     * Criar botão de instalação
     */
    createInstallButton() {
        let installBtn = document.getElementById('pwa-install-btn');
        
        if (!installBtn) {
            installBtn = document.createElement('button');
            installBtn.id = 'pwa-install-btn';
            installBtn.className = 'fixed bottom-4 right-4 bg-primary-600 hover:bg-primary-700 text-white px-4 py-2 rounded-lg shadow-lg z-50 hidden transition-all duration-300 flex items-center gap-2';
            installBtn.innerHTML = `
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
                </svg>
                <span>Instalar App</span>
            `;
            document.body.appendChild(installBtn);
        }
        
        return installBtn;
    }
    
    /**
     * API Request com cache e retry
     */
    async apiRequest(url, options = {}) {
        const cacheKey = `${options.method || 'GET'}-${url}`;
        const cached = this.state.cache.get(cacheKey);
        
        // Return cached if available and not expired
        if (cached && Date.now() - cached.timestamp < (options.cacheTime || 300000)) {
            return cached.data;
        }
        
        const requestOptions = {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        };
        
        try {
            const response = await fetch(url, requestOptions);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            
            // Cache successful GET requests
            if (requestOptions.method === 'GET') {
                this.state.cache.set(cacheKey, {
                    data,
                    timestamp: Date.now()
                });
            }
            
            return data;
            
        } catch (error) {
            // If offline, try to return cached data
            if (!this.state.isOnline && cached) {
                this.showToast('Dados do cache (offline)', 'warning');
                return cached.data;
            }
            
            throw error;
        }
    }
    
    /**
     * Utilitários
     */
    getCurrentPage() {
        const path = window.location.pathname;
        if (path === '/' || path === '/consulta') return 'consulta';
        if (path === '/nova_ocorrencia') return 'nova_ocorrencia';
        if (path === '/analise') return 'analise';
        if (path === '/analise_IA') return 'analise_IA';
        return 'unknown';
    }
    
    showLoader(container) {
        if (container) {
            container.innerHTML = '<div class="loader"></div>';
        }
    }
    
    hideLoader(container) {
        const loader = container?.querySelector('.loader');
        if (loader) {
            loader.remove();
        }
    }
    
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
    
    formatDate(date) {
        if (!date) return 'N/D';
        try {
            const d = new Date(date);
            return d.toLocaleDateString('pt-BR') + ' ' + d.toLocaleTimeString('pt-BR', { 
                hour: '2-digit', 
                minute: '2-digit' 
            });
        } catch {
            return String(date);
        }
    }
    
    validateField(event) {
        const field = event.target;
        const value = field.value.trim();
        let isValid = true;
        let message = '';
        
        if (field.hasAttribute('required') && !value) {
            isValid = false;
            message = 'Este campo é obrigatório';
        } else if (field.type === 'email' && value && !this.isValidEmail(value)) {
            isValid = false;
            message = 'Email inválido';
        } else if (field.classList.contains('placa-input') && value && !this.isValidPlaca(value)) {
            isValid = false;
            message = 'Formato de placa inválido';
        }
        
        this.setFieldError(field, isValid ? null : message);
        return isValid;
    }
    
    setFieldError(field, message) {
        const errorElement = field.parentNode.querySelector('.form-error');
        
        if (message) {
            field.classList.add('border-red-500');
            if (errorElement) {
                errorElement.textContent = message;
            } else {
                const error = document.createElement('div');
                error.className = 'form-error text-red-600 text-xs mt-1';
                error.textContent = message;
                field.parentNode.appendChild(error);
            }
        } else {
            field.classList.remove('border-red-500');
            if (errorElement) {
                errorElement.remove();
            }
        }
    }
    
    clearFieldError(event) {
        this.setFieldError(event.target, null);
    }
    
    isValidEmail(email) {
        return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
    }
    
    isValidPlaca(placa) {
        return /^[A-Z]{3}[0-9]{4}$|^[A-Z]{3}[0-9][A-Z][0-9]{2}$/.test(placa);
    }
    
    /**
     * Event Handlers
     */
    handleFormSubmit(event) {
        const form = event.target;
        const submitBtn = form.querySelector('[type="submit"]');
        
        // Prevenir double submit
        if (submitBtn && submitBtn.disabled) {
            event.preventDefault();
            return;
        }
        
        // Validar campos
        const fields = form.querySelectorAll('.form-input[required]');
        let isValid = true;
        
        fields.forEach(field => {
            if (!this.validateField({ target: field })) {
                isValid = false;
            }
        });
        
        if (!isValid) {
            event.preventDefault();
            this.showToast('Por favor, corrija os erros no formulário', 'error');
            return;
        }
        
        // Desabilitar botão temporariamente
        if (submitBtn) {
            submitBtn.disabled = true;
            const originalText = submitBtn.textContent;
            submitBtn.textContent = 'Processando...';
            
            setTimeout(() => {
                submitBtn.disabled = false;
                submitBtn.textContent = originalText;
            }, 2000);
        }
    }
    
    handleKeyboardShortcuts(event) {
        // Ctrl+K ou Cmd+K para busca
        if ((event.ctrlKey || event.metaKey) && event.key === 'k') {
            event.preventDefault();
            const searchInput = document.querySelector('.search-box__input, #search-input');
            if (searchInput) {
                searchInput.focus();
            }
        }
        
        // Esc para fechar modais
        if (event.key === 'Escape') {
            this.closeModal();
        }
    }
    
    handleDataChange() {
        // Limpar cache relacionado
        this.state.cache.clear();
        
        // Recarregar dados se necessário
        this.eventBus.dispatchEvent(new CustomEvent('refresh-data'));
    }
    
    handleResize() {
        // Ajustar layout responsivo
        this.updatePageState();
    }
    
    handleVisibilityChange() {
        if (document.hidden) {
            // Página ficou invisible
            this.state.lastActivity = Date.now();
        } else {
            // Página ficou visible novamente
            this.syncOfflineData();
        }
    }
    
    /**
     * Modal methods
     */
    openModal(type, dataString) {
        // Implementação específica no componente correspondente
        this.eventBus.dispatchEvent(new CustomEvent('open-modal', {
            detail: { type, dataString }
        }));
    }
    
    closeModal() {
        const modal = document.getElementById('edit-modal');
        if (modal) {
            modal.classList.add('hidden');
        }
    }
    
    async handleModalSave() {
        // Implementação específica no componente correspondente
        this.eventBus.dispatchEvent(new CustomEvent('modal-save'));
    }
    
    /**
     * Toast notifications
     */
    showToast(message, type = 'info', duration = 5000) {
        const container = document.getElementById('toast-container');
        if (!container) return;
        
        const toast = document.createElement('div');
        toast.className = `toast animate-slide-in ${type}`;
        
        const typeColors = {
            success: 'bg-green-500',
            error: 'bg-red-500', 
            warning: 'bg-orange-500',
            info: 'bg-blue-500'
        };
        
        toast.innerHTML = `
            <div class="toast__container ${typeColors[type]} text-white p-4 rounded-lg shadow-lg">
                <div class="flex justify-between items-start gap-3">
                    <div class="flex-1">
                        <p class="text-sm font-medium">${message}</p>
                    </div>
                    <button class="toast__close text-white hover:text-gray-200" onclick="this.closest('.toast').remove()">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                        </svg>
                    </button>
                </div>
            </div>
        `;
        
        container.appendChild(toast);
        
        // Auto remove
        setTimeout(() => {
            if (toast.parentNode) {
                toast.remove();
            }
        }, duration);
    }
    
    showUpdateNotification() {
        this.showToast(
            'Nova versão disponível! Atualize para obter as últimas funcionalidades.',
            'info',
            10000
        );
    }
    
    showInstallButton() {
        const installBtn = document.getElementById('pwa-install-btn');
        if (installBtn) {
            installBtn.classList.remove('hidden');
        }
    }
    
    hideInstallButton() {
        const installBtn = document.getElementById('pwa-install-btn');
        if (installBtn) {
            installBtn.classList.add('hidden');
        }
    }
    
    /**
     * Estado da aplicação
     */
    updateConnectionStatus() {
        const indicator = this.getOrCreateConnectionIndicator();
        
        if (this.state.isOnline) {
            indicator.className = 'connection-indicator connection-indicator--online';
            indicator.innerHTML = `
                <div class="connection-indicator__dot"></div>
                <span>Online</span>
            `;
        } else {
            indicator.className = 'connection-indicator connection-indicator--offline';
            indicator.innerHTML = `
                <div class="connection-indicator__dot"></div>
                <span>Offline</span>
            `;
        }
    }
    
    getOrCreateConnectionIndicator() {
        let indicator = document.getElementById('connection-indicator');
        
        if (!indicator) {
            indicator = document.createElement('div');
            indicator.id = 'connection-indicator';
            document.body.appendChild(indicator);
        }
        
        return indicator;
    }
    
    updatePageState() {
        // Atualizar classes no body baseado no estado atual
        document.body.className = [
            `page-${this.state.currentPage}`,
            this.state.isOnline ? 'online' : 'offline',
            window.innerWidth < 768 ? 'mobile' : 'desktop'
        ].join(' ');
    }
    
    /**
     * Cache e sync
     */
    warmupCache() {
        // Pre-carregar recursos importantes
        const criticalEndpoints = [
            '/api/municipios',
            '/api/analise/filtros'
        ];
        
        criticalEndpoints.forEach(endpoint => {
            this.apiRequest(endpoint).catch(() => {
                // Falha silenciosa para warmup
            });
        });
    }
    
    async syncOfflineData() {
        if (!this.state.isOnline) return;
        
        try {
            // Sync dados pendentes aqui
            this.log('📤 Sincronizando dados offline...');
            // TODO: Implementar sync de dados salvos offline
        } catch (error) {
            this.error('Erro na sincronização:', error);
        }
    }
    
    /**
     * Logging
     */
    log(...args) {
        if (this.config.debug) {
            console.log('[Sentinela]', ...args);
        }
    }
    
    warn(...args) {
        if (this.config.debug) {
            console.warn('[Sentinela]', ...args);
        }
    }
    
    error(...args) {
        console.error('[Sentinela]', ...args);
    }
    
    /**
     * API pública para outros módulos
     */
    getEventBus() {
        return this.eventBus;
    }
    
    getState() {
        return { ...this.state };
    }
    
    getConfig() {
        return { ...this.config };
    }
}

// Métodos globais para compatibilidade
window.openEditModal = function(type, dataString) {
    window.sentinelaApp?.openModal(type, dataString);
};

window.closeModal = function() {
    window.sentinelaApp?.closeModal();
};

window.deleteItem = function(type, id) {
    window.sentinelaApp?.eventBus.dispatchEvent(new CustomEvent('delete-item', {
        detail: { type, id }
    }));
};

// Inicializar aplicação
window.sentinelaApp = new SentinelaApp();

// Export para módulos ES6
export default SentinelaApp;