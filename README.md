# CS2 — Calendário único (HLTV IDs)
- Um único `cs2.ics` (root) com **próximos jogos** e **resultados** dos times (HLTV).
- `index.html` mostra exatamente o que está no `.ics`.
- `times.json` define times com **IDs do HLTV** (sem /search).
- `generate_calendars.py` usa `/matches?team=ID` e `/results?team=ID` com headers+retry.
- Action roda a cada 30min e commita só se houver mudança.

URLs depois de publicar:
- Página: https://SEU_USUARIO.github.io/cs2-calendario/
- ICS:    https://SEU_USUARIO.github.io/cs2-calendario/cs2.ics
