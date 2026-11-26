# Which hotel performs best? — data project

Business question: **City Hotel vs Resort Hotel, which one performs best?**

Pipeline: `hotel_pipeline.py` (load -> describe -> clean -> merge -> fill -> export -> charts).
Only functions seen in the course slides (read_csv/read_excel, isna, duplicated, drop_duplicates,
.str.strip/lower, replace, to_numeric, to_datetime, fillna, where, mask, abs, quantile/between,
merge, groupby/agg/transform, pivot_table, matplotlib, seaborn).

## Lancer (depuis le dossier data-project)
```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python hotel_pipeline.py
```

## Arborescence
- `data/raw/` : les deux fichiers bruts (jamais modifiés)
- `output/hotel_bookings_clean.csv` : table propre, 1 ligne par réservation (25 000 lignes)
- `output/cleaning_log.csv` : chaque étape de nettoyage (lignes avant/après, valeurs modifiées)
- `output/scoreboard.csv` : les indicateurs City vs Resort
- `figures/01-02` : avant/après nettoyage (noms d'hôtel, prix par nuit)
- `figures/03-07` : réponse à la question (annulations, segments, valeur d'un séjour, prix par mois, CA 2016)
