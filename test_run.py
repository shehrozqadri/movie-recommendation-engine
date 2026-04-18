import asyncio
from backend.main import recommend, RecommendRequest

async def test():
    req = RecommendRequest(query="sci-fi")
    res = await recommend(req)
    print(res)

asyncio.run(test())
