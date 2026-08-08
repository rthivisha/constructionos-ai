# Router handling POST /api/events to run the live query and agent pipeline against current database state.
from fastapi import APIRouter

router = APIRouter(prefix="/api/events", tags=["events"])
