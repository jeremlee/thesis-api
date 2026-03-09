import uvicorn
from fastapi import FastAPI, HTTPException

from app.routers import accuracy_reports, chatbot, comparison, score


app = FastAPI()

app.include_router(score.router)
app.include_router(comparison.router)
app.include_router(chatbot.router)
app.include_router(accuracy_reports.router)


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
