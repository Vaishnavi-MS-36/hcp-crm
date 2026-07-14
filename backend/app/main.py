import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from .database import Base, engine
from . import models  # noqa: F401 ensures models are registered before create_all
from .routers import chat, interactions, hcps

load_dotenv()

Base.metadata.create_all(bind=engine)

app = FastAPI(title="AI-First CRM - HCP Interaction Log API")

origins = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router)
app.include_router(interactions.router)
app.include_router(hcps.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
