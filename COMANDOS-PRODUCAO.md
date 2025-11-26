# Comandos de Produção - Sistema Familiar

## 🚀 Redeploy Seguro em Produção

**⚠️ COMANDO PADRÃO PARA ATUALIZAR E FAZER REDEPLOY EM PRODUÇÃO:**

```bash
cd /opt/sistema-familiar && git pull origin master && chmod +x redeploy-seguro.sh && ./redeploy-seguro.sh
```

**Este é o comando seguro e recomendado para todas as atualizações em produção.**

Este comando:
1. Navega para o diretório do projeto
2. Faz pull das alterações do Git
3. Garante que o script tem permissão de execução
4. Executa o redeploy seguro

## 📝 Outros Comandos Úteis

### Verificar Status dos Serviços
```bash
docker stack services sistema-familiar
```

### Ver Logs do Backend
```bash
docker service logs -f sistema-familiar_backend
```

### Ver Logs do Frontend
```bash
docker service logs -f sistema-familiar_frontend
```

### Diagnosticar Rede
```bash
cd /opt/sistema-familiar
./diagnostico-rede.ps1  # ou .sh se disponível
```

### Verificar Redes Docker
```bash
docker network ls
docker network inspect db_network
```

### Remover Stack (se necessário)
```bash
docker stack rm sistema-familiar
```

### Deploy Manual
```bash
cd /opt/sistema-familiar
docker stack deploy -c docker-stack.yml sistema-familiar
```

## ⚠️ Importante

- Sempre use o comando de redeploy seguro para evitar downtime
- Verifique os logs após o deploy
- Teste a aplicação após o deploy
- Mantenha backup do banco de dados antes de grandes atualizações

## 🚨 ATENÇÃO - Versão 1.1

**A versão 1.1 requer migração do banco de dados ANTES do redeploy!**

Consulte o arquivo `MIGRACAO-V1.1.md` para instruções detalhadas de migração.

**Resumo rápido:**
1. Fazer backup do banco
2. Executar scripts de migração (ver MIGRACAO-V1.1.md)
3. Depois fazer o redeploy normalmente

