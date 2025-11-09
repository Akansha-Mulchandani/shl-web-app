# SHL Assessment Recommender

End-to-end system to recommend SHL assessments from job descriptions or natural language queries.

## Project Structure

- /backend
- /frontend
- /data
- /experiments

## Setup

1) Create and activate a Python 3.10+ environment.
2) Install dependencies:

```
pip install -r requirements.txt
```

3) (Optional) Set Google Gemini API Key for reranking:

- On Windows PowerShell:
```
$env:GEMINI_API_KEY = "YOUR_KEY"
```

## Data

- Put/keep the uploaded Excel dataset in the project root as `Gen_AI Dataset.xlsx`.
- Crawl the SHL catalog (Individual Test Solutions only):

```
python data/crawl_shl_catalog.py
```
This creates `data/catalog.jsonl` and `data/catalog.parquet`.

- Process the dataset to CSVs for experiments:
```
python data/process_dataset.py
```

## Run Backend (FastAPI)

```
uvicorn backend.main:app --reload --port 8000
```

Health:
```
curl http://localhost:8000/health
```

Recommend:
```
curl -X POST http://localhost:8000/recommend -H "Content-Type: application/json" -d '{"query":"Java developer who collaborates well"}'
```

### API Endpoints and Schema

- `GET /health` → `{ "status": "ok" }`
- `POST /recommend`
  - Request JSON:
    ```json
    {
      "query": "Looking to hire Python + SQL in 60 minutes",
      "k": 10
    }
    ```
    - `query` string, required
    - `k` integer, optional (default 10)
  - Response JSON:
    ```json
    {
      "recommended_assessments": [
        {
          "url": "https://www.shl.com/solutions/products/product-catalog/view/python-new/",
          "adaptive_support": true,
          "description": "Short description if available",
          "duration": "~30 mins",
          "remote_support": true,
          "test_type": ["cognitive", "skills"]
        }
      ]
    }
    ```
  - Notes:
    - CORS is enabled in `backend/main.py` for browser access.
    - Endpoint accepts POST only.

## Run Frontend (Streamlit)

```
streamlit run frontend/app.py
```

- Sidebar allows setting `API_BASE_URL` and running a health check.
- Enter a query, choose `k`, view results table, and download CSV.

## Experiments

- Use `/experiments` for evaluation notebooks.

### Prediction file outputs

Running:
```
python experiments/predict.py --out predictions.csv
```
produces multiple formats for Excel compatibility, all with exactly two columns:

- `predictions.csv` (UTF-8 BOM, comma)
- `predictions_fixed_excel.csv` (UTF-8 BOM, semicolon)
- `predictions_readable.csv` (same two columns; repeated `Query` blanked for visual readability only)
- `predictions.tsv` (tab-delimited)
- `predictions.xlsx` (sheet `predictions`)

Format requirements:
- Two columns only: `Query` and `Assessment_url`.
- One recommendation per row. The same `Query` repeats on multiple rows (one URL per row).
- Queries are normalized to single-line text (no embedded newlines).

## Deployment

### Backend on Render (FastAPI)

Prereqs:
- Push this repository to GitHub (with `Procfile`, `render.yaml`, `requirements.txt` at repo root).
- Have your `GEMINI_API_KEY` ready (optional for reranking).

Render setup:
1) Render Dashboard → New → Blueprint → select this repo.
2) Render will detect `render.yaml` and create a Web Service using:
   - Build: `pip install -r requirements.txt`
   - Start: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
3) In the service → Settings → Environment → add env var:
   - `GEMINI_API_KEY` = your key (optional)
4) Deploy and verify:
   - `GET https://<service>.onrender.com/health` → `{ "status": "ok" }`
   - `POST https://<service>.onrender.com/recommend`

`Procfile` and `render.yaml` are already included and configured.

### Frontend on Streamlit Cloud (optional)

1) New app → point to this repo → main file: `frontend/app.py`.
2) Set environment variable in Streamlit Cloud:
   - `API_BASE_URL` = `https://<your-render-service>.onrender.com`
3) Deploy. Use the sidebar health check to confirm connectivity.
