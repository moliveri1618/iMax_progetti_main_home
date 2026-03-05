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

if os.getenv("GITHUB_ACTIONS"):
    sys.path.append(os.path.dirname(__file__))
from routers import (
    commesse,
    vendite,
    tickets,
    workInProgress,
    savePDF,
    savePDFNautica,
    rilievoMisure,
    collaudoFinale,
    iParametriDaInserire,
    parametriTecnici,
    valoriWorkInProgressOdoo,
    users,
    commesseNautica,
    collaudoFinaleNautica,
    workInProgressNautica,
    ticketsNautica,
    rilievoMisureNautica,
    iParametriDaInserire_Nautica,
)
from dependecies import create_db_and_tables, verify_cognito_token, get_db
from routers.commesse import sync_commesse_home_from_odoo
from routers.commesseNautica import sync_commesse_nautica_odoo
from routers.tickets import sync_tickets_home_from_odoo
from routers.ticketsNautica import sync_tickets_nautica_from_odoo


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
    allow_origins=[
        "http://localhost:5173",
        "https://main.d3tifap6eylrpa.amplifyapp.com",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

app.include_router(commesse.router, prefix="/commesse", tags=["Commesse"])

app.include_router(
    commesseNautica.router, prefix="/commesseNautica", tags=["Commesse Nautica"]
)

# app.include_router(
#     vendite.router,
#     prefix="/vendite",
#     tags=["Vendite"]
#     )

app.include_router(tickets.router, prefix="/tickets", tags=["Tickets"])

app.include_router(
    ticketsNautica.router, prefix="/ticketsNautica", tags=["Tickets Nautica"]
)

app.include_router(
    workInProgress.router, prefix="/workInProgress", tags=["workInProgress"]
)

app.include_router(
    workInProgressNautica.router,
    prefix="/workInProgressNautica",
    tags=["workInProgressNautica"],
)

app.include_router(savePDF.router, prefix="/savePDF", tags=["savePDF"])

app.include_router(
    savePDFNautica.router, prefix="/savePDFNautica", tags=["savePDFNautica"]
)

app.include_router(
    rilievoMisure.router, prefix="/rilievoMisure", tags=["rilievoMisure"]
)

app.include_router(
    rilievoMisureNautica.router,
    prefix="/rilievoMisureNautica",
    tags=["rilievoMisureNautica"],
)

app.include_router(
    collaudoFinale.router, prefix="/collaudoFinale", tags=["collaudoFinale"]
)

app.include_router(
    collaudoFinaleNautica.router,
    prefix="/collaudoFinaleNautica",
    tags=["collaudoFinaleNautica"],
)

app.include_router(
    iParametriDaInserire.router,
    prefix="/iParametriDaInserire",
    tags=["iParametriDaInserire"],
)

app.include_router(
    iParametriDaInserire_Nautica.router,
    prefix="/iParametriDaInserireNautica",
    tags=["iParametriDaInserireNautica"],
)

app.include_router(
    parametriTecnici.router, prefix="/parametriTecnici", tags=["parametriTecnici"]
)

app.include_router(
    valoriWorkInProgressOdoo.router,
    prefix="/valoriWorkInProgressOdoo",
    tags=["valoriWorkInProgressOdoo"],
)

app.include_router(users.router, prefix="/users", tags=["users"])


@app.get("/")
async def root(current_user: dict = Depends(verify_cognito_token)):
    return {"message": "Hello"}


#####################################################
######### Event Bridge Night API INTEGRATIONS #######
#####################################################


async def run_commesse_home() -> None:
    logger.info(
        "✅ run commesse home START at %s", datetime.now(timezone.utc).isoformat()
    )

    db = None
    try:
        db = next(get_db())  # get one Session from the dependency generator
        inserted = sync_commesse_home_from_odoo(db)
        logger.info("✅ commesse_home DONE inserted=%s", inserted)

    except Exception:
        logger.exception("❌ run commesse home FAILED")
        raise

    finally:
        if db is not None:
            try:
                db.close()
            except Exception:
                logger.exception("❌ db.close() failed")

        logger.info(
            "✅ run commesse home END at %s", datetime.now(timezone.utc).isoformat()
        )


async def run_commesse_nautica() -> None:
    logger.info(
        "✅ run commesse Nautica START at %s", datetime.now(timezone.utc).isoformat()
    )

    db = None
    try:
        db = next(get_db())  # get one Session from the dependency generator
        inserted = sync_commesse_nautica_odoo(db)
        logger.info("✅ commesse Nautica DONE inserted=%s", inserted)

    except Exception:
        logger.exception("❌ run commesse Nautica FAILED")
        raise

    finally:
        if db is not None:
            try:
                db.close()
            except Exception:
                logger.exception("❌ db.close() failed")

        logger.info(
            "✅ run commesse Nautica END at %s", datetime.now(timezone.utc).isoformat()
        )


async def run_tickets_home() -> None:
    logger.info(
        "✅ run ticket Home START at %s", datetime.now(timezone.utc).isoformat()
    )

    db = None
    try:
        db = next(get_db())  # get one Session from the dependency generator
        inserted = sync_tickets_home_from_odoo(db)
        logger.info("✅ ticket home DONE inserted=%s", inserted)

    except Exception:
        logger.exception("❌ run ticket Home FAILED")
        raise

    finally:
        if db is not None:
            try:
                db.close()
            except Exception:
                logger.exception("❌ db.close() failed")

        logger.info(
            "✅ run ticket Home END at %s", datetime.now(timezone.utc).isoformat()
        )


async def run_tickets_nautica() -> None:
    logger.info(
        "✅ run ticket Nautica START at %s", datetime.now(timezone.utc).isoformat()
    )

    db = None
    try:
        db = next(get_db())  # get one Session from the dependency generator
        inserted = sync_tickets_nautica_from_odoo(db)
        logger.info("✅ ticket Nautica DONE inserted=%s", inserted)

    except Exception:
        logger.exception("❌ run ticket Nautica FAILED")
        raise

    finally:
        if db is not None:
            try:
                db.close()
            except Exception:
                logger.exception("❌ db.close() failed")

        logger.info(
            "✅ run ticket Nautica END at %s", datetime.now(timezone.utc).isoformat()
        )


def lambda_handler(event: Dict[str, Any], context):

    # EventBridge Scheduler / Rule invocation typically has "source": "aws.scheduler" or "aws.events"
    # detect by presence of "detail-type" and lack of API Gateway fields.
    logger.info("Invocation keys=%s source=%s", list(event.keys()), event.get("source"))
    is_apigw = "requestContext" in event and (
        event.get("version") == "2.0" or "httpMethod" in event
    )

    if not is_apigw:

        # ✅ internal scheduled invocation
        # You can use detail to route multiple jobs
        detail = event.get("detail", {}) or {}
        job = detail.get("job") or event.get("job")

        if job == "commesse_home":
            asyncio.run(run_commesse_home())
            return {"ok": True, "ran": "commesse_home"}
        elif job == "commesse_nautica":
            asyncio.run(run_commesse_nautica())
            return {"ok": True, "ran": "commesse_nautica"}
        elif job == "tickets_home":
            asyncio.run(run_tickets_home())
            return {"ok": True, "ran": "tickets_home"}
        elif job == "tickets_nautica":
            asyncio.run(run_tickets_nautica())
            return {"ok": True, "ran": "tickets_nautica"}

        # Unknown non-HTTP invocation
        return {"ok": False, "error": "Unknown event", "event_keys": list(event.keys())}

    # ✅ normal HTTP request via API Gateway -> FastAPI
    return handler(event, context)
