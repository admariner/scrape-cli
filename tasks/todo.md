# Agent-friendly CLI improvements

## Analisi dei principi applicabili

La CLI è già non-interattiva e stateless. I miglioramenti utili per gli agenti sono:

| Principio | Stato attuale | Azione |
|-----------|---------------|--------|
| Non-interattiva | ✅ OK | — |
| `--help` con esempi | ⚠️ Solo 1 esempio | Migliorare |
| Errori su stderr | ⚠️ Alcuni su stdout | Correggere |
| Messaggio errore mancante espressione | ⚠️ Stampa tutto `--help` | Rendere conciso |
| Stdin e pipeline | ✅ OK | — |
| Fail fast con errori azionabili | ⚠️ Parziale | Migliorare messaggi |
| Idempotente | ✅ OK (read-only) | — |

## Todo

- [x] **1. --help con esempi** — aggiungere epilog multi-riga con esempi per ogni caso d'uso principale (XPath, CSS, testo, attributi, URL, stdin, check-existence)
- [x] **2. Errori su stderr** — spostare tutti i `print("Error: ...")` su `sys.stderr`; aggiornare i test che controllano `result.stdout` → `result.stderr`
- [x] **3. Messaggio errore conciso su espressione mancante** — rimuovere `parser.print_help()` e sostituire con messaggio breve + esempio azionabile
- [x] **4. Aggiornare LOG.md**

## Review

- `scrape.py`: epilog con `RawDescriptionHelpFormatter` + 8 esempi; tutti gli errori su stderr; errore espressione mancante conciso con esempio
- `tests/test_scrape.py`: 3 test aggiornati da `result.stdout` a `result.stderr`
- 18/18 test passati

## Domande aperte

- Vuoi mantenere il vecchio comportamento di stampare l'help completo quando manca `-e`? (i.e., solo per umani)
- Preferisci che i messaggi di errore includano anche un esempio d'uso corretto (es. `scrape -e "//h1" file.html`)?
