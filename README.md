# api-pharmacie

API pour récupérer les pharmacies de garde du Cameroun depuis:
`https://www.annuaire-medical.cm/fr/pharmacies-de-garde/`

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Lancer l'API

```bash
uvicorn app:app --reload
```

## Endpoints

- `GET /health`
- `GET /pharmacies-de-garde?ville=Yaounde&region=Centre&autour=Bastos`
- `GET /pharmacies-de-garde/filters`

### Paramètres

- `ville` (optionnel): filtre par ville
- `region` (optionnel): filtre par région
- `autour` (optionnel): filtre libre (quartier/environ)

Les valeurs autorisées pour `ville` et `region` sont exposées par
`GET /pharmacies-de-garde/filters`.

Réponse:

```json
{
  "source": "https://www.annuaire-medical.cm/fr/pharmacies-de-garde/",
  "filters": {
    "ville": "Yaounde",
    "region": "Centre",
    "autour": "Bastos"
  },
  "count": 1,
  "results": [
    {
      "name": "Pharmacie Bastos",
      "address": "...",
      "city": "...",
      "region": "...",
      "phone": "...",
      "details": "..."
    }
  ]
}
```
