# Script de Setup Automático - Sistema Familiar 2.0
# Execute: .\setup.ps1

Write-Host "🏠 Sistema Familiar 2.0 - Setup Automático" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""

# Verificar Python
Write-Host "📦 Verificando Python..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version
    Write-Host "✓ Python encontrado: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ Python não encontrado! Instale Python 3.10+ primeiro." -ForegroundColor Red
    exit 1
}

# Verificar Node.js
Write-Host "📦 Verificando Node.js..." -ForegroundColor Yellow
try {
    $nodeVersion = node --version
    Write-Host "✓ Node.js encontrado: $nodeVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ Node.js não encontrado! Instale Node.js 18+ primeiro." -ForegroundColor Red
    exit 1
}

# Verificar PostgreSQL
Write-Host "📦 Verificando PostgreSQL..." -ForegroundColor Yellow
try {
    $pgVersion = psql --version
    Write-Host "✓ PostgreSQL encontrado: $pgVersion" -ForegroundColor Green
} catch {
    Write-Host "⚠ PostgreSQL não encontrado no PATH. Certifique-se de que está instalado." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "🔧 Configurando Backend..." -ForegroundColor Cyan

# Backend Setup
Set-Location backend

# Criar ambiente virtual
if (!(Test-Path "venv")) {
    Write-Host "Criando ambiente virtual Python..." -ForegroundColor Yellow
    python -m venv venv
}

# Ativar ambiente virtual
Write-Host "Ativando ambiente virtual..." -ForegroundColor Yellow
.\venv\Scripts\Activate.ps1

# Instalar dependências
Write-Host "Instalando dependências do backend..." -ForegroundColor Yellow
pip install -r requirements.txt

Write-Host "✓ Backend configurado!" -ForegroundColor Green

Set-Location ..

Write-Host ""
Write-Host "🎨 Configurando Frontend..." -ForegroundColor Cyan

# Frontend Setup
Set-Location frontend

# Instalar dependências
Write-Host "Instalando dependências do frontend..." -ForegroundColor Yellow
npm install

# Instalar dependência adicional
Write-Host "Instalando tailwindcss-animate..." -ForegroundColor Yellow
npm install tailwindcss-animate

Write-Host "✓ Frontend configurado!" -ForegroundColor Green

Set-Location ..

Write-Host ""
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "✅ Setup concluído com sucesso!" -ForegroundColor Green
Write-Host ""
Write-Host "📝 Próximos passos:" -ForegroundColor Yellow
Write-Host ""
Write-Host "1. Configure o PostgreSQL:" -ForegroundColor White
Write-Host "   - Crie o banco: sistema_familiar_db" -ForegroundColor Gray
Write-Host "   - Usuário: sistema_familiar_user" -ForegroundColor Gray
Write-Host "   - Senha: (definida no .env)" -ForegroundColor Gray
Write-Host ""
Write-Host "2. Edite os arquivos .env se necessário:" -ForegroundColor White
Write-Host "   - backend/.env" -ForegroundColor Gray
Write-Host "   - frontend/.env.local" -ForegroundColor Gray
Write-Host ""
Write-Host "3. Inicie os servidores:" -ForegroundColor White
Write-Host ""
Write-Host "   Terminal 1 (Backend):" -ForegroundColor Cyan
Write-Host "   cd backend" -ForegroundColor Gray
Write-Host "   .\venv\Scripts\activate" -ForegroundColor Gray
Write-Host "   uvicorn app.main:app --reload" -ForegroundColor Gray
Write-Host ""
Write-Host "   Terminal 2 (Frontend):" -ForegroundColor Cyan
Write-Host "   cd frontend" -ForegroundColor Gray
Write-Host "   npm run dev" -ForegroundColor Gray
Write-Host ""
Write-Host "4. Acesse:" -ForegroundColor White
Write-Host "   Frontend: http://localhost:5173" -ForegroundColor Cyan
Write-Host "   Backend API: http://localhost:8001" -ForegroundColor Cyan
Write-Host "   Documentação: http://localhost:8001/api/v1/docs" -ForegroundColor Cyan
Write-Host ""
Write-Host "🎉 Bom desenvolvimento!" -ForegroundColor Green

