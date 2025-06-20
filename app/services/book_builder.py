import json
import base64
from io import BytesIO
from pathlib import Path
from PIL import Image, ImageFilter, ImageEnhance
from app.services.llm_client import generate_text
from weasyprint import HTML, CSS

def analyze_profile_data(posts_data: list) -> dict:
    """Анализирует данные профиля для создания контекста книги"""
    if not posts_data:
        return {}
    
    profile = posts_data[0]
    posts = profile.get("latestPosts", [])
    
    analysis = {
        "username": profile.get("username", "Unknown"),
        "full_name": profile.get("fullName", ""),
        "bio": profile.get("biography", ""),
        "followers": profile.get("followersCount", 0),
        "following": profile.get("followsCount", 0),
        "posts_count": len(posts),
        "verified": profile.get("verified", False),
        "profile_pic": profile.get("profilePicUrl", ""),
        "locations": [],
        "captions": [],
        "hashtags": set(),
        "mentions": set(),
        "post_details": []
    }
    
    # Собираем детальную информацию о постах
    for post in posts:
        post_info = {
            "caption": post.get("caption", ""),
            "location": post.get("locationName", ""),
            "likes": post.get("likesCount", 0),
            "comments": post.get("commentsCount", 0),
            "type": post.get("type", ""),
            "alt": post.get("alt", ""),
            "timestamp": post.get("timestamp", "")
        }
        analysis["post_details"].append(post_info)
        
        if post.get("locationName"):
            analysis["locations"].append(post["locationName"])
        
        if post.get("caption"):
            analysis["captions"].append(post["caption"])
        
        analysis["hashtags"].update(post.get("hashtags", []))
        analysis["mentions"].update(post.get("mentions", []))
    
    return analysis

def build_romantic_book(run_id: str, images: list[Path], texts: str):
    """Создание романтической книги-подарка"""
    try:
        # Загружаем данные профиля
        run_dir = Path("data") / run_id
        posts_json = run_dir / "posts.json"
        images_dir = run_dir / "images"
        
        if posts_json.exists():
            posts_data = json.loads(posts_json.read_text(encoding="utf-8"))
        else:
            posts_data = []
        
        # Ждем загрузки изображений и собираем их
        actual_images = []
        if images_dir.exists():
            # Собираем все изображения из папки
            for img_file in sorted(images_dir.glob("*")):
                if img_file.suffix.lower() in ['.jpg', '.jpeg', '.png', '.webp']:
                    actual_images.append(img_file)
        
        print(f"💕 Создаем романтическую книгу для профиля")
        print(f"📸 Найдено {len(actual_images)} прекрасных фотографий в {images_dir}")
        
        # Анализируем профиль
        analysis = analyze_profile_data(posts_data)
        
        # Генерируем романтический контент
        romantic_content = generate_romantic_content(analysis, actual_images)
        
        # Создаем HTML в романтическом стиле
        html = create_romantic_book_html(romantic_content, analysis, actual_images)
        
        # Сохраняем HTML и PDF
        out = Path("data") / run_id
        out.mkdir(parents=True, exist_ok=True)
        
        # Сохраняем HTML файл
        html_file = out / "book.html"
        html_file.write_text(html, encoding="utf-8")
        
        # Создаем PDF
        try:
            print("📄 Создаем PDF версию романтической книги...")
            
            # Простой CSS для PDF
            pdf_css = CSS(string="""
                @page {
                    size: A4;
                    margin: 1.5cm;
                    background: #f8f5f0;
                }
                .romantic-page {
                    page-break-before: always;
                }
                .cover-page {
                    page-break-after: always;
                }
                body {
                    background: #f8f5f0 !important;
                }
            """)
            
            # Создаем PDF
            pdf_doc = HTML(string=html)
            pdf_doc.write_pdf(str(out / "book.pdf"), stylesheets=[pdf_css])
            
            print(f"✅ Романтическая книга создана: {out / 'book.pdf'}")
            print(f"💕 HTML версия: {out / 'book.html'}")
            
        except Exception as pdf_error:
            print(f"❌ Ошибка при создании PDF: {pdf_error}")
            print(f"💕 Доступна HTML версия: {out / 'book.html'}")
        
    except Exception as e:
        print(f"❌ Ошибка при создании романтической книги: {e}")
        # Создаем базовую версию
        try:
            basic_html = f"""
            <html>
            <head>
                <title>Книга Любви</title>
                <style>
                    body {{ background: linear-gradient(135deg, #ff9a9e 0%, #fecfef 100%); 
                           font-family: Arial, sans-serif; padding: 20px; }}
                    .error {{ background: white; padding: 20px; border-radius: 10px; text-align: center; }}
                </style>
            </head>
            <body>
                <div class="error">
                    <h1>💕 Романтическая Книга</h1>
                    <p>Извините, произошла ошибка при создании книги: {e}</p>
                    <p>Попробуйте еще раз позже ❤️</p>
                </div>
            </body>
            </html>
            """
            out = Path("data") / run_id
            out.mkdir(parents=True, exist_ok=True)
            
            html_file = out / "book.html"
            html_file.write_text(basic_html, encoding="utf-8")
            
            print(f"✅ Создана базовая версия: {out / 'book.html'}")
            
        except Exception as final_error:
            print(f"❌ Критическая ошибка: {final_error}")

def generate_romantic_content(analysis: dict, images: list[Path]) -> dict:
    """Генерирует романтический контент для книги"""
    
    username = analysis.get('username', 'Неизвестный')
    full_name = analysis.get('full_name', username)
    bio = analysis.get('bio', 'Прекрасная душа')
    followers = analysis.get('followers', 0)
    following = analysis.get('following', 0)
    posts_count = analysis.get('posts_count', 0)
    
    # Создаем универсальный романтический контекст без гендерных предположений
    context = f"""
    === ГЕРОЙ/ГЕРОИНЯ НАШЕЙ ИСТОРИИ ===
    Имя: @{username} ({full_name})
    О себе: "{bio}"
    Популярность: {followers:,} людей восхищаются этой личностью
    Подписки: {following:,} избранных аккаунтов
    Публикаций: {posts_count} моментов жизни
    
    === РОМАНТИЧЕСКИЕ ДЕТАЛИ ===
    Фотографий: {len(images)} моментов счастья
    Места: {', '.join(analysis.get('locations', [])[:3]) if analysis.get('locations') else 'волшебные уголки мира'}
    """
    
    # Промпты для романтического контента (универсальные)
    prompts = {
        "title": f"""
        Ты создаешь романтическую книгу-подарок о @{username}. 
        Придумай элегантное романтическое название для книги о красоте и восхищении.
        
        СТИЛЬ: Изысканно, поэтично, универсально
        ПРИМЕРЫ: "Ода красоте", "Портрет души", "Звезда моя"
        
        Ответь ТОЛЬКО названием, максимум 4 слова.
        """,
        
        "romantic_intro": f"""
        Ты создаешь романтическую книгу о @{username}.
        Напиши изысканное вступление (4-5 абзацев) как истинный ценитель красоты.
        
        РАССКАЖИ УНИВЕРСАЛЬНО:
        ✨ Как среди миллионов людей выделяется именно эта особенная личность
        🌟 Что делает этого человека исключительным и прекрасным
        💎 Как каждая деталь говорит об утончённости души
        📖 Почему этот человек достоин книги-посвящения
        
        КОНТЕКСТ: {context}
        
        СТИЛЬ: Галантно, изысканно, как в исторических романах. Используй красивые метафоры.
        """,
        
        "stats_admiration": f"""
        Ты восхищаешься популярностью @{username}.
        Напиши элегантный анализ социального влияния (3 абзаца).
        
        ВОСХИТИСЬ ЦИФРАМИ:
        👑 {followers:,} подписчиков - целая армия поклонников
        📱 {posts_count} публикаций - галерея моментов красоты
        🌟 Как эти цифры отражают харизму и магнетизм
        
        СТИЛЬ: Восхищённо, как ценитель таланта оценивает влияние в обществе.
        """,
        
        "beauty_details": f"""
        Ты - поэт и ценитель красоты. Опиши прекрасные качества @{username} как произведение искусства (4 абзаца).
        
        ВОСПЕВАЙ ДЕТАЛИ:
        👁️ Взгляд - что в нём читается?
        😊 Улыбка - как она преображает пространство?
        💫 Стиль - как выбираются образы?
        ✨ Естественность - что делает живым?
        
        КОНТЕКСТ: {context}
        
        СТИЛЬ: Поэтично, как ценитель искусства описывает шедевр.
        """,
        
        "lifestyle_admiration": f"""
        Создай восхищённый рассказ о стиле жизни @{username} (4 абзаца).
        
        ВОСХИТИСЬ ОБРАЗОМ ЖИЗНИ:
        🌍 Места, которые выбираются для посещения
        📸 Моменты, которые считаются важными
        🎨 Эстетика мира этого человека
        💝 Что это говорит о характере
        
        СТИЛЬ: Как ценитель утончённости восхищается образом жизни.
        """,
        
        "photo_stories": f"""
        Создай 15 коротких поэтических подписей к фотографиям @{username} 
        (по 1-2 предложения каждая).
        
        СОЗДАЙ ПОДПИСИ:
        💖 Каждая фотография - стихотворение в кадре
        ✨ Мгновения, достойные картинной галереи
        🌸 Естественная грация в каждом движении
        😍 Кадры, которые останавливают время
        
        Напиши 15 подписей, разделенных символом "|". Например:
        "Взгляд, который пишет стихи в душе | Улыбка, затмевающая рассвет | ..."
        """,
        
        "romantic_wishes": f"""
        Напиши романтические пожелания для @{username} (4 абзаца).
        
        ПОЖЕЛАЙ С ЛЮБОВЬЮ:
        🌟 Чтобы красота всегда сияла
        💖 Чтобы жизнь дарила только лучшее
        🦋 Чтобы мечты становились реальностью
        🌺 Чтобы всегда знать свою ценность
        
        СТИЛЬ: Искренне, с пожеланиями счастья.
        """,
        
        "final_dedication": f"""
        Напиши финальное посвящение для @{username} (3-4 абзаца).
        
        ЗАВЕРШИ ЭЛЕГАНТНО:
        💕 Благодарность за вдохновение
        🌟 Признание исключительности
        ✨ Уверенность в прекрасном будущем
        💝 Подпись от всего сердца
        
        СТИЛЬ: Торжественно и трогательно, как посвящение в книге.
        """
    }
    
    # Генерируем весь контент
    content = {}
    for key, prompt in prompts.items():
        print(f"💕 Создаем {key}...")
        generated_text = generate_text(prompt, max_tokens=1000)
        
        if generated_text is None or generated_text == "":
            # Резервный романтический текст
            fallback_texts = {
                "title": "Ода Твоей Красоте",
                "romantic_intro": f"В мире, где красота стала редкостью, @{username} сияет как драгоценный бриллиант. Каждая публикация - это произведение искусства, каждый взгляд - поэзия, каждая улыбка - мелодия для души. Как истинный ценитель прекрасного, я не мог не создать эту книгу-посвящение удивительному человеку, который умеет быть собой в мире масок.",
                "stats_admiration": f"Цифры говорят сами за себя: {followers:,} человек выбрали следить за этой жизнью. Это не просто подписчики - это свидетели красоты, ценители искусства жить красиво. {posts_count} публикаций создают галерею моментов, каждый из которых достоин восхищения.",
                "beauty_details": f"Красота @{username} многогранна, как драгоценный камень. В этом взгляде читается глубина океана, в улыбке - тепло солнца. Умение быть элегантным и естественным одновременно - это истинное искусство.",
                "lifestyle_admiration": f"Стиль жизни @{username} отражает утончённую натуру. Места, которые выбираются, моменты, которые считаются важными - всё говорит о человеке с изысканным вкусом и глубоким пониманием красоты.",
                "photo_stories": "Мгновение совершенства | Взгляд, пишущий стихи | Улыбка, дарящая надежду | Естественность как искусство | Красота без фильтров | Момент чистой радости | Элегантность в движении | Свет в глазах | Грация в каждом жесте | Искренность как украшение | Красота изнутри | Кадр для вечности | Поэзия момента | Совершенство в простоте | Магия обычного дня",
                "romantic_wishes": f"Желаю @{username} всегда оставаться таким же искренним и прекрасным. Пусть жизнь дарит только самые яркие краски, а каждый день приносит новые поводы для улыбки. Пусть красота души всегда находит отражение в окружающем мире.",
                "final_dedication": f"Эта книга - скромная дань восхищения исключительному человеку. @{username}, спасибо за то, что делаешь мир ярче своим присутствием. Пусть эти страницы напоминают о том, какой ты особенный. С глубоким уважением и восхищением."
            }
            generated_text = fallback_texts.get(key, "Прекрасные слова о замечательном человеке")
        
        content[key] = generated_text
    
    return content

def create_romantic_book_html(content: dict, analysis: dict, images: list[Path]) -> str:
    """Создает HTML для романтической книги"""
    
    username = analysis.get('username', 'Неизвестный')
    full_name = analysis.get('full_name', username)
    followers = analysis.get('followers', 0)
    following = analysis.get('following', 0)
    posts_count = analysis.get('posts_count', 0)
    bio = analysis.get('bio', '')
    verified = analysis.get('verified', False)
    
    # Конвертируем изображения в base64 (если есть)
    image_data = []
    for i, img_path in enumerate(images[:15]):  # Максимум 15 фотографий
        if img_path.exists():
            base64_img = convert_image_to_base64(img_path, style="romantic")
            if base64_img:
                image_data.append(base64_img)
    
    print(f"💕 Обработано {len(image_data)} изображений для книги")
    
    # Получаем подписи к фотографиям
    photo_stories = content.get('photo_stories', '').split('|') if content.get('photo_stories') else []
    default_captions = [
        "Мгновение совершенства",
        "Взгляд, пишущий стихи", 
        "Улыбка, дарящая надежду",
        "Естественность как искусство",
        "Красота без фильтров",
        "Момент чистой радости",
        "Элегантность в движении",
        "Свет в глазах",
        "Грация в каждом жесте",
        "Искренность как украшение",
        "Красота изнутри",
        "Кадр для вечности",
        "Поэзия момента",
        "Совершенство в простоте",
        "Магия обычного дня"
    ]
    
    # Создаем интегрированные страницы с фото и текстом (если есть фото)
    integrated_pages = ""
    
    if image_data:
        # Разбиваем фотографии на группы для страниц
        photos_per_page = 3
        for page_num in range(0, min(len(image_data), 15), photos_per_page):
            page_photos = image_data[page_num:page_num + photos_per_page]
            
            photo_gallery = ""
            for i, img_base64 in enumerate(page_photos):
                global_index = page_num + i
                caption = photo_stories[global_index].strip() if global_index < len(photo_stories) else default_captions[global_index % len(default_captions)]
                photo_gallery += f'''
                <div class="romantic-photo-frame">
                    <div class="photo-wrapper">
                        <img src="{img_base64}" alt="Прекрасный момент {global_index+1}">
                        <div class="photo-glow"></div>
                    </div>
                    <div class="photo-caption">{caption}</div>
                    <div class="frame-ornament">❦</div>
                </div>
                '''
            
            # Выбираем текст для страницы
            if page_num == 0:
                page_text = content.get('beauty_details', 'Красота в каждой детали...')
                page_title = "Портрет Души"
            elif page_num == 3:
                page_text = content.get('lifestyle_admiration', 'Стиль жизни как искусство...')
                page_title = "Эстетика Жизни"
            elif page_num == 6:
                page_text = content.get('romantic_wishes', 'Пожелания от всего сердца...')
                page_title = "Мечты и Пожелания"
            else:
                page_text = "Каждый момент, запечатлённый в этих кадрах, говорит о красоте души и утончённости вкуса. Эти фотографии - не просто снимки, а окна в мир полный гармонии и эстетики."
                page_title = "Моменты Красоты"
            
            integrated_pages += f'''
            <div class="romantic-page integrated-page">
                <div class="page-background"></div>
                <h2 class="page-title">{page_title}</h2>
                <div class="integrated-content">
                    <div class="text-section">
                        <div class="romantic-text">{page_text}</div>
                        <div class="text-ornament">✧ ✦ ✧</div>
                    </div>
                    <div class="photos-section">
                        {photo_gallery}
                    </div>
                </div>
            </div>
            '''
    else:
        # Если нет фото, создаем текстовые страницы
        text_pages = [
            ("Портрет Души", content.get('beauty_details', 'Красота души проявляется в каждом жесте, каждом взгляде, каждом слове. Это особенный человек, который умеет находить прекрасное в обычном и делиться этой красотой с миром.')),
            ("Эстетика Жизни", content.get('lifestyle_admiration', 'Стиль жизни говорит о человеке больше, чем слова. Выбор моментов, которые считаются важными, места, которые притягивают - всё это создаёт портрет утончённой души.')),
            ("Мечты и Пожелания", content.get('romantic_wishes', 'Пусть каждый день приносит новые поводы для радости, пусть мечты находят своё воплощение, а красота души всегда находит отражение в окружающем мире.'))
        ]
        
        for page_title, page_text in text_pages:
            integrated_pages += f'''
            <div class="romantic-page text-only-page">
                <div class="page-background"></div>
                <h2 class="page-title">{page_title}</h2>
                <div class="romantic-text">{page_text}</div>
                <div class="decorative-element">✧ ✦ ✧</div>
            </div>
            '''
    
    # Создаем HTML
    html = f"""
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{content.get('title', 'Ода Твоей Красоте')}</title>
        <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,700;1,400&family=Dancing+Script:wght@400;700&family=Libre+Baskerville:wght@400;700&family=Great+Vibes&display=swap" rel="stylesheet">
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            
            body {{
                font-family: 'Libre Baskerville', serif;
                line-height: 1.8;
                color: #2d1b14;
                background: 
                    linear-gradient(135deg, #fdf6f0 0%, #f8f2e4 25%, #f5ede0 50%, #f2e8dc 75%, #f0e5d8 100%),
                    radial-gradient(circle at 20% 80%, rgba(218, 165, 32, 0.1) 0%, transparent 50%),
                    radial-gradient(circle at 80% 20%, rgba(139, 69, 19, 0.1) 0%, transparent 50%);
                min-height: 100vh;
                position: relative;
            }}
            
            body::before {{
                content: '';
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><circle cx="10" cy="20" r="1" fill="rgba(218,165,32,0.1)"/><circle cx="90" cy="80" r="1.5" fill="rgba(139,69,19,0.1)"/><circle cx="30" cy="70" r="0.8" fill="rgba(218,165,32,0.1)"/><circle cx="70" cy="30" r="1.2" fill="rgba(139,69,19,0.1)"/></svg>') repeat;
                pointer-events: none;
                z-index: 0;
            }}
            
            .book-container {{
                max-width: 1000px;
                margin: 0 auto;
                background: 
                    linear-gradient(135deg, #fefdfb 0%, #faf7f2 100%),
                    radial-gradient(circle at 50% 50%, rgba(255,255,255,0.8) 0%, transparent 70%);
                box-shadow: 
                    inset 0 0 0 1px rgba(218, 165, 32, 0.3),
                    inset 0 0 0 8px #f5f0e8,
                    inset 0 0 0 16px rgba(139, 69, 19, 0.1),
                    0 0 0 4px #e8dcc8,
                    0 0 0 8px rgba(139, 69, 19, 0.2),
                    0 30px 80px rgba(45, 27, 20, 0.4);
                min-height: 100vh;
                position: relative;
                border: 3px solid #d4c4a8;
                z-index: 1;
            }}
            
            .book-container::before {{
                content: '';
                position: absolute;
                top: 20px;
                left: 20px;
                right: 20px;
                bottom: 20px;
                border: 2px double #daa520;
                border-radius: 12px;
                pointer-events: none;
                z-index: 0;
            }}
            
            .romantic-page {{
                padding: 80px 60px;
                min-height: 100vh;
                display: flex;
                flex-direction: column;
                justify-content: center;
                position: relative;
                page-break-after: always;
                z-index: 2;
            }}
            
            .page-background {{
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: 
                    radial-gradient(circle at 10% 90%, rgba(218, 165, 32, 0.05) 0%, transparent 40%),
                    radial-gradient(circle at 90% 10%, rgba(139, 69, 19, 0.05) 0%, transparent 40%);
                pointer-events: none;
                z-index: -1;
            }}
            
            .cover-page {{
                background: 
                    linear-gradient(135deg, #8b4513 0%, #a0522d 25%, #cd853f 50%, #daa520 75%, #b8860b 100%),
                    radial-gradient(circle at 30% 70%, rgba(255,255,255,0.1) 0%, transparent 50%);
                color: #fefdfb;
                text-align: center;
                position: relative;
                overflow: hidden;
            }}
            
            .cover-page::before {{
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200"><path d="M100 20 L120 60 L80 60 Z" fill="rgba(255,255,255,0.05)"/><path d="M50 100 L70 140 L30 140 Z" fill="rgba(255,255,255,0.03)"/><path d="M150 100 L170 140 L130 140 Z" fill="rgba(255,255,255,0.03)"/></svg>') repeat;
                animation: sparkle 20s linear infinite;
                pointer-events: none;
            }}
            
            @keyframes sparkle {{
                0% {{ transform: translateX(0) translateY(0); }}
                100% {{ transform: translateX(-200px) translateY(-200px); }}
            }}
            
            .cover-page::after {{
                content: '';
                position: absolute;
                top: 40px;
                left: 40px;
                right: 40px;
                bottom: 40px;
                border: 4px double #ffd700;
                border-radius: 16px;
                box-shadow: 
                    inset 0 0 0 8px rgba(255,215,0,0.3),
                    0 0 30px rgba(255,215,0,0.5);
                pointer-events: none;
                z-index: 1;
            }}
            
            .cover-title {{
                font-family: 'Playfair Display', serif;
                font-size: 4.8em;
                font-weight: 700;
                margin-bottom: 30px;
                text-shadow: 
                    3px 3px 0px rgba(0,0,0,0.3),
                    6px 6px 10px rgba(0,0,0,0.2),
                    0 0 20px rgba(255,215,0,0.5);
                position: relative;
                z-index: 2;
                letter-spacing: 3px;
                background: linear-gradient(45deg, #fff, #ffd700, #fff);
                -webkit-background-clip: text;
                background-clip: text;
                -webkit-text-fill-color: transparent;
                filter: drop-shadow(2px 2px 4px rgba(0,0,0,0.3));
            }}
            
            .cover-subtitle {{
                font-family: 'Great Vibes', cursive;
                font-size: 2.8em;
                margin-bottom: 40px;
                opacity: 0.95;
                position: relative;
                z-index: 2;
                text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
            }}
            
            .cover-names {{
                font-family: 'Playfair Display', serif;
                font-size: 1.8em;
                margin-top: 60px;
                position: relative;
                z-index: 2;
            }}
            
            .verified-badge {{
                display: inline-block;
                background: linear-gradient(45deg, #ffd700, #ffed4e);
                color: #8b4513;
                padding: 6px 15px;
                border-radius: 20px;
                font-size: 0.7em;
                margin-left: 12px;
                vertical-align: middle;
                font-weight: bold;
                box-shadow: 0 4px 15px rgba(255,215,0,0.4);
                border: 2px solid rgba(255,255,255,0.3);
            }}
            
            .stats-page {{
                background: linear-gradient(135deg, 
                    rgba(254, 253, 251, 0.95) 0%, 
                    rgba(248, 242, 228, 0.8) 25%,
                    rgba(245, 237, 224, 0.9) 75%,
                    rgba(240, 229, 216, 0.95) 100%);
                text-align: center;
                position: relative;
            }}
            
            .stats-container {{
                display: grid;
                grid-template-columns: repeat(3, 1fr);
                gap: 50px;
                margin: 60px 0;
            }}
            
            .stat-item {{
                background: 
                    linear-gradient(135deg, #fefdfb 0%, #f8f5f0 100%),
                    radial-gradient(circle at 50% 50%, rgba(218,165,32,0.1) 0%, transparent 70%);
                padding: 50px 25px;
                border-radius: 20px;
                box-shadow: 
                    0 0 0 3px rgba(218, 165, 32, 0.2),
                    0 15px 40px rgba(139, 69, 19, 0.3),
                    inset 0 0 20px rgba(255,255,255,0.8);
                transition: all 0.4s ease;
                border: 2px solid rgba(218, 165, 32, 0.3);
                position: relative;
                overflow: hidden;
            }}
            
            .stat-item::before {{
                content: '';
                position: absolute;
                top: -2px;
                left: -2px;
                right: -2px;
                bottom: -2px;
                background: linear-gradient(45deg, #daa520, #8b4513, #daa520);
                border-radius: 20px;
                z-index: -1;
                opacity: 0;
                transition: opacity 0.4s ease;
            }}
            
            .stat-item:hover {{
                transform: translateY(-12px) scale(1.02);
                box-shadow: 
                    0 0 0 3px rgba(218, 165, 32, 0.4),
                    0 25px 60px rgba(139, 69, 19, 0.4),
                    inset 0 0 30px rgba(255,255,255,0.9);
            }}
            
            .stat-item:hover::before {{
                opacity: 1;
            }}
            
            .stat-number {{
                font-family: 'Playfair Display', serif;
                font-size: 3.5em;
                font-weight: 700;
                color: #8b4513;
                margin-bottom: 15px;
                text-shadow: 1px 1px 3px rgba(0,0,0,0.1);
                position: relative;
                z-index: 1;
            }}
            
            .stat-label {{
                font-family: 'Dancing Script', cursive;
                font-size: 1.6em;
                color: #a0522d;
                text-transform: capitalize;
                font-weight: 600;
                position: relative;
                z-index: 1;
            }}
            
            .bio-section {{
                background: 
                    linear-gradient(135deg, rgba(254, 253, 251, 0.95) 0%, rgba(248, 245, 240, 0.8) 100%),
                    radial-gradient(circle at 30% 70%, rgba(218,165,32,0.1) 0%, transparent 60%);
                padding: 40px;
                border-radius: 20px;
                margin: 50px 0;
                border-left: 6px solid #daa520;
                font-style: italic;
                font-size: 1.4em;
                color: #2d1b14;
                box-shadow: 
                    0 10px 30px rgba(139, 69, 19, 0.2),
                    inset 0 0 20px rgba(255,255,255,0.7);
                position: relative;
            }}
            
            .bio-section::before {{
                content: '"';
                font-family: 'Playfair Display', serif;
                font-size: 4em;
                color: rgba(218, 165, 32, 0.3);
                position: absolute;
                top: -10px;
                left: 20px;
                line-height: 1;
            }}
            
            .bio-section::after {{
                content: '"';
                font-family: 'Playfair Display', serif;
                font-size: 4em;
                color: rgba(218, 165, 32, 0.3);
                position: absolute;
                bottom: -30px;
                right: 20px;
                line-height: 1;
            }}
            
            .page-title {{
                font-family: 'Playfair Display', serif;
                font-size: 4em;
                color: #8b4513;
                text-align: center;
                margin-bottom: 60px;
                font-weight: 700;
                position: relative;
                text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
            }}
            
            .page-title::before {{
                content: '';
                position: absolute;
                top: -20px;
                left: 50%;
                transform: translateX(-50%);
                width: 80px;
                height: 4px;
                background: linear-gradient(90deg, transparent, #daa520, transparent);
                border-radius: 2px;
            }}
            
            .page-title::after {{
                content: '';
                position: absolute;
                bottom: -25px;
                left: 50%;
                transform: translateX(-50%);
                width: 120px;
                height: 3px;
                background: linear-gradient(90deg, transparent, #daa520, transparent);
                border-radius: 2px;
            }}
            
            .romantic-text {{
                font-family: 'Libre Baskerville', serif;
                font-size: 1.4em;
                line-height: 2;
                text-align: justify;
                color: #2d1b14;
                margin-bottom: 30px;
                text-indent: 3em;
                position: relative;
            }}
            
            .romantic-text::first-letter {{
                font-family: 'Playfair Display', serif;
                font-size: 3.5em;
                font-weight: 700;
                float: left;
                line-height: 0.8;
                margin: 8px 8px 0 0;
                color: #8b4513;
                text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
            }}
            
            .integrated-page {{
                background: linear-gradient(135deg, 
                    rgba(254, 253, 251, 0.98) 0%, 
                    rgba(250, 247, 242, 0.95) 50%,
                    rgba(245, 240, 235, 0.98) 100%);
            }}
            
            .text-only-page {{
                background: linear-gradient(135deg, 
                    rgba(254, 253, 251, 0.98) 0%, 
                    rgba(248, 245, 240, 0.95) 100%);
                text-align: center;
            }}
            
            .integrated-content {{
                display: grid;
                grid-template-columns: 1.3fr 0.7fr;
                gap: 60px;
                align-items: start;
            }}
            
            .text-section {{
                padding-right: 30px;
                position: relative;
            }}
            
            .text-ornament {{
                text-align: center;
                font-size: 2.2em;
                color: #daa520;
                margin: 40px 0;
                letter-spacing: 15px;
                opacity: 0.7;
            }}
            
            .photos-section {{
                display: flex;
                flex-direction: column;
                gap: 35px;
                position: relative;
            }}
            
            .romantic-photo-frame {{
                position: relative;
                background: 
                    linear-gradient(135deg, #fefdfb 0%, #f8f5f0 100%);
                padding: 20px;
                border-radius: 15px;
                box-shadow: 
                    0 0 0 4px rgba(218, 165, 32, 0.2),
                    0 0 0 8px rgba(255, 255, 255, 0.8),
                    0 0 0 12px rgba(218, 165, 32, 0.1),
                    0 20px 40px rgba(139, 69, 19, 0.3);
                transition: all 0.5s ease;
                border: 3px solid rgba(218, 165, 32, 0.3);
                overflow: hidden;
            }}
            
            .romantic-photo-frame::before {{
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: 
                    linear-gradient(45deg, transparent 30%, rgba(255,215,0,0.1) 50%, transparent 70%),
                    radial-gradient(circle at 20% 80%, rgba(218,165,32,0.1) 0%, transparent 50%);
                pointer-events: none;
                z-index: 1;
            }}
            
            .romantic-photo-frame:hover {{
                transform: translateY(-8px) scale(1.02);
                box-shadow: 
                    0 0 0 4px rgba(218, 165, 32, 0.4),
                    0 0 0 8px rgba(255, 255, 255, 0.9),
                    0 0 0 12px rgba(218, 165, 32, 0.2),
                    0 30px 60px rgba(139, 69, 19, 0.4);
            }}
            
            .photo-wrapper {{
                position: relative;
                border-radius: 10px;
                overflow: hidden;
                z-index: 2;
            }}
            
            .photo-wrapper img {{
                width: 100%;
                height: 220px;
                object-fit: cover;
                border-radius: 10px;
                display: block;
                filter: sepia(5%) saturate(1.1) brightness(1.05);
                transition: all 0.4s ease;
            }}
            
            .romantic-photo-frame:hover .photo-wrapper img {{
                filter: sepia(8%) saturate(1.2) brightness(1.1);
                transform: scale(1.02);
            }}
            
            .photo-glow {{
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: 
                    radial-gradient(circle at 30% 30%, rgba(255,215,0,0.1) 0%, transparent 50%),
                    linear-gradient(135deg, rgba(255,255,255,0.1) 0%, transparent 50%);
                pointer-events: none;
                opacity: 0;
                transition: opacity 0.4s ease;
            }}
            
            .romantic-photo-frame:hover .photo-glow {{
                opacity: 1;
            }}
            
            .photo-caption {{
                padding: 15px 5px;
                font-family: 'Dancing Script', cursive;
                font-size: 1.3em;
                color: #8b4513;
                text-align: center;
                font-weight: 600;
                position: relative;
                z-index: 2;
                min-height: 50px;
                display: flex;
                align-items: center;
                justify-content: center;
            }}
            
            .frame-ornament {{
                position: absolute;
                bottom: 5px;
                right: 15px;
                font-size: 1.5em;
                color: rgba(218, 165, 32, 0.5);
                z-index: 2;
            }}
            
            .intro-page {{
                background: linear-gradient(135deg, 
                    rgba(254, 253, 251, 0.95) 0%, 
                    rgba(248, 245, 240, 0.9) 50%,
                    rgba(245, 237, 224, 0.95) 100%);
            }}
            
            .quote-page {{
                background: 
                    linear-gradient(135deg, #8b4513 0%, #a0522d 25%, #cd853f 50%, #daa520 75%, #b8860b 100%),
                    radial-gradient(circle at 70% 30%, rgba(255,255,255,0.1) 0%, transparent 50%);
                color: #fefdfb;
                text-align: center;
                position: relative;
                overflow: hidden;
            }}
            
            .quote-page::before {{
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><circle cx="20" cy="30" r="1" fill="rgba(255,255,255,0.1)"/><circle cx="80" cy="70" r="1.5" fill="rgba(255,255,255,0.1)"/><circle cx="50" cy="20" r="0.8" fill="rgba(255,255,255,0.1)"/></svg>') repeat;
                animation: twinkle 15s ease-in-out infinite;
                pointer-events: none;
            }}
            
            @keyframes twinkle {{
                0%, 100% {{ opacity: 0.3; }}
                50% {{ opacity: 0.8; }}
            }}
            
            .quote-page::after {{
                content: '';
                position: absolute;
                top: 60px;
                left: 60px;
                right: 60px;
                bottom: 60px;
                border: 3px solid rgba(255, 215, 0, 0.6);
                border-radius: 12px;
                box-shadow: 
                    inset 0 0 0 8px rgba(255,215,0,0.2),
                    0 0 40px rgba(255,215,0,0.4);
                pointer-events: none;
                z-index: 1;
            }}
            
            .quote-text {{
                font-family: 'Playfair Display', serif;
                font-size: 3.8em;
                font-weight: 700;
                margin-bottom: 50px;
                text-shadow: 
                    3px 3px 0px rgba(0,0,0,0.3),
                    6px 6px 15px rgba(0,0,0,0.2);
                position: relative;
                z-index: 2;
                line-height: 1.3;
                font-style: italic;
            }}
            
            .final-page {{
                background: linear-gradient(135deg, 
                    rgba(254, 253, 251, 0.98) 0%, 
                    rgba(248, 245, 240, 0.95) 50%,
                    rgba(245, 237, 224, 0.98) 100%);
                text-align: center;
            }}
            
            .final-message {{
                font-family: 'Libre Baskerville', serif;
                font-size: 1.5em;
                line-height: 2;
                margin-bottom: 50px;
                color: #2d1b14;
                text-align: justify;
                text-indent: 3em;
            }}
            
            .signature {{
                font-family: 'Great Vibes', cursive;
                font-size: 3.2em;
                color: #8b4513;
                margin-top: 60px;
                text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
            }}
            
            .decorative-element {{
                font-size: 2.5em;
                color: #daa520;
                margin: 50px 0;
                text-align: center;
                letter-spacing: 25px;
                opacity: 0.8;
            }}
            
            .ornament {{
                text-align: center;
                font-size: 3em;
                color: #daa520;
                margin: 40px 0;
                filter: drop-shadow(2px 2px 4px rgba(0,0,0,0.1));
            }}
            
            @media print {{
                body {{ background: #fefdfb !important; }}
                .romantic-page {{ page-break-after: always; }}
                .page-background {{ display: none; }}
            }}
            
            @media (max-width: 768px) {{
                .romantic-page {{ padding: 40px 25px; }}
                .cover-title {{ font-size: 3.2em; }}
                .page-title {{ font-size: 2.8em; }}
                .integrated-content {{ grid-template-columns: 1fr; gap: 40px; }}
                .stats-container {{ grid-template-columns: 1fr; gap: 30px; }}
                .romantic-text {{ font-size: 1.2em; text-indent: 2em; }}
                .photo-wrapper img {{ height: 180px; }}
            }}
        </style>
    </head>
    <body>
        <div class="book-container">
            
            <!-- Обложка -->
            <div class="romantic-page cover-page">
                <h1 class="cover-title">{content.get('title', 'Ода Твоей Красоте')}</h1>
                <div class="ornament">❦ ❧ ❦</div>
                <p class="cover-subtitle">Романтическое посвящение</p>
                <div class="cover-names">
                    <p style="font-size: 2.4em; font-weight: 600;">@{username}</p>
                    <p style="margin-top: 25px; font-size: 1.8em; opacity: 0.95;">
                        {full_name}
                        {f'<span class="verified-badge">✓ Verified</span>' if verified else ''}
                    </p>
                </div>
            </div>
            
            <!-- Статистика профиля -->
            <div class="romantic-page stats-page">
                <div class="page-background"></div>
                <h2 class="page-title">Цифры Восхищения</h2>
                <div class="stats-container">
                    <div class="stat-item">
                        <div class="stat-number">{followers:,}</div>
                        <div class="stat-label">Поклонников</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-number">{posts_count}</div>
                        <div class="stat-label">Моментов</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-number">{following:,}</div>
                        <div class="stat-label">Избранных</div>
                    </div>
                </div>
                {f'<div class="bio-section">{bio}</div>' if bio else ''}
                <div class="romantic-text">
                    {content.get('stats_admiration', 'Цифры говорят сами за себя...')}
                </div>
            </div>
            
            <!-- Романтическое вступление -->
            <div class="romantic-page intro-page">
                <div class="page-background"></div>
                <h2 class="page-title">Ода Красоте</h2>
                <div class="romantic-text">
                    {content.get('romantic_intro', 'Прекрасные слова о встрече...')}
                </div>
                <div class="ornament">✧ ✦ ✧</div>
            </div>
            
            <!-- Интегрированные страницы с фото и текстом или только текст -->
            {integrated_pages}
            
            <!-- Цитата -->
            <div class="romantic-page quote-page">
                <div class="quote-text">"Красота - язык, понятный всем"</div>
                <div class="ornament">❦</div>
                <p style="font-size: 1.6em; opacity: 0.95; font-style: italic; position: relative; z-index: 2;">Ральф Эмерсон</p>
            </div>
            
            <!-- Финальная страница -->
            <div class="romantic-page final-page">
                <div class="page-background"></div>
                <h2 class="page-title">Посвящение</h2>
                <div class="final-message">
                    {content.get('final_dedication', 'Финальное послание восхищения...')}
                </div>
                <div class="signature">
                    С искренним восхищением ❤
                </div>
                <div style="font-style: italic; color: #8b4513; margin-top: 40px; font-size: 1.2em;">
                    Создано с любовью специально для тебя
                </div>
                <div class="ornament">❦ ❧ ❦</div>
            </div>
            
        </div>
    </body>
    </html>
    """
    
    return html

def convert_image_to_base64(image_path: Path, max_size: tuple = (600, 400), style: str = "original") -> str:
    """Конвертирует изображение в base64 с применением романтических стилей"""
    try:
        if not image_path.exists():
            print(f"❌ Файл изображения не найден: {image_path}")
            return ""
            
        with Image.open(image_path) as img:
            print(f"📸 Обрабатываем изображение: {image_path.name}")
            
            # Конвертируем в RGB если нужно
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Изменяем размер с сохранением пропорций
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            # Применяем романтические стили
            if style == "romantic":
                # Винтажный романтический стиль
                enhancer = ImageEnhance.Color(img)
                img = enhancer.enhance(1.15)  # Больше цвета для романтики
                enhancer = ImageEnhance.Brightness(img)
                img = enhancer.enhance(1.08)  # Светлее для мягкости
                enhancer = ImageEnhance.Contrast(img)
                img = enhancer.enhance(1.05)  # Мягкий контраст
                # Очень легкое размытие для винтажности
                img = img.filter(ImageFilter.GaussianBlur(radius=0.2))
                
            # Конвертируем в base64
            buffer = BytesIO()
            img.save(buffer, format='JPEG', quality=85, optimize=True)
            img_str = base64.b64encode(buffer.getvalue()).decode()
            print(f"✅ Изображение {image_path.name} успешно обработано")
            return f"data:image/jpeg;base64,{img_str}"
            
    except Exception as e:
        print(f"❌ Ошибка при обработке изображения {image_path}: {e}")
        return ""
