from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

from db.index import connect_db, close_db, db


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_db()
    yield
    await close_db()


app = FastAPI(
    title="Knoc Interview API",
    description="AI-powered interview backend",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/")
async def root():
    return {
        "message": "Knoc Interview API is running!",
        "status": "online",
    }


@app.get("/api/v1/health")
async def health():
    return {"status": "ok"}


@app.get("/api/v1/health/database")
async def database_health():
    try:
        await db.command("ping")
        return {
            "status": "connected",
            "database": "knoc_interview",
        }
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail="MongoDB connection failed",
        ) from exc