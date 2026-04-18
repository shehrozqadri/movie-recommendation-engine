# AI Movie Recommendation Engine

Movie recommendation web app powered by MongoDB Atlas vector search + LLM synthesis.

## Features

- Semantic vector search using `plot_embedding_voyage_3_large`
- Optional hybrid search (vector + Atlas Search text, fused with RRF)
- Movie Q&A endpoint grounded in the movie plot

## Tech Stack

- Backend: FastAPI
- Database: MongoDB Atlas (`sample_mflix.embedded_movies`)
- Embeddings: Voyage AI (`voyage-3-large`)
- LLM: Groq (`llama-3.1-8b-instant`)

## Architecture Diagram

```text
User Query
	|
	v
FastAPI Backend
	|
	+--> Voyage AI Embedding
	|        |
	|        v
	|   Query Vector
	|        |
	|        v
	+--> MongoDB Atlas
	|      - Vector Search (`$vectorSearch`)
	|      - Atlas Search (`$search`, optional)
	|
	v
Retrieved Movie Context
	|
	v
Groq LLM
	|
	v
Recommendation / Movie Q&A Response
```

## Semantic Search Implementation

Semantic search is implemented with a MongoDB aggregation pipeline using the Atlas `$vectorSearch` stage against the `vector_index`.

Flow:

1. User query is embedded with Voyage AI
2. The embedding is sent to MongoDB Atlas Vector Search
3. Top matching movies are returned with `vectorSearchScore`

Sample pipeline:

```json
[
	{
		"$vectorSearch": {
			"index": "vector_index",
			"path": "plot_embedding_voyage_3_large",
			"queryVector": ["<embedding-vector-here>"],
			"numCandidates": 100,
			"limit": 5
		}
	},
	{
		"$project": {
			"_id": 0,
			"title": 1,
			"year": 1,
			"plot": 1,
			"score": { "$meta": "vectorSearchScore" }
		}
	}
]
```

## Hybrid Search Implementation

Hybrid search is implemented in two steps:

1. A vector-search aggregation pipeline using `$vectorSearch`
2. A keyword-search aggregation pipeline using Atlas `$search`

The results are then merged in Python using **Reciprocal Rank Fusion (RRF)**.

This means hybrid search is **not** a single MongoDB pipeline in this project; it is two retrieval pipelines combined in application code.

Sample vector branch:

```json
[
	{
		"$vectorSearch": {
			"index": "vector_index",
			"path": "plot_embedding_voyage_3_large",
			"queryVector": ["<embedding-vector-here>"],
			"numCandidates": 100,
			"limit": 10
		}
	},
	{
		"$project": {
			"_id": 1,
			"title": 1,
			"plot": 1,
			"year": 1,
			"poster": 1,
			"score": { "$meta": "vectorSearchScore" }
		}
	}
]
```

Sample Atlas Search branch:

```json
[
	{
		"$search": {
			"index": "movies_search_index",
			"text": {
				"query": "space adventure movies",
				"path": ["title", "plot", "fullplot"]
			}
		}
	},
	{ "$limit": 10 },
	{
		"$project": {
			"_id": 1,
			"title": 1,
			"plot": 1,
			"year": 1,
			"poster": 1,
			"score": { "$meta": "searchScore" }
		}
	}
]
```

Those two result sets are fused in Python with RRF rather than combined with `$unionWith`.

## RAG Implementation

This project uses a lightweight custom RAG flow and **does not use LangChain**.

### Recommendation RAG

1. Embed the user query with Voyage AI
2. Retrieve relevant movies from MongoDB using semantic or hybrid search
3. Build a prompt from the retrieved movie plots/titles
4. Send that grounded context to Groq for the final recommendation response

### Movie Q&A RAG

For the movie Q&A feature:

1. The selected movie document is fetched from MongoDB
2. Its `fullplot` (or `plot`) is used as the only context
3. Groq is prompted to answer using only that retrieved plot

So the RAG layer here is implemented manually with:

- MongoDB Atlas for retrieval
- Voyage AI for embeddings
- Groq for generation
- FastAPI application logic for orchestration

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

Health check:

```bash
curl -v http://127.0.0.1:8001/api/health
```

Run simple semantic search script:

```bash
python run_semantic_search.py --query "space adventure movies" --limit 5
```

---

## Troubleshooting

### `ModuleNotFoundError: dotenv`

Ensure `python-dotenv` is in `requirements.txt`.

### MongoDB TLS/connection errors

- Use `mongodb+srv://` URI
- Keep `dnspython` + `certifi` installed
- Ensure Atlas Network Access is configured correctly for your runtime environment

---

Built in 2026.
