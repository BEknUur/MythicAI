# app/main.py
from fastapi import FastAPI, Request, BackgroundTasks, HTTPException
from pydantic import AnyUrl
from pathlib import Path
import json, logging

from app.config import settings
from app.services.apify_client import run_actor, fetch_run, fetch_items
from app.services.downloader import download_photos


logging.basicConfig(level=logging.INFO)
log = logging.getLogger("api")

app = FastAPI(title="Instagram Book Generator")


# ──────────────── /start-scrape ──────────────────────────────────────────────
@app.get("/start-scrape")
async def start_scrape(url: AnyUrl):
    # Apify не любит слэш на конце — удаляем
    clean_url = str(url).rstrip("/")

    run_input = {
        "directUrls":     [clean_url],
        "resultsType":    "details",
        "scrapeComments": True,
        "resultsLimit":   200
    }

    webhook = {
        "eventTypes":      ["ACTOR.RUN.SUCCEEDED"],
        "requestUrl":      f"{settings.BACKEND_BASE}/webhook/apify",
        # только нужные нам данные
        "payloadTemplate": (
            '{"runId":"{{runId}}","datasetId":"{{defaultDatasetId}}"}'
        )
    }

    run = await run_actor(run_input, webhooks=[webhook])
    log.info("Actor started  runId=%s", run["id"])
    return {"runId": run["id"]}


# ──────────────── /webhook/apify ─────────────────────────────────────────────
@app.post("/webhook/apify")
async def apify_webhook(request: Request, background_tasks: BackgroundTasks):
    try:
        payload = await request.json()
    except Exception:
        payload = {}

    run_id = payload.get("runId") or request.headers.get("x-apify-run-id")
    if not run_id:
        raise HTTPException(400, "runId missing in webhook")

    dataset_id = payload.get("datasetId")
    if not dataset_id:
        run = await fetch_run(run_id)
        dataset_id = run.get("defaultDatasetId")

    if not dataset_id:
        raise HTTPException(500, "datasetId unresolved")

    items = await fetch_items(dataset_id)
    if not items:
        log.error("Dataset %s came empty — profile may be private", dataset_id)

    run_dir = Path("data") / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "posts.json").write_text(
        json.dumps(items, ensure_ascii=False, indent=2)
    )

    background_tasks.add_task(download_photos, items, run_dir / "photos")
    

    return {"status": "processing", "runId": run_id}


# ──────────────── /status/{run_id} ───────────────────────────────────────────
@app.get("/status/{run_id}")
def status(run_id: str):
    pdf = Path("data") / run_id / "book.pdf"
    return {"ready": pdf.exists(), "pdf": str(pdf) if pdf.exists() else None}
