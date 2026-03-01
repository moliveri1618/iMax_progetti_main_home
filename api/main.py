import sys
import os
from fastapi import FastAPI, Depends
from mangum import Mangum
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio
from typing import Any, Dict
import logging
from datetime import datetime, timezone

if os.getenv("GITHUB_ACTIONS"):sys.path.append(os.path.dirname(__file__)) 
from routers import commesse, vendite, tickets, workInProgress, savePDF, savePDFNautica, rilievoMisure, collaudoFinale, iParametriDaInserire, parametriTecnici, valoriWorkInProgressOdoo, users, commesseNautica, collaudoFinaleNautica, workInProgressNautica, ticketsNautica, rilievoMisureNautica, iParametriDaInserire_Nautica
from dependecies import create_db_and_tables, verify_cognito_token


@asynccontextmanager
async def lifespan(app: FastAPI):
    await asyncio.to_thread(create_db_and_tables)
    yield

app = FastAPI(lifespan=lifespan)
handler = Mangum(app=app)

logger = logging.getLogger()
logger.setLevel(logging.INFO)

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


async def run_daily_job() -> None:
    now = datetime.now(timezone.utc).isoformat()
    logger.info("✅ run_daily_job START at %s", now)

    try:
        # your logic here
        # await asyncio.to_thread(do_odoo_sync)
        logger.info("✅ run_daily_job doing work...")
    except Exception:
        logger.exception("❌ run_daily_job FAILED")
        raise
    finally:
        logger.info("✅ run_daily_job END at %s", datetime.now(timezone.utc).isoformat())


def lambda_handler(event: Dict[str, Any], context):
    # EventBridge Scheduler / Rule invocation typically has "source": "aws.scheduler" or "aws.events"
    # We'll detect by presence of "detail-type" and lack of API Gateway fields.
    is_apigw = (
        "requestContext" in event and
        (event.get("version") == "2.0" or "httpMethod" in event)
    )

    if not is_apigw:
        # ✅ internal scheduled invocation
        # You can use detail to route multiple jobs
        detail = event.get("detail", {}) or {}
        job = detail.get("job") or event.get("job")  # support simple payload too

        if job == "daily_integration":
            asyncio.run(run_daily_job())
            return {"ok": True, "ran": "daily_integration"}

        # Unknown non-HTTP invocation
        return {"ok": False, "error": "Unknown event", "event_keys": list(event.keys())}

    # ✅ normal HTTP request via API Gateway -> FastAPI
    return handler(event, context)