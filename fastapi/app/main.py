from fastapi import FastAPI
from fastapi.responses import JSONResponse, PlainTextResponse

app = FastAPI(title="OKR AI Stack API")

@app.get("/health")
def health() -> PlainTextResponse:
    return PlainTextResponse("ok")

