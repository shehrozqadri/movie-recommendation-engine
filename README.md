# AI Movie Recommendation Engine

A highly advanced, fully-featured Retrieval-Augmented Generation (RAG) web application that recommends movies using both **Semantic Inference** and **Hybrid Search** logic.

## 🚀 Key Features

*   **Semantic Vector Search**: Understands the "meaning" of a query (e.g. "a scary movie about a shark") using advanced mathematical embeddings rather than relying strictly on keyword matches.
*   **Hybrid Search**: Uses Reciprocal Rank Fusion (RRF) to merge mathematical vector searches with exact keyword searches, maximizing relevance across highly specific names (e.g. "Christopher Nolan space thriller").
*   **Deep Dive Q&A (RAG)**: A dedicated frosted glass UI model securely fetches the entire extended plot of a specific movie from the database and restricts the LLM to *only* synthesize answers directly from that verified source.

## 🛠️ Architecture & Tech Stack

*   **Database**: MongoDB Atlas (`sample_mflix.embedded_movies` dataset)
*   **Vector Embeddings**: Voyage AI (`voyage-3-large`)
*   **Generative AI (LLM)**: Groq API (`llama-3.1-8b-instant`)
*   **Backend Framework**: FastAPI (Python)
*   **Frontend**: Vanilla HTML / CSS / Vanilla JS (No bloated dependencies)

---

## 💻 Local Setup Instructions

### 1. Prerequisites
You will need a minimum of Python 3.9+ and active accounts for MongoDB Atlas, Voyage AI, and Groq.

### 2. Environment Variables
Clone the repository and create a hidden `.env` file in the root directory. You must supply your own active API keys:

```ini
MONGODB_URI=mongodb+srv://<username>:<password>@<cluster>.mongodb.net/...
VOYAGE_API_KEY=pa-...
GROQ_API_KEY=gsk_...
```

### 3. Install Dependencies
Spin up a Python virtual environment to isolate the packages:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 4. Database Initialization (Crucial)
Because this application runs off the **MongoDB sample dataset**, you must ensure your Atlas Cluster has loaded the `sample_mflix` database.

You must then manually create **two** indexes in your MongoDB Atlas Dashboard:

**A. Vector Search Index (`vector_index`)**
Create an Atlas Vector Search index on the `embedded_movies` collection targeting the `plot_embedding_voyage_3_large` field (2048 dimensions).

**B. Keyword Search Index (`movies_search_index`)**
Create a standard Atlas Search Index (Visual Editor) using "Dynamic Mapping" on the `embedded_movies` collection. This allows the backend to perform the Hybrid Search text matching.

### 5. Start the Application
Boot up the Python FastAPI backend:
```bash
uvicorn backend.main:app --reload --port 8001
```

Boot up the Frontend (using any static HTTP server, like `npx` or Python's `http.server`):
```bash
python3 -m http.server 3005 -d frontend
```
Navigate to `http://localhost:3005` inside your web browser to enjoy the cinematic engine!

---
*Built with ❤️ in 2026 as an exploration into agentic programming and vector-driven architecture.*
