"""
Main application entry point (API)
"""
from fastapi import FastAPI
from app.api.routes import router

app = FastAPI(
    title="Medical Gynecology & Pregnancy AI",
    description="Ollama-powered gynecology and pregnancy consultation system",
    version="1.0.0"
)

app.include_router(router)

@app.get("/")
def root():
    return {
        "status": "ok",
        "message": "Medical Gynecology AI is running"
    }
