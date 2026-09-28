from contextlib import asynccontextmanager
from fastapi import FastAPI
from .database.schema import create_tables

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()
    yield

app = FastAPI(
    title="Project Chronos API",
    lifespan=lifespan
)

@app.get("/")
def home():
    return {"message": "Project Chronos API is running"}
