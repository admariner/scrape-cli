# Agent-friendly CLI improvements

## Analisi dei principi applicabili

La CLI è già non-interattiva e stateless. I miglioramenti utili per gli agenti sono:

| Principio | Stato attuale | Azione |
|-----------|---------------|--------|
| Non-interattiva | ✅ OK | — |
| `--help` con esempi | ✅ OK (v1.2.3) | — |
| Errori su stderr | ✅ OK (v1.2.3) | — |
| Messaggio errore conciso su espressione mancante | ✅ OK (v1.2.3) | — |
| Stdin e pipeline | ✅ OK | — |
| Fail fast con errori azionabili | ✅ OK (v1.2.3) | — |
| Idempotente | ✅ OK (read-only) | — |

## Gap residui dopo v1.2.3

- [x] **1. `-eb` detection** — `sys.exit("Error string")` su riga 119 è inconsistente: usa `print(..., file=sys.stderr); sys.exit(1)` come il resto del codice
- [x] **2. `--check_existence` vs `--check-existence`** — l'help mostra `--check_existence` (underscore), non standard Unix. Unificato in `--check-existence` (kebab-case) come arg primario; rimosso il doppio alias
- [x] **3. Aggiornare LOG.md**

## Review (v1.2.3 completato)

- `scrape.py`: epilog con `RawDescriptionHelpFormatter` + 8 esempi; tutti gli errori su stderr; errore espressione mancante conciso con esempio
- `tests/test_scrape.py`: 3 test aggiornati da `result.stdout` a `result.stderr`
- 18/18 test passati

## Domande aperte

- Vuoi mantenere il vecchio comportamento di stampare l'help completo quando manca `-e`? (i.e., solo per umani)
- Preferisci che i messaggi di errore includano anche un esempio d'uso corretto (es. `scrape -e "//h1" file.html`)?
