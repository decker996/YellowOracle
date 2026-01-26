# Database Schema

Schema completo del database PostgreSQL su Supabase.

## Diagramma Relazioni

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ competitions│     │   teams     │     │  referees   │
└──────┬──────┘     └──────┬──────┘     └──────┬──────┘
       │                   │                   │
       │    ┌──────────────┼───────────────────┤
       │    │              │                   │
       ▼    ▼              ▼                   ▼
┌─────────────────────────────────────────────────────┐
│                      matches                         │
└───────────────────────┬─────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
        ▼               ▼               ▼
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│   lineups   │  │match_events │  │match_stats  │
└──────┬──────┘  └──────┬──────┘  └─────────────┘
       │                │
       │                │
       ▼                ▼
┌─────────────────────────────────────────────────────┐
│                      players                         │
└─────────────────────────────────────────────────────┘
```

## Tabelle Principali

### competitions
Metadati delle competizioni calcistiche.

| Colonna | Tipo | Null | Descrizione |
|---------|------|------|-------------|
| id | UUID | NO | Primary key |
| external_id | INTEGER | NO | ID football-data.org |
| code | TEXT | NO | Codice (SA, PL, PD, BL1, FL1, CL, EL) |
| name | TEXT | NO | Nome completo |
| area_name | TEXT | YES | Paese/Area geografica |
| area_code | TEXT | YES | Codice area |
| emblem_url | TEXT | YES | URL logo competizione |
| created_at | TIMESTAMP | NO | Data creazione |
| updated_at | TIMESTAMP | NO | Data aggiornamento |

### teams
Club calcistici.

| Colonna | Tipo | Null | Descrizione |
|---------|------|------|-------------|
| id | UUID | NO | Primary key |
| external_id | INTEGER | NO | ID football-data.org |
| name | TEXT | NO | Nome completo |
| short_name | TEXT | YES | Nome abbreviato |
| tla | TEXT | YES | Sigla 3 lettere (es. JUV, MIL) |
| crest_url | TEXT | YES | URL stemma |
| stadium | TEXT | YES | Nome stadio |
| created_at | TIMESTAMP | NO | Data creazione |
| updated_at | TIMESTAMP | NO | Data aggiornamento |

### players
Giocatori con informazioni anagrafiche.

| Colonna | Tipo | Null | Descrizione |
|---------|------|------|-------------|
| id | UUID | NO | Primary key |
| external_id | INTEGER | NO | ID football-data.org |
| name | TEXT | NO | Nome completo |
| first_name | TEXT | YES | Nome |
| last_name | TEXT | YES | Cognome |
| date_of_birth | DATE | YES | Data di nascita |
| nationality | TEXT | YES | Nazionalità |
| position | TEXT | YES | Goalkeeper/Defence/Midfield/Offence |
| shirt_number | INTEGER | YES | Numero maglia |
| current_team_id | UUID | YES | FK → teams |
| created_at | TIMESTAMP | NO | Data creazione |
| updated_at | TIMESTAMP | NO | Data aggiornamento |

### referees
Arbitri con statistiche aggregate.

| Colonna | Tipo | Null | Descrizione |
|---------|------|------|-------------|
| id | UUID | NO | Primary key |
| external_id | INTEGER | NO | ID football-data.org |
| name | TEXT | NO | Nome completo |
| nationality | TEXT | YES | Nazionalità |
| total_matches | INTEGER | YES | Partite totali dirette |
| total_yellows | INTEGER | YES | Gialli totali estratti |
| total_reds | INTEGER | YES | Rossi totali estratti |
| avg_yellows_per_match | DECIMAL | YES | Media gialli/partita |
| avg_fouls_per_match | DECIMAL | YES | Media falli/partita |
| created_at | TIMESTAMP | NO | Data creazione |
| updated_at | TIMESTAMP | NO | Data aggiornamento |

### matches
Partite con risultati e metadati.

| Colonna | Tipo | Null | Descrizione |
|---------|------|------|-------------|
| id | UUID | NO | Primary key |
| external_id | INTEGER | NO | ID football-data.org |
| competition_id | UUID | NO | FK → competitions |
| season | TEXT | NO | Stagione (es. 2025-2026) |
| matchday | INTEGER | YES | Giornata |
| match_date | TIMESTAMP | NO | Data e ora partita |
| status | TEXT | NO | SCHEDULED/LIVE/FINISHED/POSTPONED |
| home_team_id | UUID | NO | FK → teams |
| away_team_id | UUID | NO | FK → teams |
| home_score | INTEGER | YES | Gol casa (finale) |
| away_score | INTEGER | YES | Gol trasferta (finale) |
| home_score_ht | INTEGER | YES | Gol casa (primo tempo) |
| away_score_ht | INTEGER | YES | Gol trasferta (primo tempo) |
| referee_id | UUID | YES | FK → referees |
| var_referee_id | UUID | YES | FK → referees (VAR) |
| is_derby | BOOLEAN | YES | Flag derby |
| home_position | INTEGER | YES | Posizione classifica casa |
| away_position | INTEGER | YES | Posizione classifica trasferta |
| created_at | TIMESTAMP | NO | Data creazione |
| updated_at | TIMESTAMP | NO | Data aggiornamento |

### match_events
Eventi singoli durante le partite.

| Colonna | Tipo | Null | Descrizione |
|---------|------|------|-------------|
| id | UUID | NO | Primary key |
| match_id | UUID | NO | FK → matches |
| team_id | UUID | YES | FK → teams |
| player_id | UUID | YES | FK → players |
| event_type | TEXT | NO | Tipo evento (vedi sotto) |
| minute | INTEGER | YES | Minuto evento |
| extra_time_minute | INTEGER | YES | Minuto recupero |
| detail | TEXT | YES | Dettagli aggiuntivi |
| player_in_id | UUID | YES | FK → players (per sostituzioni) |
| created_at | TIMESTAMP | NO | Data creazione |

**Valori event_type:**
- `YELLOW_CARD` - Cartellino giallo
- `RED_CARD` - Cartellino rosso
- `GOAL` - Gol
- `OWN_GOAL` - Autogol
- `PENALTY` - Rigore
- `SUBSTITUTION` - Sostituzione

### lineups
Formazioni e partecipazione giocatori.

| Colonna | Tipo | Null | Descrizione |
|---------|------|------|-------------|
| id | UUID | NO | Primary key |
| match_id | UUID | NO | FK → matches |
| team_id | UUID | NO | FK → teams |
| player_id | UUID | NO | FK → players |
| is_starter | BOOLEAN | NO | Titolare |
| is_substitute | BOOLEAN | NO | In panchina |
| shirt_number | INTEGER | YES | Numero maglia |
| position | TEXT | YES | Posizione in campo |
| minutes_played | INTEGER | YES | Minuti giocati |
| subbed_in_minute | INTEGER | YES | Minuto entrata |
| subbed_out_minute | INTEGER | YES | Minuto uscita |
| created_at | TIMESTAMP | NO | Data creazione |

### match_statistics
Statistiche partita (Statistics Add-On).

| Colonna | Tipo | Null | Descrizione |
|---------|------|------|-------------|
| id | UUID | NO | Primary key |
| match_id | UUID | NO | FK → matches |
| team_id | UUID | NO | FK → teams |
| ball_possession | INTEGER | YES | Possesso palla % |
| shots_total | INTEGER | YES | Tiri totali |
| shots_on_goal | INTEGER | YES | Tiri in porta |
| shots_off_goal | INTEGER | YES | Tiri fuori |
| corners | INTEGER | YES | Calci d'angolo |
| free_kicks | INTEGER | YES | Calci di punizione |
| saves | INTEGER | YES | Parate |
| offsides | INTEGER | YES | Fuorigioco |
| fouls_committed | INTEGER | YES | Falli commessi |
| fouls_suffered | INTEGER | YES | Falli subiti |
| yellow_cards | INTEGER | YES | Cartellini gialli |
| red_cards | INTEGER | YES | Cartellini rossi |
| created_at | TIMESTAMP | NO | Data creazione |

### player_season_stats
Statistiche aggregate per giocatore/stagione.

| Colonna | Tipo | Null | Descrizione |
|---------|------|------|-------------|
| id | UUID | NO | Primary key |
| player_id | UUID | NO | FK → players |
| team_id | UUID | NO | FK → teams |
| season | TEXT | NO | Stagione |
| matches_played | INTEGER | YES | Partite giocate |
| matches_started | INTEGER | YES | Partite da titolare |
| minutes_played | INTEGER | YES | Minuti totali |
| goals | INTEGER | YES | Gol segnati |
| assists | INTEGER | YES | Assist |
| yellow_cards | INTEGER | YES | Cartellini gialli |
| red_cards | INTEGER | YES | Cartellini rossi |
| fouls_committed | INTEGER | YES | Falli commessi |
| fouls_suffered | INTEGER | YES | Falli subiti |
| yellows_per_90 | DECIMAL | GENERATED | Gialli per 90 minuti |
| fouls_per_90 | DECIMAL | GENERATED | Falli per 90 minuti |
| foul_to_card_ratio | DECIMAL | GENERATED | Rapporto falli/cartellini |

## Views Analitiche

### player_season_cards
Statistiche cartellini per giocatore, stagione e competizione.

```sql
SELECT
  player_name, team_name, competition_code, season,
  matches_played, yellow_cards, red_cards,
  minutes_played, yellows_per_90
FROM player_season_cards
WHERE player_name ILIKE '%barella%';
```

### player_season_cards_total
Statistiche aggregate (tutte le competizioni insieme).

```sql
SELECT
  player_name, team_name, season,
  total_matches, total_yellows, total_reds,
  total_minutes, yellows_per_90,
  competitions  -- array di competizioni
FROM player_season_cards_total;
```

### referee_player_history
Storico ammonizioni arbitro-giocatore.

```sql
SELECT
  referee_name, player_name, team_name,
  times_booked, matches_with_referee,
  booking_percentage, booking_details  -- JSON array
FROM referee_player_history
WHERE referee_name = 'Orsato';
```

### head_to_head_player_cards
Cartellini negli scontri diretti.

```sql
SELECT
  player_name, team1, team2,
  total_h2h_matches, total_yellows, total_reds,
  card_percentage, match_details  -- JSON array
FROM head_to_head_player_cards;
```

### team_fouls_stats
Statistiche falli a livello squadra.

```sql
SELECT
  team_name, season,
  total_matches, total_fouls_committed,
  avg_fouls_per_match, total_yellows,
  foul_to_card_pct
FROM team_fouls_stats;
```

## Funzioni RPC

### get_player_season_stats(player_name, season?, competition?)
Restituisce statistiche giocatore per competizione.

```sql
SELECT * FROM get_player_season_stats('Barella', '2025-2026', 'SA');
```

### get_player_season_stats_total(player_name, season?)
Restituisce statistiche aggregate tutte competizioni.

```sql
SELECT * FROM get_player_season_stats_total('Barella', '2025-2026');
```

### get_referee_player_cards(referee_name, team1_name, team2_name)
Restituisce storico ammonizioni arbitro vs giocatori di due squadre.

```sql
SELECT * FROM get_referee_player_cards('Orsato', 'Inter', 'Milan');
```

### get_head_to_head_cards(player_name, team1_name, team2_name)
Restituisce cartellini giocatore negli scontri diretti.

```sql
SELECT * FROM get_head_to_head_cards('Barella', 'Inter', 'Milan');
```

### get_team_fouls_stats(team_name?, season?)
Restituisce statistiche falli squadra.

```sql
SELECT * FROM get_team_fouls_stats('Inter', '2025-2026');
```

## Indici

```sql
-- Matches
CREATE INDEX idx_matches_season ON matches(season);
CREATE INDEX idx_matches_date ON matches(match_date);
CREATE INDEX idx_matches_status ON matches(status);
CREATE INDEX idx_matches_home_team ON matches(home_team_id);
CREATE INDEX idx_matches_away_team ON matches(away_team_id);
CREATE INDEX idx_matches_referee ON matches(referee_id);
CREATE INDEX idx_matches_competition ON matches(competition_id);

-- Events
CREATE INDEX idx_match_events_match ON match_events(match_id);
CREATE INDEX idx_match_events_player ON match_events(player_id);
CREATE INDEX idx_match_events_type ON match_events(event_type);

-- Lineups
CREATE INDEX idx_lineups_match ON lineups(match_id);
CREATE INDEX idx_lineups_player ON lineups(player_id);

-- Statistics
CREATE INDEX idx_match_stats_match ON match_statistics(match_id);

-- Player stats
CREATE INDEX idx_player_stats_player ON player_season_stats(player_id);
CREATE INDEX idx_player_stats_season ON player_season_stats(season);
```

## File SQL

| File | Contenuto |
|------|-----------|
| `database/schema_v2.sql` | Definizione tabelle (21.5 KB) |
| `database/analysis_views.sql` | Views e RPC functions (21.5 KB) |
