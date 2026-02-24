import sys
import os
from fastapi import FastAPI, Depends
from mangum import Mangum
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio

if os.getenv("GITHUB_ACTIONS"):sys.path.append(os.path.dirname(__file__)) 
from routers import commesse, vendite, tickets, workInProgress, savePDF, savePDFNautica, rilievoMisure, collaudoFinale, iParametriDaInserire, parametriTecnici, valoriWorkInProgressOdoo, users, commesseNautica, collaudoFinaleNautica, workInProgressNautica, ticketsNautica, rilievoMisureNautica, iParametriDaInserire_Nautica
from dependecies import create_db_and_tables, verify_cognito_token


@asynccontextmanager
async def lifespan(app: FastAPI):
    await asyncio.to_thread(create_db_and_tables)
    yield

app = FastAPI(lifespan=lifespan)
handler = Mangum(app=app)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173","https://main.d3tifap6eylrpa.amplifyapp.com",],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"], 
    allow_headers=["Content-Type", "Authorization"], 
)

app.include_router(
    commesse.router, 
    prefix="/commesse", 
    tags=["Commesse"]
    )

app.include_router(
    commesseNautica.router, 
    prefix="/commesseNautica", 
    tags=["Commesse Nautica"]
    )

# app.include_router(
#     vendite.router, 
#     prefix="/vendite", 
#     tags=["Vendite"]
#     )

app.include_router(
    tickets.router, 
    prefix="/tickets", 
    tags=["Tickets"]
    )

app.include_router(
    ticketsNautica.router, 
    prefix="/ticketsNautica", 
    tags=["Tickets Nautica"]
    )

app.include_router(
    workInProgress.router, 
    prefix="/workInProgress", 
    tags=["workInProgress"]
    )

app.include_router(
    workInProgressNautica.router, 
    prefix="/workInProgressNautica", 
    tags=["workInProgressNautica"]
    )

app.include_router(
    savePDF.router, 
    prefix="/savePDF", 
    tags=["savePDF"]
    )

app.include_router(
    savePDFNautica.router, 
    prefix="/savePDFNautica", 
    tags=["savePDFNautica"]
    )

app.include_router(
    rilievoMisure.router, 
    prefix="/rilievoMisure", 
    tags=["rilievoMisure"]
    )

app.include_router(
    rilievoMisureNautica.router, 
    prefix="/rilievoMisureNautica", 
    tags=["rilievoMisureNautica"]
    )

app.include_router(
    collaudoFinale.router, 
    prefix="/collaudoFinale", 
    tags=["collaudoFinale"]
    )

app.include_router(
    collaudoFinaleNautica.router, 
    prefix="/collaudoFinaleNautica", 
    tags=["collaudoFinaleNautica"]
    )

app.include_router(
    iParametriDaInserire.router, 
    prefix="/iParametriDaInserire", 
    tags=["iParametriDaInserire"]
    )

app.include_router(
    iParametriDaInserire_Nautica.router, 
    prefix="/iParametriDaInserireNautica", 
    tags=["iParametriDaInserireNautica"]
    )

app.include_router(
    parametriTecnici.router, 
    prefix="/parametriTecnici", 
    tags=["parametriTecnici"]
    )

app.include_router(
    valoriWorkInProgressOdoo.router, 
    prefix="/valoriWorkInProgressOdoo", 
    tags=["valoriWorkInProgressOdoo"]
    )

app.include_router(
    users.router, 
    prefix="/users", 
    tags=["users"]
    )



@app.get("/")
async def root(current_user: dict = Depends(verify_cognito_token)):
    return {"message": "Hello"}
