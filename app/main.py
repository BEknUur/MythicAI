# app/main.py
from fastapi import FastAPI, Request, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import AnyUrl
from pathlib import Path
import json, logging, anyio

from app.config import settings
from app.services.apify_client import run_actor, fetch_run, fetch_items
from app.services.downloader import download_photos

log = logging.getLogger("api")
app = FastAPI(title="Instagram Book Generator", description="Создает крутые книги на основе Instagram профилей")

# Подключаем статические файлы
app.mount("/static", StaticFiles(directory="static"), name="static")

# ───────────── /start-scrape ────────────────────────────────
@app.get("/start-scrape")
async def start_scrape(url: AnyUrl):
    clean_url = str(url).rstrip("/")        # без закрывающего «/»

    run_input = {
        "directUrls":     [clean_url],
        "resultsType":    "details",
        "scrapeComments": False,
        
        "resultsLimit":   200,
    }

    webhook = {
        "eventTypes": ["ACTOR.RUN.SUCCEEDED"],
        "requestUrl": f"{settings.BACKEND_BASE}/webhook/apify",
        "payloadTemplate": (
            '{"runId":"{{runId}}",'
            '"datasetId":"{{defaultDatasetId}}"}'
        ),
    }

    run = await run_actor(run_input, webhooks=[webhook])
    log.info("Actor started runId=%s", run["id"])
    return {"runId": run["id"], "message": "Парсинг Instagram профиля начат!"}


# ───────────── /webhook/apify ───────────────────────────────
@app.post("/webhook/apify")
async def apify_webhook(request: Request, background: BackgroundTasks):
    try:
        payload = await request.json()
    except Exception:
        payload = {}

    # --- run / dataset ------------------------------------------------------------------
    run_id = payload.get("runId") or request.headers.get("x-apify-run-id")
    if not run_id:
        raise HTTPException(400, "runId missing")

    dataset_id = payload.get("datasetId")
    if not dataset_id:
        run = await fetch_run(run_id)
        dataset_id = run.get("defaultDatasetId")          # fallback

    if not dataset_id:
        raise HTTPException(500, "datasetId unresolved")

    # --- сохраняем JSON -----------------------------------------------------------------
    items = await fetch_items(dataset_id)
    run_dir = Path("data") / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "posts.json").write_text(json.dumps(items, ensure_ascii=False, indent=2))

    # --- качаем картинки ---------------------------------------------------------------
    images_dir = run_dir / "images"
    background.add_task(download_photos, items, images_dir)

    # --- строим книгу (markdown + html) -------------------------------------------------
    async def _build():
        from app.services.image_processor import process_folder
        from app.services.text_collector import collect_texts
        from app.services.book_builder import build_book

        imgs      = await process_folder(images_dir)
        comments  = collect_texts(run_dir / "posts.json")
        build_book(run_id, imgs, comments)

    background.add_task(lambda: anyio.run(_build))

    return {"status": "processing", "runId": run_id, "message": "Создание книги началось!"}


# ───────────── /status/{run_id} ────────────────────────────
@app.get("/status/{run_id}")
def status(run_id: str):
    run_dir = Path("data") / run_id
    posts_json = run_dir / "posts.json"
    images_dir = run_dir / "images"
    pdf_file = run_dir / "book.pdf"
    html_file = run_dir / "book.html"
    
    # Проверяем этапы создания
    status_info = {
        "runId": run_id,
        "stages": {
            "data_collected": posts_json.exists(),
            "images_downloaded": images_dir.exists() and any(images_dir.glob("*")),
            "book_generated": pdf_file.exists()
        },
        "files": {}
    }
    
    # Добавляем информацию о файлах
    if pdf_file.exists():
        status_info["files"]["pdf"] = f"/download/{run_id}/book.pdf"
    if html_file.exists():
        status_info["files"]["html"] = f"/view/{run_id}/book.html"
    
    # Добавляем информацию о профиле если есть
    if posts_json.exists():
        try:
            posts_data = json.loads(posts_json.read_text(encoding="utf-8"))
            if posts_data:
                profile = posts_data[0]
                status_info["profile"] = {
                    "username": profile.get("username"),
                    "fullName": profile.get("fullName"),
                    "followers": profile.get("followersCount"),
                    "posts": len(profile.get("latestPosts", []))
                }
        except:
            pass
    
    return status_info


# ───────────── /download/{run_id}/{filename} ─────────────
@app.get("/download/{run_id}/{filename}")
def download_file(run_id: str, filename: str):
    """Скачивание готовых файлов (PDF, HTML)"""
    run_dir = Path("data") / run_id
    file_path = run_dir / filename
    
    if not file_path.exists():
        raise HTTPException(404, f"Файл {filename} не найден")
    
    # Определяем MIME тип
    media_type = "application/pdf" if filename.endswith(".pdf") else "text/html"
    
    return FileResponse(
        path=file_path,
        media_type=media_type,
        filename=filename
    )


# ───────────── /view/{run_id}/book.html ─────────────────
@app.get("/view/{run_id}/book.html")
def view_book_html(run_id: str):
    """Просмотр HTML версии книги в браузере"""
    run_dir = Path("data") / run_id
    html_file = run_dir / "book.html"
    
    if not html_file.exists():
        raise HTTPException(404, "HTML версия книги не найдена")
    
    html_content = html_file.read_text(encoding="utf-8")
    return HTMLResponse(content=html_content)


# ───────────── / (главная страница) ─────────────────────
@app.get("/")
def home():
    """Главная страница с веб-интерфейсом"""
    static_dir = Path("static")
    index_file = static_dir / "index.html"
    
    if index_file.exists():
        html_content = index_file.read_text(encoding="utf-8")
        return HTMLResponse(content=html_content)
    else:
        return {
            "message": "🔥 Instagram Book Generator API",
            "description": "Создает крутые книги на основе Instagram профилей",
            "endpoints": {
                "start": "/start-scrape?url={instagram_url}",
                "status": "/status/{runId}",
                "download_pdf": "/download/{runId}/book.pdf",
                "view_html": "/view/{runId}/book.html"
            },
            "example": "/start-scrape?url=https://www.instagram.com/username"
        }
