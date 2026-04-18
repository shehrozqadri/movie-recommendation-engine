# AI Movie Recommendation Engine

Movie recommendation web app powered by MongoDB Atlas vector search + LLM synthesis.

## Features

- Semantic vector search using `plot_embedding_voyage_3_large`
- Optional hybrid search (vector + Atlas Search text, fused with RRF)
- Movie Q&A endpoint grounded in the movie plot
- Frontend built with vanilla HTML/CSS/JS

## Tech Stack

- Backend: FastAPI
- Database: MongoDB Atlas (`sample_mflix.embedded_movies`)
- Embeddings: Voyage AI (`voyage-3-large`)
- LLM: Groq (`llama-3.1-8b-instant`)
- Frontend: static files (`frontend/`)

---

## Local Setup

### 1) Prerequisites

- Python 3.9+
- MongoDB Atlas cluster with `sample_mflix` loaded
- Voyage + Groq API keys

### 2) Environment Variables

Create a `.env` file in repo root:

```ini
MONGODB_URI=mongodb+srv://<username>:<password>@<cluster>.mongodb.net/...
VOYAGE_API_KEY=pa-...
GROQ_API_KEY=gsk_...
```

### 3) Install

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 4) Required Atlas Indexes

1. Vector index: `vector_index`
	 - Collection: `sample_mflix.embedded_movies`
	 - Path: `plot_embedding_voyage_3_large`
	 - Dimensions: `2048`

2. Atlas Search index: `movies_search_index`
	 - Collection: `sample_mflix.embedded_movies`
	 - Dynamic mapping enabled

### 5) Run locally

Start backend:

```bash
uvicorn backend.main:app --host 127.0.0.1 --port 8001 --reload
```

Start frontend static server:

```bash
python3 -m http.server 8080 --directory frontend
```

Open: `http://localhost:8080`

Health check:

```bash
curl -v http://127.0.0.1:8001/api/health
```

Run simple semantic search script:

```bash
python run_semantic_search.py --query "space adventure movies" --limit 5
```

---

## Deploy to Vercel (from scratch)

### 1) Push latest code

```bash
git add .
git commit -m "Prepare Vercel deployment"
git push origin main
```

### 2) Install/login/link

```bash
npm i -g vercel
vercel login
vercel
```

### 3) Add environment variables in Vercel project

Set these in **Project → Settings → Environment Variables**:

- `MONGODB_URI`
- `VOYAGE_API_KEY`
- `GROQ_API_KEY`

Use at least `Production` environment (and `Preview` if you test there).

### 4) Deploy

Either push to `main` (if repo connected), or run:

```bash
vercel --prod
```

### 5) Verify deployed API

```bash
curl -v https://<your-app-domain>/api/health
curl -v -H "Content-Type: application/json" \
	-d '{"query":"inception","search_type":"vector"}' \
	https://<your-app-domain>/api/recommend
```

---

## Troubleshooting

### `FUNCTION_INVOCATION_FAILED`

Fetch production logs:

```bash
vercel logs <deployment-url-or-id> \
	--project <project-name> \
	--environment production \
	--since 1h \
	--no-follow \
	--expand
```

### `ModuleNotFoundError: dotenv`

Ensure `python-dotenv` is in `requirements.txt`.

### `Voyage AI client not available`

Ensure both are true:

1. `voyageai` is installed (`requirements.txt`)
2. `VOYAGE_API_KEY` is set in Vercel env vars

### `DEPLOYMENT_NOT_FOUND`

Usually wrong domain/alias. Verify active alias:

```bash
vercel inspect https://<your-domain>.vercel.app
```

### MongoDB TLS/connection errors

- Use `mongodb+srv://` URI
- Keep `dnspython` + `certifi` installed
- Ensure Atlas Network Access permits Vercel (use `0.0.0.0/0` temporarily while testing)

---

Built in 2026.
