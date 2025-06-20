import json
import base64
from io import BytesIO
from pathlib import Path
from PIL import Image, ImageFilter, ImageEnhance, ImageDraw, ImageFont
from app.services.llm_client import generate_text
import markdown
import pdfkit
import qrcode
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from typing import List, Tuple

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
        
        # Создаем Markdown версию
        markdown_content = create_markdown_from_content(romantic_content, analysis, actual_images)
        
        # Сохраняем файлы
        out = Path("data") / run_id
        out.mkdir(parents=True, exist_ok=True)
        
        # Сохраняем HTML файл
        html_file = out / "book.html"
        html_file.write_text(html, encoding="utf-8")
        
        # Сохраняем Markdown файл
        markdown_file = out / "book.md"
        markdown_file.write_text(markdown_content, encoding="utf-8")
        
        # Создаем PDF через Markdown → HTML → PDF
        try:
            print("📄 Создаем PDF через Markdown...")
            
            # Конвертируем Markdown в HTML с красивым стилем
            markdown_html = markdown.markdown(markdown_content, extensions=['tables', 'toc'])
            
            # Добавляем стили для PDF
            styled_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>Книга @{analysis.get("username", "")}</title>
                <style>
                    body {{
                        font-family: 'Crimson Text', serif;
                        line-height: 1.8;
                        color: #1a1a1a;
                        background: white;
                        margin: 0;
                        padding: 40px;
                        max-width: 800px;
                        margin: 0 auto;
                    }}
                    
                    h1 {{
                        font-family: 'Playfair Display', serif;
                        font-size: 2.5em;
                        color: #1a1a1a;
                        text-align: center;
                        margin-bottom: 10px;
                    }}
                    
                    h2 {{
                        font-family: 'Playfair Display', serif;
                        font-size: 2em;
                        color: #1a1a1a;
                        border-bottom: 2px solid #666666;
                        padding-bottom: 10px;
                        margin-top: 40px;
                    }}
                    
                    h3 {{
                        font-family: 'Playfair Display', serif;
                        font-size: 1.4em;
                        color: #1a1a1a;
                        margin-top: 30px;
                    }}
                    
                    p {{
                        font-size: 12pt;
                        text-align: justify;
                        margin-bottom: 15px;
                        text-indent: 1.5em;
                    }}
                    
                    blockquote {{
                        background: #f8f9fa;
                        border-left: 4px solid #666666;
                        padding: 15px 20px;
                        margin: 20px 0;
                        font-style: italic;
                        border-radius: 5px;
                    }}
                    
                    table {{
                        width: 100%;
                        border-collapse: collapse;
                        margin: 20px 0;
                        background: white;
                        border-radius: 8px;
                        overflow: hidden;
                    }}
                    
                    th, td {{
                        padding: 12px;
                        text-align: left;
                        border-bottom: 1px solid #e9ecef;
                    }}
                    
                    th {{
                        background: #1a1a1a;
                        color: white;
                        font-weight: 600;
                    }}
                    
                    code {{
                        background: #1a1a1a;
                        color: white;
                        padding: 3px 8px;
                        border-radius: 12px;
                        font-size: 0.9em;
                        margin: 2px;
                        display: inline-block;
                    }}
                </style>
            </head>
            <body>
                {markdown_html}
            </body>
            </html>
            """
            
            # Сохраняем HTML версию для PDF
            pdf_html_file = out / "book_for_pdf.html"
            pdf_html_file.write_text(styled_html, encoding="utf-8")
            
            # Конфигурация для wkhtmltopdf
            options = {
                'page-size': 'A4',
                'margin-top': '1.5cm',
                'margin-right': '1.5cm',
                'margin-bottom': '1.5cm',
                'margin-left': '1.5cm',
                'encoding': "UTF-8",
                'no-outline': None,
                'enable-local-file-access': None,
                'print-media-type': None,
                'disable-smart-shrinking': None,
                'header-center': f'Instagram книга @{analysis.get("username", "")}',
                'header-font-size': '10',
                'header-spacing': '10',
                'footer-center': '[page] из [topage]',
                'footer-font-size': '10',
                'footer-spacing': '10'
            }
            
            # Создаем PDF
            pdfkit.from_file(str(pdf_html_file), str(out / "book.pdf"), options=options)
            
            print(f"✅ Минималистичная книга создана!")
            print(f"📄 PDF версия: {out / 'book.pdf'}")
            print(f"📝 Markdown версия: {out / 'book.md'}")
            print(f"📖 HTML версия: {out / 'book.html'}")
            
        except Exception as pdf_error:
            print(f"❌ Ошибка при создании PDF: {pdf_error}")
            print(f"📖 Доступны Markdown и HTML версии")
        
    except Exception as e:
        print(f"❌ Ошибка при создании книги: {e}")
        # Создаем базовую версию
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
            
            print(f"✅ Создана базовая версия: {out / 'book.html'}")
            
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

def generate_romantic_content(analysis: dict, images: list[Path]) -> dict:
    """Генерирует романтический контент на основе РЕАЛЬНЫХ данных Instagram"""
    
    # Безопасное извлечение данных с fallback значениями
    username = analysis.get('username', 'Неизвестный')
    full_name = analysis.get('full_name', username)
    bio = analysis.get('bio', '')
    followers = max(0, analysis.get('followers', 0))
    following = max(0, analysis.get('following', 0))
    posts_count = max(0, analysis.get('posts_count', 0))
    total_likes = max(0, analysis.get('total_likes', 0))
    total_comments = max(0, analysis.get('total_comments', 0))
    
    # Реальные данные из Instagram с проверками
    real_captions = analysis.get('captions', [])[:10] if analysis.get('captions') else ['Прекрасный момент жизни']
    common_hashtags = analysis.get('common_hashtags', [])[:5] if analysis.get('common_hashtags') else [('beautiful', 1), ('life', 1)]
    mentioned_users = analysis.get('mentioned_users', [])[:5] if analysis.get('mentioned_users') else []
    locations = analysis.get('locations', [])[:5] if analysis.get('locations') else ['Неизвестное место']
    most_liked = analysis.get('most_liked_post')
    most_commented = analysis.get('most_commented_post')
    
    # Создаем контекст на основе РЕАЛЬНЫХ данных
    instagram_context = f"""
    === РЕАЛЬНЫЙ ПРОФИЛЬ INSTAGRAM ===
    Имя: @{username} ({full_name})
    {f"Описание: {bio}" if bio else ""}
    Подписчики: {followers:,} человек
    Подписки: {following:,} аккаунтов
    Публикаций: {posts_count} постов
    Общие лайки: {total_likes:,}
    Общие комментарии: {total_comments:,}
    
    === РЕАЛЬНЫЕ ПОДПИСИ К ПОСТАМ ===
    {chr(10).join([f'"{caption}"' for caption in real_captions[:5] if caption and len(caption.strip()) > 0])}
    
    === ПОПУЛЯРНЫЕ ХЭШТЕГИ ===
    {', '.join([f'#{hashtag[0]} ({hashtag[1]}x)' for hashtag in common_hashtags if hashtag and len(hashtag) >= 2])}
    
    === УПОМИНАНИЯ ДРУЗЕЙ ===
    {', '.join([f'@{user}' for user in mentioned_users if user and len(user.strip()) > 0])}
    
    === ПОСЕЩЕННЫЕ МЕСТА ===
    {', '.join([loc for loc in locations if loc and len(loc.strip()) > 0])}
    
    === САМЫЙ ПОПУЛЯРНЫЙ ПОСТ ===
    {f'"{most_liked["caption"]}" - {most_liked["likes"]} лайков' if most_liked and most_liked.get("caption") else "Самые яркие моменты жизни"}
    """
    
    # Улучшенные промпты с защитой от ошибок
    prompts = {
        "prologue": f"""
        Напиши пролог автора (1 страница) - почему мы создаем такие Instagram-книги.
        
        Расскажи:
        - Как социальные сети стали новой формой искусства
        - Почему каждый профиль заслуживает быть книгой
        - Философию превращения цифровых моментов в осязаемые воспоминания
        
        Стиль: Вдохновляющий, философский, с английскими вставками voice-over.
        Структура: 2-3 коротких предложения, затем 1 длинная фраза, затем цитата.
        Максимум 500 слов.
        """,
        
        "title": f"""
        Создай поэтическое название для Instagram-книги @{username}.
        Используй данные: {bio if bio else 'творческая душа'}
        Максимум 4 слова, с намеком на кинематографичность.
        """,
        
        "chapter1_frame": f"""
        Глава 1 - КАДР. Опиши визуальный стиль @{username} как кинорежиссер.
        
        ДАННЫЕ: {posts_count} постов, хэштеги: {', '.join([f'#{h[0]}' for h in common_hashtags[:3] if h and len(h) >= 2])}
        
        Структура:
        - Кадр: как они компонуют фотографии
        - Эмоция: какие чувства передают
        - Урок: чему учит их визуальный язык
        
        Добавь режиссерские ремарки курсивом: "Cut — держите кадр так, чтобы..."
        Максимум 800 слов.
        """,
        
        "chapter2_emotion": f"""
        Глава 2 - ЭМОЦИЯ. Анализ эмоционального слоя @{username}.
        
        ПОДПИСИ: {chr(10).join([f'"{caption[:100]}..."' for caption in real_captions[:3] if caption and len(caption.strip()) > 0])}
        
        Структура по подпунктам:
        - Кадр: какие эмоции видны на фото
        - Эмоция: как подписи раскрывают внутренний мир  
        - Урок: как найти красоту в повседневности
        
        Чередуй короткие и длинные предложения. Добавь voice-over на английском.
        Максимум 800 слов.
        """,
        
        "chapter3_journey": f"""
        Глава 3 - ПУТЕШЕСТВИЕ. География души через локации.
        
        МЕСТА: {', '.join([loc for loc in locations if loc and len(loc.strip()) > 0]) if any(loc and len(loc.strip()) > 0 for loc in locations) else 'удивительные места'}
        
        Подпункты:
        - Кадр: как места формируют кадр
        - Эмоция: что ищет душа в путешествиях
        - Урок: как география влияет на характер
        Максимум 800 слов.
        """,
        
        "chapter4_community": f"""
        Глава 4 - СООБЩЕСТВО. Связи через экран.
        
        ДАННЫЕ: {followers:,} подписчиков, упоминания {', '.join(mentioned_users[:3]) if mentioned_users else 'близких друзей'}
        
        - Кадр: как выглядит цифровое сообщество
        - Эмоция: теплота человеческих связей онлайн
        - Урок: построение подлинных отношений в сети
        Максимум 800 слов.
        """,
        
        "chapter5_legacy": f"""
        Глава 5 - НАСЛЕДИЕ. Что останется от цифрового следа.
        
        ИТОГИ: {posts_count} постов = жизненная история
        
        - Кадр: как посты складываются в биографию
        - Эмоция: ценность сохраненных моментов
        - Урок: создание осмысленного цифрового наследия
        
        Финальная режиссерская ремарка о вечности мгновений.
        Максимум 800 слов.
        """
    }
    
    # Генерируем контент с улучшенной обработкой ошибок
    content = {}
    for key, prompt in prompts.items():
        print(f"💕 Создаем {key} с защитой от ошибок...")
        try:
            generated_text = generate_text(prompt, max_tokens=1500)
            
            if generated_text and len(generated_text.strip()) > 20:
                # Применяем улучшения ритма и voice-over
                generated_text = add_text_rhythm(generated_text)
                generated_text = add_english_voiceover(generated_text)
                content[key] = generated_text
            else:
                raise ValueError("Пустой или слишком короткий ответ от AI")
                
        except Exception as e:
            print(f"❌ Ошибка при генерации {key}: {e}")
            # Используем улучшенные резервные тексты
            fallbacks = {
                "prologue": f"""В эпоху цифровых историй каждый профиль Instagram становится уникальной книгой. Пиксели превращаются в память. Лайки становятся наследием. <blockquote>"Мы живем в мире, где каждый момент может стать искусством."</blockquote> *Digital soul meets paper heart.* Эта книга — мост между виртуальным и вещественным, между мгновением и вечностью.""",
                
                "title": f"Кадры жизни @{username}",
                
                "chapter1_frame": f"""*Cut — камера ловит свет в глазах @{username}.* Каждый из {posts_count if posts_count > 0 else '1'} постов — это режиссерское решение. Кадр говорит больше слов. Композиция рассказывает истории. <blockquote>"Великая фотография — это та, что заставляет остановиться и почувствовать."</blockquote> *Frame perfect.* Урок: в каждом кадре живет целая вселенная.""",
                
                "chapter2_emotion": f"""Подписи @{username} — это поэзия современности. Короткие строки. Длинные размышления о жизни. <blockquote>"Слова под фотографией — это окно в душу автора."</blockquote> *Pure emotion.* Каждая подпись раскрывает тайны сердца.""",
                
                "chapter3_journey": f"""География @{username}: {', '.join(locations[:2]) if locations and any(loc.strip() for loc in locations) else 'неизведанные тропы'}. Каждое место оставляет отпечаток в душе. Кадр меняется с широтой. <blockquote>"Мы путешествуем, чтобы найти себя."</blockquote> *Wanderlust in pixels.*""",
                
                "chapter4_community": f"""{format_statistics_creatively('followers', followers)} образуют уникальную аудиторию. Цифровая близость рождает настоящие чувства. Каждый лайк — связь. <blockquote>"Технологии лучше всего работают, когда объединяют сердца."</blockquote> *Connection beyond screens.*""",
                
                "chapter5_legacy": f"""Что останется от наших Instagram-историй? {posts_count if posts_count > 0 else 'Каждый'} пост — капсула времени. Цифровое наследие обретает физическую форму. <blockquote>"Мы создаем будущее из пикселей прошлого."</blockquote> *Forever captured.* *Final cut — и камера отъезжает, оставляя вечность мгновений...*"""
            }
            content[key] = fallbacks.get(key, "Прекрасная история...")
    
    return content

def create_romantic_book_html(content: dict, analysis: dict, images: list[Path]) -> str:
    """Создает HTML книгу в стиле настоящей печатной книги с белым фоном"""
    
    username = analysis.get('username', 'Неизвестный')
    full_name = analysis.get('full_name', username)
    followers = analysis.get('followers', 0)
    following = analysis.get('following', 0)
    posts_count = analysis.get('posts_count', 0)
    bio = analysis.get('bio', '')
    verified = analysis.get('verified', False)
    
    # Обрабатываем изображения в классическом стиле
    processed_images = []
    
    for i, img_path in enumerate(images[:8]):
        if img_path.exists():
            try:
                with Image.open(img_path) as img:
                    # Простая обработка для книжного качества
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    
                    # Изменяем размер для книжного формата
                    img.thumbnail((800, 600), Image.Resampling.LANCZOS)
                    
                    # Легкое улучшение контраста для печати
                    enhancer = ImageEnhance.Contrast(img)
                    img = enhancer.enhance(1.05)
                    
                    # Конвертируем в base64
                    buffer = BytesIO()
                    img.save(buffer, format='JPEG', quality=95)
                    img_str = base64.b64encode(buffer.getvalue()).decode()
                    processed_images.append(f"data:image/jpeg;base64,{img_str}")
            except Exception as e:
                print(f"❌ Ошибка при обработке изображения {img_path}: {e}")
    
    # Реальные данные для любовной истории
    real_captions = analysis.get('captions', ['Прекрасный момент'])[:6]
    locations = analysis.get('locations', ['Неизвестное место'])[:5]
    
    # HTML книги в классическом стиле
    html = f"""
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <title>Книга о @{username}</title>
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Crimson+Text:ital,wght@0,400;0,600;1,400&family=Playfair+Display:wght@400;700&family=Cormorant+Garamond:ital,wght@0,400;0,500;1,400&display=swap" rel="stylesheet">
        
        <style>
        body {{
            font-family: 'Crimson Text', serif;
            font-size: 12pt;
            line-height: 1.8;
            color: #1a1a1a;
            background: white;
            margin: 0;
            padding: 0;
            max-width: 800px;
            margin: 0 auto;
        }}
        
        .page {{
            min-height: 90vh;
            padding: 3cm 2.5cm;
            margin-bottom: 2cm;
            page-break-after: always;
            background: white;
            border: none;
        }}
        
        .page:last-child {{
            page-break-after: auto;
        }}
        
        h1 {{
            font-family: 'Playfair Display', serif;
            font-size: 28pt;
            text-align: center;
            margin: 4cm 0 2cm 0;
            color: #1a1a1a;
            font-weight: 400;
            letter-spacing: 1px;
        }}
        
        h2 {{
            font-family: 'Playfair Display', serif;
            font-size: 18pt;
            color: #1a1a1a;
            margin: 3cm 0 1.5cm 0;
            text-align: left;
            font-weight: 400;
        }}
        
        h3 {{
            font-family: 'Playfair Display', serif;
            font-size: 14pt;
            color: #1a1a1a;
            margin: 2cm 0 1cm 0;
            font-weight: 400;
        }}
        
        .chapter-number {{
            font-family: 'Cormorant Garamond', serif;
            font-size: 14pt;
            color: #666;
            text-align: center;
            margin-bottom: 1cm;
            font-style: italic;
        }}
        
        p {{
            margin: 0 0 1.5em 0;
            text-align: justify;
            text-indent: 2em;
        }}
        
        .first-paragraph {{
            text-indent: 0;
            font-size: 13pt;
        }}
        
        .drop-cap {{
            float: left;
            font-family: 'Playfair Display', serif;
            font-size: 72pt;
            line-height: 60pt;
            padding-right: 8pt;
            margin-top: 4pt;
            color: #1a1a1a;
        }}
        
        blockquote {{
            font-style: italic;
            margin: 2em 3em;
            padding: 0;
            border: none;
            text-align: center;
            font-size: 11pt;
            color: #444;
        }}
        
        .quote-author {{
            text-align: right;
            margin-top: 1em;
            font-size: 10pt;
            color: #666;
        }}
        
        .photo-page {{
            text-align: center;
            page-break-inside: avoid;
        }}
        
        .photo {{
            margin: 2cm 0 1.5cm 0;
            text-align: center;
        }}
        
        .photo img {{
            max-width: 100%;
            max-height: 400px;
            border: 1px solid #ddd;
            padding: 10px;
            background: white;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        
        .photo-caption {{
            font-family: 'Cormorant Garamond', serif;
            font-style: italic;
            font-size: 11pt;
            color: #666;
            margin-top: 1cm;
            text-align: center;
        }}
        
        .photo-inline {{
            float: right;
            margin: 0 0 1em 2em;
            width: 300px;
        }}
        
        .photo-inline img {{
            width: 100%;
            border: 1px solid #ddd;
            padding: 8px;
            background: white;
            box-shadow: 0 2px 6px rgba(0,0,0,0.08);
        }}
        
        .stats-elegant {{
            margin: 2cm 0;
            text-align: center;
            font-family: 'Cormorant Garamond', serif;
            font-size: 11pt;
            color: #666;
        }}
        
        .dedication {{
            text-align: center;
            font-style: italic;
            margin: 4cm 0;
            font-size: 12pt;
            color: #666;
        }}
        
        .chapter-separator {{
            text-align: center;
            margin: 3cm 0;
            font-size: 14pt;
            color: #ccc;
        }}
        
        .page-number {{
            position: absolute;
            bottom: 2cm;
            right: 2.5cm;
            font-size: 10pt;
            color: #999;
        }}
        
        @media print {{
            body {{
                margin: 0;
                padding: 0;
            }}
            .page {{
                page-break-after: always;
                margin: 0;
                box-shadow: none;
            }}
        }}
        </style>
    </head>
    <body>

    <!-- ОБЛОЖКА -->
    <div class="page">
        <h1>{content.get('title', f'История @{username}')}</h1>
        
        <div class="dedication">
            <em>Посвящается тем моментам,<br>
            что делают жизнь прекрасной</em>
        </div>
        
        <div style="position: absolute; bottom: 4cm; left: 50%; transform: translateX(-50%); text-align: center;">
            <p style="font-family: 'Cormorant Garamond', serif; font-size: 11pt; color: #999; margin: 0;">
                Книга создана с любовью<br>
                {full_name if full_name != username else username}
            </p>
        </div>
    </div>

    <!-- ПРОЛОГ -->
    <div class="page">
        <div class="chapter-number">Пролог</div>
        <h2>О красоте мгновений</h2>
        
        <p class="first-paragraph">
            <span class="drop-cap">В</span> каждой жизни есть моменты, которые хочется сохранить навсегда. Они приходят незаметно — в утреннем свете, падающем на лицо, в смехе с друзьями, в тишине вечернего города. Instagram стал нашим способом ловить эти мгновения, но экран не может передать всю их глубину.
        </p>
        
        <p>
            Эта книга — попытка вернуть цифровым воспоминаниям их настоящий вес. Здесь каждая фотография обретает новую жизнь, каждая подпись становится строчкой в большой истории. Это не просто сборник постов — это летопись души, записанная светом и словами.
        </p>
        
        <blockquote>
            "Фотография — это секрет о секрете. Чем больше она рассказывает, тем меньше вы знаете."
            <div class="quote-author">— Дайан Арбус</div>
        </blockquote>
        
        <p>
            Переворачивая страницы этой книги, мы путешествуем по внутреннему миру @{username}, где каждый кадр — это окно в уникальную вселенную чувств и переживаний.
        </p>
    </div>

    <!-- ГЛАВА 1: ПОРТРЕТ -->
    <div class="page">
        <div class="chapter-number">Глава первая</div>
        <h2>Портрет в цифровую эпоху</h2>
        
        <p class="first-paragraph">
            <span class="drop-cap">@</span>{username} — это имя, за которым скрывается {full_name if full_name != username else 'удивительная личность'}. В мире Instagram, где миллионы голосов звучат одновременно, этот профиль выделяется своей искренностью и глубиной.
        </p>
        
        <div class="stats-elegant">
            {format_statistics_creatively('followers', followers)}<br>
            {format_statistics_creatively('posts', posts_count)}<br>
            {"✓ Подтвержденный аккаунт" if verified else ""}
        </div>
        
        <p>
            {bio if bio else 'Биография может быть пустой, но жизнь, отраженная в фотографиях, говорит громче любых слов.'}
        </p>
        
        <p>
            В каждом посте читается характер автора. Выбор кадра, игра света и тени, момент, который показался достойным сохранения — все это создает портрет современного человека, живущего на пересечении реального и виртуального миров.
        </p>
        
        <blockquote>
            "Каждая фотография — это автопортрет души фотографа."
        </blockquote>
    </div>"""
    
    # Добавляем фотографии в элегантном книжном стиле
    for i, img_base64 in enumerate(processed_images):
        caption = real_captions[i] if i < len(real_captions) else f'Момент {i+1}'
        
        # Чередуем полностраничные фото и встроенные
        if i % 2 == 0:
            # Полностраничное фото
            html += f"""
    
    <div class="page photo-page">
        <div class="photo">
            <img src="{img_base64}" alt="Фотография {i+1}">
        </div>
        
        <div class="photo-caption">
            {caption}
        </div>
        
        <p style="margin-top: 2cm; font-style: italic; text-align: center; color: #666;">
            Каждая фотография — это остановленное время, момент, который больше никогда не повторится. В этом кадре живет частичка души, переданная через объектив в наши сердца.
        </p>
    </div>"""
        else:
            # Встроенное фото с текстом
            html += f"""
    
    <div class="page">
        <div class="photo-inline">
            <img src="{img_base64}" alt="Фотография {i+1}">
            <div class="photo-caption" style="margin-top: 0.5cm; font-size: 10pt;">
                {caption}
            </div>
        </div>
        
        <p class="first-paragraph">
            <span class="drop-cap">Э</span>тот снимок рассказывает историю без слов. В композиции кадра читается настроение момента, в игре света и тени — эмоции автора. Фотография становится мостом между внутренним миром @{username} и нами, зрителями.
        </p>
        
        <p>
            Искусство фотографии заключается не в технических параметрах камеры, а в способности увидеть необычное в обычном, поймать ускользающую красоту повседневности. Каждый кадр в этой коллекции — свидетельство того, что красота окружает нас везде, нужно только научиться её замечать.
        </p>
        
        <p>
            Подпись к фотографии — это не просто описание изображенного. Это ключ к пониманию того, что чувствовал автор в момент съемки, что хотел передать зрителю. Слова и изображение дополняют друг друга, создавая полную картину переживания.
        </p>
    </div>"""
    
    # Добавляем главы о путешествиях и местах
    html += f"""
    
    <!-- ГЛАВА 2: ГЕОГРАФИЯ ДУШИ -->
    <div class="page">
        <div class="chapter-number">Глава вторая</div>
        <h2>География души</h2>
        
        <p class="first-paragraph">
            <span class="drop-cap">М</span>еста, которые мы выбираем для фотографий, рассказывают о нас не меньше, чем наши лица. В галерее @{username} запечатлены локации, каждая из которых имеет свою историю и значение.
        </p>
        
        <p>
            {chr(10).join([f"<em>{location}</em> — место, где время останавливается, где каждый кадр наполнен особым смыслом." for location in locations[:3]])}
        </p>
        
        <p>
            Путешествия в Instagram — это не только смена декораций. Это внутренние путешествия, открытия новых граней себя в новых обстоятельствах. Каждое место оставляет отпечаток в душе, меняет нас, заставляет взглянуть на мир под другим углом.
        </p>
        
        <blockquote>
            "Мы путешествуем не для того, чтобы убежать от жизни, а для того, чтобы жизнь не убежала от нас."
        </blockquote>
        
        <p>
            В эпоху цифровых технологий фотография из путешествий становится способом поделиться не только видом, но и чувством. Через кадр передается атмосфера места, его энергетика, то неуловимое ощущение, которое невозможно описать словами.
        </p>
    </div>

    <!-- ГЛАВА 3: ЯЗЫК ЭМОЦИЙ -->
    <div class="page">
        <div class="chapter-number">Глава третья</div>
        <h2>Язык эмоций</h2>
        
        <p class="first-paragraph">
            <span class="drop-cap">П</span>одписи к фотографиям в Instagram — это новая форма поэзии. Краткие, емкие, они передают целую гамму чувств в нескольких словах. @{username} владеет этим языком в совершенстве.
        </p>
        
        <p>
            Каждая подпись — это ключ к пониманию внутреннего мира автора. В них звучат размышления о жизни, любви, дружбе, мечтах. Это честный разговор с миром, где эмоции важнее правильности формулировок.
        </p>
        
        <div style="margin: 2cm 0; font-style: italic; color: #666; text-align: center;">
            {chr(10).join([f'"{caption}"' for caption in real_captions[:3]])}
        </div>
        
        <p>
            В этих строчках живет поэзия современности — искренняя, непосредственная, идущая от сердца. Они напоминают нам, что в эпоху цифровых технологий человеческие эмоции остаются главной ценностью.
        </p>
        
        <blockquote>
            "Лучшие слова — те, что идут от сердца к сердцу."
        </blockquote>
    </div>

    <!-- ФИНАЛЬНАЯ ГЛАВА -->
    <div class="page">
        <div class="chapter-number">Эпилог</div>
        <h2>Что останется</h2>
        
        <p class="first-paragraph">
            <span class="drop-cap">К</span>огда-нибудь серверы Instagram перестанут работать, приложения устареют, а цифровые файлы исчезнут. Но эта книга останется — как свидетельство времени, как хроника души, как доказательство того, что красота была здесь.
        </p>
        
        <p>
            Каждая страница этой книги — попытка остановить время, сохранить мгновения, которые делают жизнь @{username} уникальной и прекрасной. В мире, где все ускоряется, где внимание рассеивается между тысячами постов, эта книга предлагает остановиться и всмотреться.
        </p>
        
        <p>
            Здесь нет лайков и комментариев, нет алгоритмов и рекламы. Есть только чистая человеческая история, рассказанная светом и словами. История о том, как прекрасна может быть обычная жизнь, если научиться видеть её красоту.
        </p>
        
        <blockquote>
            "Самые важные моменты жизни случаются между кадрами."
        </blockquote>
        
        <p>
            Пусть эта книга станет напоминанием о том, что каждый день полон чудес, каждый момент достоин внимания, каждая жизнь — уникальная и бесценная история, заслуживающая быть рассказанной.
        </p>
        
        <div class="dedication" style="margin-top: 4cm;">
            <em>Конец первой главы.<br>
            Продолжение следует...</em>
        </div>
    </div>

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
