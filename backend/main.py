import os
import logging
import traceback
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from bson.objectid import ObjectId
from pymongo import MongoClient
from bson.objectid import ObjectId

# Optional external clients — import lazily and handle ImportError so the
# Vercel function won't crash if packages aren't installed during the build.
voyage_imported = False
groq_imported = False
vo = None
groq_client = None
try:
    import voyageai
    voyage_imported = True
except Exception:
    voyage_imported = False

try:
    from groq import Groq
    groq_imported = True
except Exception:
    groq_imported = False
from dotenv import load_dotenv
import certifi

load_dotenv()

app = FastAPI()

# Global exception handler to ensure tracebacks appear in Vercel logs
@app.exception_handler(Exception)
async def all_exception_handler(request: Request, exc: Exception):
    tb = traceback.format_exc()
    logging.error("Unhandled exception: %s", tb)
    return JSONResponse(status_code=500, content={"detail": "Internal server error", "error": str(exc)})


@app.get("/api/health")
async def health_check():
    status = {"ready": True}
    try:
        if client:
            # quick ping
            client.admin.command('ping')
            status["mongodb"] = "ok"
        else:
            status["mongodb"] = "unavailable"
    except Exception as e:
        status["mongodb"] = f"error: {e}"
    return status

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize clients
MONGO_URI = os.getenv("MONGODB_URI")
VOYAGE_API_KEY = os.getenv("VOYAGE_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not all([MONGO_URI, VOYAGE_API_KEY, GROQ_API_KEY]):
    print("Warning: Missing required environment variables. Please check your .env file.")

client = None
db = None
collection = None


@app.on_event("startup")
async def startup_db_client():
    """Initialize MongoDB client on startup. Don't fail the whole app if
    the database is unreachable (prevents build-time or deploy-time failures).
    """
    global client, db, collection
    if MONGO_URI:
        try:
            # Use certifi CA bundle to ensure a proper CA is available in the runtime.
            # dnspython is required for mongodb+srv URIs (added in requirements).
            client = MongoClient(
                MONGO_URI,
                tls=True,
                tlsCAFile=certifi.where(),
                serverSelectionTimeoutMS=5000,
            )
            db = client.sample_mflix
            collection = db.embedded_movies
            client.admin.command('ping')
        except Exception as e:
            print("Warning: Could not connect to MongoDB on startup:", e)
            client = None
            collection = None
    else:
        collection = None
    # Initialize external API clients if available and configured.
    global vo, groq_client
    if voyage_imported and VOYAGE_API_KEY:
        try:
            vo = voyageai.Client(api_key=VOYAGE_API_KEY)
        except Exception as e:
            print("Warning: voyageai client init failed:", e)
            vo = None

    if groq_imported and GROQ_API_KEY:
        try:
            groq_client = Groq(api_key=GROQ_API_KEY)
        except Exception as e:
            print("Warning: groq client init failed:", e)
            groq_client = None

# Note: clients `vo` and `groq_client` are initialized during the FastAPI
# `startup` event above. Avoid initializing them at import time to prevent
# crashes when optional packages are not installed or env vars are missing.

class RecommendRequest(BaseModel):
    query: str
    search_type: str = "vector"

@app.post("/api/recommend")
async def recommend(req: RecommendRequest):
    if collection is None or not VOYAGE_API_KEY or not GROQ_API_KEY:
        raise HTTPException(status_code=500, detail="Server not configured properly with API keys.")

    try:
        # 1. Embed query using Voyage AI
        # Using voyage-3-large assuming it was the embedding stored in 'plot_embedding_voyage_3_large'
        # Adjust model name and path if the user used a different one.
        embedding_result = vo.embed(
            [req.query], 
            model="voyage-3-large", 
            input_type="query",
            output_dimension=2048
        )
        query_embedding = embedding_result.embeddings[0]

        # 2. Search Execution
        movies = []
        vector_pipeline = [
            {
                "$vectorSearch": {
                    "index": "vector_index", 
                    "path": "plot_embedding_voyage_3_large", 
                    "queryVector": query_embedding,
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
                    "score": {"$meta": "vectorSearchScore"}
                }
            }
        ]

        if req.search_type == "hybrid":
            # Execute Vector Search
            vector_results = list(collection.aggregate(vector_pipeline))
            
            # Execute Keyword Search
            text_pipeline = [
                {
                    "$search": {
                        "index": "movies_search_index",
                        "text": {
                            "query": req.query,
                            "path": ["title", "plot", "fullplot"]
                        }
                    }
                },
                {"$limit": 10},
                {
                    "$project": {
                        "_id": 1,
                        "title": 1,
                        "plot": 1,
                        "year": 1,
                        "poster": 1,
                        "score": {"$meta": "searchScore"}
                    }
                }
            ]
            text_results = list(collection.aggregate(text_pipeline))
            
            # Reciprocal Rank Fusion (RRF)
            rrf_scores = {}
            k = 60
            movie_map = {}
            
            for rank, doc in enumerate(vector_results):
                doc_id = str(doc["_id"])
                movie_map[doc_id] = doc
                rrf_scores[doc_id] = 1 / (k + rank + 1)
                
            for rank, doc in enumerate(text_results):
                doc_id = str(doc["_id"])
                if doc_id not in movie_map:
                    movie_map[doc_id] = doc
                    rrf_scores[doc_id] = 0
                rrf_scores[doc_id] += 1 / (k + rank + 1)
                
            sorted_docs = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
            
            for doc_id, _ in sorted_docs[:5]:
                m = movie_map[doc_id]
                m["_id"] = str(m["_id"])
                movies.append(m)
        else:
            # Standard Vector Search only
            results = list(collection.aggregate(vector_pipeline))[:5]
            for m in results:
                m["_id"] = str(m["_id"])
                movies.append(m)
        
        if not movies:
            return {"recommendation": "Sorry, I couldn't find any relevant movies. Make sure your vector index is correctly built and named 'vector_index'.", "movies": []}

        # 3. Generate response with Groq
        contextText = ""
        for m in movies:
            contextText += f"- {m.get('title')} ({m.get('year')}): {m.get('plot')}\n"

        prompt = f"""
You are an expert movie recommender. The user asked: "{req.query}".
Based on our vector search, here are the most relevant movies found in our database:

{contextText}

Synthesize these results into a friendly, helpful recommendation for the user. Mention why these movies fit their request.
"""
        
        chat_completion = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a helpful, enthusiastic movie recommendation assistant."},
                {"role": "user", "content": prompt}
            ],
            model="llama-3.1-8b-instant",
        )
        
        return {
            "recommendation": chat_completion.choices[0].message.content,
            "movies": movies
        }

    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=str(e))

class AskRequest(BaseModel):
    movie_id: str
    question: str

@app.post("/api/movie/ask")
async def ask_movie(req: AskRequest):
    if collection is None or not GROQ_API_KEY:
        raise HTTPException(status_code=500, detail="Server missing database or Groq configuration.")
    try:
        movie = collection.find_one({"_id": ObjectId(req.movie_id)})
        if not movie:
            raise HTTPException(status_code=404, detail="Movie not found.")
        
        fullplot = movie.get("fullplot", movie.get("plot", "No plot available."))
        title = movie.get("title", "Unknown Title")
        
        prompt = f"""
You are an expert movie assistant. The user is asking a question about the movie "{title}".
Here is the full plot of the movie:
{fullplot}

User Question: {req.question}

Please answer the user's question accurately using ONLY the plot provided above. If the plot does not contain the answer, politely say so.
"""
        chat_completion = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a helpful movie assistant."},
                {"role": "user", "content": prompt}
            ],
            model="llama-3.1-8b-instant",
        )
        return {"answer": chat_completion.choices[0].message.content}
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=str(e))
