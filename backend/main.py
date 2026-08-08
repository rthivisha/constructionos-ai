# FastAPI application entrypoint and CORS configuration.
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.db import init_db
from backend.routes.project_setup import router as project_setup_router
from backend.routes.events import router as events_router

app = FastAPI(title="ConstructionOS AI Backend")

# Initialize database and seed tables on startup
@app.on_event("startup")
def startup_event():
    init_db()

# Configure CORS
allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000")
origins = [origin.strip() for origin in allowed_origins_env.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(project_setup_router)
app.include_router(events_router)

@app.get("/")
def read_root():
    return {"status": "online", "service": "ConstructionOS AI"}
