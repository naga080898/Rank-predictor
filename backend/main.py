import logging
import sys
import os
from pathlib import Path
from datetime import datetime
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.config import ALLOWED_ORIGINS
from backend.database import init_db, get_db
from backend.models import CandidateSubmission
from backend.routes.evaluate import router as evaluate_router
from backend.routes.stats import router as stats_router
from backend.routes.leaderboard import router as leaderboard_router

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("rank_predictor_api")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycles."""
    logger.info("Starting Rank Predictor Backend API...")
    init_db()
    logger.info("Application startup complete.")
    yield
    logger.info("Shutting down Rank Predictor Backend API...")

app = FastAPI(
    title="Exam Rank Predictor & Response Sheet Analytics API",
    description="High-performance backend for parsing DigiALM / TCS iON response sheets, calculating scores, real-time rank percentiles, and exam statistics.",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for frontend integration (Vercel, Cloudflare Pages, Localhost)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if "*" in ALLOWED_ORIGINS else ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(evaluate_router)
app.include_router(stats_router)
app.include_router(leaderboard_router)

# Mount Frontend Static Assets
frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
if frontend_dir.exists():
    css_dir = frontend_dir / "css"
    js_dir = frontend_dir / "js"
    assets_dir = frontend_dir / "assets"
    if css_dir.exists():
        app.mount("/css", StaticFiles(directory=str(css_dir)), name="css")
    if js_dir.exists():
        app.mount("/js", StaticFiles(directory=str(js_dir)), name="js")
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    logo_file = frontend_dir / "assets" / "logo.jpeg"
    if logo_file.exists():
        return FileResponse(str(logo_file))
    return {}

@app.get("/health", tags=["System"])
def health_check(db: Session = Depends(get_db)):
    """Health check endpoint for monitoring uptime (e.g. UptimeRobot) and cold-start keep-alive."""
    total_submissions = db.query(func.count(CandidateSubmission.id)).scalar() or 0
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "total_submissions_recorded": total_submissions
    }

@app.get("/", tags=["System"])
def root():
    """Serves the main frontend Web UI or API info if frontend not found."""
    index_file = frontend_dir / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {
        "service": "Exam Rank Predictor API",
        "status": "online",
        "docs_url": "/docs",
        "health_url": "/health"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
