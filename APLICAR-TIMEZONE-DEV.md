# Aplicar Timezone em Desenvolvimento (Sem Docker)

## 🎯 Problema Identificado

Você está rodando a aplicação diretamente no Windows (sem Docker) e observou:
- **Inseriu**: 11:15
- **Sistema gravou**: 14:15
- **Diferença**: +3 horas

Isso acontece porque o Python não estava com o timezone configurado corretamente.

## ✅ Solução Aplicada

Os seguintes arquivos foram atualizados para configurar automaticamente o timezone:

### 1. `start.ps1`
✅ Adicionada linha: `$env:TZ = 'America/Sao_Paulo'`

### 2. `start-backend.ps1`
✅ Adicionada linha: `$env:TZ = 'America/Sao_Paulo'`

## 🚀 Como Aplicar

### Passo 1: Parar a Aplicação

```powershell
.\stop.ps1
```

### Passo 2: Iniciar Novamente

```powershell
.\start.ps1
```

Ou:

```powershell
.\start-backend.ps1
```

### Passo 3: Verificar Timezone

```powershell
.\testar-timezone-dev.ps1
```

Você deve ver:
```
Variavel TZ: America/Sao_Paulo
Hora atual (datetime.now()): 2025-11-28 11:15:00 (horário de São Paulo)
```

## 🧪 Testar a Correção

1. **Acesse a aplicação**: http://localhost:5173

2. **Crie uma nova consulta médica**:
   - Paciente: Qualquer
   - Data/Hora: **11:15** (ou qualquer horário)
   - Médico: Teste
   - Especialidade: Teste

3. **Verifique se gravou corretamente**:
   - A consulta deve aparecer com **11:15** (mesmo horário que você inseriu)
   - Não deve mais adicionar 3 horas!

## 📝 O Que Foi Alterado

### Antes ❌
```powershell
# start.ps1
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

### Depois ✅
```powershell
# start.ps1
$env:TZ = 'America/Sao_Paulo'
Write-Host 'Timezone configurado: America/Sao_Paulo' -ForegroundColor Cyan
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

## ⚠️ Importante

### Para Desenvolvimento (Windows - Sem Docker)
✅ Use os scripts atualizados: `start.ps1` ou `start-backend.ps1`  
✅ A variável `$env:TZ` é configurada automaticamente

### Para Produção (Linux - Com Docker)
✅ Use `docker-stack.yml` que já tem `TZ: America/Sao_Paulo`  
✅ Execute `./redeploy-seguro.sh` para aplicar

## 🔍 Troubleshooting

### Problema: Timezone ainda está errado

**Solução:**
1. Verifique se realmente parou o backend:
   ```powershell
   .\stop.ps1
   ```

2. Verifique se nenhum processo está na porta 8001:
   ```powershell
   .\status.ps1
   ```

3. Inicie novamente:
   ```powershell
   .\start.ps1
   ```

4. Teste:
   ```powershell
   .\testar-timezone-dev.ps1
   ```

### Problema: Backend já estava rodando

Se o backend já estava rodando quando você atualizou os scripts, a variável TZ não foi aplicada.

**Solução:** Reinicie o backend.

## ✅ Checklist

- [ ] Parou a aplicação (`.\stop.ps1`)
- [ ] Iniciou novamente (`.\start.ps1`)
- [ ] Testou timezone (`.\testar-timezone-dev.ps1`)
- [ ] Verificou que TZ = 'America/Sao_Paulo'
- [ ] Testou criar uma consulta
- [ ] Verificou que o horário está correto

## 🎉 Resultado Esperado

Agora, quando você:
- Criar uma consulta para **11:15**
- O sistema deve gravar **11:15**
- E exibir **11:15**

**Sem mais diferença de 3 horas!** ✅

---

**Data**: 28/11/2025  
**Status**: ✅ Pronto para Testar

