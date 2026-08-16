# FastAPI application entrypoint and CORS configuration.
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from backend.db import init_db
from backend.routes.project_setup import router as project_setup_router
from backend.routes.events import router as events_router
from backend.routes.schedule import router as schedule_router

app = FastAPI(title="ConstructionOS AI Backend")

# Ensure uploads directory exists and mount it
uploads_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
os.makedirs(uploads_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")

# Initialize database and seed tables on startup
@app.on_event("startup")
def startup_event():
    init_db()

# Configure CORS
allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "")
origins = [origin.strip() for origin in allowed_origins_env.split(",") if origin.strip()]

for default_origin in ["http://localhost:3000", "http://localhost:3001", "http://127.0.0.1:3000"]:
    if default_origin not in origins:
        origins.append(default_origin)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"^https://.*\.vercel\.app$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(project_setup_router)
app.include_router(events_router)
app.include_router(schedule_router)

@app.get("/")
def read_root():
    return {"status": "online", "service": "ConstructionOS AI"}
