from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from config import settings
import httpx

app = FastAPI()


@app.api_route("/{full_path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy(request: Request, full_path: str):
    target_url = (settings.listing_service_url if full_path.startswith("api-listings") else settings.auth_service_url)
    async with httpx.AsyncClient(timeout=20) as client:
        method = request.method
        headers = dict(request.headers)
        body = await request.body()
        resp = await client.request(method, f"{target_url}/{full_path}", headers=headers, content=body)
        return JSONResponse(status_code=resp.status_code, content=resp.json())
