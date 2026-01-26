# YellowOracle - Stato del Progetto

**Ultimo aggiornamento:** 2026-01-26
**Fase attuale:** Setup completato, in attesa di attivazione API

---

## Cosa è stato fatto

### 1. Design (completato)
- Documento di design: `docs/plans/2026-01-26-yelloworacle-design.md`
- Architettura definita: Claude + Supabase + football-data.org API

### 2. Ambiente tecnico (completato)
- Python virtual environment: `./venv`
- Librerie installate: supabase, pandas, streamlit, requests, beautifulsoup4, cloudscraper, python-dotenv
- File configurazione: `.env` (contiene credenziali)

### 3. Database Supabase (completato)
- URL: https://nxodgbawbgzzgqffihwv.supabase.co
- Schema v2 applicato con tutte le tabelle
- Tabelle: teams, players, referees, matches, match_events, lineups, match_statistics, player_season_stats
- Viste: player_card_risk, referee_stats, match_cards, head_to_head_cards

### 4. Script di sincronizzazione (completato)
- `scripts/sync_football_data.py` - pronto per l'uso

### 5. Repository GitHub (completato)
- URL: https://github.com/decker996/YellowOracle
- Nota: per il push serve reinserire il token GitHub

---

## Cosa manca da fare

### Prossimo passo: Attivare API football-data.org
L'utente deve:
1. Andare su https://www.football-data.org/
2. Attivare piano "Free + Deep Data" (€29/mese)
3. Attivare "Statistics Add-On" (€15/mese)

### Dopo l'attivazione API:
1. Eseguire sincronizzazione dati:
   ```bash
   cd ~/Scrivania/soccer
   ./venv/bin/python scripts/sync_football_data.py --all --full
   ```

2. Verificare dati su Supabase (Table Editor)

3. Configurare MCP per connessione Claude-Database

4. Creare dashboard Streamlit

5. Test del sistema completo

---

## Credenziali (in .env)

- SUPABASE_URL: configurato
- SUPABASE_KEY: configurato
- FOOTBALL_API_KEY: configurato (tier gratuito, da aggiornare con piano a pagamento)

---

## Come riprendere

Quando riapri Claude Code in questa cartella, di' semplicemente:

> "Continua il progetto YellowOracle - ho attivato l'API a pagamento"

oppure

> "Leggi STATO_PROGETTO.md e dimmi cosa fare"

Claude leggerà questo file e saprà esattamente da dove riprendere.
