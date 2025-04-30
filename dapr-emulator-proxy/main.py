from fastapi import FastAPI, Request, Response
import httpx, os

DAPR_HOST = os.getenv("DAPR_HOST", "http://localhost:3500")  # inside the Pod
TIMEOUT    = 30  # seconds

app = FastAPI()

@app.api_route("/v1.0/bindings/{binding_name}", methods=["POST"])
async def invoke_binding(binding_name: str, request: Request):
    body = await request.body()
    headers = {k: v for k, v in request.headers.items() if k != "host"}

    target = f"{DAPR_HOST}/v1.0/bindings/{binding_name}"
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        dapr_resp = await client.post(target, content=body, headers=headers)

    return Response(
        content=dapr_resp.content,
        status_code=dapr_resp.status_code,
        media_type=dapr_resp.headers.get("content-type", "application/json"),
    )
