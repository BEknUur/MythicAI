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
    """Генерирует креативную книгу с интересными историями и анализом фотографий"""
    
    # Анализируем соотношение подписчиков/подписок для характеристики
    followers_ratio = "сбалансированный"
    personality_type = "загадочная личность"
    
    if analysis['followers'] > analysis['following'] * 5:
        followers_ratio = "звезда"
        personality_type = "харизматичный лидер"
    elif analysis['followers'] > analysis['following'] * 2:
        followers_ratio = "популярный"
        personality_type = "вдохновляющая личность"
    elif analysis['following'] > analysis['followers'] * 2:
        followers_ratio = "активный исследователь"
        personality_type = "любознательная натура"
    
    # Анализируем фотографии для контекста
    photo_analysis = analyze_photos_for_story(images, analysis)
    
    # Создаем богатый контекст для ИИ
    context = f"""
    === ПРОФИЛЬ ГЕРОЯ ===
    Имя: @{analysis['username']} ({analysis['full_name']})
    Девиз: "{analysis['bio']}"
    Цифры: {analysis['followers']} подписчиков, {analysis['following']} подписок
    Типаж: {personality_type} ({followers_ratio})
    
    === ГЕОГРАФИЯ ДУШИ ===
    Любимые места: {', '.join(analysis['locations'][:3]) if analysis['locations'] else 'таинственные локации'}
    
    === ЦИФРОВЫЕ СЛЕДЫ ===
    Стиль постов: {len(analysis['post_details'])} историй рассказано
    Последние мысли: {analysis['captions'][:2] if analysis['captions'] else ['скрытые размышления']}
    
    === ВИЗУАЛЬНЫЙ АНАЛИЗ ===
    {photo_analysis}
    """
    
    prompts = {
        "title": f"""
        Ты - мастер литературных названий. Создай поэтическое, загадочное название для книги-портрета о @{analysis['username']}.
        
        ВДОХНОВЕНИЕ:
        - Личность: {personality_type}
        - Суть: {analysis['bio'][:50] if analysis['bio'] else 'загадочная натура'}
        
        СТИЛЬ: Как у классиков - "Портрет Дориана Грея", "Незнакомка", "Душа в цифрах"
        
        Ответь ТОЛЬКО названием на русском языке, максимум 5 слов.
        """,
        
        "opening": f"""
        Ты - талантливый писатель-наблюдатель. Напиши завораживающее начало книги (3-4 абзаца) о случайной встрече с @{analysis['username']} в цифровом пространстве.
        
        ТВОЯ РОЛЬ: Цифровой антрополог, который изучает души через экраны
        
        РАССКАЖИ:
        🎭 Как в бескрайнем океане Instagram ты наткнулся на этот профиль
        ✨ Что именно зацепило - первое фото, взгляд, атмосфера?
        🔍 Почему решил копнуть глубже и написать целую книгу
        💫 Какая тайна скрывается за обычными постами?
        
        КОНТЕКСТ: {context}
        
        СТИЛЬ: Пиши как Паустовский - лирично, но с интригой. Каждое предложение должно тянуть читать дальше.
        """,
        
        "first_impression": f"""
        Ты - искусствовед и психолог в одном лице. Проанализируй визуальный мир @{analysis['username']} (3-4 абзаца).
        
        ТВОЙ ВЗГЛЯД ПРОФЕССИОНАЛА:
        🎨 Композиция кадров - что выдает характер?
        🌈 Цветовая палитра - какие эмоции преобладают?
        👁️ Взгляды и позы - что говорят о внутреннем мире?
        🏃‍♀️ Динамика или статика - темперамент личности?
        📸 Стиль съемки - спонтанность или продуманность?
        
        АНАЛИЗ ФОТОГРАФИЙ: {photo_analysis}
        
        КОНТЕКСТ: {context}
        
        СТИЛЬ: Пиши как профессиональный искусствовед, который видит душу через объектив. Красиво, умно, проникновенно.
        """,
        
        "story_from_photo": f"""
        Ты - мастер микроновелл. Выбери одну фотографию @{analysis['username']} и создай вокруг неё трогательную историю (3-4 абзаца).
        
        СОЗДАЙ ИСТОРИЮ:
        ⏰ За 10 минут ДО снимка - что происходило?
        💫 Секунда кадра - какие мысли, эмоции?
        🌊 Через час ПОСЛЕ - как изменилась жизнь?
        
        ДЕТАЛИ ДЛЯ ВДОХНОВЕНИЯ:
        📍 Место: {analysis['locations'][0] if analysis['locations'] else 'загадочная локация'}
        💭 Контекст: {analysis['post_details'][0] if analysis['post_details'] else 'момент из жизни'}
        🎭 Настроение: {photo_analysis[:100]}...
        
        СТИЛЬ: Как у О. Генри - короткая, но глубокая история с неожиданным поворотом. Читатель должен почувствовать себя свидетелем чужой жизни.
        """,
        
        "social_analysis": f"""
        Ты - цифровой социолог. Расскажи о @{analysis['username']} как о явлении современного мира (3-4 абзаца).
        
        АНАЛИЗИРУЙ КАК ЭКСПЕРТ:
        📊 Цифры {analysis['followers']} ↔ {analysis['following']} - что это говорит о личности?
        🤝 Стиль коммуникации - лидер, наблюдатель, вдохновитель?
        🌐 Роль в цифровом обществе - кто этот человек для своей аудитории?
        💡 Влияние на других - какой след оставляет?
        
        ТИП ЛИЧНОСТИ: {personality_type}
        СОЦИАЛЬНЫЙ ПОРТРЕТ: {followers_ratio}
        
        СТИЛЬ: Как статья в National Geographic - научно, но увлекательно. Раскрой социальные механизмы через конкретную личность.
        """,
        
        "hidden_story": f"""
        Ты - детектив человеческих душ. Создай интригующую историю о том, что скрывается за кадром у @{analysis['username']} (3-4 абзаца).
        
        РАСКРОЙ ТАЙНЫ:
        🎭 Какая личность скрывается за публичным образом?
        🚪 Что происходит в моменты между постами?
        💭 Какие мечты не попадают в ленту?
        🌙 Какие секреты хранит приватность?
        
        УЛИКИ ДЛЯ ДЕТЕКТИВА:
        📝 Био: "{analysis['bio']}"
        💬 Намеки в постах: {analysis['captions'][:2] if analysis['captions'] else ['скрытые смыслы']}
        🕵️ Визуальные подсказки: {photo_analysis[:150]}...
        
        СТИЛЬ: Как у Агаты Кристи - интригующе, но деликатно. Строй догадки, а не обвинения. Пусть читатель сам додумает.
        """,
        
        "philosophical_thoughts": f"""
        Ты - современный философ. Размысли о природе цифрового существования через призму @{analysis['username']} (3-4 абзаца).
        
        ФИЛОСОФСКИЕ ВОПРОСЫ:
        🤔 Что значит "быть собой" в эпоху Instagram?
        📱 Как селфи меняют самосознание?
        🌐 Парадокс близости: тысячи подписчиков, но одинок ли человек?
        ⏳ Как цифровое бессмертие влияет на смысл жизни?
        
        ПОВОД ДЛЯ РАЗМЫШЛЕНИЙ:
        Профиль @{analysis['username']} как зеркало современности
        
        СТИЛЬ: Как эссе Умберто Эко - глубоко, но доступно. Философия через конкретный пример. Заставь читателя задуматься о себе.
        """,
        
        "final_portrait": f"""
        Ты - портретист душ. Создай финальный, трогательный портрет @{analysis['username']} (3-4 абзаца) как прощание с новым другом.
        
        СОЗДАЙ ЖИВОЙ ПОРТРЕТ:
        💖 Что узнал о человеке за время наблюдения?
        🎨 Какой образ сложился в воображении?
        ✨ Чем этот человек обогатил твой мир?
        🌟 Какие пожелания для будущего пути?
        
        ИТОГИ ПУТЕШЕСТВИЯ:
        {context}
        
        СТИЛЬ: Как письмо близкому другу - тепло, искренне, с благодарностью. Пусть читатель почувствует, что и он подружился с героем книги.
        """
    }
    
    # Генерируем контент
    content = {}
    for section, prompt in prompts.items():
        print(f"📝 Генерируем раздел: {section}")
        content[section] = generate_text(prompt, max_tokens=1200)
    
    return content

def analyze_photos_for_story(images: list[Path], analysis: dict) -> str:
    """Анализирует фотографии для создания контекста истории"""
    if not images:
        return "Фотографии скрыты от посторонних глаз, что само по себе говорит о характере"
    
    photo_count = len(images)
    
    # Базовый анализ по количеству и данным профиля
    visual_style = []
    
    if photo_count > 10:
        visual_style.append("богатая визуальная история")
    elif photo_count > 5:
        visual_style.append("тщательно отобранные моменты")
    else:
        visual_style.append("избирательность в публикациях")
    
    # Анализируем локации
    locations = analysis.get('locations', [])
    if len(locations) > 3:
        visual_style.append("любитель путешествий")
    elif len(locations) > 1:
        visual_style.append("исследователь новых мест")
    else:
        visual_style.append("ценит привычную обстановку")
    
    # Анализируем активность постов
    posts_count = len(analysis.get('post_details', []))
    if posts_count > 15:
        visual_style.append("активный рассказчик")
    elif posts_count > 5:
        visual_style.append("вдумчивый куратор контента")
    else:
        visual_style.append("минималист в самовыражении")
    
    return f"Визуальный мир из {photo_count} кадров: {', '.join(visual_style)}. Каждая фотография - окно в душу, где свет и тени рассказывают больше, чем слова."

def create_realistic_book_html(content: dict, analysis: dict, images: list[Path]) -> str:
    """Создает HTML реалистичной книги с настоящим книжным дизайном"""
    
    # Выбираем лучшие изображения и конвертируем их в base64 с разными стилями
    selected_images = images[:8] if len(images) >= 8 else images
    
    # Стили для фотографий
    photo_styles = ["vintage", "bw", "soft", "dramatic", "original", "vintage", "soft", "bw"]
    
    # Создаем главное фото для обложки
    cover_image = ""
    if selected_images:
        cover_image = convert_image_to_base64(selected_images[0], max_size=(400, 400), style="dramatic")
    
    # Создаем галерею с разными стилями
    photo_gallery = ""
    photo_descriptions = [
        "Мгновение, застывшее во времени",
        "Взгляд сквозь призму воспоминаний", 
        "Место, где живут мечты",
        "Улыбка, которая греет душу",
        "Тень прошлого в настоящем",
        "Свет, что освещает путь",
        "Момент истинной красоты",
        "История, рассказанная без слов"
    ]
    
    frame_styles = ["polaroid", "classic", "modern", "vintage", "gallery", "polaroid", "classic", "modern"]
    
    for i, img in enumerate(selected_images):
        style = photo_styles[i] if i < len(photo_styles) else "original"
        frame_style = frame_styles[i] if i < len(frame_styles) else "classic"
        desc = photo_descriptions[i] if i < len(photo_descriptions) else f"Момент {i+1}"
        
        img_base64 = convert_image_to_base64(img, max_size=(600, 450), style=style)
        if img_base64:
            photo_gallery += f"""
            <div class="photo-page">
                <div class="photo-frame {frame_style}">
                    <img src="{img_base64}" alt="Фотография {i+1}" class="book-photo" />
                    <p class="photo-story">{desc}</p>
                    <div class="photo-number">#{i+1}</div>
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
            @import url('https://fonts.googleapis.com/css2?family=Libre+Baskerville:ital,wght@0,400;0,700;1,400&family=Crimson+Text:ital,wght@0,400;0,600;1,400&family=Dancing+Script:wght@400;700&display=swap');
            
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
                --silver-color: #c0c0c0;
                --sepia-color: #704214;
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
            
            /* Обложка с фото */
            .cover {{
                background: linear-gradient(135deg, #1a1a1a 0%, #2c1810 30%, #5d4e37 70%, #8b4513 100%);
                color: var(--gold-color);
                padding: 60px 50px;
                text-align: center;
                position: relative;
                border-radius: 8px 8px 0 0;
                min-height: 700px;
                display: flex;
                flex-direction: column;
                justify-content: center;
                align-items: center;
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
                border: 3px solid var(--gold-color);
                border-radius: 8px;
                opacity: 0.7;
            }}
            
            .cover-photo {{
                width: 200px;
                height: 200px;
                object-fit: cover;
                border-radius: 50%;
                border: 6px solid var(--gold-color);
                box-shadow: 
                    0 0 30px rgba(212, 175, 55, 0.3),
                    inset 0 0 20px rgba(0,0,0,0.2);
                margin-bottom: 30px;
                position: relative;
                z-index: 2;
            }}
            
            .book-title {{
                font-family: 'Crimson Text', serif;
                font-size: 3.5em;
                font-weight: 700;
                margin-bottom: 20px;
                text-shadow: 3px 3px 10px rgba(0,0,0,0.8);
                position: relative;
                z-index: 2;
                line-height: 1.1;
                letter-spacing: 2px;
            }}
            
            .book-subtitle {{
                font-size: 1.6em;
                font-style: italic;
                opacity: 0.9;
                position: relative;
                z-index: 2;
                margin-bottom: 30px;
                font-family: 'Dancing Script', cursive;
            }}
            
            .book-author {{
                font-size: 1.2em;
                font-weight: 400;
                position: relative;
                z-index: 2;
                border-top: 2px solid var(--gold-color);
                padding-top: 25px;
                margin-top: 40px;
                opacity: 0.9;
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
                font-size: 2.4em;
                color: var(--accent-color);
                text-align: center;
                margin-bottom: 40px;
                font-weight: 600;
                position: relative;
                padding-bottom: 20px;
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
            
            /* НОВЫЕ СТИЛИ ДЛЯ ФОТОГРАФИЙ */
            .photo-page {{
                display: flex;
                align-items: center;
                justify-content: center;
                min-height: 700px;
                padding: 40px 20px;
            }}
            
            .photo-frame {{
                position: relative;
                max-width: 500px;
                text-align: center;
                transition: transform 0.3s ease;
            }}
            
            /* Поляроид стиль */
            .photo-frame.polaroid {{
                background: white;
                padding: 20px 20px 60px 20px;
                border-radius: 2px;
                box-shadow: 
                    0 20px 40px rgba(0,0,0,0.2),
                    0 6px 20px rgba(0,0,0,0.15);
                transform: rotate(-2deg);
            }}
            
            .photo-frame.polaroid:nth-child(even) {{
                transform: rotate(2deg);
            }}
            
            /* Классическая рамка */
            .photo-frame.classic {{
                background: linear-gradient(45deg, #d4af37, #ffd700);
                padding: 25px;
                border-radius: 8px;
                box-shadow: 
                    0 15px 35px rgba(0,0,0,0.3),
                    inset 0 0 20px rgba(255,255,255,0.2);
                transform: rotate(-1deg);
            }}
            
            .photo-frame.classic .book-photo {{
                border: 5px solid white;
            }}
            
            /* Современная рамка */
            .photo-frame.modern {{
                background: linear-gradient(135deg, #2c3e50, #34495e);
                padding: 15px;
                border-radius: 15px;
                box-shadow: 
                    0 25px 50px rgba(0,0,0,0.25),
                    0 0 0 1px rgba(255,255,255,0.1);
                transform: rotate(1deg);
            }}
            
            .photo-frame.modern .book-photo {{
                border-radius: 10px;
            }}
            
            /* Винтажная рамка */
            .photo-frame.vintage {{
                background: linear-gradient(45deg, #8b4513, #a0522d);
                padding: 30px;
                border-radius: 4px;
                box-shadow: 
                    0 20px 40px rgba(139, 69, 19, 0.4),
                    inset 0 0 30px rgba(0,0,0,0.3);
                transform: rotate(-1.5deg);
                position: relative;
            }}
            
            .photo-frame.vintage::before {{
                content: '';
                position: absolute;
                top: 15px;
                left: 15px;
                right: 15px;
                bottom: 15px;
                border: 2px solid var(--gold-color);
                opacity: 0.6;
            }}
            
            /* Галерейная рамка */
            .photo-frame.gallery {{
                background: white;
                padding: 40px;
                border: 1px solid #ddd;
                box-shadow: 
                    0 10px 30px rgba(0,0,0,0.1),
                    0 0 0 8px white,
                    0 0 0 9px #ddd;
                transform: rotate(0deg);
            }}
            
            .book-photo {{
                width: 100%;
                max-width: 400px;
                height: 300px;
                object-fit: cover;
                border-radius: 4px;
                display: block;
                transition: all 0.3s ease;
            }}
            
            .photo-story {{
                font-family: 'Crimson Text', serif;
                font-style: italic;
                color: var(--accent-color);
                margin-top: 20px;
                font-size: 1.2em;
                line-height: 1.4;
                max-width: 300px;
                margin-left: auto;
                margin-right: auto;
            }}
            
            .photo-number {{
                position: absolute;
                top: -10px;
                right: -10px;
                background: var(--gold-color);
                color: white;
                width: 30px;
                height: 30px;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 0.9em;
                font-weight: bold;
                box-shadow: 0 4px 8px rgba(0,0,0,0.2);
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
            <!-- Страница 1: Обложка с фото -->
            <div class="cover">
                {f'<img src="{cover_image}" alt="Главное фото" class="cover-photo" />' if cover_image else ''}
                <h1 class="book-title">{content.get('title', 'Цифровые мемуары')}</h1>
                <p class="book-subtitle">Портрет современной души</p>
                <p class="book-author">Из записок цифрового антрополога</p>
            </div>
            
            <!-- Страница 2: Герой книги -->
            <div class="page">
                <div class="page-number">2</div>
                <div class="hero-profile">
                    <h3>Герой нашей истории</h3>
                    <p style="font-size: 1.3em; margin: 20px 0;"><strong>@{analysis['username']}</strong></p>
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
            
            <!-- Страницы 5-12: Стильная фотогалерея -->
            {photo_gallery}
            
            <!-- Страница: История из фото -->
            <div class="page">
                <div class="page-number">{13 if len(selected_images) >= 8 else 5 + len(selected_images)}</div>
                <h2 class="chapter-title">История одного кадра</h2>
                <div class="chapter-content">
                    <p>{content.get('story_from_photo', 'Глядя на эту фотографию, я придумал историю...')}</p>
                </div>
            </div>
            
            <!-- Страница: Социальный анализ -->
            <div class="page">
                <div class="page-number">{14 if len(selected_images) >= 8 else 6 + len(selected_images)}</div>
                <h2 class="chapter-title">Цифровая личность</h2>
                <div class="chapter-content">
                    <p>{content.get('social_analysis', 'Анализируя активность в социальных сетях...')}</p>
                </div>
            </div>
            
            <!-- Страница: Скрытая история -->
            <div class="page">
                <div class="page-number">{15 if len(selected_images) >= 8 else 7 + len(selected_images)}</div>
                <h2 class="chapter-title">Между строк</h2>
                <div class="chapter-content">
                    <p>{content.get('hidden_story', 'За публичным образом скрывается...')}</p>
                </div>
                <div class="ornament">❦ ❦ ❦</div>
                <div class="quote">
                    "{analysis.get('bio', 'Каждый человек - это целая вселенная, скрытая за несколькими фотографиями.')}"
                </div>
            </div>
            
            <!-- Финальная страница -->
            <div class="page final-page">
                <div class="page-number">{16 if len(selected_images) >= 8 else 8 + len(selected_images)}</div>
                <h2 class="chapter-title">Прощальный портрет</h2>
                <div class="chapter-content">
                    <p>{content.get('final_portrait', 'Завершая наше знакомство...')}</p>
                </div>
                <div class="ornament">✦ ✦ ✦</div>
                <div class="book-end">
                    <p>Конец истории о @{analysis['username']}</p>
                    <p style="margin-top: 20px; font-size: 0.9em;">Создано с любовью к человеческим историям</p>
                    <p style="margin-top: 10px; font-size: 0.8em; opacity: 0.7;">🎨 Фотографии обработаны в стиле арт-книги</p>
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

def convert_image_to_base64(image_path: Path, max_size: tuple = (800, 600), style: str = "original") -> str:
    """Конвертирует изображение в base64 с применением стилей для PDF"""
    try:
        with Image.open(image_path) as img:
            # Конвертируем в RGB если нужно
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Изменяем размер с сохранением пропорций
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            # Применяем стили
            if style == "vintage":
                # Винтажный стиль
                enhancer = ImageEnhance.Color(img)
                img = enhancer.enhance(0.7)  # Уменьшаем насыщенность
                enhancer = ImageEnhance.Contrast(img)
                img = enhancer.enhance(1.2)  # Увеличиваем контраст
                # Добавляем сепию
                pixels = img.load()
                for y in range(img.height):
                    for x in range(img.width):
                        r, g, b = pixels[x, y]
                        tr = int(0.393 * r + 0.769 * g + 0.189 * b)
                        tg = int(0.349 * r + 0.686 * g + 0.168 * b)
                        tb = int(0.272 * r + 0.534 * g + 0.131 * b)
                        pixels[x, y] = (min(255, tr), min(255, tg), min(255, tb))
                        
            elif style == "bw":
                # Черно-белый с легким контрастом
                img = img.convert('L').convert('RGB')
                enhancer = ImageEnhance.Contrast(img)
                img = enhancer.enhance(1.3)
                
            elif style == "soft":
                # Мягкий, теплый стиль
                enhancer = ImageEnhance.Brightness(img)
                img = enhancer.enhance(1.1)
                enhancer = ImageEnhance.Color(img)
                img = enhancer.enhance(0.9)
                img = img.filter(ImageFilter.GaussianBlur(radius=0.5))
                
            elif style == "dramatic":
                # Драматичный стиль
                enhancer = ImageEnhance.Contrast(img)
                img = enhancer.enhance(1.4)
                enhancer = ImageEnhance.Brightness(img)
                img = enhancer.enhance(0.9)
                enhancer = ImageEnhance.Color(img)
                img = enhancer.enhance(1.2)
            
            # Конвертируем в base64
            buffer = BytesIO()
            img.save(buffer, format='JPEG', quality=85, optimize=True)
            img_str = base64.b64encode(buffer.getvalue()).decode()
            return f"data:image/jpeg;base64,{img_str}"
            
    except Exception as e:
        print(f"❌ Ошибка при обработке изображения {image_path}: {e}")
        return ""
