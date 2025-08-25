from fastapi import FastAPI

app = FastAPI(title="OKR MLOps API", version="0.1.0")


@app.get("/health")
async def health():
    return {"status": "ok"}