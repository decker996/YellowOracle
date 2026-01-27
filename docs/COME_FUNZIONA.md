# Come Funziona YellowOracle

> Guida completa al sistema di analisi rischio cartellini gialli

---

## Panoramica

YellowOracle è un sistema di analisi predittiva che calcola la probabilità che un giocatore riceva un cartellino giallo in una specifica partita. Non si limita a guardare le statistiche stagionali: combina **8 fattori distinti** per produrre uno score personalizzato per ogni giocatore, in ogni partita, considerando il contesto specifico dell'incontro.

L'obiettivo è identificare i giocatori con il **miglior rapporto rischio/opportunità** per il betting sui cartellini, andando oltre le semplici medie che i bookmaker già incorporano nelle quote.

---

## I Tre Pilastri dell'Analisi

### 1. Dati Storici (Database)

Il sistema interroga un database con:
- **Statistiche stagionali** di ogni giocatore (cartellini, minuti, falli)
- **Storico arbitro-giocatore** (come si comporta un arbitro con specifici giocatori)
- **Scontri diretti** (cartellini nelle partite tra le due squadre)
- **Statistiche di squadra** (possesso, falli medi, stile di gioco)

### 2. Contesto Web (Ricerca Real-Time)

Prima di ogni analisi, il sistema cerca automaticamente:
- **Formazioni probabili** (chi gioca titolare?)
- **Arbitro designato** (fondamentale per il calcolo)
- **Assenze** (infortunati, squalificati)
- **Contesto partita** (classifica, posta in gioco, rivalità)

### 3. Moltiplicatori Contestuali (8 Fattori)

Lo score finale viene modulato da 8 fattori che amplificano o riducono il rischio base.

---

## I Fattori di Rischio: Spiegazione Dettagliata

### Fattore 1: Score Stagionale (Peso: 35%)

**Cosa misura:** La propensione storica del giocatore a ricevere cartellini nella stagione corrente.

**Come si calcola:**
```
yellows_per_90 = (cartellini_gialli / minuti_giocati) × 90
```

**Esempio:**
- Barella: 8 gialli in 2.100 minuti → 0.34 gialli/90min
- Bastoni: 3 gialli in 2.400 minuti → 0.11 gialli/90min

Barella ha uno score stagionale 3 volte superiore a Bastoni.

**Perché è importante:** È la base statistica. Un giocatore che prende molti cartellini continuerà probabilmente a prenderli. Ma da solo non basta: i bookmaker già lo sanno.

---

### Fattore 2: Storico Arbitro (Peso: 30%)

**Cosa misura:** Come uno specifico arbitro si comporta con uno specifico giocatore.

**Come si calcola:**
```
booking_percentage = (volte_ammonito / partite_con_arbitro) × 100
```

**Esempio:**
- Barella con Mariani: ammonito 4 volte su 6 partite → 66%
- Barella con Doveri: ammonito 1 volta su 8 partite → 12.5%

Con Mariani, Barella ha un rischio **5 volte superiore** rispetto a Doveri.

**Perché è importante:** Gli arbitri hanno stili diversi e "rapporti" diversi con certi giocatori. Alcuni arbitri tollerano il gioco duro, altri no. Alcuni ammoniscono sempre i soliti noti.

---

### Fattore 3: Scontri Diretti H2H (Peso: 15%)

**Cosa misura:** Se un giocatore tende a prendere cartellini contro una specifica squadra.

**Come si calcola:**
```
h2h_card_rate = cartellini_negli_scontri_diretti / partite_h2h
```

**Esempio:**
- Theo Hernandez vs Inter: 3 gialli in 5 partite → 60%
- Theo Hernandez vs Empoli: 0 gialli in 4 partite → 0%

Contro l'Inter, Theo ha uno storico di nervosismo/intensità molto più alto.

**Perché è importante:** Alcune partite "accendono" certi giocatori. Derby, rivalità personali, marcature specifiche.

---

### Fattore 4: Falli di Squadra (Peso: 20%)

**Cosa misura:** Quanto la squadra nel suo complesso commette falli.

**Come si calcola:**
```
team_foul_rate = falli_medi_partita / media_campionato
```

**Esempio:**
- Atalanta: 14.2 falli/partita (pressing aggressivo)
- Napoli: 10.8 falli/partita (possesso palla)

I giocatori dell'Atalanta partono con un rischio base più alto perché il loro stile di gioco genera più falli.

**Perché è importante:** Lo stile di gioco della squadra influenza tutti i giocatori. Una squadra che pressa alto commette più falli tattici.

---

### Fattore 5: Derby/Rivalità (Moltiplicatore: +10% a +26%)

**Cosa misura:** Se la partita è un derby o una rivalità storica.

**Livelli di intensità:**
| Livello | Moltiplicatore | Esempi |
|---------|----------------|--------|
| 1 - Normale | ×1.10 (+10%) | Rivalità regionali minori |
| 2 - Sentito | ×1.18 (+18%) | Napoli-Juventus, Roma-Napoli |
| 3 - Storico | ×1.26 (+26%) | Derby della Madonnina, El Clásico, Derby della Capitale |

**Esempio:**
- Score base Barella: 45
- Inter-Milan (intensità 3): 45 × 1.26 = **56.7**

**Perché è importante:** I derby generano tensione, contrasti più duri, arbitri più severi. La ricerca mostra +20-30% di cartellini nei derby rispetto a partite normali.

---

### Fattore 6: Casa/Trasferta (Moltiplicatore: ±6%)

**Cosa misura:** Se il giocatore gioca in casa o in trasferta.

**Valori:**
- Casa: ×0.94 (-6% rischio)
- Trasferta: ×1.06 (+6% rischio)

**Fonte:** Studio CIES su 101.491 partite: il 53% dei cartellini va alla squadra in trasferta.

**Esempio:**
- Barella a San Siro (casa): score × 0.94
- Barella al Maradona (trasferta): score × 1.06

**Perché è importante:** La squadra ospite subisce più pressione psicologica, arbitrale e del pubblico.

---

### Fattore 7: Baseline di Lega (Moltiplicatore: ±30%)

**Cosa misura:** La severità media della competizione.

**Valori per lega:**
| Lega | Fattore | Gialli/Partita |
|------|---------|----------------|
| La Liga | ×1.30 | 5.33 |
| Premier League | ×1.18 | 4.85 |
| Serie A | ×1.00 (baseline) | 4.10 |
| Bundesliga | ×0.95 | 3.90 |
| Ligue 1 | ×0.89 | 3.65 |

**Esempio:**
Un giocatore con stesso comportamento:
- In La Liga: score × 1.30
- In Serie A: score × 1.00
- In Bundesliga: score × 0.95

**Perché è importante:** La Liga estrae il 30% di cartellini in più della Serie A. È una differenza culturale e regolamentare.

---

### Fattore 8: Arbitro Outlier (Moltiplicatore: ±15%)

**Cosa misura:** Se l'arbitro designato è statisticamente più severo o più permissivo della media.

**Classificazione:**
| Profilo | Delta vs Media | Moltiplicatore |
|---------|----------------|----------------|
| STRICT_OUTLIER | > +1.0 gialli/partita | ×1.15 |
| ABOVE_AVERAGE | +0.5 a +1.0 | ×1.05 |
| AVERAGE | -0.5 a +0.5 | ×1.00 |
| BELOW_AVERAGE | -1.0 a -0.5 | ×0.95 |
| LENIENT_OUTLIER | < -1.0 gialli/partita | ×0.85 |

**Esempio:**
- Maresca: media 5.2 gialli/partita vs media Serie A 4.1 → delta +1.1 → STRICT_OUTLIER → ×1.15
- Fabbri: media 3.5 gialli/partita vs media Serie A 4.1 → delta -0.6 → BELOW_AVERAGE → ×0.95

**Perché è importante:** Circa il 23% degli arbitri sono outlier statistici. Identificarli dà un vantaggio predittivo.

---

### Fattore 9: Matchup Posizionale (Moltiplicatore: +5% a +15%)

**Cosa misura:** Se un giocatore affronta avversari che "attirano falli".

**Logica:** I terzini che marcano ali veloci (Vinicius, Leao, Kvaratskhelia) commettono più falli tattici per fermare le ripartenze.

**Foul Drawers noti:**
| Giocatore | Bonus Avversario |
|-----------|------------------|
| Vinicius Jr | +15% |
| Rafael Leao | +12% |
| Kvaratskhelia | +12% |
| Saka | +10% |
| Doku | +10% |
| Yamal | +8% |

**Esempio:**
- Theo Hernandez vs Udinese: matchup × 1.00
- Theo Hernandez vs Napoli (marca Kvara): matchup × 1.12

**Perché è importante:** Lo "Stopping Promising Attack" (SPA) è una delle cause principali di cartellini gialli. I difensori che affrontano dribblatori veloci sono costretti a fare falli tattici.

---

### Fattore 10: Differenziale Possesso (Moltiplicatore: ±15%)

**Cosa misura:** Se la squadra ha storicamente alto o basso possesso palla.

**Logica:** Chi ha meno possesso deve rincorrere il pallone → commette più falli.

**Formula:**
```
possession_factor = 1 + (50 - possesso_medio) × 0.01
```

**Esempio:**
| Squadra | Possesso Medio | Fattore |
|---------|----------------|---------|
| Napoli | 58% | ×0.92 (-8%) |
| Inter | 55% | ×0.95 (-5%) |
| Atalanta | 48% | ×1.02 (+2%) |
| Verona | 42% | ×1.08 (+8%) |

**Perché è importante:** Le squadre che giocano in contropiede o con possesso basso sono strutturalmente esposte a più falli.

---

## La Formula Completa

```
Score_Finale = Score_Base × Casa/Trasferta × Derby × Lega × Arbitro_Outlier × Matchup × Possesso

Dove:
Score_Base = (Stagionale × 35%) + (Arbitro × 30% × Ref_Adj) + (H2H × 15%) + (Falli_Squadra × 20%)
```

Lo score finale è cappato a 100.

---

## Flusso di Analisi: Passo per Passo

Quando l'utente chiede "Analizza Roma vs Lazio":

```
FASE 0: RICERCA AUTOMATICA
├── WebSearch: "Roma Lazio formazioni probabili [data]"
├── WebSearch: "Roma Lazio arbitro designato Serie A"
├── WebSearch: "Roma Lazio assenze infortunati"
└── WebSearch: "classifica Serie A 2025-2026"

FASE 1: QUERY DATABASE
├── get_team_players("Roma") → lista giocatori con stats
├── get_team_players("Lazio") → lista giocatori con stats
├── is_derby_match(Roma, Lazio) → Derby della Capitale, intensità 3
├── get_referee_profile("Arbitro") → profilo e delta
├── get_possession_factor("Roma", "Lazio") → fattori possesso
└── Per ogni giocatore:
    ├── get_player_season_stats() → yellows_per_90
    ├── get_referee_player_cards() → storico con arbitro
    └── get_head_to_head_cards() → storico H2H

FASE 2: CALCOLO SCORE
├── Per ogni giocatore:
│   ├── Score_Base = weighted average dei 4 componenti
│   ├── Applica moltiplicatore casa/trasferta
│   ├── Applica moltiplicatore derby (×1.26)
│   ├── Applica moltiplicatore lega (×1.00 Serie A)
│   ├── Applica moltiplicatore arbitro outlier
│   ├── Applica moltiplicatore matchup
│   ├── Applica moltiplicatore possesso
│   └── Cap a 100
└── Ordina per score decrescente

FASE 3: OUTPUT
├── Top 5 giocatori a rischio per squadra
├── Analisi discorsiva del contesto
├── Breakdown score per ogni giocatore
└── Note su assenze e fonti
```

---

## Casi Studio

### Caso 1: Derby della Madonnina (Inter vs Milan)

**Richiesta utente:** "Analizza Inter-Milan di domenica"

**Contesto identificato:**
- Tipo partita: **Derby storico** (intensità 3)
- Arbitro: Mariani
- Classifica: Inter 1°, Milan 4° (alta posta in gioco)
- Formazioni: confermate da Sky Sport

**Fattori applicati:**
| Fattore | Valore |
|---------|--------|
| Derby | ×1.26 |
| Casa Inter | ×0.94 |
| Trasferta Milan | ×1.06 |
| Lega Serie A | ×1.00 |
| Mariani (avg) | ×1.00 |
| Possesso Inter 55% | ×0.95 |
| Possesso Milan 52% | ×0.98 |

**Analisi tipo:**

> "Il Derby della Madonnina è sempre una partita ad alta tensione. Il moltiplicatore derby ×1.26 amplifica tutti gli score.
>
> **Barella** emerge come candidato principale: il suo ruolo di schermo davanti alla difesa lo porta a interrompere le ripartenze milaniste. Con Mariani ha uno storico del 45% di ammonizioni. Score: **67.2**
>
> Per il Milan, **Theo Hernandez** è il giocatore più a rischio. Nei derby ha sempre mostrato nervosismo, e dovrà contenere Dumfries sulle ripartenze. Storico H2H: 3 gialli in 5 derby. Score: **71.8** (trasferta + storico H2H elevato)
>
> **Calabria** è un outsider interessante: marca Thuram, giocatore fisico. Nei derby ha 2 gialli in 4 partite."

**Top 5 Output:**

| # | Giocatore | Squadra | Score | Breakdown |
|---|-----------|---------|-------|-----------|
| 1 | Theo Hernandez | Milan | 71.8 | Stag: 28 + Arb: 18 + H2H: 15 + Falli: 10 × 1.26 × 1.06 |
| 2 | Barella | Inter | 67.2 | Stag: 32 + Arb: 14 + H2H: 8 + Falli: 12 × 1.26 × 0.94 |
| 3 | Calabria | Milan | 58.4 | ... |
| 4 | Mkhitaryan | Inter | 52.1 | ... |
| 5 | Reijnders | Milan | 49.7 | ... |

---

### Caso 2: Partita Salvezza (Como vs Udinese)

**Richiesta utente:** "Analizza Como-Udinese di sabato"

**Contesto identificato:**
- Tipo partita: **Scontro salvezza diretto**
- Arbitro: Fabbri (BELOW_AVERAGE, delta -0.6)
- Classifica: Como 16°, Udinese 17° (entrambe a rischio)
- Formazioni: probabili da Gazzetta

**Fattori applicati:**
| Fattore | Valore |
|---------|--------|
| Derby | ×1.00 (nessuno) |
| Casa Como | ×0.94 |
| Trasferta Udinese | ×1.06 |
| Lega Serie A | ×1.00 |
| Fabbri (permissivo) | ×0.95 |
| Possesso Como 46% | ×1.04 |
| Possesso Udinese 44% | ×1.06 |

**Analisi tipo:**

> "Partita da tripla con enorme pressione per entrambe. Anche senza il moltiplicatore derby, l'intensità sarà alta per la posta in gioco.
>
> **Fabbri** è un arbitro relativamente permissivo (3.5 gialli/partita vs media 4.1), il che abbassa leggermente tutti gli score del 5%.
>
> Entrambe le squadre hanno basso possesso palla (46% e 44%), il che significa partita spezzettata con molti falli tattici.
>
> **Lovric** dell'Udinese è il candidato principale: centrocampista di rottura, 6 gialli stagionali, trasferta + basso possesso squadra. Score: **54.2**
>
> Per il Como, **Braunöder** ha il ruolo più esposto: mediano davanti alla difesa, 4 gialli in 18 partite. Score: **48.7**"

**Note importanti:**
> La combinazione "arbitro permissivo" + "nessun derby" abbassa gli score rispetto a partite di cartello. Per questo tipo di match, i giocatori con score >50 sono comunque significativi.

---

### Caso 3: Partita Equilibrata (Udinese vs Verona)

**Richiesta utente:** "Analizza Udinese-Verona"

**Contesto identificato:**
- Tipo partita: **Partita di metà classifica**
- Arbitro: Colombo (AVERAGE)
- Classifica: Udinese 12°, Verona 14°
- Nessuna rivalità particolare

**Fattori applicati:**
| Fattore | Valore |
|---------|--------|
| Derby | ×1.00 |
| Casa Udinese | ×0.94 |
| Trasferta Verona | ×1.06 |
| Lega Serie A | ×1.00 |
| Colombo (avg) | ×1.00 |
| Possesso Udinese 44% | ×1.06 |
| Possesso Verona 42% | ×1.08 |

**Analisi tipo:**

> "Partita senza particolari fattori amplificanti. Nessun derby, arbitro nella media, posta in gioco moderata.
>
> Il fattore distintivo è che **entrambe le squadre hanno basso possesso** (44% e 42%), il che suggerisce una partita fisica con molti duelli.
>
> **Payero** dell'Udinese è il centrocampista più esposto: 5 gialli stagionali, ruolo di interdizione. Score: **47.3**
>
> Per il Verona in trasferta, **Serdar** combina trasferta + basso possesso squadra + ruolo mediano. Score: **51.8**
>
> Questa è una partita dove lo score soglia per considerare una scommessa dovrebbe essere più basso (~45) rispetto ai big match (~55)."

---

### Caso 4: Big Match (Napoli vs Juventus)

**Richiesta utente:** "Analizza Napoli-Juve"

**Contesto identificato:**
- Tipo partita: **Rivalità storica** (intensità 2)
- Arbitro: Rocchi (STRICT_OUTLIER, delta +1.2)
- Classifica: Napoli 2°, Juventus 3° (sfida scudetto)
- Ambiente: Maradona infuocato

**Fattori applicati:**
| Fattore | Valore |
|---------|--------|
| Rivalità storica | ×1.18 |
| Casa Napoli | ×0.94 |
| Trasferta Juve | ×1.06 |
| Lega Serie A | ×1.00 |
| Rocchi (severo) | ×1.15 |
| Possesso Napoli 58% | ×0.92 |
| Possesso Juve 54% | ×0.96 |

**Analisi tipo:**

> "La combinazione **rivalità storica + arbitro severo** rende questa partita ad altissimo rischio cartellini. Il moltiplicatore composto è 1.18 × 1.15 = **1.36** prima ancora di considerare gli altri fattori.
>
> Paradossalmente, il Napoli ha alto possesso (58%) che riduce il rischio dei suoi giocatori. Ma la Juve in trasferta con Rocchi è una combinazione pericolosa.
>
> **Locatelli** è il candidato #1: mediano davanti alla difesa, 7 gialli stagionali, trasferta, arbitro severo. Con Rocchi ha uno storico di 3 gialli in 4 partite. Score: **78.4**
>
> **Anguissa** del Napoli ha il ruolo più esposto in casa: box-to-box che contrasta molto. Nonostante il possesso alto del Napoli, il suo score è **62.1** per via dell'arbitro.
>
> **Attenzione a Gatti**: difensore aggressivo, 5 gialli, marca Lukaku (fisico). Matchup + trasferta + arbitro = Score **69.7**"

---

### Caso 5: El Clásico (Real Madrid vs Barcelona)

**Richiesta utente:** "Analizza Real Madrid-Barcelona"

**Contesto identificato:**
- Tipo partita: **El Clásico** (intensità 3)
- Arbitro: Hernández Hernández (STRICT_OUTLIER)
- Competizione: La Liga (baseline ×1.30)
- Classifica: Real 1°, Barça 2°

**Fattori applicati:**
| Fattore | Valore |
|---------|--------|
| El Clásico | ×1.26 |
| Casa Real | ×0.94 |
| Trasferta Barça | ×1.06 |
| **La Liga** | **×1.30** |
| Hernández² (severo) | ×1.15 |
| Possesso Real 52% | ×0.98 |
| Possesso Barça 62% | ×0.88 |

**Analisi tipo:**

> "El Clásico + La Liga + arbitro severo = la **tempesta perfetta per i cartellini**. Il moltiplicatore composto arriva a 1.26 × 1.30 × 1.15 = **1.88** per i giocatori base!
>
> La Liga da sola vale +30% rispetto alla Serie A. Aggiungi El Clásico e un arbitro severo, e gli score esplodono.
>
> **Tchouaméni** è il candidato #1: schermo davanti alla difesa, marca le ripartenze di Raphinha/Yamal. Score: **84.2**
>
> Interessante che il Barça, nonostante trasferta, ha possesso 62% che abbassa il rischio dei suoi giocatori. Ma **Gavi** rimane alto rischio: 8 gialli stagionali, temperamento caldo. Score: **79.1**
>
> **De Jong** in mediana contro i contropiedi del Real: Score **71.3**
>
> Per questi score altissimi, quasi tutti i centrocampisti sono a rischio. La partita media di El Clásico ha 6-7 cartellini."

---

### Caso 6: Champions League (Inter vs Atlético Madrid)

**Richiesta utente:** "Analizza Inter-Atletico Madrid di Champions"

**Contesto identificato:**
- Tipo partita: Ottavi Champions League
- Competizione: **Champions League** (baseline ×1.02)
- Arbitro: Turpin (ABOVE_AVERAGE)
- Atlético: squadra notoriamente aggressiva

**Fattori applicati:**
| Fattore | Valore |
|---------|--------|
| Rivalità | ×1.00 (nessuna) |
| Casa Inter | ×0.94 |
| Trasferta Atlético | ×1.06 |
| Champions League | ×1.02 |
| Turpin (sopra media) | ×1.05 |
| Possesso Inter 55% | ×0.95 |
| Possesso Atlético 45% | ×1.05 |

**Analisi tipo:**

> "L'Atlético di Simeone è una **macchina da falli tattici**: possesso basso (45%), pressing alto, 15.2 falli/partita (massimo in Liga).
>
> In Champions il baseline è neutro (×1.02), ma l'Atlético porta il suo stile ovunque.
>
> **Koke** è il candidato #1: capitano, 9 gialli stagionali tra Liga e Champions, ruolo di interdizione. Score: **68.4**
>
> **De Paul** ha uno storico di nervosismo nelle partite europee: 4 gialli in 8 partite Champions. Score: **64.1**
>
> Per l'Inter, **Barella** resta il più esposto anche in casa: contrasta le ripartenze dell'Atlético. Score: **52.3**
>
> **Nota tattica:** L'Atlético in trasferta si chiude ancora di più (40% possesso atteso), il che aumenterà i falli nel tentativo di recuperare palla."

---

## Interpretazione degli Score

### Fasce di Rischio

| Score | Interpretazione | Azione Suggerita |
|-------|-----------------|------------------|
| 75-100 | **Altissimo rischio** | Candidato principale, quasi certo |
| 60-74 | **Alto rischio** | Ottimo candidato |
| 45-59 | **Rischio moderato** | Buon candidato se quota interessante |
| 30-44 | **Rischio basso** | Solo se quota molto alta |
| 0-29 | **Rischio minimo** | Evitare |

### Adattamento per Tipo Partita

Le soglie vanno calibrate in base al contesto:

| Tipo Partita | Score Soglia Suggerito |
|--------------|------------------------|
| Derby intensità 3 + arbitro severo | 55+ |
| Rivalità storica | 50+ |
| Partita normale Serie A | 45+ |
| Partita con arbitro permissivo | 40+ |
| Bundesliga (baseline basso) | 40+ |
| La Liga (baseline alto) | 55+ |

---

## Limitazioni del Sistema

### Cosa NON può prevedere:

1. **Cartellini per proteste/comportamento** - Il sistema si basa su falli, non su dissent
2. **Espulsioni per falli gravi** - Eventi rari e imprevedibili
3. **Cambi tattici a partita in corso** - Se un allenatore cambia modulo, i matchup cambiano
4. **Infortuni durante la partita** - Possono alterare i minuti giocati
5. **Decisioni VAR** - Possono annullare o confermare cartellini

### Margine di errore:

- Accuratezza stimata sui top 5: **65-70%** (almeno 1 dei 5 prende giallo)
- Accuratezza sul #1: **35-40%**
- Il sistema identifica i **candidati probabili**, non certezze

---

## Conclusione

YellowOracle trasforma l'analisi dei cartellini da "intuizione" a "sistema pesato". Combinando:

1. **Dati storici** (cosa è successo)
2. **Contesto partita** (perché questa partita è diversa)
3. **Fattori moltiplicativi** (quanto amplificare/ridurre)

Il sistema produce score calibrati che vanno oltre le semplici medie stagionali, identificando opportunità dove il mercato potrebbe non aver incorporato tutti i fattori contestuali.

L'edge non sta nel prevedere con certezza, ma nel trovare situazioni dove la probabilità reale è **sistematicamente diversa** da quella implicita nelle quote.

---

*Documento generato per YellowOracle v2 - Sistema di Analisi Rischio Cartellini*
