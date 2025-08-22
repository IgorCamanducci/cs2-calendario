# CS2 — Calendário único (HLTV, 90 dias)
- `cs2.ics`: calendário único (próximos jogos + últimos resultados).
- `index.html`: exibe os eventos lendo o `cs2.ics`.
- `times.json`: edite os times; flexível.
- `generate_calendars.py`: busca HLTV (headers + retry) e gera ICS no root.
- `.github/workflows/update.yml`: roda a cada 30 min (commit automático).

URLs após publicar:
- Página: https://SEU_USUARIO.github.io/cs2-calendario/
- ICS:    https://SEU_USUARIO.github.io/cs2-calendario/cs2.ics
