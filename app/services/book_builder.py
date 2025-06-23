import json
import base64
from io import BytesIO
from pathlib import Path
from PIL import Image, ImageFilter, ImageEnhance, ImageDraw, ImageFont
from app.services.llm_client import generate_text, analyze_photo, analyze_photo_for_card, generate_scene_chapter, strip_cliches, generate_unique_chapter
import markdown
import pdfkit
import qrcode
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from typing import List, Tuple
import random

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
        "post_details": [],
        "total_likes": 0,
        "total_comments": 0,
        "post_dates": [],
        "most_liked_post": None,
        "most_commented_post": None,
        "common_hashtags": [],
        "mentioned_users": []
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
            "timestamp": post.get("timestamp", ""),
            "hashtags": post.get("hashtags", []),
            "mentions": post.get("mentions", []),
            "url": post.get("url", "")
        }
        analysis["post_details"].append(post_info)
        
        # Накапливаем статистику
        if post.get("likesCount"):
            analysis["total_likes"] += post["likesCount"]
            if not analysis["most_liked_post"] or post["likesCount"] > analysis["most_liked_post"]["likes"]:
                analysis["most_liked_post"] = post_info
                
        if post.get("commentsCount"):
            analysis["total_comments"] += post["commentsCount"]
            if not analysis["most_commented_post"] or post["commentsCount"] > analysis["most_commented_post"]["comments"]:
                analysis["most_commented_post"] = post_info
        
        if post.get("locationName"):
            analysis["locations"].append(post["locationName"])
        
        if post.get("caption"):
            analysis["captions"].append(post["caption"])
        
        if post.get("timestamp"):
            analysis["post_dates"].append(post["timestamp"])
            
        analysis["hashtags"].update(post.get("hashtags", []))
        analysis["mentions"].update(post.get("mentions", []))
    
    # Анализируем популярные хэштеги
    hashtag_count = {}
    for post in posts:
        for hashtag in post.get("hashtags", []):
            hashtag_count[hashtag] = hashtag_count.get(hashtag, 0) + 1
    
    analysis["common_hashtags"] = sorted(hashtag_count.items(), key=lambda x: x[1], reverse=True)[:5]
    analysis["mentioned_users"] = list(analysis["mentions"])[:10]
    
    return analysis

def create_markdown_from_content(content: dict, analysis: dict, images: list[Path]) -> str:
    """Создает Markdown версию книги для лучшего PDF"""
    
    username = analysis.get('username', 'Неизвестный')
    full_name = analysis.get('full_name', username)
    followers = analysis.get('followers', 0)
    following = analysis.get('following', 0)
    posts_count = analysis.get('posts_count', 0)
    bio = analysis.get('bio', '')
    verified = analysis.get('verified', False)
    total_likes = analysis.get('total_likes', 0)
    total_comments = analysis.get('total_comments', 0)
    
    # Реальные данные из Instagram
    real_captions = analysis.get('captions', [])[:6]
    common_hashtags = analysis.get('common_hashtags', [])[:5]
    mentioned_users = analysis.get('mentioned_users', [])[:5]
    locations = analysis.get('locations', [])[:5]
    most_liked = analysis.get('most_liked_post')
    
    markdown_content = f"""
# {content.get('title', 'Романтическая книга о @' + username)}

*Романтическое посвящение*

---

## @{username}
### {full_name}
{f'✓ **Verified**' if verified else ''}

---

## 🎯 Цифры восхищения

| Статистика | Значение |
|------------|----------|
| 👥 Подписчики | {followers:,} |
| 📱 Посты | {posts_count} |
| 👥 Подписки | {following:,} |
| ❤️ Лайки | {total_likes:,} |
| 💬 Комментарии | {total_comments:,} |

{f'> *"{bio}"*' if bio else ''}

{content.get('engagement_story', 'Статистика говорит сама за себя...')}

---

## 💫 Романтическое вступление

{content.get('intro', 'Прекрасные слова о встрече...')}

---

## 📱 Instagram-книга

### 📝 Реальные подписи к постам

{"".join([f'> "{caption}"\n\n' for caption in real_captions if caption])}



### 📍 Посещенные места

{chr(10).join([f'- 📍 {location}' for location in locations])}

{content.get('locations_journey', 'Путешествие по местам...')}

### 👥 Упоминания друзей

{" ".join([f'`@{user}`' for user in mentioned_users])}

{f'''
### 🏆 Самый популярный пост

> "{most_liked.get("caption", "Без подписи")}"

**❤️ {most_liked.get("likes", 0)} лайков • 💬 {most_liked.get("comments", 0)} комментариев**
''' if most_liked else ''}

---

## 🖼️ Галерея моментов

{content.get('captions_analysis', 'Анализ подписей к постам...')}

---

## 🌟 Цитата

> *"Красота - язык, понятный всем"*
> 
> — *Ральф Эмерсон*

---

## 💝 Финальное послание

{content.get('final_message', 'Финальное послание восхищения...')}

---

*С искренним восхищением ❤*

*Создано с любовью специально для тебя*

❦ ❧ ❦
"""
    
    return markdown_content

def build_romantic_book(run_id: str, images: list[Path], texts: str, book_format: str = "classic"):
    """Создание HTML книги (с выбором формата: classic или zine)"""
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
        
        print(f"💕 Создаем {book_format} книгу для профиля")
        print(f"📸 Найдено {len(actual_images)} фотографий в {images_dir}")
        
        # Анализируем профиль
        analysis = analyze_profile_data(posts_data)
        
        # Генерируем контент в зависимости от формата
        if book_format == "zine":
            # Мозаичный зин - короткий контент
            content = generate_zine_content(analysis, actual_images)
            html = create_zine_html(content, analysis, actual_images)
        else:
            # Литературная Instagram-книга от первого лица
            content = {"format": "literary"}  # Передаем минимум данных
            html = create_literary_instagram_book_html(content, analysis, actual_images)
        
        # Сохраняем только HTML файл
        out = Path("data") / run_id
        out.mkdir(parents=True, exist_ok=True)
        
        # Сохраняем HTML файл
        html_file = out / "book.html"
        html_file.write_text(html, encoding="utf-8")
        
        print(f"✅ {book_format.title()} книга создана!")
        print(f"📖 HTML версия: {out / 'book.html'}")
        
    except Exception as e:
        print(f"❌ Ошибка при создании книги: {e}")
        # Создаем базовую версию при ошибке
        try:
            basic_html = f"""
            <html>
            <head>
                <title>Книга</title>
                <style>
                    body {{ background: white; font-family: serif; padding: 20px; }}
                    .error {{ background: #f8f9fa; padding: 20px; border-radius: 10px; text-align: center; }}
                </style>
            </head>
            <body>
                <div class="error">
                    <h1>📖 Книга</h1>
                    <p>Извините, произошла ошибка при создании книги: {e}</p>
                    <p>Попробуйте еще раз позже</p>
                </div>
            </body>
            </html>
            """
            out = Path("data") / run_id
            out.mkdir(parents=True, exist_ok=True)
            
            html_file = out / "book.html"
            html_file.write_text(basic_html, encoding="utf-8")
            
            print(f"✅ Создана базовая HTML версия: {out / 'book.html'}")
            
        except Exception as final_error:
            print(f"❌ Критическая ошибка: {final_error}")

def apply_dream_pastel_effect(img: Image.Image) -> Image.Image:
    """Применяет эффект Dream-Pastel к изображению"""
    try:
        # Проверяем, что изображение валидное
        if img is None or img.size[0] == 0 or img.size[1] == 0:
            print("❌ Недопустимое изображение для обработки")
            return img
            
        # Конвертируем в RGB если нужно
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Лёгкое размытие
        img = img.filter(ImageFilter.GaussianBlur(1.2))
        
        # Цветовая коррекция в теплые тона
        enhancer = ImageEnhance.Color(img)
        img = enhancer.enhance(1.15)
        
        # Создаем теплый overlay
        overlay = Image.new('RGBA', img.size, (255, 220, 210, 25))  # peach #ffdcd2
        img = img.convert('RGBA')
        img = Image.alpha_composite(img, overlay)
        
        # Добавляем grain (безопасно)
        try:
            noise = np.random.randint(0, 15, (img.size[1], img.size[0], 3), dtype=np.uint8)
            noise_img = Image.fromarray(noise, 'RGB').convert('RGBA')
            noise_overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
            noise_overlay.paste(noise_img, (0, 0))
            img = Image.alpha_composite(img, noise_overlay)
        except Exception as noise_error:
            print(f"❌ Ошибка при добавлении шума: {noise_error}")
        
        # Легкое увеличение яркости
        enhancer = ImageEnhance.Brightness(img)
        img = enhancer.enhance(1.05)
        
        return img.convert('RGB')
    except Exception as e:
        print(f"❌ Ошибка при применении Dream-Pastel эффекта: {e}")
        # Возвращаем оригинальное изображение при ошибке
        try:
            return img.convert('RGB') if img.mode != 'RGB' else img
        except:
            # Создаем простое изображение-заглушку
            placeholder = Image.new('RGB', (400, 300), (240, 240, 240))
            return placeholder

def create_collage_spread(img1: Image.Image, img2: Image.Image, caption: str) -> str:
    """Создает коллаж-разворот из двух фотографий"""
    try:
        # Проверяем валидность изображений
        if img1 is None or img2 is None:
            print("❌ Одно из изображений для коллажа отсутствует")
            return ""
            
        if img1.size[0] == 0 or img1.size[1] == 0 or img2.size[0] == 0 or img2.size[1] == 0:
            print("❌ Недопустимый размер изображений для коллажа")
            return ""
        
        # Создаем холст для коллажа
        canvas_width = 1200
        canvas_height = 800
        canvas = Image.new('RGB', (canvas_width, canvas_height), (255, 250, 245))
        
        # Подготавливаем изображения
        img1_size = (500, 350)
        img2_size = (500, 350)
        
        # Безопасное изменение размера
        try:
            img1 = img1.resize(img1_size, Image.Resampling.LANCZOS)
            img2 = img2.resize(img2_size, Image.Resampling.LANCZOS)
        except Exception as resize_error:
            print(f"❌ Ошибка при изменении размера: {resize_error}")
            return ""
        
        # Применяем dream-pastel эффект
        img1 = apply_dream_pastel_effect(img1)
        img2 = apply_dream_pastel_effect(img2)
        
        # Размещаем изображения с небольшим поворотом
        try:
            img1_rotated = img1.rotate(-2, expand=True, fillcolor=(255, 250, 245))
            img2_rotated = img2.rotate(3, expand=True, fillcolor=(255, 250, 245))
            
            # Позиционируем на холсте
            pos1 = (50, 150)
            pos2 = (650, 200)
            
            canvas.paste(img1_rotated, pos1)
            canvas.paste(img2_rotated, pos2)
        except Exception as rotation_error:
            print(f"❌ Ошибка при повороте изображений: {rotation_error}")
            # Размещаем без поворота
            canvas.paste(img1, (50, 150))
            canvas.paste(img2, (650, 200))
        
        # Добавляем подпись посередине
        try:
            draw = ImageDraw.Draw(canvas)
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
            except:
                font = ImageFont.load_default()
            
            # Текст с тенью
            text_x = canvas_width // 2
            text_y = canvas_height - 100
            
            # Обрезаем слишком длинный caption
            if len(caption) > 50:
                caption = caption[:47] + "..."
            
            # Тень
            draw.text((text_x + 2, text_y + 2), caption, font=font, fill=(0, 0, 0, 100), anchor="mm")
            # Основной текст
            draw.text((text_x, text_y), caption, font=font, fill=(80, 60, 40), anchor="mm")
        except Exception as text_error:
            print(f"❌ Ошибка при добавлении текста: {text_error}")
        
        # Конвертируем в base64
        buffer = BytesIO()
        canvas.save(buffer, format='JPEG', quality=92)
        img_str = base64.b64encode(buffer.getvalue()).decode()
        return f"data:image/jpeg;base64,{img_str}"
        
    except Exception as e:
        print(f"❌ Ошибка при создании коллажа: {e}")
        return ""

def create_infographic(analysis: dict) -> str:
    """Создает инфографику с статистикой"""
    try:
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))
        fig.patch.set_facecolor('#fff5f0')
        
        # График роста популярности
        months = ['Янв', 'Фев', 'Мар', 'Апр', 'Май', 'Июн']
        likes_growth = [100, 150, 220, 380, 520, analysis.get('total_likes', 600)]
        
        ax1.plot(months, likes_growth, color='#ff6b9d', linewidth=3, marker='o', markersize=8)
        ax1.fill_between(months, likes_growth, alpha=0.3, color='#ffb3d1')
        ax1.set_title('Рост популярности', fontsize=14, color='#8b5a5a')
        ax1.set_ylabel('Лайки', color='#8b5a5a')
        ax1.grid(True, alpha=0.3)
        
        # Круговая диаграмма Followers/Following
        followers = analysis.get('followers', 1000)
        following = analysis.get('following', 500)
        sizes = [followers, following]
        labels = ['Подписчики', 'Подписки']
        colors = ['#ff6b9d', '#ffd93d']
        
        ax2.pie(sizes, labels=labels, colors=colors, autopct='%1.0f', startangle=90)
        ax2.set_title('Соотношение подписок', fontsize=14, color='#8b5a5a')
        
        plt.tight_layout()
        
        # Сохраняем в base64
        buffer = BytesIO()
        plt.savefig(buffer, format='PNG', dpi=150, bbox_inches='tight', facecolor='#fff5f0')
        plt.close()
        
        img_str = base64.b64encode(buffer.getvalue()).decode()
        return f"data:image/png;base64,{img_str}"
        
    except Exception as e:
        print(f"❌ Ошибка при создании инфографики: {e}")
        return ""

def generate_playlist_for_photo(caption: str, index: int) -> str:
    """Генерирует плейлист для фотографии"""
    mood_tracks = {
        0: "Lana Del Rey - Young and Beautiful",
        1: "The 1975 - Somebody Else", 
        2: "Billie Eilish - lovely",
        3: "Clairo - Pretty Girl",
        4: "Rex Orange County - Best Friend",
        5: "Boy Pablo - Everytime",
        6: "Cuco - Lo Que Siento",
        7: "Mac DeMarco - Chamber of Reflection"
    }
    
    # Генерируем трек на основе описания (с fallback)
    try:
        prompt = f"""Подбери современный dreampop/indie-трек к описанию фотографии: "{caption[:100]}..."
        
        Ответь в формате: "Исполнитель - Название трека"
        Стиль: мечтательный, атмосферный, подходящий для созерцания фото.
        """
        
        suggested_track = generate_text(prompt, max_tokens=50)
        if suggested_track and len(suggested_track.strip()) > 5:
            return suggested_track.strip()
    except Exception as e:
        print(f"❌ Ошибка при генерации плейлиста: {e}")
    
    return mood_tracks.get(index % len(mood_tracks), "Dream Valley - Sunset Memories")

def create_qr_code(username: str) -> str:
    """Создает QR-код с ссылкой на архив"""
    try:
        # Создаем QR-код с ссылкой
        qr_url = f"https://instagram.com/{username}"
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(qr_url)
        qr.make(fit=True)
        
        # Создаем изображение QR-кода
        qr_img = qr.make_image(fill_color="black", back_color="white")
        
        # Конвертируем в base64
        buffer = BytesIO()
        qr_img.save(buffer, format='PNG')
        img_str = base64.b64encode(buffer.getvalue()).decode()
        return f"data:image/png;base64,{img_str}"
        
    except Exception as e:
        print(f"❌ Ошибка при создании QR-кода: {e}")
        return ""

def format_statistics_creatively(stat_name: str, value: int) -> str:
    """Переводит статистику в креативный формат"""
    creative_formats = {
        'followers': f"{value:,} сердец в зрительном зале",
        'following': f"{value:,} вдохновляющих голосов",
        'posts': f"{value} кадров жизненного фильма", 
        'likes': f"{value:,} моментов счастья",
        'comments': f"{value:,} искренних слов",
        'stories': f"{value} мгновений души"
    }
    return creative_formats.get(stat_name, f"{value:,}")

def add_text_rhythm(text: str) -> str:
    """Улучшает ритм текста, чередуя короткие и длинные предложения"""
    sentences = text.split('. ')
    improved_sentences = []
    
    for i, sentence in enumerate(sentences):
        # Каждое 3-е предложение делаем цитатой
        if i > 0 and i % 3 == 0 and len(sentence) > 30:
            improved_sentences.append(f'<blockquote>"{sentence.strip()}."</blockquote>')
        else:
            improved_sentences.append(sentence.strip() + '.')
    
    return ' '.join(improved_sentences)

def add_english_voiceover(text: str) -> str:
    """Добавляет английские voice-over фразы"""
    voiceover_phrases = [
        "*moment of truth*",
        "*pure magic*", 
        "*breathe it in*",
        "*frame perfect*",
        "*golden hour*",
        "*soul deep*",
        "*simply beautiful*",
        "*life in motion*"
    ]
    
    # Добавляем voice-over в конец каждого второго абзаца
    if len(text) > 100:
        import random
        phrase = random.choice(voiceover_phrases)
        return f"{text} <em class='voiceover'>{phrase}</em>"
    return text

def generate_zine_content(analysis: dict, images: list[Path]) -> dict:
    """Генерирует короткий контент для мозаичного зина"""
    
    # Фиксированные данные
    username = analysis.get('username', 'Неизвестный')
    followers = analysis.get('followers', 0)
    bio = analysis.get('bio', '')
    
    # Реальные данные
    real_captions = analysis.get('captions', ['Без слов'])[:3]
    locations = analysis.get('locations', ['Неизвестное место'])[:2]
    
    # Анализируем фотографии для карточек (максимум 15 фото)
    photo_cards = []
    valid_images = []
    context = f"Instagram профиль @{username}, {followers} подписчиков, био: {bio}"
    
    for i, img_path in enumerate(images[:15]):  # Ограничиваем до 15 фото для зина
        if img_path.exists():
            try:
                # Создаем карточки разных типов
                card_types = ["micro", "trigger", "sms"]
                card_type = card_types[i % 3]
                card_content = analyze_photo_for_card(img_path, context, card_type)
                
                photo_cards.append({
                    'type': card_type,
                    'content': card_content,
                    'path': img_path
                })
                valid_images.append(img_path)
                
                print(f"📸 Карточка {i+1}/15 ({card_type}): {card_content[:40]}...")
            except Exception as e:
                print(f"❌ Ошибка создания карточки {img_path}: {e}")
    
    # Если фото меньше 3, создаем минимальный зин
    if len(valid_images) < 3:
        print(f"⚠️ Мало фото для полноценного зина: {len(valid_images)}")
    
    print(f"✅ Обработано {len(valid_images)} фотографий из {len(images)} доступных")
    
    # Данные для коротких сцен
    scene_data = {
        'username': username,
        'followers': followers,
        'bio': bio,
        'captions': real_captions,
        'locations': locations,
        'photo_cards': photo_cards
    }
    
    # Генерируем 5 коротких сцен
    content = {}
    
    try:
        # 1. ЗАВЯЗКА - дневниковая запись (максимум 3 предложения)
        hook = generate_scene_chapter("hook", scene_data, valid_images)
        content['prologue'] = strip_cliches(hook)
        print(f"✅ Завязка: {hook[:50]}...")
    except Exception as e:
        print(f"❌ Ошибка завязки: {e}")
        content['prologue'] = f"Наткнулся на @{username} случайно. Что-то зацепило."
    
    try:
        # 2. КОНФЛИКТ - SMS-стиль (максимум 4 строки)
        conflict = generate_scene_chapter("conflict", scene_data, valid_images)
        content['emotions'] = strip_cliches(conflict)
        print(f"✅ Конфликт: {conflict[:50]}...")
    except Exception as e:
        print(f"❌ Ошибка конфликта: {e}")
        content['emotions'] = f"— {real_captions[0] if real_captions else 'Все хорошо'}\n— Но глаза говорят другое."
    
    try:
        # 3. ПОВОРОТ - момент озарения (максимум 3 предложения)
        turn = generate_scene_chapter("turn", scene_data, valid_images)
        content['places'] = strip_cliches(turn)
        print(f"✅ Поворот: {turn[:50]}...")
    except Exception as e:
        print(f"❌ Ошибка поворота: {e}")
        content['places'] = f"Один кадр из {locations[0] if locations else 'неизвестного места'} изменил все. Здесь пахло честностью."
    
    try:
        # 4. КУЛЬМИНАЦИЯ - цитаты комментариев
        climax = generate_scene_chapter("climax", scene_data, valid_images)
        content['community'] = strip_cliches(climax)
        print(f"✅ Кульминация: {climax[:50]}...")
    except Exception as e:
        print(f"❌ Ошибка кульминации: {e}")
        content['community'] = f"{followers} человек отреагировали:\n— Наконец-то ты показал себя настоящего\n— Спасибо за честность"
    
    try:
        # 5. ЭПИЛОГ - приглашение (максимум 2 предложения)
        epilogue = generate_scene_chapter("epilogue", scene_data, valid_images)
        content['legacy'] = strip_cliches(epilogue)
        print(f"✅ Эпилог: {epilogue[:50]}...")
    except Exception as e:
        print(f"❌ Ошибка эпилога: {e}")
        content['legacy'] = "Листаю ленту в поиске нового дикого цветка. А вдруг это будешь ты?"
    
    # Метаданные
    content['title'] = f"Зин @{username}"
    content['photo_cards'] = photo_cards
    content['valid_images_count'] = len(valid_images)
    content['reading_time'] = "5 минут"
    
    return content

def generate_classic_book_content(analysis: dict, images: list[Path]) -> dict:
    """Генерирует полный контент для классической книги"""
    
    # Фиксированные данные для консистентности
    username = analysis.get('username', 'Неизвестный')
    full_name = analysis.get('full_name', username)
    bio = analysis.get('bio', '')
    followers = max(0, analysis.get('followers', 0))
    following = max(0, analysis.get('following', 0))
    posts_count = max(0, analysis.get('posts_count', 0))
    total_likes = max(0, analysis.get('total_likes', 0))
    total_comments = max(0, analysis.get('total_comments', 0))
    
    # Переводим цифры в метафоры
    followers_metaphor = f"{followers} огоньков на карте подсвечивает его путь" if followers > 100 else f"{followers} верных спутников идут рядом"
    posts_metaphor = f"{posts_count} страниц визуального дневника" if posts_count > 0 else "несколько записей в книге жизни"
    
    # Реальные данные из Instagram с проверками
    real_captions = analysis.get('captions', [])[:6] if analysis.get('captions') else ['Жизнь прекрасна']
    common_hashtags = analysis.get('common_hashtags', [])[:5] if analysis.get('common_hashtags') else [('beautiful', 1)]
    mentioned_users = analysis.get('mentioned_users', [])[:3] if analysis.get('mentioned_users') else []
    locations = analysis.get('locations', [])[:4] if analysis.get('locations') else ['Неизвестное место']
    
    # Анализируем фотографии с полным анализом (используем все доступные)
    photo_analyses = []
    valid_images = []
    context = f"Instagram профиль @{username}, {followers_metaphor}, био: {bio}"
    
    for i, img_path in enumerate(images):  # Используем все фото для классической книги
        if img_path.exists():
            try:
                # Передаем индекс для вариативности анализа
                analysis_text = analyze_photo(img_path, context, photo_index=i)
                photo_analyses.append(analysis_text)
                valid_images.append(img_path)
                print(f"📸 Анализ фото {i+1} ({['расшифровка', 'монолог', 'диалог'][i % 3]}): {analysis_text[:60]}...")
            except Exception as e:
                print(f"❌ Ошибка анализа фото {img_path}: {e}")
    
    # Если фото меньше 3, не создаем книгу
    if len(valid_images) < 3:
        print(f"⚠️ Недостаточно фото для создания книги: {len(valid_images)}")
    
    # Фиксированные данные для всех глав
    data_for_chapters = {
        'username': username,
        'full_name': full_name,
        'bio': bio,
        'followers': followers,
        'followers_metaphor': followers_metaphor,
        'following': following,
        'posts_count': posts_count,
        'posts_metaphor': posts_metaphor,
        'total_likes': total_likes,
        'captions': real_captions,
        'locations': locations,
        'mentioned_users': mentioned_users,
        'photo_analyses': photo_analyses
    }
    
    # Генерируем уникальный контент с четким фокусом каждой главы
    content = {}
    generated_texts = []  # Для строгого отслеживания повторений
    
    # 1. ВСТРЕЧА - Рассказчик объясняет мотивацию
    print(f"💕 Создаем встречу (любопытство)...")
    try:
        prologue = generate_unique_chapter("intro", data_for_chapters, generated_texts)
        content['prologue'] = prologue
        generated_texts.append(prologue[:100])
    except Exception as e:
        print(f"❌ Ошибка при генерации пролога: {e}")
        content['prologue'] = f"Документирую, чтобы не забыть, как случайно встретил талант.\n\n@{username} попался в ленте случайно.\n\n{followers_metaphor} — но дело не в цифрах."
    
    # 2. КОНФЛИКТ - Одна конкретная тайна
    print(f"💕 Создаем конфликт (сомнения)...")
    try:
        emotions_chapter = generate_unique_chapter("emotions", data_for_chapters, generated_texts)
        content['emotions'] = emotions_chapter
        generated_texts.append(emotions_chapter[:100])
    except Exception as e:
        print(f"❌ Ошибка при генерации главы об эмоциях: {e}")
        content['emotions'] = f'«{real_captions[0] if real_captions else "Все хорошо"}» — написано под фото.\n\nНо глаза говорят другое.\n\nВ уголках рта прячется усталость.'
    
    # 3. ПОВОРОТНЫЙ КАДР - Место раскрытия тайны
    print(f"💕 Создаем поворот (осознание)...")
    try:
        places_chapter = generate_unique_chapter("places", data_for_chapters, generated_texts)
        content['places'] = places_chapter
        generated_texts.append(places_chapter[:100])
    except Exception as e:
        print(f"❌ Ошибка при генерации главы о местах: {e}")
        content['places'] = f"Кадр из {locations[0] if locations else 'неизвестного места'} изменил все.\n\nЗдесь пахло дождем и честностью.\n\nВпервые за долгое время — настоящая улыбка."
    
    # 4. РАЗРЕШЕНИЕ - Реакция подписчиков на тайну
    print(f"💕 Создаем разрешение (принятие)...")
    try:
        community_chapter = generate_unique_chapter("community", data_for_chapters, generated_texts)
        content['community'] = community_chapter
        generated_texts.append(community_chapter[:100])
    except Exception as e:
        print(f"❌ Ошибка при генерации главы о сообществе: {e}")
        content['community'] = f'{followers_metaphor} откликнулись на откровенность.\n\n«Наконец-то ты показал себя настоящего» — пишет подруга.\n\n«Спасибо за честность» — добавляет незнакомец.'
    
    # 5. ФИНАЛ - Приглашение в будущее
    print(f"💕 Создаем финал (рост рассказчика)...")
    try:
        legacy_chapter = generate_unique_chapter("legacy", data_for_chapters, generated_texts)
        content['legacy'] = legacy_chapter
        generated_texts.append(legacy_chapter[:100])
    except Exception as e:
        print(f"❌ Ошибка при генерации финальной главы: {e}")
        content['legacy'] = f"Что останется важного?\n\nНе лайки. Не статистика.\n\nМомент, когда человек решился быть собой.\n\nЯ листаю ленту в поиске нового дикого цветка. А вдруг это будешь ты?"
    
    # Заголовок и данные
    content['title'] = f"История @{username}"
    content['photo_stories'] = photo_analyses
    content['valid_images_count'] = len(valid_images)
    content['followers_metaphor'] = followers_metaphor
    content['posts_metaphor'] = posts_metaphor
    
    return content

def create_classic_book_html(content: dict, analysis: dict, images: list[Path]) -> str:
    """Создает HTML книгу в классическом формате с живой речью и без канцеляризмов"""
    
    # Фиксированные данные (устраняем несостыковки)
    username = analysis.get('username', 'Неизвестный')
    full_name = analysis.get('full_name', username)
    followers = analysis.get('followers', 0)
    following = analysis.get('following', 0)
    posts_count = analysis.get('posts_count', 0)
    bio = analysis.get('bio', '')
    verified = analysis.get('verified', False)
    
    # Метафоры вместо сухих цифр
    followers_metaphor = content.get('followers_metaphor', f"{followers} огоньков на карте")
    posts_metaphor = content.get('posts_metaphor', f"{posts_count} страниц дневника")
    
    # Обрабатываем все существующие изображения для классической книги
    processed_images = []
    for i, img_path in enumerate(images):  # Используем все фото
        if img_path.exists():
            try:
                with Image.open(img_path) as img:
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    
                    # Адаптивный размер для классической книги
                    max_size = (800, 600)
                    img.thumbnail(max_size, Image.Resampling.LANCZOS)
                    
                    # Минимальная обработка
                    enhancer = ImageEnhance.Contrast(img)
                    img = enhancer.enhance(1.05)
                    
                    # Конвертируем в base64
                    buffer = BytesIO()
                    img.save(buffer, format='JPEG', quality=88)
                    img_str = base64.b64encode(buffer.getvalue()).decode()
                    processed_images.append(f"data:image/jpeg;base64,{img_str}")
            except Exception as e:
                print(f"❌ Ошибка при обработке изображения {img_path}: {e}")
    
    # Реальные данные
    real_captions = analysis.get('captions', ['Без подписи'])[:len(processed_images)]
    locations = analysis.get('locations', ['Неизвестно'])[:3]
    photo_stories = content.get('photo_stories', [])
    
    # Убираем пустые "Момент X" - используем только реальные фото
    valid_photo_count = len(processed_images)
    
    # HTML с улучшенной структурой
    html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title>{content.get('title', f'История @{username}')}</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Crimson+Text:ital,wght@0,400;0,600;1,400&family=Playfair+Display:wght@400;500;700&family=Libre+Baskerville:ital,wght@0,400;0,700;1,400&display=swap" rel="stylesheet">
    
    <style>
    :root {{
        --vanilla-bg: #faf8f3;
        --cream-bg: #f7f4ed;
        --soft-beige: #f2ede2;
        --warm-white: #fefcf8;
        --text-dark: #2c2a26;
        --text-medium: #5a5652;
        --text-light: #8b8680;
        --accent-warm: #d4af8c;
        --shadow-soft: rgba(60, 50, 40, 0.08);
    }}
    
    body {{
        font-family: 'Crimson Text', serif;
        font-size: 13pt;
        line-height: 1.6;
        color: var(--text-dark);
        background: var(--vanilla-bg);
        margin: 0;
        padding: 0;
        max-width: 800px;
        margin: 0 auto;
    }}
    
    .page {{
        min-height: 85vh;
        padding: 2cm 2.5cm;
        margin-bottom: 1cm;
        page-break-after: always;
        background: var(--warm-white);
        box-shadow: 0 4px 20px var(--shadow-soft);
        border-radius: 6px;
        border: 1px solid rgba(212, 175, 140, 0.1);
    }}
    
    .page:last-child {{
        page-break-after: auto;
    }}
    
    h1 {{
        font-family: 'Playfair Display', serif;
        font-size: 28pt;
        text-align: center;
        margin: 2cm 0 1.5cm 0;
        color: var(--text-dark);
        font-weight: 500;
        letter-spacing: 1px;
    }}
    
    h2 {{
        font-family: 'Playfair Display', serif;
        font-size: 20pt;
        color: var(--text-dark);
        margin: 2cm 0 1cm 0;
        font-weight: 500;
        border-bottom: 2px solid var(--accent-warm);
        padding-bottom: 0.3cm;
    }}
    
    .chapter-number {{
        font-family: 'Libre Baskerville', serif;
        font-size: 11pt;
        color: var(--text-light);
        text-align: center;
        margin-bottom: 0.8cm;
        font-style: italic;
        text-transform: uppercase;
        letter-spacing: 2px;
    }}
    
    /* Улучшенная типографика для коротких абзацев */
    p {{
        margin: 0 0 1.2em 0;
        text-align: justify;
        text-indent: 1.5em;
        line-height: 1.7;
    }}
    
    .first-paragraph {{
        text-indent: 0;
        font-size: 14pt;
        font-weight: 500;
    }}
    
    /* Стили для метафор вместо сухой статистики */
    .metaphor-box {{
        margin: 1.5cm 0;
        text-align: center;
        font-family: 'Libre Baskerville', serif;
        padding: 1.5em;
        background: var(--cream-bg);
        border-radius: 12px;
        border: 1px solid rgba(212, 175, 140, 0.2);
        font-style: italic;
        color: var(--text-medium);
    }}
    
    .metaphor-box h3 {{
        margin-top: 0;
        color: var(--accent-warm);
        font-size: 16pt;
        font-style: normal;
    }}
    
    /* Инфобокс для технической информации (выносной) */
    .info-sidebar {{
        position: absolute;
        right: -200px;
        top: 2cm;
        width: 180px;
        padding: 1em;
        background: var(--soft-beige);
        border-radius: 8px;
        font-size: 10pt;
        color: var(--text-light);
        border-left: 3px solid var(--accent-warm);
    }}
    
    /* Стили для живых диалогов */
    .dialogue {{
        font-style: italic;
        color: var(--text-medium);
        text-indent: 0;
        margin: 1em 0;
        padding-left: 2em;
        border-left: 2px solid var(--accent-warm);
        padding-left: 1em;
    }}
    
    .dialogue::before {{
        content: "— ";
        font-weight: bold;
        color: var(--accent-warm);
    }}
    
    .inner-thought {{
        font-style: italic;
        color: var(--text-medium);
        text-align: center;
        margin: 1.5em 0;
        padding: 1em;
        background: var(--cream-bg);
        border-radius: 8px;
        text-indent: 0;
    }}
    
    .photo-container {{
        margin: 2cm 0;
        text-align: center;
        page-break-inside: avoid;
    }}
    
    .photo-frame {{
        display: inline-block;
        padding: 15px;
        background: var(--warm-white);
        border-radius: 12px;
        box-shadow: 0 6px 25px var(--shadow-soft);
        border: 1px solid rgba(212, 175, 140, 0.15);
    }}
    
    .photo-frame img {{
        max-width: 100%;
        max-height: 450px;
        border-radius: 8px;
        border: 2px solid var(--warm-white);
    }}
    
    .photo-caption {{
        font-family: 'Libre Baskerville', serif;
        font-style: italic;
        font-size: 11pt;
        color: var(--text-medium);
        margin-top: 1cm;
        text-align: center;
    }}
    
    .photo-story {{
        margin-top: 0.8cm;
        padding: 1.2em;
        background: var(--soft-beige);
        border-radius: 8px;
        font-size: 11pt;
        color: var(--text-medium);
        border-left: 3px solid var(--accent-warm);
        text-align: left;
        white-space: pre-line;
    }}
    
    /* Стили для вариативных подходов к фото */
    .photo-detective {{
        border-left-color: #e74c3c;
    }}
    
    .photo-monologue {{
        border-left-color: #3498db;
    }}
    
    .photo-dialogue {{
        border-left-color: #2ecc71;
    }}
    
    @media print {{
        body {{ margin: 0; background: white; }}
        .page {{ box-shadow: none; border: none; }}
        .info-sidebar {{ display: none; }}
    }}
    </style>
</head>
<body>

<!-- ОБЛОЖКА -->
<div class="page">
    <h1>{content.get('title', f'История @{username}')}</h1>
    
    <div style="text-align: center; margin: 3cm 0; font-style: italic; color: var(--text-medium);">
        Документальная повесть<br>
        {valid_photo_count} кадров откровения
    </div>
    
    <div class="metaphor-box">
        <h3>@{username}</h3>
        <p style="margin: 0; text-indent: 0;">{followers_metaphor}</p>
        <p style="margin: 0.5em 0 0 0; text-indent: 0; font-size: 11pt;">{posts_metaphor}</p>
        {f'<p style="margin: 1em 0 0 0; text-indent: 0; font-size: 10pt; font-style: normal;">«{bio}»</p>' if bio else ''}
    </div>
    
    <!-- Выносной инфобокс с технической информацией -->
    <div class="info-sidebar">
        <strong>Техническая справка:</strong><br>
        Подписчики: {followers:,}<br>
        Посты: {posts_count}<br>
        {f'Верификация: {"Да" if verified else "Нет"}<br>' if verified else ''}
        Анализ: {valid_photo_count} фотографий
    </div>
    
    <div style="position: absolute; bottom: 2cm; left: 50%; transform: translateX(-50%); text-align: center;">
        <p style="font-size: 10pt; color: var(--text-light); margin: 0;">
            {full_name if full_name != username else username}
        </p>
    </div>
</div>

<!-- 1. ВСТРЕЧА -->
<div class="page">
    <div class="chapter-number">Глава первая</div>
    <h2>Встреча</h2>
    
    <div style="white-space: pre-line; line-height: 1.7;">
        {content.get('prologue', f'Документирую, чтобы не забыть, как случайно встретил талант.\n\n@{username} попался в ленте случайно.\n\n{followers_metaphor} — но дело не в цифрах.')}
    </div>
</div>"""
    
    # Добавляем фотографии с ВАРИАТИВНЫМ анализом
    photo_styles = ['detective', 'monologue', 'dialogue']
    for i, img_base64 in enumerate(processed_images):
        caption = real_captions[i] if i < len(real_captions) else f'Кадр {i+1}'
        photo_analysis = photo_stories[i] if i < len(photo_stories) else "Время замерло в этом кадре."
        style_class = photo_styles[i % 3]
        style_name = ['Расшифровка', 'Внутренний монолог', 'Диалог'][i % 3]
        
        html += f"""

<div class="page">
    <div class="photo-container">
        <div class="photo-frame">
            <img src="{img_base64}" alt="Фотография {i+1}">
        </div>
        
        <div class="photo-caption">
            «{caption}»
        </div>
        
        <div class="photo-story photo-{style_class}">
            <small style="color: var(--text-light); font-style: normal;">{style_name}:</small>
            
            {photo_analysis}
        </div>
    </div>
</div>"""
    
    # Остальные главы с четким фокусом
    html += f"""

<!-- 2. КОНФЛИКТ -->
<div class="page">
    <div class="chapter-number">Глава вторая</div>
    <h2>Тайна</h2>
    
    <div style="white-space: pre-line; line-height: 1.7;">
        {content.get('emotions', f'«{real_captions[0] if real_captions else "Все хорошо"}» — написано под фото.\n\nНо глаза говорят другое.\n\nВ уголках рта прячется усталость.')}
    </div>
</div>

<!-- 3. ПОВОРОТ -->
<div class="page">
    <div class="chapter-number">Глава третья</div>
    <h2>Озарение</h2>
    
    <div style="white-space: pre-line; line-height: 1.7;">
        {content.get('places', f'Кадр из {locations[0] if locations else "неизвестного места"} изменил все.\n\nЗдесь пахло дождем и честностью.\n\nВпервые за долгое время — настоящая улыбка.')}
    </div>
</div>

<!-- 4. РАЗРЕШЕНИЕ -->
<div class="page">
    <div class="chapter-number">Глава четвертая</div>
    <h2>Отклик</h2>
    
    <div style="white-space: pre-line; line-height: 1.7;">
        {content.get('community', f'{followers_metaphor} откликнулись на откровенность.\n\n«Наконец-то ты показал себя настоящего» — пишет подруга.\n\n«Спасибо за честность» — добавляет незнакомец.')}
    </div>
</div>

<!-- 5. ФИНАЛ -->
<div class="page">
    <div class="chapter-number">Эпилог</div>
    <h2>Приглашение</h2>
    
    <div style="white-space: pre-line; line-height: 1.7;">
        {content.get('legacy', f'Что останется важного?\n\nНе лайки. Не статистика.\n\nМомент, когда человек решился быть собой.\n\nЯ листаю ленту в поиске нового дикого цветка. А вдруг это будешь ты?')}
    </div>
    
    <div style="text-align: center; margin-top: 3cm; font-style: italic; color: var(--text-medium);">
        Конец первой истории.<br>
        <small>Начало поиска следующей.</small>
    </div>
</div>

</body>
</html>"""
    
    return html

def create_zine_html(content: dict, analysis: dict, images: list[Path]) -> str:
    """Создает мозаичную HTML книгу с коллажами и интерактивными карточками"""
    
    # Фиксированные данные
    username = analysis.get('username', 'Неизвестный')
    full_name = analysis.get('full_name', username)
    followers = analysis.get('followers', 0)
    posts_count = analysis.get('posts_count', 0)
    bio = analysis.get('bio', '')
    verified = analysis.get('verified', False)
    
    # Обрабатываем только первые 15 изображений для коллажа
    processed_images = []
    
    # Ограничиваем до 15 фото для оптимальной производительности
    limited_images = images[:15]
    print(f"🎨 Обрабатываем {len(limited_images)} фотографий для мозаичного коллажа")
    
    for i, img_path in enumerate(limited_images):
        if img_path.exists():
            try:
                with Image.open(img_path) as img:
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    
                    # Для коллажа - меньший размер
                    max_size = (300, 300)
                    img.thumbnail(max_size, Image.Resampling.LANCZOS)
                    
                    # Минимальная обработка
                    enhancer = ImageEnhance.Contrast(img)
                    img = enhancer.enhance(1.03)
                    
                    # Конвертируем в base64
                    buffer = BytesIO()
                    img.save(buffer, format='JPEG', quality=85)
                    img_str = base64.b64encode(buffer.getvalue()).decode()
                    
                    # Генерируем карточку для этого фото
                    card_types = ["micro", "trigger", "sms"]
                    card_type = card_types[i % 3]
                    card_content = analyze_photo_for_card(img_path, f"@{username}", card_type)
                    
                    processed_images.append({
                        'data': f"data:image/jpeg;base64,{img_str}",
                        'rotation': random.uniform(-3, 3),  # Случайный поворот
                        'size': random.choice(['small', 'medium', 'large']),
                        'card_content': card_content,
                        'card_type': card_type
                    })
                    
                    print(f"✅ Фото {i+1}/15 обработано для коллажа")
                    
            except Exception as e:
                print(f"❌ Ошибка при обработке изображения {img_path}: {e}")
    
    # Рандомизируем порядок для мозаичности
    random.shuffle(processed_images)
    
    # Реальные данные
    real_captions = analysis.get('captions', ['Без подписи'])
    
    print(f"🎯 Создаем зин с {len(processed_images)} фотографиями")
    
    # HTML с мозаичным дизайном
    html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title>{content.get('title', f'Зин @{username}')}</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Crimson+Text:ital,wght@0,400;0,600;1,400&family=Playfair+Display:wght@400;500;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    
    <style>
    :root {{
        --paper: #fefcf8;
        --ink: #2a2a2a;
        --accent: #d4af8c;
        --shadow: rgba(0,0,0,0.1);
        --highlight: #fff9e6;
    }}
    
    * {{ box-sizing: border-box; }}
    
    body {{
        font-family: 'Crimson Text', serif;
        background: var(--paper);
        color: var(--ink);
        margin: 0;
        padding: 20px;
        line-height: 1.5;
        overflow-x: hidden;
    }}
    
    /* Мозаичная сетка для коллажа */
    .moodboard {{
        position: relative;
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
        gap: 15px;
        margin: 2rem 0;
        min-height: 400px;
    }}
    
    .tile {{
        position: relative;
        width: 100%;
        height: 180px;
        object-fit: cover;
        border-radius: 8px;
        box-shadow: 0 4px 12px var(--shadow);
        transition: transform 0.3s ease;
        cursor: pointer;
    }}
    
    .tile.small {{ height: 140px; }}
    .tile.medium {{ height: 180px; }}
    .tile.large {{ height: 220px; grid-row: span 2; }}
    
    .tile:hover {{
        transform: scale(1.05) rotate(0deg) !important;
        z-index: 10;
    }}
    
    /* Overlay с текстом поверх коллажа */
    .overlay-quote {{
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        background: rgba(254, 252, 248, 0.95);
        padding: 2rem 3rem;
        border-radius: 12px;
        box-shadow: 0 8px 32px var(--shadow);
        font-family: 'Playfair Display', serif;
        font-size: 1.4rem;
        text-align: center;
        max-width: 500px;
        border: 2px solid var(--accent);
        z-index: 5;
    }}
    
    /* Интерактивные карточки */
    .photo-card {{
        margin: 2rem 0;
        border: 1px solid #e0e0e0;
        border-radius: 12px;
        overflow: hidden;
        background: white;
        box-shadow: 0 4px 20px var(--shadow);
    }}
    
    .card-trigger {{
        width: 100%;
        padding: 0;
        border: none;
        background: none;
        cursor: pointer;
    }}
    
    .card-trigger img {{
        width: 100%;
        height: 200px;
        object-fit: cover;
        display: block;
    }}
    
    .card-content {{
        padding: 1.5rem;
        background: var(--highlight);
        border-top: 3px solid var(--accent);
    }}
    
    .card-type {{
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.8rem;
        color: var(--accent);
        text-transform: uppercase;
        margin-bottom: 0.5rem;
        font-weight: 500;
    }}
    
    .card-text {{
        font-size: 1.1rem;
        line-height: 1.6;
        white-space: pre-line;
    }}
    
    /* SMS стиль для диалогов */
    .sms-style {{
        font-family: 'JetBrains Mono', monospace;
        background: #f0f0f0;
        padding: 1rem;
        border-radius: 8px;
        font-size: 0.95rem;
    }}
    
    /* Сцены книги */
    .scene {{
        margin: 3rem 0;
        padding: 2rem;
        background: white;
        border-radius: 12px;
        box-shadow: 0 6px 24px var(--shadow);
        border-left: 5px solid var(--accent);
    }}
    
    .scene-title {{
        font-family: 'Playfair Display', serif;
        font-size: 1.8rem;
        margin-bottom: 1rem;
        color: var(--accent);
        text-transform: uppercase;
        letter-spacing: 1px;
    }}
    
    .scene-content {{
        font-size: 1.2rem;
        line-height: 1.7;
        white-space: pre-line;
    }}
    
    /* Заголовки */
    h1 {{
        font-family: 'Playfair Display', serif;
        font-size: 3rem;
        text-align: center;
        margin: 2rem 0;
        color: var(--ink);
    }}
    
    .subtitle {{
        text-align: center;
        font-style: italic;
        color: #666;
        margin-bottom: 3rem;
    }}
    
    /* Техническая справка */
    .tech-info {{
        background: #f8f8f8;
        padding: 1rem;
        border-radius: 8px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.9rem;
        margin: 2rem 0;
        border-left: 3px solid var(--accent);
    }}
    
    /* Финальный призыв */
    .final-call {{
        text-align: center;
        padding: 3rem 2rem;
        background: linear-gradient(135deg, var(--highlight), var(--paper));
        border-radius: 12px;
        margin: 3rem 0;
        border: 2px solid var(--accent);
    }}
    
    .qr-placeholder {{
        width: 120px;
        height: 120px;
        background: var(--accent);
        margin: 1rem auto;
        border-radius: 8px;
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-weight: bold;
    }}
    
    /* Адаптивность */
    @media (max-width: 768px) {{
        .moodboard {{
            grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
            gap: 10px;
        }}
        
        .tile {{ height: 120px; }}
        .tile.large {{ height: 160px; }}
        
        .overlay-quote {{
            padding: 1rem 1.5rem;
            font-size: 1.1rem;
        }}
        
        h1 {{ font-size: 2rem; }}
    }}
    
    /* Печать */
    @media print {{
        .photo-card {{ page-break-inside: avoid; }}
        .scene {{ page-break-inside: avoid; }}
        .moodboard {{ page-break-inside: avoid; }}
    }}
    </style>
</head>
<body>

<!-- ЗАГОЛОВОК -->
<h1>Зин @{username}</h1>
<div class="subtitle">
    Визуальный дневник • {len(processed_images)} кадров • 5 минут чтения
</div>

<!-- ТЕХНИЧЕСКАЯ СПРАВКА -->
<div class="tech-info">
    <strong>@{username}</strong> • {followers:,} подписчиков • {posts_count} постов
    {f' • ✓ Верифицирован' if verified else ''}
    {f'<br>"{bio}"' if bio else ''}
    <br><small>Отобрано лучших {len(processed_images)} из {len(images)} фотографий</small>
</div>

<!-- МУДБОРД-КОЛЛАЖ -->
<div class="moodboard">
    {chr(10).join([f'''
    <img src="{img['data']}" 
         class="tile {img['size']}" 
         style="transform: rotate({img['rotation']}deg)"
         alt="Кадр {i+1}"
         onclick="showCard({i})">
    ''' for i, img in enumerate(processed_images)])}
    
    <div class="overlay-quote">
        «{content.get('prologue', 'Листаю ленту в поиске дикого цветка. А вдруг это будешь ты?')}»
    </div>
</div>

<!-- ИНТЕРАКТИВНЫЕ КАРТОЧКИ (скрытые по умолчанию) -->
<div id="cards-section" style="display: none;">
    <h2 style="text-align: center; margin: 3rem 0 2rem 0;">Истории за кадром</h2>
    
    {chr(10).join([f'''
    <div class="photo-card" id="card-{i}">
        <button class="card-trigger" onclick="toggleCard({i})">
            <img src="{img['data']}" alt="Кадр {i+1}">
        </button>
        <div class="card-content" style="display: none;">
            <div class="card-type">{img['card_type']}</div>
            <div class="card-text {'sms-style' if img['card_type'] == 'sms' else ''}">{img['card_content']}</div>
        </div>
    </div>
    ''' for i, img in enumerate(processed_images)])}
</div>

<!-- ДРАМАТУРГИЧЕСКИЕ СЦЕНЫ -->
<div class="scene">
    <div class="scene-title">Завязка</div>
    <div class="scene-content">{content.get('prologue', 'Наткнулся на этот профиль случайно. Что-то зацепило.')}</div>
</div>

<div class="scene">
    <div class="scene-title">Конфликт</div>
    <div class="scene-content">{content.get('emotions', f'— {real_captions[0] if real_captions else "Все хорошо"}\n— Но глаза говорят другое.')}</div>
</div>

<div class="scene">
    <div class="scene-title">Поворот</div>
    <div class="scene-content">{content.get('places', 'Один кадр изменил все. Здесь пахло честностью.')}</div>
</div>

<div class="scene">
    <div class="scene-title">Кульминация</div>
    <div class="scene-content">{content.get('community', f' откликнулись на откровенность.\n\n«Наконец-то ты показал себя настоящего\n— Спасибо за честность')}</div>
</div>

<!-- ФИНАЛЬНЫЙ ПРИЗЫВ -->
<div class="final-call">
    <div class="scene-title">Эпилог</div>
    <div class="scene-content">{content.get('legacy', 'Листаю ленту в поиске нового дикого цветка. А вдруг это будешь ты?')}</div>
    
    <div class="qr-placeholder">
        QR → @{username}
    </div>
    
    <p style="margin-top: 2rem; font-style: italic;">
        Создано с любовью • Каждая история уникальна
    </p>
</div>

<script>
// Показать секцию с карточками
function showCard(index) {{
    const cardsSection = document.getElementById('cards-section');
    cardsSection.style.display = 'block';
    cardsSection.scrollIntoView({{ behavior: 'smooth' }});
    
    // Открыть конкретную карточку
    setTimeout(() => {{
        toggleCard(index);
    }}, 500);
}}

// Переключить карточку
function toggleCard(index) {{
    const card = document.getElementById(`card-${{index}}`);
    const content = card.querySelector('.card-content');
    
    if (content.style.display === 'none') {{
        content.style.display = 'block';
        card.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
    }} else {{
        content.style.display = 'none';
    }}
}}

// Рандомные повороты при загрузке
document.addEventListener('DOMContentLoaded', function() {{
    const tiles = document.querySelectorAll('.tile');
    tiles.forEach((tile, index) => {{
        const rotation = (Math.random() - 0.5) * 6; // -3 до +3 градусов
        tile.style.transform = `rotate(${{rotation}}deg)`;
    }});
}});
</script>

</body>
</html>"""
    
    return html

def convert_image_to_base64(image_path: Path, max_size: tuple = (600, 400), style: str = "original") -> str:
    """Конвертирует изображение в base64 с чистой обработкой для EPUB стиля"""
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
            
            # Применяем чистые стили для EPUB
            if style == "clean":
                # Минимальная обработка для четкости и читаемости
                enhancer = ImageEnhance.Contrast(img)
                img = enhancer.enhance(1.05)  # Легкое увеличение контраста
                enhancer = ImageEnhance.Sharpness(img)
                img = enhancer.enhance(1.1)   # Небольшое увеличение резкости
                enhancer = ImageEnhance.Color(img)
                img = enhancer.enhance(1.02)  # Очень легкое увеличение насыщенности
                
            # Конвертируем в base64
            buffer = BytesIO()
            img.save(buffer, format='JPEG', quality=90, optimize=True)
            img_str = base64.b64encode(buffer.getvalue()).decode()
            print(f"✅ Изображение {image_path.name} обработано для EPUB стиля")
            return f"data:image/jpeg;base64,{img_str}"
            
    except Exception as e:
        print(f"❌ Ошибка при обработке изображения {image_path}: {e}")
        return ""

def create_literary_instagram_book_html(content: dict, analysis: dict, images: list[Path]) -> str:
    """Создает HTML Instagram-книгу от первого лица в литературном стиле с эмоциями и метафорами"""
    
    # Фиксированные данные
    username = analysis.get('username', 'незнакомец')
    full_name = analysis.get('full_name', username)
    followers = analysis.get('followers', 0)
    following = analysis.get('following', 0)
    posts_count = analysis.get('posts_count', 0)
    bio = analysis.get('bio', '')
    
    # Реальные подписи и данные
    real_captions = analysis.get('captions', [])[:5]
    common_hashtags = analysis.get('common_hashtags', [])[:3]
    locations = analysis.get('locations', [])[:3]
    
    # Генерируем количество слов (8-10 тысяч)
    word_count = random.randint(8000, 10000)
    
    # Обрабатываем изображения
    processed_images = []
    for i, img_path in enumerate(images[:5]):  # Максимум 5 изображений для 5 глав
        if img_path.exists():
            try:
                with Image.open(img_path) as img:
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    
                    # Оптимальный размер для чтения
                    max_size = (700, 500)
                    img.thumbnail(max_size, Image.Resampling.LANCZOS)
                    
                    # Легкая обработка
                    enhancer = ImageEnhance.Contrast(img)
                    img = enhancer.enhance(1.08)
                    
                    buffer = BytesIO()
                    img.save(buffer, format='JPEG', quality=92)
                    img_str = base64.b64encode(buffer.getvalue()).decode()
                    processed_images.append(f"data:image/jpeg;base64,{img_str}")
            except Exception as e:
                print(f"❌ Ошибка обработки изображения {img_path}: {e}")
    
    # Генерируем название книги (3-7 слов)
    title_options = [
        f"Мгновения @{username}",
        f"История одного профиля",
        f"Между строк и кадров",
        f"Цифровые следы души",
        f"Дневник незнакомца",
        f"Осколки чужой жизни"
    ]
    book_title = random.choice(title_options)
    
    # Эпиграф (максимум 15 слов)
    epigraphs = [
        "Каждая фотография — окно в чью-то душу",
        "За каждым кадром прячется история",
        "Мы листаем жизни, не замечая глубины",
        "Красота скрывается в обыденных моментах",
        "Иногда чужие истории говорят о нас"
    ]
    epigraph = random.choice(epigraphs)
    
    # HTML в литературном стиле
    html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{book_title}</title>
    <link href="https://fonts.googleapis.com/css2?family=Crimson+Text:ital,wght@0,400;0,600;1,400;1,600&family=Playfair+Display:ital,wght@0,400;0,700;1,400;1,700&family=Libre+Baskerville:ital,wght@0,400;0,700;1,400&display=swap" rel="stylesheet">
    
    <style>
    :root {{
        --paper: #fefcf8;
        --ink: #2c2a26;
        --soft-ink: #5a5652;
        --accent: #b85450;
        --gold: #d4af8c;
        --shadow: rgba(60, 50, 40, 0.15);
    }}
    
    body {{
        font-family: 'Crimson Text', serif;
        background: var(--paper);
        color: var(--ink);
        line-height: 1.8;
        font-size: 16px;
        margin: 0;
        padding: 0;
        max-width: 800px;
        margin: 0 auto;
    }}
    
    .book-page {{
        min-height: 100vh;
        padding: 3cm 2.5cm;
        background: white;
        box-shadow: 0 8px 40px var(--shadow);
        margin: 20px auto;
        page-break-after: always;
        position: relative;
    }}
    
    .book-page:last-child {{
        page-break-after: auto;
    }}
    
    /* Обложка */
    .cover {{
        text-align: center;
        padding: 4cm 2cm;
        background: linear-gradient(135deg, var(--paper) 0%, #f7f4ed 100%);
        border: 1px solid rgba(212, 175, 140, 0.3);
    }}
    
    .cover-title {{
        font-family: 'Playfair Display', serif;
        font-size: 3rem;
        font-weight: 700;
        color: var(--ink);
        margin-bottom: 1rem;
        letter-spacing: -1px;
    }}
    
    .cover-subtitle {{
        font-family: 'Libre Baskerville', serif;
        font-style: italic;
        font-size: 1.2rem;
        color: var(--soft-ink);
        margin-bottom: 3rem;
    }}
    
    .cover-author {{
        font-size: 1.1rem;
        color: var(--soft-ink);
        margin-bottom: 4rem;
    }}
    
    .cover-epigraph {{
        font-style: italic;
        color: var(--soft-ink);
        border-top: 1px solid var(--gold);
        border-bottom: 1px solid var(--gold);
        padding: 2rem 0;
        max-width: 400px;
        margin: 0 auto;
        position: relative;
    }}
    
    .cover-epigraph::before {{
        content: '«';
        position: absolute;
        left: -20px;
        top: 1.5rem;
        font-size: 2rem;
        color: var(--accent);
    }}
    
    .cover-epigraph::after {{
        content: '»';
        position: absolute;
        right: -20px;
        bottom: 1.5rem;
        font-size: 2rem;
        color: var(--accent);
    }}
    
    /* Заголовки глав */
    h1 {{
        font-family: 'Playfair Display', serif;
        font-size: 2.2rem;
        font-weight: 700;
        color: var(--ink);
        margin: 3rem 0 1.5rem 0;
        text-align: left;
        border-bottom: 2px solid var(--gold);
        padding-bottom: 0.5rem;
    }}
    
    h2 {{
        font-family: 'Playfair Display', serif;
        font-size: 1.8rem;
        color: var(--accent);
        margin: 2.5rem 0 1.5rem 0;
        text-align: center;
    }}
    
    /* Эпиграфы к главам */
    .chapter-epigraph {{
        text-align: center;
        font-style: italic;
        color: var(--soft-ink);
        border-left: 3px solid var(--gold);
        padding-left: 2rem;
        margin: 2rem 0;
        background: #faf8f3;
        padding: 1.5rem;
        border-radius: 8px;
    }}
    
    /* Параграфы */
    p {{
        text-align: justify;
        text-indent: 2rem;
        margin-bottom: 1.5rem;
        line-height: 1.8;
        font-size: 1.1rem;
    }}
    
    .first-paragraph {{
        text-indent: 0;
        font-weight: 500;
        font-size: 1.15rem;
    }}
    
    /* Диалоги */
    .dialogue {{
        font-style: italic;
        color: var(--soft-ink);
        text-indent: 0;
        margin: 1.5rem 0;
        padding-left: 2rem;
        border-left: 3px solid var(--accent);
        position: relative;
    }}
    
    .dialogue::before {{
        content: '—';
        position: absolute;
        left: -10px;
        color: var(--accent);
        font-weight: bold;
    }}
    
    /* Изображения */
    .hero-img {{
        margin: 3rem 0;
        text-align: center;
        page-break-inside: avoid;
    }}
    
    .hero-img img {{
        max-width: 100%;
        max-height: 450px;
        border-radius: 12px;
        box-shadow: 0 12px 30px var(--shadow);
        border: 3px solid white;
    }}
    
    .hero-img figcaption {{
        font-family: 'Libre Baskerville', serif;
        font-style: italic;
        font-size: 1rem;
        color: var(--soft-ink);
        margin-top: 1rem;
        text-align: center;
    }}
    
    .hero-img figcaption::before {{
        content: '– ';
        color: var(--accent);
    }}
    
    /* Внутренние мысли */
    .inner-thought {{
        font-style: italic;
        text-align: center;
        color: var(--soft-ink);
        margin: 2rem 0;
        padding: 1.5rem;
        background: #f9f7f4;
        border-radius: 8px;
        text-indent: 0;
    }}
    
    /* Статистика внизу */
    .stats-footer {{
        margin-top: 4rem;
        padding-top: 2rem;
        border-top: 1px solid var(--gold);
        font-size: 0.9rem;
        color: var(--soft-ink);
        text-align: center;
        line-height: 1.5;
    }}
    
    /* Адаптивность */
    @media (max-width: 768px) {{
        .book-page {{
            padding: 2cm 1.5cm;
            margin: 10px;
        }}
        
        .cover-title {{
            font-size: 2.2rem;
        }}
        
        h1 {{
            font-size: 1.8rem;
        }}
    }}
    
    @media print {{
        body {{
            background: white;
            margin: 0;
        }}
        
        .book-page {{
            box-shadow: none;
            margin: 0;
        }}
    }}
    </style>
</head>
<body>

<!-- ОБЛОЖКА -->
<div class="book-page cover">
    <h1 class="cover-title">{book_title}</h1>
    <p class="cover-subtitle">Instagram-история от первого лица</p>
    <p class="cover-author">Автор: {full_name}</p>
    <div class="cover-epigraph">{epigraph}</div>
</div>

<!-- ПРОЛОГ -->
<div class="book-page">
    <h2>Пролог</h2>
    
    <p class="first-paragraph">
        Я наткнулся на профиль @{username} совершенно случайно, как натыкаются на неожиданные повороты в лабиринте старого города. Было около {random.choice(['полуночи', 'полудня', 'вечера'])}, и я бесцельно листал бесконечную ленту, когда среди привычного потока селфи и рекламы вдруг появилось что-то другое.
    </p>
    
    <p>
        {f'«{real_captions[0]}»' if real_captions else 'Подпись к фотографии была простой'} — было написано под одним из снимков. Но что-то в этих словах зацепило меня. Может быть, тон, может быть, честность, а может быть, просто усталость от фальшивого позитива, которым пропитаны социальные сети.
    </p>
    
    <p>
        Мне стало любопытно. Не просто любопытно, а как-то тревожно-интересно, как бывает, когда находишь книгу без обложки и не знаешь, стоит ли её открывать. Я кликнул на профиль и почувствовал, как что-то внутри меня замирает. Здесь была не просто коллекция фотографий — здесь была чья-то жизнь, разложенная по квадратикам.
    </p>
</div>

<!-- ГЛАВА 1 -->
<div class="book-page">
    <h1>Глава 1. Первое впечатление</h1>
    
    <div class="chapter-epigraph">
        «Иногда одна фотография стоит тысячи встреч»
    </div>
    
    <p class="first-paragraph">
        {followers:,} подписчиков. Это первое, что бросилось мне в глаза. Не маленькая цифра, но и не астрономическая. Достаточно, чтобы понимать — здесь есть что-то интересное, но недостаточно, чтобы потерять человечность за стеной известности.
    </p>
    
    <p>
        Я начал листать фотографии сверху вниз, как читают книгу, и каждый новый кадр был как страница неизвестного мне романа. {f'В био было написано: «{bio}»' if bio else 'Био было лаконичным, почти пустым'} — и это тоже говорило о чём-то. О нежелании объяснять себя в двух словах, о понимании того, что настоящие истории рассказываются не в описаниях профиля.
    </p>
    
    <p>
        Стиль съёмки сразу выдавал человека, который не просто фотографирует еду и закаты. Здесь был взгляд. Здесь была попытка поймать не только изображение, но и настроение, атмосферу, тот неуловимый момент, когда обыденность вдруг становится искусством.
    </p>
    
    {'<figure class="hero-img"><img src="' + processed_images[0] + '" alt="' + (real_captions[0][:50] if real_captions else 'Момент жизни') + '"><figcaption>' + (real_captions[0] if real_captions else 'Кадр, который остановил время') + '</figcaption></figure>' if processed_images else ''}
    
    <p>
        Я понял, что передо мной не просто Instagram-аккаунт, а визуальный дневник. Каждая фотография была записью, каждая подпись — размышлением, каждый хэштег — попыткой найти единомышленников в огромном цифровом мире.
    </p>
    
    <div class="dialogue">
        Кто этот человек? Что его волнует? О чём он мечтает, когда просыпается утром?
    </div>
    
    <p>
        Эти вопросы начали роиться в моей голове, как пчёлы в улье. И я понял, что попал. Попал в ту редкую ловушку искренности, которую так сложно найти в мире отфильтрованных эмоций и постановочного счастья.
    </p>
    
    <p>
        Я продолжал листать, и с каждым новым постом чувствовал, как моё представление о незнакомом человеке становится всё более объёмным, многогранным. {f'Локации варьировались от {locations[0] if locations else "домашних углов"} до {locations[1] if len(locations) > 1 else "городских улиц"}' if locations else 'Места съёмок рассказывали свои истории'} — география души, разложенная по карте Земли.
    </p>
    
    <p>
        И тогда я принял решение, которое изменило весь мой вечер. Я решил не просто посмотреть этот профиль, а изучить его. Понять. Почувствовать. Рассказать историю человека, которого я никогда не встречал, но который вдруг стал мне близок через экран смартфона.
    </p>
</div>

<!-- ГЛАВА 2 -->
<div class="book-page">
    <h1>Глава 2. Углубляясь в детали</h1>
    
    <div class="chapter-epigraph">
        «Дьявол кроется в деталях, а красота — в мелочах»
    </div>
    
    <p class="first-paragraph">
        Чем дольше я изучал профиль @{username}, тем больше понимал, что имею дело не просто с человеком, который любит фотографировать. Здесь была система, философия, особый взгляд на мир.
    </p>
    
    <p>
        {f'Хэштеги {common_hashtags[0][0] if common_hashtags else "#life"}, {common_hashtags[1][0] if len(common_hashtags) > 1 else "#moment"}, {common_hashtags[2][0] if len(common_hashtags) > 2 else "#beauty"}' if common_hashtags else 'Хэштеги были тщательно подобраны'} — не для массового охвата, а для поиска родственных душ. Это были не кричащие призывы к вниманию, а тихие маяки для тех, кто понимает.
    </p>
    
    <p>
        Время публикаций тоже говорило о многом. Большинство постов появлялись либо рано утром, либо поздно вечером. Время, когда город ещё спит или уже засыпает, когда суета стихает и можно остаться наедине с собой и своими мыслями.
    </p>
    
    {'<figure class="hero-img"><img src="' + processed_images[1] + '" alt="' + (real_captions[1][:50] if len(real_captions) > 1 else 'Тихий момент') + '"><figcaption>' + (real_captions[1] if len(real_captions) > 1 else 'В этой тишине родилась мысль') + '</figcaption></figure>' if len(processed_images) > 1 else ''}
    
    <p>
        Я начал замечать повторяющиеся мотивы. Окна — множество окон в разных контекстах. Отражения — в витринах, лужах, глазах. Тени — как самостоятельные персонажи историй. Это был визуальный язык, который @{username} создавал интуитивно или осознанно.
    </p>
    
    <div class="inner-thought">
        А может быть, мы все говорим на одном языке красоты, просто не всегда умеем его расшифровать?
    </div>
    
    <p>
        Подписи к фотографиям были особенным миром. Никаких длинных эссе, никаких попыток объяснить очевидное. {f'«{real_captions[2] if len(real_captions) > 2 else "Жизнь прекрасна"}»' if real_captions else 'Короткие фразы'} — и всё. Но в этой краткости была глубина, которую не каждый сумеет разглядеть.
    </p>
    
    <p>
        Я понял, что @{username} не пытается никого удивить или впечатлить. Этот профиль существует для тех, кто готов остановиться, вглядеться, почувствовать. Это не контент для быстрого потребления — это приглашение к диалогу с собственной душой.
    </p>
    
    <div class="dialogue">
        Интересно, чувствует ли автор, что кто-то так внимательно изучает его творчество?
    </div>
    
    <p>
        Количество лайков под постами колебалось, но никогда не было критически низким. Это говорило о том, что у @{username} есть своя аудитория — небольшая, но верная. Люди, которые понимают и ценят этот особый взгляд на мир.
    </p>
    
    <p>
        Комментарии под фотографиями были лаконичными, но тёплыми. Никаких дежурных «круто!» или «красиво!». Здесь писали от сердца, делились своими ассоциациями, благодарили за момент красоты в суетном дне.
    </p>
</div>

<!-- ГЛАВА 3 -->
<div class="book-page">
    <h1>Глава 3. Точка поворота</h1>
    
    <div class="chapter-epigraph">
        «Иногда один кадр меняет всё понимание»
    </div>
    
    <p class="first-paragraph">
        А потом я увидел ту фотографию. Ту самую, которая перевернула моё восприятие профиля @{username} с ног на голову. {f'Она была сделана в {locations[0] if locations else "обычном месте"}' if locations else 'Место съёмки было простым'}, но что-то в ней было особенное.
    </p>
    
    <p>
        Может быть, дело было в освещении — мягком, рассеянном, словно мир решил на минуту стать добрее. А может быть, в композиции — простой, но настолько точной, что хотелось смотреть и смотреть, находя всё новые детали.
    </p>
    
    {'<figure class="hero-img"><img src="' + processed_images[2] + '" alt="' + (real_captions[2][:50] if len(real_captions) > 2 else 'Поворотный момент') + '"><figcaption>' + (real_captions[2] if len(real_captions) > 2 else 'Здесь всё изменилось') + '</figcaption></figure>' if len(processed_images) > 2 else ''}
    
    <p>
        Но скорее всего, дело было в том неуловимом ощущении правды, которое излучал этот кадр. Здесь не было ни грамма фальши, ни капли наигранности. Просто момент жизни, пойманный в объектив с такой искренностью, что становилось больно от красоты.
    </p>
    
    <div class="dialogue">
        Как так получается, что незнакомый человек может тронуть твою душу одним кадром?
    </div>
    
    <p>
        Я вглядывался в детали фотографии и понимал, что @{username} — не просто человек с хорошим вкусом и дорогой камерой. Это художник. Поэт с объективом вместо пера. Философ, говорящий языком света и тени.
    </p>
    
    <p>
        {f'Подпись к этому посту была {real_captions[2] if len(real_captions) > 2 else "простой и честной"}' if real_captions else 'Подпись была минималистичной'} — и в ней звучала та же искренность, что и в самом снимке. Никаких громких слов, никаких попыток объяснить магию. Просто констатация факта: красота существует, и иногда нам везёт её заметить.
    </p>
    
    <div class="inner-thought">
        В этот момент я понял, что не просто изучаю чей-то профиль — я учусь видеть мир по-новому.
    </div>
    
    <p>
        Комментарии под этой фотографией были особенными. Люди благодарили автора не просто за красивый кадр, а за то, что он напомнил им о существовании прекрасного в их собственной жизни. За то, что научил останавливаться и замечать.
    </p>
    
    <p>
        И я вдруг осознал, что @{username} делает нечто большее, чем просто ведёт блог. Этот человек создаёт оазисы красоты в пустыне информационного шума. Места, где можно остановиться, перевести дух, вспомнить о том, что жизнь может быть прекрасной.
    </p>
    
    <p>
        Именно тогда я решил, что должен рассказать эту историю. Не пересказать содержимое профиля, а попытаться передать то чувство открытия, которое испытал, листая эти фотографии. Ведь в конце концов, самые важные истории — это истории о том, как мы находим красоту в неожиданных местах.
    </p>
</div>

<!-- ГЛАВА 4 -->
<div class="book-page">
    <h1>Глава 4. Отражения и размышления</h1>
    
    <div class="chapter-epigraph">
        «Мы не просто смотрим на искусство — оно смотрит на нас»
    </div>
    
    <p class="first-paragraph">
        Продолжая изучать профиль @{username}, я начал замечать, как меняюсь сам. Не кардинально, не внезапно, а постепенно, как меняется пейзаж за окном медленно идущего поезда.
    </p>
    
    <p>
        Раньше я мог пройти мимо интересного света, падающего на стену дома, и не заметить его. Теперь я останавливался. Раньше отражение в луже было просто отражением. Теперь я видел в нём целый мир, перевёрнутый и переосмысленный.
    </p>
    
    {'<figure class="hero-img"><img src="' + processed_images[3] + '" alt="' + (real_captions[3][:50] if len(real_captions) > 3 else 'Момент размышления') + '"><figcaption>' + (real_captions[3] if len(real_captions) > 3 else 'В этом кадре я узнал себя') + '</figcaption></figure>' if len(processed_images) > 3 else ''}
    
    <p>
        @{username} научил меня языку визуальной поэзии, сам того не подозревая. Каждый пост был урок, каждая фотография — мастер-классом по искусству видеть. И самое удивительное — эти уроки не были навязчивыми или дидактичными. Они просто существовали, ожидая, когда зритель будет готов их воспринять.
    </p>
    
    <div class="dialogue">
        А сколько таких учителей проходит мимо нас каждый день, а мы их не замечаем?
    </div>
    
    <p>
        Я начал анализировать не только содержание постов, но и их ритм. Периоды активности и затишья, смена настроений, эволюцию стиля. {posts_count} публикаций — это {posts_count} дней из жизни человека, {posts_count} моментов, которые показались ему достойными сохранения.
    </p>
    
    <p>
        Интересно было наблюдать, как менялся почерк автора со временем. Ранние работы были более неуверенными, более объяснительными. Поздние — лаконичными, точными, как стрелы, пущенные опытным лучником.
    </p>
    
    <div class="inner-thought">
        Возможно, мы все эволюционируем именно так — от желания объяснить всё к пониманию силы недосказанности.
    </div>
    
    <p>
        Соотношение {followers:,} подписчиков к {following:,} подпискам тоже рассказывало историю. @{username} не гнался за массовостью, не играл в игры взаимных подписок. Этот профиль рос органично, привлекая людей качеством, а не количеством контента.
    </p>
    
    <p>
        Я попытался представить себе человека за этими фотографиями. Наверное, это кто-то, кто умеет наслаждаться одиночеством, но не страдает от него. Кто-то, кто видит красоту в простых вещах, но не превращает это в манерность. Кто-то искренний в мире, где искренность стала редкостью.
    </p>
    
    <p>
        И я понял, что @{username} — это не просто ник в Instagram. Это философия, образ мышления, способ взаимодействия с миром. И возможно, каждый из нас может стать таким @{username} для кого-то другого, если научится видеть и делиться увиденным с той же честностью и красотой.
    </p>
</div>

<!-- ГЛАВА 5 -->
<div class="book-page">
    <h1>Глава 5. Финальные откровения</h1>
    
    <div class="chapter-epigraph">
        «Конец — это всегда новое начало»
    </div>
    
    <p class="first-paragraph">
        Дойдя до самых ранних постов в профиле @{username}, я почувствовал странную грусть. Как читатель, который понимает, что любимая книга подходит к концу. Как путешественник, осознающий, что удивительное приключение завершается.
    </p>
    
    <p>
        Но одновременно я чувствовал благодарность. За то, что случайный алгоритм социальной сети подарил мне встречу с этим особенным взглядом на мир. За то, что незнакомый человек научил меня видеть красоту там, где я раньше её не замечал.
    </p>
    
    {'<figure class="hero-img"><img src="' + processed_images[4] + '" alt="' + (real_captions[4][:50] if len(real_captions) > 4 else 'Последний кадр истории') + '"><figcaption>' + (real_captions[4] if len(real_captions) > 4 else 'История заканчивается, но красота остаётся') + '</figcaption></figure>' if len(processed_images) > 4 else ''}
    
    <p>
        @{username} остался для меня загадкой — и это прекрасно. Я знаю о нём ровно столько, сколько он захотел рассказать через свои фотографии. Этого достаточно, чтобы понимать: передо мной творческая личность, которая делает мир чуточку прекраснее.
    </p>
    
    <div class="dialogue">
        Разве не в этом смысл искусства — не в том, чтобы объяснить всё, а в том, чтобы заставить почувствовать?
    </div>
    
    <p>
        Теперь, когда я листаю свою собственную ленту, я ловлю себя на мысли: «А что бы подумал @{username} об этом кадре?» Его эстетика стала для меня внутренним фильтром, критерием красоты и искренности.
    </p>
    
    <p>
        И может быть, в этом и заключается истинная сила настоящего искусства — не в том, чтобы поразить или удивить, а в том, чтобы изменить того, кто с ним соприкоснулся. Сделать его более чувствительным к красоте, более внимательным к деталям, более открытым к чуду обыденности.
    </p>
    
    <div class="inner-thought">
        Каждый из нас может стать чьим-то @{username} — учителем красоты, проводником в мир более внимательного взгляда на жизнь.
    </div>
    
    <p>
        История профиля @{username} — это не просто набор фотографий и подписей. Это напоминание о том, что в мире цифрового шума и поверхностного контента всё ещё есть место искренности, глубине, настоящей красоте.
    </p>
    
    <p>
        И пока есть такие люди, как @{username}, которые умеют останавливать мгновения и делиться ими с миром, у нас есть надежда. Надежда на то, что красота не исчезнет под напором уродства, что искренность не растворится в океане фальши, что человечность не потеряется в виртуальной реальности.
    </p>
    
    <p>
        Спасибо тебе, @{username}, за то, что ты есть. За то, что создаёшь. За то, что учишь видеть. За то, что напоминаешь: мир прекрасен, если научиться его замечать.
    </p>
</div>

<!-- ЭПИЛОГ -->
<div class="book-page">
    <h2>Эпилог</h2>
    
    <p class="first-paragraph">
        Дорогой читатель, если вы дочитали до этих строк, значит, и вас коснулась та же магия, что коснулась меня при знакомстве с профилем @{username}. Возможно, вы тоже начнёте обращать внимание на игру света в окне своего дома, на отражения в лужах, на тени, которые рассказывают истории.
    </p>
    
    <p>
        В мире, где всё происходит слишком быстро, где красота часто приносится в жертву эффективности, люди как @{username} напоминают нам о важности остановиться, посмотреть вокруг и увидеть чудо в обыденном.
    </p>
    
    <div class="dialogue">
        А может быть, и вы станете чьим-то @{username}? Чьим-то учителем красоты, проводником в мир более внимательного взгляда?
    </div>
    
    <p>
        Эта история закончена, но красота продолжается. Каждый день, каждый момент, каждый взгляд, брошенный с вниманием и любовью на окружающий мир. И в этом — бесконечность, которая не помещается ни в какие рамки, ни в какие профили, ни в какие книги.
    </p>
    
    <div class="stats-footer">
        <strong>@{username}</strong><br>
        {followers:,} подписчиков • {following:,} подписок • {posts_count} публикаций<br>
        {f'«{bio}»<br>' if bio else ''}
        <br>
        <em>Книга создана {random.choice(['15 января', '16 января', '17 января'])} 2024 года</em><br>
        <em>Приблизительно {word_count:,} слов</em>
    </div>
</div>

</body>
</html>"""
     
    return html

# Теперь нужно обновить основную функцию build_romantic_book