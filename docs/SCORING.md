# Sistema di Scoring

Documentazione delle formule e dei calcoli per il risk score cartellini.

## Panoramica

Il sistema calcola un **score 0-100** che rappresenta la probabilità relativa che un giocatore riceva un cartellino giallo in una specifica partita.

Score più alto = rischio maggiore.

## Metriche Base

### Livello Giocatore

| Metrica | Formula | Descrizione |
|---------|---------|-------------|
| **yellows_per_90** | `(gialli / minuti) × 90` | Cartellini ogni 90 minuti giocati |
| **fouls_per_90** | `(falli / minuti) × 90` | Falli commessi ogni 90 minuti |
| **foul_to_card_ratio** | `gialli / falli_commessi` | Percentuale falli che diventano cartellini |

### Livello Squadra

| Metrica | Formula | Descrizione |
|---------|---------|-------------|
| **team_fouls_per_match** | `SUM(falli) / COUNT(partite)` | Media falli commessi per partita |
| **team_yellows_per_match** | `SUM(gialli) / COUNT(partite)` | Media cartellini per partita |
| **foul_to_card_pct** | `(gialli / falli) × 100` | % falli squadra che diventano cartellini |

## Componenti dello Score

Il punteggio finale è composto da 4 componenti, ciascuno normalizzato su scala 0-100.

### 1. Score Stagionale

Basato sul tasso di cartellini del giocatore nella stagione corrente.

```
seasonal_score = min(yellows_per_90 × 100, 100)
```

**Esempio:**
- Giocatore con 0.45 yellows_per_90 → score 45
- Giocatore con 1.2 yellows_per_90 → score 100 (capped)

### 2. Score Arbitro

Basato sullo storico del giocatore con l'arbitro designato.

```
referee_score = (volte_ammonito / partite_con_arbitro) × 100
```

**Se nessuno storico:** score default = 25

**Esempio:**
- Ammonito 3 volte su 8 partite con Orsato → score 37.5

### 3. Score H2H (Head-to-Head)

Basato sui cartellini negli scontri diretti contro l'avversario.

```
h2h_score = (gialli_in_h2h / partite_h2h) × 100
```

**Ottimizzazione:** Query H2H eseguita solo per giocatori con seasonal_score > 25

**Esempio:**
- 4 gialli in 10 derby → score 40

### 4. Score Falli

Combinazione di propensione ai falli individuale e di squadra.

```
base_fouls = (team_foul_to_card_pct × 0.5) + (yellows_per_90_normalized × 0.5)

# Bonus posizione
if position in ['Midfield', 'Defence']:
    fouls_score = base_fouls × 1.20  # +20%
else:
    fouls_score = base_fouls

fouls_score = min(fouls_score, 100)  # cap a 100
```

**Razionale bonus posizione:**
- Centrocampisti e difensori commettono più falli tattici
- Attaccanti e portieri tendono a subire più falli che commetterli

## Formula Finale

### Con Arbitro Designato

Quando l'arbitro è noto, il suo storico ha peso significativo.

```
Score = (Stagionale × 0.35) + (Arbitro × 0.30) + (H2H × 0.15) + (Falli × 0.20)
```

| Componente | Peso | Razionale |
|------------|------|-----------|
| Stagionale | 35% | Forma attuale del giocatore |
| Arbitro | 30% | Rapporto specifico con arbitro |
| H2H | 15% | Storico contro avversario |
| Falli | 20% | Stile di gioco e contesto squadra |

### Senza Arbitro

Quando l'arbitro non è ancora designato, i pesi vengono ridistribuiti.

```
Score = (Stagionale × 0.45) + (H2H × 0.25) + (Falli × 0.30)
```

| Componente | Peso | Razionale |
|------------|------|-----------|
| Stagionale | 45% | Peso maggiore alla forma attuale |
| H2H | 25% | Più peso allo storico diretto |
| Falli | 30% | Più peso al contesto squadra |

## Esempi di Calcolo

### Esempio 1: Con Arbitro

**Giocatore:** Barella (Midfield)
**Partita:** Inter vs Milan
**Arbitro:** Orsato

| Componente | Valore | Peso | Contributo |
|------------|--------|------|------------|
| Stagionale | 45.0 | 35% | 15.75 |
| Arbitro | 37.5 | 30% | 11.25 |
| H2H | 40.0 | 15% | 6.00 |
| Falli | 42.0 | 20% | 8.40 |
| **Totale** | - | - | **41.40** |

### Esempio 2: Senza Arbitro

**Giocatore:** Barella (Midfield)
**Partita:** Inter vs Milan
**Arbitro:** Non designato

| Componente | Valore | Peso | Contributo |
|------------|--------|------|------------|
| Stagionale | 45.0 | 45% | 20.25 |
| H2H | 40.0 | 25% | 10.00 |
| Falli | 42.0 | 30% | 12.60 |
| **Totale** | - | - | **42.85** |

## Ottimizzazioni Performance

### Soglia H2H

Per evitare query costose su giocatori a basso rischio:

```python
if seasonal_score > 25:
    # Esegui query H2H
    h2h_score = get_h2h_score(player, opponent)
else:
    # Salta query H2H
    h2h_score = 0
```

### Cache Arbitro

Le statistiche arbitro vengono caricate una volta per analisi:

```python
referee_stats = get_referee_stats(referee_name)  # Una sola query
for player in players:
    player_referee_score = calculate_referee_score(player, referee_stats)
```

## Interpretazione Score

| Range | Interpretazione |
|-------|-----------------|
| 0-20 | Rischio basso |
| 21-40 | Rischio moderato |
| 41-60 | Rischio medio-alto |
| 61-80 | Rischio alto |
| 81-100 | Rischio molto alto |

## Moltiplicatori Contestuali (v2)

A partire dalla versione 2.0, lo score base viene moltiplicato per fattori contestuali che aumentano o diminuiscono il rischio in base al tipo di partita.

### Formula Finale v2

```
final_score = base_score × derby × home_away × referee_adj × possession
final_score = min(final_score, 100)  # cap a 100
```

### 1. Moltiplicatore Derby

Basato sulla tabella `rivalries` con intensità 1-3.

| Intensità | Moltiplicatore | Esempi |
|-----------|----------------|--------|
| 1 (minore) | ×1.10 (+10%) | Derby regionali |
| 2 (sentito) | ×1.18 (+18%) | Rivalità storiche |
| 3 (massimo) | ×1.26 (+26%) | Derby Madonnina, El Clásico |

```
derby_multiplier = 1.0 + (0.08 × intensity + 0.02)
```

**Fonte:** Ricerca accademica su comportamento giocatori in partite ad alta tensione.

### 2. Moltiplicatore Casa/Trasferta

Basato su studio CIES Football Observatory.

| Condizione | Moltiplicatore | Razionale |
|------------|----------------|-----------|
| Casa | ×0.94 (-6%) | Giocatori di casa meno ammoniti |
| Trasferta | ×1.06 (+6%) | Giocatori in trasferta più ammoniti |

**Fonte:** CIES Football Observatory - Home advantage analysis.

### 3. Moltiplicatore Arbitro (Outlier Detection)

Basato sulla vista `referee_league_comparison` che confronta ogni arbitro con la media della sua lega.

```
referee_adjustment = 1.0 + (ref_league_delta × 0.10)
referee_adjustment = max(0.85, min(1.15, referee_adjustment))
```

| Profilo | Delta | Moltiplicatore |
|---------|-------|----------------|
| STRICT_OUTLIER | > +1.0 | ×1.10-1.15 |
| ABOVE_AVERAGE | +0.5 a +1.0 | ×1.05-1.10 |
| AVERAGE | -0.5 a +0.5 | ×0.95-1.05 |
| BELOW_AVERAGE | -1.0 a -0.5 | ×0.90-0.95 |
| LENIENT_OUTLIER | < -1.0 | ×0.85-0.90 |

### 4. Moltiplicatore Possesso

Basato sulla vista `team_possession_stats`. Squadre con meno possesso tendono a commettere più falli.

```
possession_factor = 1 + (50 - avg_possession) × 0.01
possession_factor = max(0.85, min(1.15, possession_factor))
```

| Stile | Possesso | Moltiplicatore |
|-------|----------|----------------|
| POSSESSION_HEAVY | 55%+ | ×0.85-0.95 (↓ rischio) |
| BALANCED | 50-55% | ×0.95-1.00 |
| COUNTER_ATTACK | 45-50% | ×1.00-1.05 |
| DEFENSIVE | <45% | ×1.05-1.15 (↑ rischio) |

### Esempio Completo v2

**Partita:** Inter vs Milan (Derby della Madonnina)
**Arbitro:** Maresca (AVERAGE, delta -0.41)
**Possesso:** Inter 59% (×0.91), Milan 59% (×0.91)

**Giocatore:** Barella (Inter, casa)

| Componente | Valore |
|------------|--------|
| Base score | 41.40 |
| Derby (int.3) | ×1.26 |
| Casa | ×0.94 |
| Arbitro | ×0.96 |
| Possesso | ×0.91 |

```
Final = 41.40 × 1.26 × 0.94 × 0.96 × 0.91 = 42.8
```

## Limitazioni

- **Dati insufficienti:** Con poche partite, lo score può essere volatile
- **Nuovi giocatori:** Senza storico, solo score stagionale disponibile
- **Arbitri nuovi:** Default 25 se nessuno storico con giocatore
- **H2H limitato:** Solo partite presenti nel database (max 3 stagioni)
- **Rivalità mancanti:** Se una rivalità non è configurata, derby_multiplier = 1.0
- **Possesso non disponibile:** Se mancano dati possesso, possession_factor = 1.0
