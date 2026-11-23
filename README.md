# RecomAI

Multi-domain, explainable content-based recommender (movies, songs, books)
with a Django REST API and a React frontend.

## Quick start

1. Download the datasets (see data/README.md)
2. python -m venv venv; venv\Scripts\activate
3. pip install -r requirements.txt
4. cd backend; copy .env.example .env; python manage.py runserver
5. cd frontend; npm install; npm run dev -> http://localhost:5173

## Architecture

recomai/hub.py routes calls to domain engines
recomai/domains/base.py DomainRecommender contract (search / recommend / filter_schema)
recomai/<domain>/ config.py (weights, fields) + engine.py (the model)
backend/api/ REST layer (5 endpoints)
frontend/ Vite + React + TypeScript

## Changing or adding a model

- Tune a model: edit weights/fields in recomai/<domain>/config.py
- Replace a model: change recomai/<domain>/engine.py; keep the recommend() output
  contract: {id, title, subtitle, score 0-1, reason[], meta{}}
- Add a domain: implement DomainRecommender, then add one factory in
  backend/api/hub_registry.py (FACTORIES). The frontend gets a new tab automatically.

## Tests

cd backend; python manage.py test api
RECOMAI_SMOKE=1 runs the real-engine tests (needs datasets)
