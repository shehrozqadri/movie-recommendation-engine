import os
import json
import argparse
from dotenv import load_dotenv
from pymongo import MongoClient
import voyageai


def main():
    load_dotenv()

    parser = argparse.ArgumentParser(description="Run semantic vector search on sample_mflix.embedded_movies")
    parser.add_argument("--query", default="space adventure movies", help="Query text to embed and search")
    parser.add_argument("--limit", type=int, default=5, help="Number of results to return")
    args = parser.parse_args()

    mongo_uri = os.getenv("MONGODB_URI")
    voyage_api_key = os.getenv("VOYAGE_API_KEY")

    if not mongo_uri:
        raise SystemExit("Missing MONGODB_URI in environment (.env)")
    if not voyage_api_key:
        raise SystemExit("Missing VOYAGE_API_KEY in environment (.env)")

    vo = voyageai.Client(api_key=voyage_api_key)

    embedding_result = vo.embed(
        [args.query],
        model="voyage-3-large",
        input_type="query",
        output_dimension=2048,
    )
    query_vector = embedding_result.embeddings[0]

    client = MongoClient(mongo_uri)
    collection = client.sample_mflix.embedded_movies

    pipeline = [
        {
            "$vectorSearch": {
                "index": "vector_index",
                "path": "plot_embedding_voyage_3_large",
                "queryVector": query_vector,
                "numCandidates": 100,
                "limit": args.limit,
            }
        },
        {
            "$project": {
                "_id": 0,
                "title": 1,
                "year": 1,
                "plot": 1,
                "score": {"$meta": "vectorSearchScore"},
            }
        },
    ]

    results = list(collection.aggregate(pipeline))
    print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
