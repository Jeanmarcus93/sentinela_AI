# Sentinela IA - Script de Desenvolvimento
# Inicia Backend (Flask) e Frontend (Webpack) simultaneamente

Write-Host "🚀 Iniciando Sentinela IA - Desenvolvimento" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host ""

# Função para iniciar processo em nova janela
function Start-ProcessInNewWindow {
    param(
        [string]$Title,
        [string]$WorkingDirectory,
        [string]$Command
    )
    
    $processInfo = New-Object System.Diagnostics.ProcessStartInfo
    $processInfo.FileName = "powershell.exe"
    $processInfo.Arguments = "-NoExit -Command `"cd '$WorkingDirectory'; $Command`""
    $processInfo.WindowStyle = [System.Diagnostics.ProcessWindowStyle]::Normal
    
    $process = New-Object System.Diagnostics.Process
    $process.StartInfo = $processInfo
    $process.Start() | Out-Null
    
    return $process
}

try {
    Write-Host "📡 Iniciando Backend (Flask)..." -ForegroundColor Yellow
    $backendProcess = Start-ProcessInNewWindow -Title "Sentinela Backend" -WorkingDirectory "backend" -Command "python run.py"
    
    Write-Host "⏳ Aguardando 3 segundos..." -ForegroundColor Cyan
    Start-Sleep -Seconds 3
    
    Write-Host "🎨 Iniciando Frontend (Webpack)..." -ForegroundColor Yellow
    $frontendProcess = Start-ProcessInNewWindow -Title "Sentinela Frontend" -WorkingDirectory "frontend" -Command "npm start"
    
    Write-Host ""
    Write-Host "✅ Ambos os serviços foram iniciados!" -ForegroundColor Green
    Write-Host "📋 Backend: http://localhost:5000" -ForegroundColor Cyan
    Write-Host "📋 Frontend: http://localhost:3000" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "💡 Para parar os serviços, feche as janelas individuais" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Pressione qualquer tecla para fechar esta janela..." -ForegroundColor Gray
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    
} catch {
    Write-Host "❌ Erro ao iniciar os serviços: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Pressione qualquer tecla para fechar..." -ForegroundColor Gray
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
}
