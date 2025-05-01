import sys
import os
from fastapi import FastAPI, Depends
from mangum import Mangum
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio

if os.getenv("GITHUB_ACTIONS"):sys.path.append(os.path.dirname(__file__)) 
from routers import items  
from dependecies import create_db_and_tables, verify_cognito_token


@asynccontextmanager
async def lifespan(app: FastAPI):
    await asyncio.to_thread(create_db_and_tables)
    yield

app = FastAPI(lifespan=lifespan)
handler = Mangum(app=app)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"], 
    allow_headers=["Content-Type", "Authorization"], 
)


app.include_router(
    items.router, 
    prefix="/items", 
    tags=["Items"]
)


@app.get("/")
async def root(current_user: dict = Depends(verify_cognito_token)):

    return {"message": "Hello"}
