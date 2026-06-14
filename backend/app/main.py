from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import auth,vault,audit,admin,profile,generator,hibp,ws,api_keys,organizations,collections
from app.rabbitmq_client import connect_rabbitmq,disconnect_rabbitmq,setup_rabbitmq
from contextlib import asynccontextmanager
from app.middleware.rate_limiter import rate_limit_middleware
from app.middleware.security_headers import security_headers_middleware
from prometheus_fastapi_instrumentator import Instrumentator
from app.pubsub_listener import redis_pubsub_listener
import asyncio
from app.websocket_manager import manager
from app.middleware.request_size import RequestSizeLimitMiddleware
origins = ["http://localhost:5173"]

@asynccontextmanager
async def lifespan(app: FastAPI):
   await connect_rabbitmq()
   await setup_rabbitmq()
   task = asyncio.create_task(redis_pubsub_listener())
   yield
   task.cancel()
   await disconnect_rabbitmq()
   await manager.disconnect_all()
   
app = FastAPI(title = "Password Manager",lifespan=lifespan)
Instrumentator().instrument(app).expose(app)

app.add_middleware(CORSMiddleware,allow_origins=origins,allow_methods=["*"],allow_credentials= True,allow_headers=["*"])
app.add_middleware(RequestSizeLimitMiddleware)
app.middleware("http")(rate_limit_middleware)
app.middleware("http")(security_headers_middleware)
app.include_router(auth.router,prefix="/auth",tags=["auth"])
app.include_router(vault.router,prefix="/vault",tags=["vault"])
app.include_router(audit.router,prefix="/audit",tags=["audit"])
app.include_router(admin.router,prefix="/admin",tags=["admin"])
app.include_router(profile.router,prefix="/profile",tags=["profile"])
app.include_router(generator.router,prefix="/generator",tags=["generator"])
app.include_router(hibp.router,prefix="/hibp",tags=["hibp"])
app.include_router(ws.router,tags=["websocket"])
app.include_router(api_keys.router,prefix="/api-keys",tags=["api-keys"])
app.include_router(organizations.router,prefix="/organizations",tags=["organizations"])
app.include_router(collections.router,prefix="/organizations/{org_id}/collections",tags=["collections"])
@app.get("/health")
async def health():
    return {"status" : "ok"}


    