from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import auth,vault,audit,admin
from app.rabbitmq_client import connect_rabbitmq,disconnect_rabbitmq,setup_rabbitmq
from contextlib import asynccontextmanager
from app.middleware.rate_limiter import rate_limit_middleware
from app.middleware.security_headers import security_headers_middleware

origins = ["http://localhost:5173"]

@asynccontextmanager
async def lifespan(app: FastAPI):
   await connect_rabbitmq()
   await setup_rabbitmq()
   yield
   await disconnect_rabbitmq()
   
app = FastAPI(title = "Password Manager",lifespan=lifespan)

app.add_middleware(CORSMiddleware,allow_origins=origins,allow_methods=["*"],allow_credentials= True,allow_headers=["*"])
app.middleware("http")(rate_limit_middleware)
app.middleware("http")(security_headers_middleware)
app.include_router(auth.router,prefix="/auth",tags=["auth"])
app.include_router(vault.router,prefix="/vault",tags=["vault"])
app.include_router(audit.router,prefix="/audit",tags=["audit"])
app.include_router(admin.router,prefix="/admin",tags=["admin"])
@app.get("/health")
async def health():
    return {"status" : "ok"}


    