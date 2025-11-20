from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException

from app.routers import parseresume, transcribe, score, test
from app.executor import _executor


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await transcribe.get_gemma_pipe()
    except Exception as e:
        raise RuntimeError("Failed to initialize GEMMA pipeline") from e

    yield
    _executor.shutdown(wait=True)


app = FastAPI(lifespan=lifespan)

app.include_router(transcribe.router)
app.include_router(parseresume.router)
app.include_router(score.router)
app.include_router(test.router)


@app.get("/")
def read_root() -> dict[str, str]:
    return {"message": "Welcome to the Resume and Interview Analysis API!"}


@app.get("/health")
def health_check() -> dict[str, str]:
    try:
        return {"status": "ok", "message": "API is running smoothly."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
