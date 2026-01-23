# ⚡ CORREÇÃO RÁPIDA - Timezone (11:15 → 14:15)

## 🐛 Problema

Você inseriu: **11:15**  
Sistema gravou: **14:15**  
❌ Diferença de 3 horas!

## ✅ Solução (3 Passos)

### 1️⃣ Parar a Aplicação

```powershell
.\stop.ps1
```

**O que faz:** Para o backend e frontend que estão rodando

---

### 2️⃣ Iniciar Novamente

```powershell
.\start.ps1
```

**O que faz:** 
- Configura timezone automaticamente (`TZ=America/Sao_Paulo`)
- Inicia backend e frontend com a configuração correta

**Você verá:**
```
Timezone configurado: America/Sao_Paulo
Backend iniciando em http://localhost:8001
```

---

### 3️⃣ Testar (Opcional, mas recomendado)

```powershell
.\testar-timezone-dev.ps1
```

**Você deve ver:**
```
Variavel TZ: America/Sao_Paulo
Hora atual: 2025-11-28 11:15:00 (horário correto!)
```

---

## 🧪 Testar na Aplicação

1. Acesse: http://localhost:5173
2. Vá em **Consultas Médicas**
3. Crie uma nova consulta com hora **14:30**
4. Salve
5. Verifique: deve aparecer **14:30** (não 17:30!)

---

## 📝 O Que Foi Alterado

Os scripts `start.ps1` e `start-backend.ps1` foram atualizados para configurar automaticamente:

```powershell
$env:TZ = 'America/Sao_Paulo'
```

**Isso garante que o Python interprete as datas no timezone correto!**

---

## ⚠️ Importante

- ✅ Sempre use `.\start.ps1` para iniciar a aplicação
- ✅ Não inicie manualmente (sem os scripts)
- ✅ Se o problema persistir, reinicie completamente

---

## 🆘 Ainda com Problema?

Se após reiniciar o problema persistir:

1. **Verifique se realmente parou:**
   ```powershell
   .\status.ps1
   ```
   Não deve mostrar nenhum processo na porta 8001

2. **Force o stop:**
   ```powershell
   Get-Process -Name python,node | Stop-Process -Force
   ```

3. **Inicie novamente:**
   ```powershell
   .\start.ps1
   ```

---

## ✅ Resultado Esperado

| Ação | Antes ❌ | Depois ✅ |
|------|----------|-----------|
| Inserir 11:15 | Gravava 14:15 | Grava 11:15 |
| Inserir 14:30 | Gravava 17:30 | Grava 14:30 |
| Inserir 09:00 | Gravava 12:00 | Grava 09:00 |

**Sem mais diferença de 3 horas!** 🎉

---

**Execute agora:**
```powershell
.\stop.ps1
.\start.ps1
```

**Pronto!** 🚀

