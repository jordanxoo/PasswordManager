from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import auth,vault

origins = ["http://localhost:5173"]

app = FastAPI(title = "Password Manager")

app.add_middleware(CORSMiddleware,allow_origins=origins,allow_methods=["*"],allow_credentials= True,allow_headers=["*"])

app.include_router(auth.router,prefix="/auth",tags=["auth"])
app.include_router(vault.router,prefix="/vault",tags=["vault"])

@app.get("/health")
async def health():
    return {"status" : "ok"}



