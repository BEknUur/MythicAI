import json
from pathlib import Path
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
        "locations": [],
        "captions": [],
        "hashtags": set(),
        "mentions": set(),
        "post_details": []
    }
    
    # Собираем детальную информацию о постах для анализа
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

def generate_creative_book(analysis: dict, images: list[Path]) -> dict:
    """Генерирует креативную книгу с интересными историями"""
    
    # Анализируем соотношение подписчиков/подписок для характеристики
    followers_ratio = "сбалансированный"
    if analysis['followers'] > analysis['following'] * 2:
        followers_ratio = "популярный"
    elif analysis['following'] > analysis['followers'] * 2:
        followers_ratio = "активный исследователь"
    
    # Создаем контекст для ИИ
    context = f"""
    Профиль: @{analysis['username']} - {analysis['full_name']}
    Биография: {analysis['bio']}
    Подписчики: {analysis['followers']}, Подписки: {analysis['following']} ({followers_ratio})
    Локации: {analysis['locations'][:2] if analysis['locations'] else ['Неизвестно']}
    Недавние посты: {len(analysis['post_details'])} шт.
    
    Детали постов для анализа:
    {analysis['post_details'][:3]}
    """
    
    prompts = {
        "title": f"""
        Создай интригующее название для мемуарной книги о @{analysis['username']}.
        Название должно быть поэтичным и загадочным, отражать суть личности.
        Примеры стиля: "Портрет незнакомца", "Между кадрами", "Цифровые следы души"
        Ответь только название на русском.
        """,
        
        "opening": f"""
        Напиши увлекательное открытие книги (2-3 абзаца), где я как автор-наблюдатель объясняю:
        - Как случайно наткнулся на профиль @{analysis['username']} в бескрайнем интернете
        - Что меня зацепило с первого взгляда
        - Почему решил написать об этом человеке целую книгу
        
        Контекст: {context}
        
        Пиши живо, с интригой, как начало детективного романа.
        """,
        
        "first_impression": f"""
        Опиши мои первые впечатления от фотографий (2-3 абзаца):
        - Что сразу бросается в глаза в манере фотографироваться
        - Какую атмосферу создает этот человек
        - Мои догадки о характере по фотографиям
        
        Контекст: {context}
        
        Пиши как профессиональный фотограф, анализирующий работы коллеги.
        """,
        
        "story_from_photo": f"""
        Глядя на одну из фотографий, я придумываю короткую историю (2-3 абзаца):
        - Что происходило ДО того, как был сделан снимок
        - Какие эмоции испытывал человек в тот момент  
        - Что случилось ПОСЛЕ съемки
        
        Локация: {analysis['locations'][0] if analysis['locations'] else 'неизвестное место'}
        Детали: {analysis['post_details'][0] if analysis['post_details'] else 'обычное фото'}
        
        Пиши как увлекательную новеллу, основанную на одном кадре.
        """,
        
        "social_analysis": f"""
        Анализирую социальную активность (2-3 абзаца):
        - Что говорит соотношение {analysis['followers']} подписчиков к {analysis['following']} подпискам
        - Стиль общения и взаимодействия с аудиторией  
        - Роль в цифровом сообществе
        
        Тип личности: {followers_ratio}
        
        Пиши как социальный психолог, изучающий поведение в сети.
        """,
        
        "hidden_story": f"""
        Создай загадочную историю "между строк" (2-3 абзаца):
        - Что скрывается за публичным образом
        - Какие тайны могут хранить непоказанные моменты
        - Мои домыслы о настоящей жизни за кадром
        
        Биография: {analysis['bio']}
        Намеки из постов: {analysis['captions'][:2]}
        
        Пиши интригующе, как детективную историю.
        """,
        
        "philosophical_thoughts": f"""
        Философские размышления о цифровой эпохе (2-3 абзаца):
        - Как Instagram меняет способ рассказывать о себе
        - Что означает "быть собой" в эпоху соцсетей
        - Парадоксы близости и отдаленности в цифровом мире
        
        Повод для размышлений: профиль @{analysis['username']}
        
        Пиши глубоко и мудро, как философ современности.
        """,
        
        "final_portrait": f"""
        Создай финальный портрет героя книги (2-3 абзаца):
        - Что я понял об этом человеке за время наблюдения
        - Какой образ сложился в моем воображении
        - Пожелания и напутствие незнакомому другу
        
        Итоги наблюдения: {context}
        
        Пиши тепло и проникновенно, как прощание с близким человеком.
        """
    }
    
    # Генерируем контент
    content = {}
    for section, prompt in prompts.items():
        content[section] = generate_text(prompt, max_tokens=900)
    
    return content

def create_realistic_book_html(content: dict, analysis: dict, images: list[Path]) -> str:
    """Создает HTML реалистичной книги с настоящим книжным дизайном"""
    
    # Выбираем лучшие изображения
    selected_images = images[:6] if len(images) >= 6 else images
    
    # Создаем галерею с описаниями
    photo_gallery = ""
    photo_descriptions = [
        "Мгновение, застывшее во времени",
        "Взгляд, полный историй", 
        "Место, где остались воспоминания",
        "Улыбка, которая говорит больше слов",
        "Тень прошлого в настоящем",
        "Свет, освещающий душу"
    ]
    
    for i, img in enumerate(selected_images):
        desc = photo_descriptions[i] if i < len(photo_descriptions) else f"Момент {i+1}"
        photo_gallery += f"""
        <div class="photo-page">
            <div class="photo-frame">
                <img src="{img}" alt="Фотография {i+1}" class="book-photo" />
                <p class="photo-story">{desc}</p>
            </div>
        </div>
        """
    
    html = f"""
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{content.get('title', 'Цифровые мемуары')}</title>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Libre+Baskerville:ital,wght@0,400;0,700;1,400&family=Crimson+Text:ital,wght@0,400;0,600;1,400&display=swap');
            
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            
            :root {{
                --paper-color: #faf8f3;
                --ink-color: #2c1810;
                --accent-color: #8b4513;
                --shadow-color: rgba(44, 24, 16, 0.1);
                --gold-color: #d4af37;
            }}
            
            body {{
                font-family: 'Libre Baskerville', serif;
                background: linear-gradient(135deg, #f5f5dc 0%, #e6e6dc 100%);
                margin: 0;
                padding: 20px;
                color: var(--ink-color);
                line-height: 1.6;
            }}
            
            .book-container {{
                max-width: 800px;
                margin: 0 auto;
                background: var(--paper-color);
                box-shadow: 
                    0 0 50px var(--shadow-color),
                    inset 0 0 0 2px #e8e0d0,
                    0 0 0 1px #d0c8b8;
                border-radius: 8px;
                position: relative;
            }}
            
            .book-container::before {{
                content: '';
                position: absolute;
                top: -5px;
                left: -5px;
                right: -5px;
                bottom: -5px;
                background: linear-gradient(45deg, #c9b876, #d4c5a9);
                border-radius: 10px;
                z-index: -1;
            }}
            
            /* Обложка */
            .cover {{
                background: linear-gradient(135deg, #2c1810 0%, #5d4e37 50%, #8b4513 100%);
                color: var(--gold-color);
                padding: 80px 50px;
                text-align: center;
                position: relative;
                border-radius: 8px 8px 0 0;
                background-image: 
                    radial-gradient(circle at 20% 20%, rgba(212, 175, 55, 0.1) 0%, transparent 50%),
                    radial-gradient(circle at 80% 80%, rgba(212, 175, 55, 0.05) 0%, transparent 50%);
            }}
            
            .cover::after {{
                content: '';
                position: absolute;
                top: 30px;
                left: 30px;
                right: 30px;
                bottom: 30px;
                border: 2px solid var(--gold-color);
                border-radius: 4px;
                opacity: 0.6;
            }}
            
            .book-title {{
                font-family: 'Crimson Text', serif;
                font-size: 3.2em;
                font-weight: 700;
                margin-bottom: 20px;
                text-shadow: 2px 2px 8px rgba(0,0,0,0.7);
                position: relative;
                z-index: 1;
                line-height: 1.1;
                letter-spacing: 1px;
            }}
            
            .book-subtitle {{
                font-size: 1.4em;
                font-style: italic;
                opacity: 0.9;
                position: relative;
                z-index: 1;
                margin-bottom: 30px;
            }}
            
            .book-author {{
                font-size: 1.1em;
                font-weight: 400;
                position: relative;
                z-index: 1;
                border-top: 1px solid var(--gold-color);
                padding-top: 20px;
                margin-top: 40px;
                opacity: 0.8;
            }}
            
            /* Страницы */
            .page {{
                padding: 60px 70px;
                min-height: 600px;
                border-bottom: 1px solid #e8e0d0;
                background: var(--paper-color);
                position: relative;
            }}
            
            .page:last-child {{
                border-bottom: none;
                border-radius: 0 0 8px 8px;
            }}
            
            .page::before {{
                content: '';
                position: absolute;
                left: 50px;
                top: 0;
                bottom: 0;
                width: 2px;
                background: linear-gradient(to bottom, transparent 60px, #e8e0d0 60px, #e8e0d0 calc(100% - 60px), transparent calc(100% - 60px));
            }}
            
            .page-number {{
                position: absolute;
                bottom: 30px;
                right: 50px;
                font-size: 0.9em;
                color: var(--accent-color);
                font-style: italic;
            }}
            
            .chapter-title {{
                font-family: 'Crimson Text', serif;
                font-size: 2.2em;
                color: var(--accent-color);
                text-align: center;
                margin-bottom: 40px;
                font-weight: 600;
                position: relative;
                padding-bottom: 15px;
            }}
            
            .chapter-title::after {{
                content: '◆ ◆ ◆';
                position: absolute;
                bottom: 0;
                left: 50%;
                transform: translateX(-50%);
                font-size: 0.4em;
                color: var(--gold-color);
                letter-spacing: 10px;
            }}
            
            .chapter-content {{
                font-size: 1.15em;
                line-height: 1.8;
                text-align: justify;
                hyphens: auto;
            }}
            
            .chapter-content p {{
                margin-bottom: 25px;
                text-indent: 2.5em;
            }}
            
            .chapter-content p:first-child {{
                text-indent: 0;
            }}
            
            .chapter-content p:first-child::first-letter {{
                font-family: 'Crimson Text', serif;
                font-size: 4.5em;
                font-weight: bold;
                float: left;
                line-height: 0.8;
                margin: 12px 12px 0 0;
                color: var(--accent-color);
                text-shadow: 2px 2px 4px var(--shadow-color);
            }}
            
            /* Профиль героя */
            .hero-profile {{
                background: linear-gradient(135deg, #f8f6f0, #f0ebe0);
                border: 2px solid var(--accent-color);
                border-radius: 12px;
                padding: 30px;
                margin: 40px 0;
                text-align: center;
                box-shadow: 0 8px 25px var(--shadow-color);
            }}
            
            .hero-profile h3 {{
                color: var(--accent-color);
                font-size: 1.5em;
                margin-bottom: 20px;
                font-family: 'Crimson Text', serif;
            }}
            
            .hero-stats {{
                display: grid;
                grid-template-columns: repeat(3, 1fr);
                gap: 20px;
                margin-top: 25px;
            }}
            
            .stat {{
                background: white;
                padding: 15px;
                border-radius: 8px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.05);
            }}
            
            .stat-number {{
                font-size: 1.8em;
                font-weight: bold;
                color: var(--accent-color);
                display: block;
                font-family: 'Crimson Text', serif;
            }}
            
            .stat-label {{
                font-size: 0.9em;
                color: #666;
                margin-top: 5px;
            }}
            
            /* Фотографии */
            .photo-page {{
                display: flex;
                align-items: center;
                justify-content: center;
                min-height: 500px;
            }}
            
            .photo-frame {{
                background: white;
                padding: 20px;
                border: 8px solid #e8e0d0;
                box-shadow: 
                    0 15px 35px var(--shadow-color),
                    inset 0 0 0 2px #f5f3ed;
                transform: rotate(-1deg);
                max-width: 400px;
                text-align: center;
            }}
            
            .photo-frame:nth-child(even) {{
                transform: rotate(1deg);
            }}
            
            .book-photo {{
                width: 100%;
                height: 300px;
                object-fit: cover;
                border-radius: 4px;
                filter: sepia(15%) contrast(1.05) brightness(1.02);
            }}
            
            .photo-story {{
                font-family: 'Crimson Text', serif;
                font-style: italic;
                color: var(--accent-color);
                margin-top: 15px;
                font-size: 1.1em;
                line-height: 1.4;
            }}
            
            /* Декоративные элементы */
            .ornament {{
                text-align: center;
                font-size: 1.8em;
                color: var(--gold-color);
                margin: 40px 0;
                letter-spacing: 15px;
            }}
            
            .quote {{
                font-family: 'Crimson Text', serif;
                font-style: italic;
                font-size: 1.3em;
                color: var(--accent-color);
                text-align: center;
                margin: 40px 0;
                padding: 30px;
                border-left: 4px solid var(--gold-color);
                background: linear-gradient(135deg, #f8f6f0, transparent);
                border-radius: 0 8px 8px 0;
            }}
            
            /* Финальная страница */
            .final-page {{
                background: linear-gradient(135deg, var(--paper-color), #f8f6f0);
                text-align: center;
                padding: 80px 50px;
            }}
            
            .book-end {{
                font-family: 'Crimson Text', serif;
                font-size: 1.2em;
                color: var(--accent-color);
                font-style: italic;
                margin-top: 40px;
            }}
        </style>
    </head>
    <body>
        <div class="book-container">
            <!-- Страница 1: Обложка -->
            <div class="cover">
                <h1 class="book-title">{content.get('title', 'Цифровые мемуары')}</h1>
                <p class="book-subtitle">Личные наблюдения незнакомца</p>
                <p class="book-author">Из записок цифрового антрополога</p>
            </div>
            
            <!-- Страница 2: Герой книги -->
            <div class="page">
                <div class="page-number">2</div>
                <div class="hero-profile">
                    <h3>Герой нашей истории</h3>
                    <p style="font-size: 1.2em; margin: 20px 0;"><strong>@{analysis['username']}</strong></p>
                    <p style="font-size: 1.1em; color: #666;">{analysis['full_name']}</p>
                    <p style="font-style: italic; margin: 20px 0; color: var(--accent-color);">"{analysis.get('bio', 'Человек, живущий свою жизнь')}"</p>
                    <div class="hero-stats">
                        <div class="stat">
                            <span class="stat-number">{analysis.get('followers', 0)}</span>
                            <span class="stat-label">подписчиков</span>
                        </div>
                        <div class="stat">
                            <span class="stat-number">{analysis.get('following', 0)}</span>
                            <span class="stat-label">подписок</span>
                        </div>
                        <div class="stat">
                            <span class="stat-number">{analysis.get('posts_count', 0)}</span>
                            <span class="stat-label">постов</span>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Страница 3: Открытие -->
            <div class="page">
                <div class="page-number">3</div>
                <h2 class="chapter-title">Случайная встреча</h2>
                <div class="chapter-content">
                    <p>{content.get('opening', 'В бескрайнем цифровом океане я наткнулся на удивительный профиль...')}</p>
                </div>
            </div>
            
            <!-- Страница 4: Первые впечатления -->
            <div class="page">
                <div class="page-number">4</div>
                <h2 class="chapter-title">Первый взгляд</h2>
                <div class="chapter-content">
                    <p>{content.get('first_impression', 'Первое что бросается в глаза...')}</p>
                </div>
            </div>
            
            <!-- Страница 5-6: Фотографии -->
            {photo_gallery}
            
            <!-- Страница 7: История из фото -->
            <div class="page">
                <div class="page-number">7</div>
                <h2 class="chapter-title">История одного кадра</h2>
                <div class="chapter-content">
                    <p>{content.get('story_from_photo', 'Глядя на эту фотографию, я придумал историю...')}</p>
                </div>
            </div>
            
            <!-- Страница 8: Социальный анализ -->
            <div class="page">
                <div class="page-number">8</div>
                <h2 class="chapter-title">Цифровая личность</h2>
                <div class="chapter-content">
                    <p>{content.get('social_analysis', 'Анализируя активность в социальных сетях...')}</p>
                </div>
            </div>
            
            <!-- Страница 9: Скрытая история -->
            <div class="page">
                <div class="page-number">9</div>
                <h2 class="chapter-title">Между строк</h2>
                <div class="chapter-content">
                    <p>{content.get('hidden_story', 'За публичным образом скрывается...')}</p>
                </div>
                <div class="ornament">❦ ❦ ❦</div>
                <div class="quote">
                    "{analysis.get('bio', 'Каждый человек - это целая вселенная, скрытая за несколькими фотографиями.')}"
                </div>
            </div>
            
            <!-- Страница 10: Финал -->
            <div class="page final-page">
                <div class="page-number">10</div>
                <h2 class="chapter-title">Прощальный портрет</h2>
                <div class="chapter-content">
                    <p>{content.get('final_portrait', 'Завершая наше знакомство...')}</p>
                </div>
                <div class="ornament">✦ ✦ ✦</div>
                <div class="book-end">
                    <p>Конец истории о @{analysis['username']}</p>
                    <p style="margin-top: 20px; font-size: 0.9em;">Создано с любовью к человеческим историям</p>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html

def build_book(run_id: str, images: list[Path], texts: str):
    """Создание реалистичной книги с интересным контентом"""
    try:
        # Загружаем данные профиля
        run_dir = Path("data") / run_id
        posts_json = run_dir / "posts.json"
        
        if posts_json.exists():
            posts_data = json.loads(posts_json.read_text(encoding="utf-8"))
        else:
            posts_data = []
        
        # Анализируем профиль
        analysis = analyze_profile_data(posts_data)
        
        # Генерируем креативную книгу
        content = generate_creative_book(analysis, images)
        
        # Создаем реалистичный HTML
        html = create_realistic_book_html(content, analysis, images)
        
        # Сохраняем HTML и PDF
        out = Path("data") / run_id
        out.mkdir(parents=True, exist_ok=True)
        
        # Сохраняем HTML файл
        html_file = out / "book.html"
        html_file.write_text(html, encoding="utf-8")
        
        # Создаем PDF с книжным CSS
        try:
            css = CSS(string="""
                @page {
                    size: A4;
                    margin: 1.5cm;
                }
                .page {
                    page-break-before: always;
                }
                .cover {
                    page-break-after: always;
                }
                .photo-page {
                    page-break-before: always;
                    page-break-after: auto;
                    page-break-inside: avoid;
                }
            """)
            
            # Создаем PDF
            html_doc = HTML(string=html)
            html_doc.write_pdf(str(out / "book.pdf"), stylesheets=[css])
            
            print(f"✅ Реалистичная книга создана: {out / 'book.pdf'}")
            print(f"📄 HTML версия: {out / 'book.html'}")
            
        except Exception as pdf_error:
            print(f"❌ Ошибка при создании PDF: {pdf_error}")
            # Создаем простую версию без CSS
            try:
                simple_html = HTML(string=html)
                simple_html.write_pdf(str(out / "book.pdf"))
                print(f"✅ Создана простая версия PDF: {out / 'book.pdf'}")
            except Exception as simple_error:
                print(f"❌ Не удалось создать PDF: {simple_error}")
                # Оставляем только HTML версию
                print(f"📄 Доступна только HTML версия: {out / 'book.html'}")
        
    except Exception as e:
        print(f"❌ Ошибка при создании книги: {e}")
        # Создаем базовую версию в случае ошибки
        try:
            basic_html = f"<html><body><h1>Цифровые мемуары</h1><p>Ошибка: {e}</p></body></html>"
            out = Path("data") / run_id
            out.mkdir(parents=True, exist_ok=True)
            
            # Сохраняем базовый HTML
            basic_html_file = out / "book.html"
            basic_html_file.write_text(basic_html, encoding="utf-8")
            
            # Пытаемся создать базовый PDF
            try:
                HTML(string=basic_html).write_pdf(str(out / "book.pdf"))
                print(f"✅ Создана базовая версия книги")
            except:
                print(f"📄 Создана только HTML версия: {out / 'book.html'}")
        except Exception as final_error:
            print(f"❌ Критическая ошибка: {final_error}")
