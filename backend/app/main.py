from contextlib import asynccontextmanager
from fastapi import FastAPI
from .database.schema import create_tables
from .routes.round1 import router as round1_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()
    yield

app = FastAPI(
    title="Project Chronos API",
    lifespan=lifespan
)
app.include_router(round1_router, prefix="/api/round1")

@app.get("/")
def home():
    return {"message": "Project Chronos API is running"}
