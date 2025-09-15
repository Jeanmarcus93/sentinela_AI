@echo off
echo ========================================
echo    CRIAR NOVO BANCO POSTGRESQL
echo ========================================
echo.

set /p DB_NAME="Digite o nome do banco de dados: "
set /p DB_HOST="Digite o host (padrao: localhost): "
set /p DB_PORT="Digite a porta (padrao: 5432): "
set /p DB_USER="Digite o usuario (padrao: postgres): "
set /p DB_PASSWORD="Digite a senha (padrao: Jmkjmk.00): "

if "%DB_HOST%"=="" set DB_HOST=localhost
if "%DB_PORT%"=="" set DB_PORT=5432
if "%DB_USER%"=="" set DB_USER=postgres
if "%DB_PASSWORD%"=="" set DB_PASSWORD=Jmkjmk.00

echo.
echo Criando banco: %DB_NAME%
echo Host: %DB_HOST%:%DB_PORT%
echo Usuario: %DB_USER%
echo.

cd /d "%~dp0..\.."

python scripts\create_database.py --db-name "%DB_NAME%" --host "%DB_HOST%" --port %DB_PORT% --user "%DB_USER%" --password "%DB_PASSWORD%"

echo.
pause

