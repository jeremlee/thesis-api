from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.routers import  score, comparison, chatbot
from app.executor import _executor
import uvicorn


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        pass
    except Exception as e:
        raise RuntimeError("Failed to initialize GEMMA pipeline") from e

    yield
    _executor.shutdown(wait=True)


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(score.router)
app.include_router(comparison.router)
app.include_router(chatbot.router)


@app.get("/")
def read_root() -> dict[str, str]:
    return {"message": "Welcome to the Resume and Interview Analysis API!"}


@app.get("/health")
def health_check() -> dict[str, str]:
    try:
        return {"status": "ok", "message": "API is running smoothly."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000)

