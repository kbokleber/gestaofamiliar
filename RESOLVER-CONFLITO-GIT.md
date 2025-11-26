# Resolver Conflito Git em Produção

## Problema
O Git está impedindo o pull porque há mudanças locais no arquivo `migrar-v1.1.sh`.

## Solução Rápida (Descartar mudanças locais)

Se as mudanças locais não são importantes, descarte-as e use a versão do repositório:

```bash
cd /opt/sistema-familiar
git checkout -- migrar-v1.1.sh
git pull origin master
```

## Solução Alternativa (Salvar mudanças locais)

Se quiser manter as mudanças locais temporariamente:

```bash
cd /opt/sistema-familiar
git stash
git pull origin master
# Se precisar das mudanças depois: git stash pop
```

## Depois de resolver

Execute o script de migração:

```bash
chmod +x migrar-v1.1.sh
./migrar-v1.1.sh
```

