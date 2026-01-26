# YellowOracle - Configurazione Aggiornamento Automatico

## Script disponibili

| Script | Uso | Durata |
|--------|-----|--------|
| `scripts/weekly_sync.sh` | Aggiorna solo stagione corrente | ~15 min |
| `scripts/full_sync.sh` | Ricostruisce tutto (3 stagioni) | ~45 min |

## Configurazione Cron Job

### 1. Apri crontab
```bash
crontab -e
```

### 2. Aggiungi la riga per sync settimanale

**Opzione A: Ogni lunedì alle 6:00** (consigliato)
```cron
0 6 * * 1 /home/salvatore/Scrivania/soccer/scripts/weekly_sync.sh
```

**Opzione B: Ogni giorno alle 5:00**
```cron
0 5 * * * /home/salvatore/Scrivania/soccer/scripts/weekly_sync.sh
```

**Opzione C: Due volte a settimana (lunedì e giovedì)**
```cron
0 6 * * 1,4 /home/salvatore/Scrivania/soccer/scripts/weekly_sync.sh
```

### 3. Salva e esci
- In nano: `Ctrl+O`, `Enter`, `Ctrl+X`
- In vim: `:wq`

### 4. Verifica
```bash
crontab -l
```

## Formato Cron

```
┌───────────── minuto (0 - 59)
│ ┌───────────── ora (0 - 23)
│ │ ┌───────────── giorno del mese (1 - 31)
│ │ │ ┌───────────── mese (1 - 12)
│ │ │ │ ┌───────────── giorno della settimana (0 - 6, 0 = domenica)
│ │ │ │ │
* * * * * comando
```

## Consultare i Log

```bash
# Ultimi log
ls -la ~/Scrivania/soccer/logs/

# Leggi ultimo log
cat ~/Scrivania/soccer/logs/$(ls -t ~/Scrivania/soccer/logs/ | head -1)

# Segui log in tempo reale (durante sync)
tail -f ~/Scrivania/soccer/logs/sync_*.log
```

## Esecuzione Manuale

```bash
# Sync settimanale (solo stagione corrente)
~/Scrivania/soccer/scripts/weekly_sync.sh

# Sync completo (tutte le stagioni)
~/Scrivania/soccer/scripts/full_sync.sh
```

## Troubleshooting

### Il cron non parte
1. Verifica che lo script sia eseguibile: `ls -la scripts/*.sh`
2. Verifica il path di Python: `which python` vs path nello script
3. Controlla i log di cron: `grep CRON /var/log/syslog`

### Errori API 403
- Verifica che l'abbonamento football-data.org sia attivo
- Controlla la chiave API in `.env`

### Errori Supabase
- Verifica connessione internet
- Controlla credenziali in `.env`
