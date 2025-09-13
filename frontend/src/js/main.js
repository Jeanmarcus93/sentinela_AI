console.log('Sentinela IA - Versão Funcional');

document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM carregado');
    
    // Testar conexão com backend
    fetch('/api/health')
        .then(response => response.json())
        .then(data => console.log('Backend OK:', data))
        .catch(error => console.error('Erro backend:', error));
    
    // Navegação com páginas funcionais
    document.addEventListener('click', function(e) {
        if (e.target.tagName === 'A' && e.target.href.includes('#')) {
            e.preventDefault();
            const page = e.target.href.split('#')[1];
            console.log('Navegando para:', page);
            loadPage(page);
        }
    });
    
    function loadPage(page) {
        const content = document.querySelector('main');
        
        switch(page) {
            case 'consulta':
                content.innerHTML = '<h2>Consulta de Placas</h2>' +
                    '<form id="form-consulta">' +
                    '<label>Digite a placa:</label>' +
                    '<input type="text" id="placa" placeholder="ABC1234" maxlength="7" style="text-transform: uppercase; padding: 10px; margin: 10px;">' +
                    '<button type="submit" style="padding: 10px 20px; background: #007bff; color: white; border: none;">Consultar</button>' +
                    '</form>' +
                    '<div id="resultado-consulta"></div>';
                
                // Adicionar evento ao formulário
                document.getElementById('form-consulta').addEventListener('submit', function(e) {
                    e.preventDefault();
                    const placa = document.getElementById('placa').value;
                    consultarPlaca(placa);
                });
                break;
                
            case 'nova-ocorrencia':
                content.innerHTML = '<h2>Nova Ocorrência</h2><p>Formulário de ocorrência em desenvolvimento...</p>';
                break;
                
            case 'analise':
                content.innerHTML = '<h2>Análise de Dados</h2><p>Dashboard de análise em desenvolvimento...</p>';
                break;
                
            case 'analise-ia':
                content.innerHTML = '<h2>Análise com IA</h2><p>Sistema de IA em desenvolvimento...</p>';
                break;
        }
    }
    
    function consultarPlaca(placa) {
        const resultado = document.getElementById('resultado-consulta');
        resultado.innerHTML = '<p>Consultando placa ' + placa + '...</p>';
        
        fetch('/api/consulta_placa/' + placa)
            .then(response => response.json())
            .then(data => {
                resultado.innerHTML = '<h3>Resultado:</h3><pre>' + JSON.stringify(data, null, 2) + '</pre>';
            })
            .catch(error => {
                resultado.innerHTML = '<p style="color: red;">Erro: ' + error.message + '</p>';
            });
    }
    
    // Carregar página inicial
    loadPage('consulta');
});
