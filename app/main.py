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
app = FastAPI(title="Романтическая Летопись Любви", description="Создает красивые романтические книги на основе Instagram профилей для ваших любимых")

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
    return {"runId": run["id"], "message": "Создание романтической книги началось! ❤️"}


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

    # --- строим романтическую книгу (markdown + html) ---------------------------------
    async def _build():
        import asyncio
        from app.services.image_processor import process_folder
        from app.services.text_collector import collect_texts
        from app.services.book_builder import build_romantic_book

        # Ждем несколько секунд для завершения загрузки изображений
        print("💕 Ожидаем завершения загрузки изображений...")
        await asyncio.sleep(5)
        
        # Проверяем загрузку изображений несколько раз
        for attempt in range(10):
            if images_dir.exists() and any(images_dir.glob("*")):
                print(f"📸 Найдены изображения в папке {images_dir}")
                break
            print(f"⏳ Попытка {attempt + 1}/10: ждем загрузки изображений...")
            await asyncio.sleep(2)

        imgs      = await process_folder(images_dir)
        comments  = collect_texts(run_dir / "posts.json")
        build_romantic_book(run_id, imgs, comments)

    background.add_task(lambda: anyio.run(_build))

    return {"status": "processing", "runId": run_id, "message": "Создание романтической книги началось! 💕"}


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
        return HTMLResponse(content="""
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Романтическая Летопись Любви</title>
    <link href="https://fonts.googleapis.com/css2?family=Dancing+Script:wght@400;700&family=Playfair+Display:wght@400;700&family=Inter:wght@300;400;500;600&display=swap" rel="stylesheet">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Inter', sans-serif;
            line-height: 1.6;
            color: #2c3e50;
            background: linear-gradient(135deg, #ff9a9e 0%, #fecfef 50%, #fecfef 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1000px;
            margin: 0 auto;
            background: rgba(255, 255, 255, 0.95);
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.15);
            overflow: hidden;
        }
        
        .header {
            background: linear-gradient(135deg, #ff6b9d 0%, #c44569 100%);
            padding: 60px 40px;
            text-align: center;
            color: white;
            position: relative;
        }
        
        .header::before {
            content: "💕";
            position: absolute;
            top: 20px;
            left: 40px;
            font-size: 2em;
            animation: float 3s ease-in-out infinite;
        }
        
        .header::after {
            content: "💖";
            position: absolute;
            top: 30px;
            right: 40px;
            font-size: 1.5em;
            animation: float 3s ease-in-out infinite reverse;
        }
        
        @keyframes float {
            0%, 100% { transform: translateY(0px); }
            50% { transform: translateY(-10px); }
        }
        
        .main-title {
            font-family: 'Dancing Script', cursive;
            font-size: 4em;
            font-weight: 700;
            margin-bottom: 20px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
        }
        
        .subtitle {
            font-family: 'Playfair Display', serif;
            font-size: 1.6em;
            opacity: 0.9;
            margin-bottom: 30px;
        }
        
        .heart-decoration {
            font-size: 2.5em;
            animation: heartbeat 2s ease-in-out infinite;
        }
        
        @keyframes heartbeat {
            0% { transform: scale(1); }
            50% { transform: scale(1.1); }
            100% { transform: scale(1); }
        }
        
        .content {
            padding: 60px 40px;
        }
        
        .love-form {
            background: linear-gradient(135deg, #ffeaa7 0%, #fab1a0 100%);
            padding: 40px;
            border-radius: 15px;
            margin-bottom: 40px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }
        
        .form-title {
            font-family: 'Dancing Script', cursive;
            font-size: 2.5em;
            color: #d63031;
            text-align: center;
            margin-bottom: 30px;
        }
        
        .input-group {
            margin-bottom: 25px;
        }
        
        .input-label {
            display: block;
            font-weight: 600;
            color: #2d3436;
            margin-bottom: 8px;
            font-size: 1.1em;
        }
        
        .input-field {
            width: 100%;
            padding: 15px 20px;
            border: 2px solid #fdcb6e;
            border-radius: 12px;
            font-size: 1em;
            transition: all 0.3s ease;
            font-family: 'Inter', sans-serif;
        }
        
        .input-field:focus {
            outline: none;
            border-color: #e17055;
            box-shadow: 0 0 0 3px rgba(225, 112, 85, 0.2);
        }
        
        .love-button {
            width: 100%;
            background: linear-gradient(135deg, #fd79a8 0%, #e84393 100%);
            color: white;
            border: none;
            padding: 20px 40px;
            border-radius: 12px;
            font-size: 1.2em;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            font-family: 'Inter', sans-serif;
            margin-top: 20px;
        }
        
        .love-button:hover {
            transform: translateY(-3px);
            box-shadow: 0 10px 30px rgba(232, 67, 147, 0.3);
        }
        
        .features {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 30px;
            margin-top: 40px;
        }
        
        .feature-card {
            background: white;
            padding: 30px;
            border-radius: 15px;
            text-align: center;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            transition: transform 0.3s ease;
        }
        
        .feature-card:hover {
            transform: translateY(-5px);
        }
        
        .feature-icon {
            font-size: 3em;
            margin-bottom: 20px;
        }
        
        .feature-title {
            font-family: 'Playfair Display', serif;
            font-size: 1.3em;
            color: #2d3436;
            margin-bottom: 15px;
        }
        
        .feature-text {
            color: #636e72;
            line-height: 1.6;
        }
        
        @media (max-width: 768px) {
            .content {
                padding: 40px 20px;
            }
            
            .header {
                padding: 40px 20px;
            }
            
            .main-title {
                font-size: 2.5em;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1 class="main-title">Романтическая Летопись Любви</h1>
            <p class="subtitle">Создайте красивую книгу воспоминаний для вашего любимого человека</p>
            <div class="heart-decoration">💝</div>
        </div>
        
        <div class="content">
            <div class="love-form">
                <h2 class="form-title">Создать Книгу Любви</h2>
                <form id="loveBookForm">
                    <div class="input-group">
                        <label class="input-label" for="instagramUrl">Instagram профиль вашего любимого человека 💕</label>
                        <input type="url" id="instagramUrl" class="input-field" placeholder="https://www.instagram.com/username" required>
                    </div>
                    
                    <button type="submit" class="love-button">
                        Создать Романтическую Книгу ❤️
                    </button>
                </form>
            </div>
            
            <div class="features">
                <div class="feature-card">
                    <div class="feature-icon">📖</div>
                    <h3 class="feature-title">Красивая Летопись</h3>
                    <p class="feature-text">Создаем красивую книгу с фотографиями и романтическими текстами о вашем любимом человеке</p>
                </div>
                
                <div class="feature-card">
                    <div class="feature-icon">💌</div>
                    <h3 class="feature-title">Романтические Послания</h3>
                    <p class="feature-text">Добавляем трогательные тексты и цитаты о любви между фотографиями</p>
                </div>
                
                <div class="feature-card">
                    <div class="feature-icon">🎨</div>
                    <h3 class="feature-title">Элегантный Дизайн</h3>
                    <p class="feature-text">Профессиональное оформление с романтическими цветами и шрифтами</p>
                </div>
                
                <div class="feature-card">
                    <div class="feature-icon">📱</div>
                    <h3 class="feature-title">Просто и Быстро</h3>
                    <p class="feature-text">Просто укажите Instagram профиль - мы сделаем всё остальное за вас</p>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        document.getElementById('loveBookForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const url = document.getElementById('instagramUrl').value;
            const button = document.querySelector('.love-button');
            
            button.disabled = true;
            button.innerHTML = 'Создаем книгу... 💕';
            
            try {
                const response = await fetch(`/start-scrape?url=${encodeURIComponent(url)}`);
                const result = await response.json();
                
                if (response.ok) {
                    // Перенаправляем на страницу статуса
                    window.location.href = `/status-page?runId=${result.runId}`;
                } else {
                    throw new Error(result.message || 'Произошла ошибка');
                }
            } catch (error) {
                alert('Ошибка: ' + error.message);
                button.disabled = false;
                button.innerHTML = 'Создать Романтическую Книгу ❤️';
            }   
        });
    </script>
</body>
</html>
        """)

# ───────────── /status-page ─────────────────────
@app.get("/status-page")
def status_page(runId: str):
    """Страница отслеживания статуса создания книги"""
    return HTMLResponse(content=f"""
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Создание Романтической Книги</title>
    <link href="https://fonts.googleapis.com/css2?family=Dancing+Script:wght@400;700&family=Playfair+Display:wght@400;700&family=Inter:wght@300;400;500;600&display=swap" rel="stylesheet">
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Inter', sans-serif;
            background: linear-gradient(135deg, #ff9a9e 0%, #fecfef 100%);
            min-height: 100vh;
            padding: 20px;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        
        .status-container {{
            max-width: 600px;
            background: rgba(255, 255, 255, 0.95);
            border-radius: 20px;
            padding: 60px 40px;
            text-align: center;
            box-shadow: 0 20px 60px rgba(0,0,0,0.15);
        }}
        
        .status-title {{
            font-family: 'Dancing Script', cursive;
            font-size: 3em;
            color: #e84393;
            margin-bottom: 30px;
        }}
        
        .status-message {{
            font-size: 1.2em;
            color: #2d3436;
            margin-bottom: 40px;
            line-height: 1.6;
        }}
        
        .progress-container {{
            margin: 40px 0;
        }}
        
        .progress-bar {{
            width: 100%;
            height: 12px;
            background: #ddd;
            border-radius: 6px;
            overflow: hidden;
            margin-bottom: 20px;
        }}
        
        .progress-fill {{
            height: 100%;
            background: linear-gradient(135deg, #fd79a8 0%, #e84393 100%);
            width: 0%;
            transition: width 0.3s ease;
            border-radius: 6px;
        }}
        
        .progress-text {{
            color: #636e72;
            font-style: italic;
        }}
        
        .heart-loading {{
            font-size: 4em;
            margin: 30px 0;
            animation: heartbeat 1.5s ease-in-out infinite;
        }}
        
        @keyframes heartbeat {{
            0%, 100% {{ transform: scale(1) rotate(0deg); }}
            50% {{ transform: scale(1.2) rotate(5deg); }}
        }}
        
        .result-container {{
            display: none;
            margin-top: 30px;
        }}
        
        .success-title {{
            font-family: 'Dancing Script', cursive;
            font-size: 2.5em;
            color: #00b894;
            margin-bottom: 20px;
        }}
        
        .download-buttons {{
            display: flex;
            gap: 20px;
            justify-content: center;
            flex-wrap: wrap;
            margin-top: 30px;
        }}
        
        .download-btn {{
            padding: 15px 30px;
            border: none;
            border-radius: 10px;
            font-weight: 600;
            text-decoration: none;
            transition: all 0.3s ease;
            cursor: pointer;
        }}
        
        .btn-view {{
            background: linear-gradient(135deg, #74b9ff 0%, #0984e3 100%);
            color: white;
        }}
        
        .btn-download {{
            background: linear-gradient(135deg, #fd79a8 0%, #e84393 100%);
            color: white;
        }}
        
        .download-btn:hover {{
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
        }}
        
        @media (max-width: 768px) {{
            .status-container {{
                padding: 40px 20px;
            }}
            
            .download-buttons {{
                flex-direction: column;
                align-items: center;
            }}
        }}
    </style>
</head>
<body>
    <div class="status-container">
        <h1 class="status-title">Создаем Вашу Книгу Любви</h1>
        <p class="status-message">Пожалуйста, подождите... Мы собираем самые красивые моменты и создаем романтическую книгу для вашего любимого человека ❤️</p>
        
        <div class="heart-loading">💕</div>
        
        <div class="progress-container">
            <div class="progress-bar">
                <div class="progress-fill" id="progressFill"></div>
            </div>
            <p class="progress-text" id="progressText">Собираем фотографии...</p>
        </div>
        
        <div class="result-container" id="resultContainer">
            <h2 class="success-title">Ваша книга готова! 🎉</h2>
            <p>Теперь вы можете просмотреть или скачать романтическую книгу</p>
            <div class="download-buttons" id="downloadButtons">
                <!-- Кнопки будут добавлены динамически -->
            </div>
        </div>
    </div>
    
    <script>
        const runId = '{runId}';
        const progressFill = document.getElementById('progressFill');
        const progressText = document.getElementById('progressText');
        const resultContainer = document.getElementById('resultContainer');
        const downloadButtons = document.getElementById('downloadButtons');
        
        const stages = [
            {{ text: 'Собираем фотографии...', progress: 20 }},
            {{ text: 'Обрабатываем изображения...', progress: 40 }},
            {{ text: 'Создаем романтические тексты...', progress: 60 }},
            {{ text: 'Оформляем книгу...', progress: 80 }},
            {{ text: 'Финальные штрихи...', progress: 95 }}
        ];
        
        let currentStage = 0;
        
        function updateProgress() {{
            if (currentStage < stages.length) {{
                const stage = stages[currentStage];
                progressFill.style.width = stage.progress + '%';
                progressText.textContent = stage.text;
                currentStage++;
                setTimeout(updateProgress, 2000);
            }}
        }}
        
        async function checkStatus() {{
            try {{
                const response = await fetch(`/status/${{runId}}`);
                const status = await response.json();
                
                if (status.stages.book_generated) {{
                    progressFill.style.width = '100%';
                    progressText.textContent = 'Готово! ✨';
                    
                    setTimeout(() => {{
                        document.querySelector('.progress-container').style.display = 'none';
                        document.querySelector('.heart-loading').style.display = 'none';
                        document.querySelector('.status-message').textContent = 'Романтическая книга создана с любовью! 💝';
                        resultContainer.style.display = 'block';
                        
                        if (status.files.html) {{
                            const viewBtn = document.createElement('a');
                            viewBtn.href = status.files.html;
                            viewBtn.className = 'download-btn btn-view';
                            viewBtn.textContent = 'Просмотреть книгу 👀';
                            viewBtn.target = '_blank';
                            downloadButtons.appendChild(viewBtn);
                        }}
                        
                        if (status.files.pdf) {{
                            const downloadBtn = document.createElement('a');
                            downloadBtn.href = status.files.pdf;
                            downloadBtn.className = 'download-btn btn-download';
                            downloadBtn.textContent = 'Скачать PDF 💕';
                            downloadBtn.download = 'romantic_book.pdf';
                            downloadButtons.appendChild(downloadBtn);
                        }}
                    }}, 1000);
                }} else {{
                    setTimeout(checkStatus, 3000);
                }}
            }} catch (error) {{
                setTimeout(checkStatus, 5000);
            }}
        }}
        
        // Запускаем обновление прогресса и проверку статуса
        updateProgress();
        setTimeout(checkStatus, 5000);
    </script>
</body>
</html>
    """)
