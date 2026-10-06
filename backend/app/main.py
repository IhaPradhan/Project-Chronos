from dotenv import load_dotenv
load_dotenv()

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .database.schema import create_tables
from .routes.round1 import router as round1_router
from .routes.round2 import router as round2_router
@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()
    yield


app = FastAPI(
    title="Project Chronos API",
    lifespan=lifespan
)


# Serve Round 1 images
BASE_DIR = Path(__file__).resolve().parents[1]

app.mount(
    "/static",
    StaticFiles(directory=BASE_DIR / "static"),
    name="static"
)


@app.get("/")
def home():
    return {"message": "Project Chronos API is running"}


app.include_router(
    round1_router,
    prefix="/api/round1"
)

app.include_router(
    round2_router
)
