# 🛠️ Comandos Úteis - Sistema Familiar

Scripts PowerShell para facilitar o desenvolvimento.

## 📋 Scripts Disponíveis

### `.\status.ps1`
Verifica o status do Backend e Frontend:
- Mostra se estão rodando ou parados
- Exibe porta, PID e uso de memória
- Testa conexão com os serviços
- Mostra URLs úteis

**Exemplo:**
```powershell
.\status.ps1
```

### `.\start.ps1`
Inicia Backend e Frontend simultaneamente em janelas separadas:
- Verifica se já estão rodando antes de iniciar
- Abre janelas do PowerShell para cada serviço
- Mostra URLs após iniciar

**Exemplo:**
```powershell
.\start.ps1
```

### `.\start-backend.ps1`
Inicia apenas o Backend:
- Verifica se já está rodando
- Ativa ambiente virtual automaticamente
- Inicia servidor na porta 8001

**Exemplo:**
```powershell
.\start-backend.ps1
```

### `.\start-frontend.ps1`
Inicia apenas o Frontend:
- Verifica se já está rodando
- Instala dependências se necessário
- Inicia servidor na porta 5173

**Exemplo:**
```powershell
.\start-frontend.ps1
```

### `.\stop.ps1`
Para Backend e Frontend:
- Encontra processos nas portas 8001 e 5173
- Para os processos de forma segura
- Mostra confirmação

**Exemplo:**
```powershell
.\stop.ps1
```

## 🔍 Verificar Status Manualmente

### Verificar Backend (porta 8001)
```powershell
# Ver processos na porta
Get-NetTCPConnection -LocalPort 8001

# Testar API
Invoke-WebRequest -Uri "http://localhost:8001/health"
```

### Verificar Frontend (porta 5173)
```powershell
# Ver processos na porta
Get-NetTCPConnection -LocalPort 5173

# Testar página
Invoke-WebRequest -Uri "http://localhost:5173"
```

## 🐛 Troubleshooting

### Porta já em uso
```powershell
# Ver qual processo está usando a porta
Get-NetTCPConnection -LocalPort 8001 | Select-Object OwningProcess

# Parar processo específico
Stop-Process -Id <PID> -Force
```

### Backend não inicia
```powershell
# Verificar ambiente virtual
Test-Path backend\venv\Scripts\Activate.ps1

# Reinstalar dependências
cd backend
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Frontend não inicia
```powershell
# Verificar node_modules
Test-Path frontend\node_modules

# Reinstalar dependências
cd frontend
npm install
```

## 📚 URLs Importantes

- **Frontend:** http://localhost:5173
- **Backend:** http://localhost:8001
- **API Docs:** http://localhost:8001/api/v1/docs
- **Health Check:** http://localhost:8001/health

## 💡 Dicas

1. **Sempre verifique o status antes de iniciar:**
   ```powershell
   .\status.ps1
   ```

2. **Use scripts individuais para debug:**
   ```powershell
   .\start-backend.ps1  # Inicia apenas backend para ver logs
   ```

3. **Para parar tudo rapidamente:**
   ```powershell
   .\stop.ps1
   ```

4. **Ver logs em tempo real:**
   - Backend: logs aparecem no terminal onde foi iniciado
   - Frontend: logs aparecem no terminal e no console do navegador (F12)

