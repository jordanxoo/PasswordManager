from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import auth,vault
from app.database import engine,Base
from app import models
from contextlib import asynccontextmanager
origins = ["http://localhost:5173"]

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield    

app = FastAPI(title = "Password Manager",lifespan=lifespan)

app.add_middleware(CORSMiddleware,allow_origins=origins,allow_methods=["*"],allow_credentials= True,allow_headers=["*"])

app.include_router(auth.router,prefix="/auth",tags=["auth"])
app.include_router(vault.router,prefix="/vault",tags=["vault"])

@app.get("/health")
async def health():
    return {"status" : "ok"}


    