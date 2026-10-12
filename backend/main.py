
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes.auth import router as auth_router
from api.routes.user import router as users_router
from db.index import connect_db, close_db
from api.routes.interviews import router as interviews_router
from api.routes.practice import router as practice_router
@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_db()
    try:
        yield
    finally:
        await close_db()


app = FastAPI(
    title="Knoc Interview API",
    description="AI-powered interview preparation backend",
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "Knoc Interview API"}


app.include_router(auth_router)
app.include_router(users_router)
app.include_router(interviews_router)
app.include_router(practice_router)