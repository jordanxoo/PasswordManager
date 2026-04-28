from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import auth,vault,audit
from app.database import engine,Base
from app import models
from contextlib import asynccontextmanager
from app.middleware.rate_limiter import rate_limit_middleware
origins = ["http://localhost:5173"]

@asynccontextmanager
async def lifespan(app: FastAPI):
   yield
   
app = FastAPI(title = "Password Manager",lifespan=lifespan)

app.add_middleware(CORSMiddleware,allow_origins=origins,allow_methods=["*"],allow_credentials= True,allow_headers=["*"])
app.middleware("http")(rate_limit_middleware)
app.include_router(auth.router,prefix="/auth",tags=["auth"])
app.include_router(vault.router,prefix="/vault",tags=["vault"])
app.include_router(audit.router,prefix="/audit",tags=["audit"])
@app.get("/health")
async def health():
    return {"status" : "ok"}


    