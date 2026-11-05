# Correção: Nota Parcial por bimestre na tela Avaliações

Data: 05/11/2026  
Contexto: Gestão Familiar ↔ sync e-class (Guilherme `aluno_id` 16, Giovana `aluno_id` 17)

## Problema
A tela de Avaliações do e-class mostra Nota Parcial por disciplina em cada bimestre, mas o GF só persistia um par (`nota_parcial` + `bimestre_nota_parcial`) na linha do boletim — o último sync sobrescrevia e o filtro 1º/2º/3º “sumia” com a parcial.

## Solução implementada
1. Tabela `estudo_nota_parcial` — histórico por `(aluno, ano_letivo, bimestre, disciplina)`.
2. Sync: upsert da parcial do bimestre do payload; **não** apaga outros bimestres.
3. `GET /estudos/notas-parciais?aluno_id=&ano_letivo=&bimestre=` — leitura para a UI.
4. Front Avaliações: cartão usa `notas-parciais`, **não** o slot único do boletim.
5. Espelho do boletim: só atualiza se o bimestre do payload for ≥ ao já espelhado (protege B4 no backfill).

## Contrato
- Chave: `eclass-parcial-{aluno_id}-B{n}-{disciplina_slug}`
- Entrada: `disciplinas[].nota_parcial` em `POST /estudos/eclass/sincronizar`
- Não criar linha de boletim só por Arte A / Arte R / Cultura Geral

## Backfill
Reprocessar scrape completo Gui+Gi B1–B4 via sync. Validar:
- Guilherme 1º → Arte 5, Ciências 10, Ed. Física 5, Ens. Religioso 9
- Guilherme 4º → parciais B4 intactas
- Giovana 1º/2º → parciais do scrape
- Boletim Notas e Faltas (b1…b4) inalterado em comportamento
