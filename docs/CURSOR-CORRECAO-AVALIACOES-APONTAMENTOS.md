# Pipeline definido — Avaliações (e-class) + Apontamentos

Data: 2026-11-05 (America/Sao_Paulo)  
Projeto: este repo **local/dev** (Kleber vai gerar build pra testar em produção — manter estas regras no código).

## Fluxo oficial (confirmado pelo Kleber)

```
Varredura semanal (segunda) no e-class
  → seção Avaliações + Notas e Faltas (+ Apontamentos quando houver)
  → POST /api/v1/estudos/eclass/sincronizar  (e import de apontamentos)
  → alimenta Estudos → Avaliações e Estudos → Apontamentos
     e o GET /estudos/boletim
```

- **Provas** (`/estudos/provas`) = calendário do PDF de critérios. Continua separado.
- **Avaliações** (`/estudos/avaliacoes`) = dados reais do e-class via sync acima. **Não** é cópia/duplicata de Provas.
- A rotina do Professor já está alinhada a esse pipeline.

## Visibilidade por filho (obrigatório)

Alunos: Guilherme `aluno_id=16`, Giovana `aluno_id=17`.

| Área em Estudos | Quem vê o menu | O que cada um enxerga |
|---|---|---|
| **Atividades** | Os dois | Continua como hoje: ambos acessam (escopo já existente da família/lista). |
| **Comunicados** | Os dois | Idem — ambos acessam. |
| **Provas** | Os dois | Idem — ambos acessam o calendário (já filtrado por turma/aluno conforme regra atual do calendário). |
| **Avaliações** | Os dois (menu visível) | **Só a própria.** Guilherme não vê avaliações/boletim da Giovana e vice-versa. Filtrar sempre por `aluno_id` do usuário logado quando `is_child`. Pais/admin podem ver/filtrar os dois. |
| **Apontamentos** | Os dois (menu visível) | **Só o próprio.** Mesma regra: filho autenticado → apenas `aluno_id` dele. Nada do irmão. |

### API / backend
- `GET /estudos/avaliacoes`, `GET /estudos/boletim`, `GET /estudos/apontamentos` (e detalhe): se o usuário for filho, **forçar** `aluno_id` = id dele; ignorar/negar pedido de outro `aluno_id`.
- Sync/import (`POST /estudos/eclass/sincronizar`, `POST /estudos/apontamentos/importar`): continua podendo gravar para 16 e 17 (integração/pais); a restrição é na **leitura** da UI e nos GETs quando o ator é o filho.
- Nunca devolver no JSON linhas do outro filho para um usuário criança.

### Frontend
- Em Avaliações e Apontamentos: se `currentUser.is_child`, ocultar seletor de irmão / travar no próprio id; listas e boletim só desse id.
- Atividades, Comunicados e Provas: **não** aplicar essa trava extra além do que já existe hoje.

## O que o código deve refletir

### Avaliações
- Fonte: `GET /estudos/avaliacoes` priorizando `fonte=eclass` / `tipo_codigo_eclass` + `GET /estudos/boletim`.
- UI: TIPO (TB1/AV1/…), DATA, ATIVIDADE, ALCANÇADO (`nota_alcancada`), VALOR, professor, Nota Parcial.
- Vazio: “aparecem após a varredura semanal / sync e-class” — não após importar PDF.

### Apontamentos
- Menu Estudos → **Apontamentos** (`/estudos/apontamentos`) ao lado de Avaliações.
- API: `POST /estudos/apontamentos/importar` (+ dry_run) e `GET /estudos/apontamentos` (filtros aluno/ano/tipo), com a regra de visibilidade acima.
- Spec: seguir o MD de apontamentos do Professor quando disponível.

### Não fazer
- Não reusar layout/fluxo de Provas como solução da aba Avaliações.
- Não deixar um filho ler avaliação ou apontamento do outro.

## Boletim (Notas e Faltas) — anti-órfãs (05/11/2026)

### Causa das órfãs
O sync criava linha de boletim a partir do nome do cartão de **Avaliações** (`disciplinas[].nota_parcial`). No e-class, Avaliações tem “Arte A”/“Arte R”; Notas e Faltas tem só **Arte**. Cultura Geral entrou como ruído vazio.

### Regras
1. `DELETE /api/v1/estudos/boletim/linhas/{linha_id}` — apaga **só a linha** (204). Auth JWT/`X-API-Token`. 404 se não existir. Não apaga o documento do boletim.
2. Linhas de boletim **só** a partir de `boletim.linhas`. Cartões Arte A/R continuam em Avaliações (`fonte=eclass`) e **não** viram linha.
3. `boletim.substituir_linhas: true` no sync: o conjunto enviado **substitui** as linhas do aluno/ano (remove órfãs ausentes no payload). Default (ausente/false) = upsert sem apagar.
4. UI Notas e Faltas: nota + faltas por bimestre (colunas separadas), espelho do e-class.

### Limpeza pontual pós-deploy (produção)
```bash
# Giovana
DELETE /api/v1/estudos/boletim/linhas/21   # Arte A
DELETE /api/v1/estudos/boletim/linhas/22   # Arte R
DELETE /api/v1/estudos/boletim/linhas/13   # Cultura Geral
# Guilherme
DELETE /api/v1/estudos/boletim/linhas/10   # Cultura Geral
```
Não mexer nas avaliações e-class Arte A/R.
