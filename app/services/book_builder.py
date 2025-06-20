import json
import base64
from io import BytesIO
from pathlib import Path
from PIL import Image, ImageFilter, ImageEnhance, ImageDraw, ImageFont
from app.services.llm_client import generate_text, analyze_photo
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
    """Генерирует романтический контент на основе РЕАЛЬНЫХ данных Instagram с анализом фотографий"""
    
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
    
    # Анализируем фотографии с помощью OpenAI Vision
    photo_analyses = []
    context = f"Instagram профиль @{username}, подписчики: {followers}, био: {bio}"
    
    for i, img_path in enumerate(images[:6]):
        if img_path.exists():
            try:
                analysis_text = analyze_photo(img_path, context)
                photo_analyses.append(analysis_text)
                print(f"📸 Анализ фото {i+1}: {analysis_text[:100]}...")
            except Exception as e:
                print(f"❌ Ошибка анализа фото {img_path}: {e}")
                photo_analyses.append("Прекрасный момент, полный эмоций и красоты")
    
    # Создаем уникальные данные для каждой главы
    data_for_chapters = {
        'username': username,
        'full_name': full_name,
        'bio': bio,
        'followers': followers,
        'posts_count': posts_count,
        'captions': real_captions,
        'locations': locations,
        'mentioned_users': mentioned_users,
        'total_likes': total_likes,
        'photo_analyses': photo_analyses
    }
    
    # Генерируем уникальный контент с помощью OpenAI
    from app.services.llm_client import generate_unique_chapter
    
    content = {}
    generated_texts = []  # Для отслеживания уже созданных текстов
    
    # Пролог
    print(f"💕 Создаем уникальный пролог...")
    try:
        prologue = generate_unique_chapter("intro", data_for_chapters, generated_texts)
        content['prologue'] = prologue
        generated_texts.append(prologue[:200])  # Запоминаем начало для избежания повторений
    except Exception as e:
        print(f"❌ Ошибка при генерации пролога: {e}")
        content['prologue'] = f"В мире миллионов профилей @{username} создает свою неповторимую историю. Каждый пост здесь — это страница дневника, написанная светом и эмоциями."
    
    # Заголовок
    content['title'] = f"Визуальная поэзия @{username}"
    
    # Глава об эмоциях  
    print(f"💕 Создаем главу об эмоциях...")
    try:
        emotions_chapter = generate_unique_chapter("emotions", data_for_chapters, generated_texts)
        content['emotions'] = emotions_chapter
        generated_texts.append(emotions_chapter[:200])
    except Exception as e:
        print(f"❌ Ошибка при генерации главы об эмоциях: {e}")
        content['emotions'] = f"В подписях @{username} живет особый язык чувств. Каждое слово выбрано с заботой, каждая фраза — это мостик между сердцами."
    
    # Глава о местах
    print(f"💕 Создаем главу о местах...")
    try:
        places_chapter = generate_unique_chapter("places", data_for_chapters, generated_texts)
        content['places'] = places_chapter
        generated_texts.append(places_chapter[:200])
    except Exception as e:
        print(f"❌ Ошибка при генерации главы о местах: {e}")
        content['places'] = f"Карта путешествий @{username} рассказывает историю поиска красоты в самых неожиданных уголках мира."
    
    # Глава о сообществе
    print(f"💕 Создаем главу о сообществе...")
    try:
        community_chapter = generate_unique_chapter("community", data_for_chapters, generated_texts)
        content['community'] = community_chapter
        generated_texts.append(community_chapter[:200])
    except Exception as e:
        print(f"❌ Ошибка при генерации главы о сообществе: {e}")
        content['community'] = f"Вокруг @{username} сформировалось особое сообщество — {format_statistics_creatively('followers', followers)} людей, объединенных любовью к прекрасному."
    
    # Финальная глава
    print(f"💕 Создаем финальную главу...")
    try:
        legacy_chapter = generate_unique_chapter("legacy", data_for_chapters, generated_texts)
        content['legacy'] = legacy_chapter
        generated_texts.append(legacy_chapter[:200])
    except Exception as e:
        print(f"❌ Ошибка при генерации финальной главы: {e}")
        content['legacy'] = f"История @{username} — это напоминание о том, что красота живет рядом с нами. Нужно только научиться её видеть и ценить."
    
    # Добавляем анализы фотографий
    content['photo_stories'] = photo_analyses
    
    return content

def create_romantic_book_html(content: dict, analysis: dict, images: list[Path]) -> str:
    """Создает HTML книгу с ванильным дизайном и улучшенными фотографиями"""
    
    username = analysis.get('username', 'Неизвестный')
    full_name = analysis.get('full_name', username)
    followers = analysis.get('followers', 0)
    following = analysis.get('following', 0)
    posts_count = analysis.get('posts_count', 0)
    bio = analysis.get('bio', '')
    verified = analysis.get('verified', False)
    
    # Обрабатываем изображения с улучшенной презентацией
    processed_images = []
    
    for i, img_path in enumerate(images[:8]):
        if img_path.exists():
            try:
                with Image.open(img_path) as img:
                    # Улучшенная обработка для user-friendly вида
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    
                    # Адаптивный размер для лучшего отображения
                    max_size = (900, 700)
                    img.thumbnail(max_size, Image.Resampling.LANCZOS)
                    
                    # Мягкое улучшение для приятного вида
                    enhancer = ImageEnhance.Contrast(img)
                    img = enhancer.enhance(1.08)
                    
                    enhancer = ImageEnhance.Brightness(img)
                    img = enhancer.enhance(1.02)
                    
                    enhancer = ImageEnhance.Color(img)
                    img = enhancer.enhance(1.05)
                    
                    # Конвертируем в base64
                    buffer = BytesIO()
                    img.save(buffer, format='JPEG', quality=92)
                    img_str = base64.b64encode(buffer.getvalue()).decode()
                    processed_images.append(f"data:image/jpeg;base64,{img_str}")
            except Exception as e:
                print(f"❌ Ошибка при обработке изображения {img_path}: {e}")
    
    # Реальные данные для контента
    real_captions = analysis.get('captions', ['Прекрасный момент'])[:6]
    locations = analysis.get('locations', ['Неизвестное место'])[:5]
    photo_stories = content.get('photo_stories', [])
    
    # HTML с ванильным дизайном
    html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title>{content.get('title', f'Визуальная поэзия @{username}')}</title>
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
        line-height: 1.7;
        color: var(--text-dark);
        background: var(--vanilla-bg);
        margin: 0;
        padding: 0;
        max-width: 850px;
        margin: 0 auto;
        background-image: 
            radial-gradient(circle at 80% 20%, var(--cream-bg) 0%, transparent 50%),
            radial-gradient(circle at 20% 80%, var(--soft-beige) 0%, transparent 50%);
    }}
    
    .page {{
        min-height: 90vh;
        padding: 2.5cm 3cm;
        margin-bottom: 1.5cm;
        page-break-after: always;
        background: var(--warm-white);
        box-shadow: 0 6px 25px var(--shadow-soft);
        border-radius: 8px;
        position: relative;
        border: 1px solid rgba(212, 175, 140, 0.1);
    }}
    
    .page::before {{
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 4px;
        background: linear-gradient(90deg, var(--accent-warm), transparent, var(--accent-warm));
        border-radius: 8px 8px 0 0;
    }}
    
    .page:last-child {{
        page-break-after: auto;
    }}
    
    h1 {{
        font-family: 'Playfair Display', serif;
        font-size: 32pt;
        text-align: center;
        margin: 3cm 0 2cm 0;
        color: var(--text-dark);
        font-weight: 500;
        letter-spacing: 2px;
        line-height: 1.3;
    }}
    
    h2 {{
        font-family: 'Playfair Display', serif;
        font-size: 22pt;
        color: var(--text-dark);
        margin: 2.5cm 0 1.5cm 0;
        text-align: left;
        font-weight: 500;
        border-bottom: 2px solid var(--accent-warm);
        padding-bottom: 0.5cm;
    }}
    
    h3 {{
        font-family: 'Libre Baskerville', serif;
        font-size: 16pt;
        color: var(--text-medium);
        margin: 1.5cm 0 1cm 0;
        font-weight: 400;
    }}
    
    .chapter-number {{
        font-family: 'Libre Baskerville', serif;
        font-size: 12pt;
        color: var(--text-light);
        text-align: center;
        margin-bottom: 1cm;
        font-style: italic;
        text-transform: uppercase;
        letter-spacing: 3px;
    }}
    
    p {{
        margin: 0 0 1.4em 0;
        text-align: justify;
        text-indent: 2.5em;
    }}
    
    .first-paragraph {{
        text-indent: 0;
        font-size: 14pt;
        font-weight: 500;
    }}
    
    .drop-cap {{
        float: left;
        font-family: 'Playfair Display', serif;
        font-size: 80pt;
        line-height: 65pt;
        padding-right: 12pt;
        margin-top: 8pt;
        color: var(--accent-warm);
        text-shadow: 2px 2px 4px var(--shadow-soft);
    }}
    
    blockquote {{
        font-style: italic;
        margin: 2.5em 2em;
        padding: 1.5em 2em;
        border: none;
        text-align: center;
        font-size: 12pt;
        color: var(--text-medium);
        background: var(--cream-bg);
        border-radius: 12px;
        border-left: 4px solid var(--accent-warm);
        box-shadow: 0 4px 15px var(--shadow-soft);
    }}
    
    .quote-author {{
        text-align: right;
        margin-top: 1em;
        font-size: 11pt;
        color: var(--text-light);
        font-style: normal;
    }}
    
    .photo-container {{
        margin: 2.5cm 0;
        text-align: center;
        page-break-inside: avoid;
    }}
    
    .photo-frame {{
        display: inline-block;
        padding: 20px;
        background: var(--warm-white);
        border-radius: 16px;
        box-shadow: 
            0 8px 32px var(--shadow-soft),
            inset 0 1px 0 rgba(255, 255, 255, 0.8);
        border: 1px solid rgba(212, 175, 140, 0.2);
        margin: 1cm 0;
    }}
    
    .photo-frame img {{
        max-width: 100%;
        max-height: 500px;
        border-radius: 12px;
        box-shadow: 0 4px 20px rgba(60, 50, 40, 0.15);
        border: 3px solid var(--warm-white);
    }}
    
    .photo-caption {{
        font-family: 'Libre Baskerville', serif;
        font-style: italic;
        font-size: 12pt;
        color: var(--text-medium);
        margin-top: 1.5cm;
        text-align: center;
        line-height: 1.5;
    }}
    
    .photo-story {{
        margin-top: 1cm;
        padding: 1.5em;
        background: var(--soft-beige);
        border-radius: 12px;
        font-size: 11pt;
        color: var(--text-medium);
        border-left: 3px solid var(--accent-warm);
    }}
    
    .photo-inline {{
        float: right;
        margin: 0 0 1.5em 2.5em;
        width: 320px;
    }}
    
    .photo-inline .photo-frame {{
        padding: 15px;
        margin: 0;
    }}
    
    .photo-inline img {{
        width: 100%;
        max-height: 280px;
        object-fit: cover;
    }}
    
    .stats-elegant {{
        margin: 2cm 0;
        text-align: center;
        font-family: 'Libre Baskerville', serif;
        padding: 2em;
        background: var(--cream-bg);
        border-radius: 16px;
        border: 1px solid rgba(212, 175, 140, 0.2);
        box-shadow: 0 6px 20px var(--shadow-soft);
    }}
    
    .stats-elegant h3 {{
        margin-top: 0;
        color: var(--accent-warm);
        font-size: 18pt;
    }}
    
    .stats-elegant p {{
        margin: 0.5em 0;
        font-size: 12pt;
        color: var(--text-medium);
        text-indent: 0;
    }}
    
    .dedication {{
        text-align: center;
        font-style: italic;
        margin: 4cm 0;
        font-size: 14pt;
        color: var(--text-medium);
        padding: 2em;
        background: var(--soft-beige);
        border-radius: 16px;
        border: 1px solid rgba(212, 175, 140, 0.15);
    }}
    
    .captions-showcase {{
        margin: 2cm 0;
        padding: 2em;
        background: var(--warm-white);
        border-radius: 16px;
        border-left: 5px solid var(--accent-warm);
        box-shadow: 0 6px 20px var(--shadow-soft);
    }}
    
    .caption-item {{
        margin: 1.5em 0;
        padding: 1em 1.5em;
        background: var(--cream-bg);
        border-radius: 8px;
        font-style: italic;
        color: var(--text-medium);
        border-left: 3px solid var(--accent-warm);
    }}
    
    @media print {{
        body {{
            margin: 0;
            padding: 0;
            background: white;
        }}
        .page {{
            page-break-after: always;
            margin: 0;
            box-shadow: none;
            border-radius: 0;
            border: none;
        }}
        .page::before {{
            display: none;
        }}
    }}
    </style>
</head>
<body>

<!-- ОБЛОЖКА -->
<div class="page">
    <h1>{content.get('title', f'Визуальная поэзия @{username}')}</h1>
    
    <div class="dedication">
        Каждый снимок — это стихотворение,<br>
        каждая подпись — строчка в большой книге жизни
    </div>
    
    <div style="position: absolute; bottom: 3cm; left: 50%; transform: translateX(-50%); text-align: center;">
        <p style="font-family: 'Libre Baskerville', serif; font-size: 12pt; color: var(--text-light); margin: 0;">
            Автор: {full_name if full_name != username else username}<br>
            <small style="font-size: 10pt;">Instagram Story Book</small>
        </p>
    </div>
</div>

<!-- ПРОЛОГ -->
<div class="page">
    <div class="chapter-number">Пролог</div>
    <h2>Цифровая поэзия</h2>
    
    <p class="first-paragraph">
        <span class="drop-cap">В</span>нутри каждого Instagram профиля скрывается удивительная история. За привычными квадратными кадрами живут настоящие эмоции, искренние переживания и моменты, которые хочется сохранить навсегда.
    </p>
    
    <p>
        {content.get('prologue', f'@{username} создает свою уникальную визуальную поэзию. Каждый пост здесь — это не просто фотография, а глава в большой книге жизни, написанная светом, цветом и искренними словами.')}
    </p>
    
    <blockquote>
        "Лучшие истории рассказываются не словами, а моментами, которые мы успеваем заметить и сохранить."
        <div class="quote-author">— Философия Instagram</div>
    </blockquote>
</div>

<!-- ПОРТРЕТ АВТОРА -->
<div class="page">
    <div class="chapter-number">Глава первая</div>
    <h2>Автор в кадре</h2>
    
    <p class="first-paragraph">
        <span class="drop-cap">@</span>{username} — это больше чем просто имя пользователя. За этими символами стоит {full_name if full_name != username else 'удивительная личность'}, которая делится с миром своим уникальным взглядом на красоту.
    </p>
    
    <div class="stats-elegant">
        <h3>Цифровой портрет</h3>
        <p><strong>{format_statistics_creatively('followers', followers)}</strong></p>
        <p><strong>{format_statistics_creatively('posts', posts_count)}</strong></p>
        <p>{f'✓ Подтвержденный аккаунт' if verified else 'Аутентичный голос'}</p>
    </div>
    
    <p>
        {bio if bio else 'Биография может молчать, но фотографии говорят громче слов. В каждом кадре читается характер автора, его видение мира и способность находить красоту в самых обычных моментах.'}
    </p>
    
    <blockquote>
        "Через объектив камеры мы познаем не только мир, но и самих себя."
    </blockquote>
</div>"""
    
    # Добавляем фотографии с анализом
    for i, img_base64 in enumerate(processed_images):
        caption = real_captions[i] if i < len(real_captions) else f'Момент {i+1}'
        photo_analysis = photo_stories[i] if i < len(photo_stories) else "Этот снимок передает особую атмосферу и настроение момента."
        
        # Чередуем полные страницы и встроенные фото
        if i % 3 == 0:
            # Полностраничное фото
            html += f"""

<div class="page">
    <div class="photo-container">
        <div class="photo-frame">
            <img src="{img_base64}" alt="Фотография {i+1}">
        </div>
        
        <div class="photo-caption">
            "{caption}"
        </div>
        
        <div class="photo-story">
            {photo_analysis}
        </div>
    </div>
</div>"""
        else:
            # Встроенное фото с текстом
            html += f"""

<div class="page">
    <div class="photo-inline">
        <div class="photo-frame">
            <img src="{img_base64}" alt="Фотография {i+1}">
        </div>
        <div class="photo-caption" style="margin-top: 0.8cm; font-size: 10pt;">
            "{caption}"
        </div>
    </div>
    
    <p class="first-paragraph">
        <span class="drop-cap">К</span>аждая фотография рассказывает свою уникальную историю. В этом кадре живет особый момент, пойманный @{username} и переданный нам через экран.
    </p>
    
    <p>
        {photo_analysis}
    </p>
    
    <p>
        Искусство современной фотографии заключается не только в технических навыках, но и в способности почувствовать момент, когда обычная сцена превращается в произведение искусства. Именно такие мгновения и ловит объектив @{username}.
    </p>
</div>"""
    
    # Добавляем главы с контентом
    html += f"""

<!-- ЭМОЦИОНАЛЬНЫЙ МИР -->
<div class="page">
    <div class="chapter-number">Глава вторая</div>
    <h2>Язык эмоций</h2>
    
    <p class="first-paragraph">
        <span class="drop-cap">С</span>лова под фотографиями — это не просто подписи. Это ключи к внутреннему миру автора, его переживаниям и мыслям в момент создания кадра.
    </p>
    
    <p>
        {content.get('emotions', f'В подписях @{username} живет особая поэзия современности. Каждое слово выбрано с заботой, каждая фраза отражает искренние чувства и переживания.')}
    </p>
    
    <div class="captions-showcase">
        <h3>Голос автора</h3>
        {chr(10).join([f'<div class="caption-item">"{caption}"</div>' for caption in real_captions[:4]])}
    </div>
    
    <blockquote>
        "В эпоху быстрых сообщений искренние слова становятся особенно ценными."
    </blockquote>
</div>

<!-- ГЕОГРАФИЯ ДУШИ -->
<div class="page">
    <div class="chapter-number">Глава третья</div>
    <h2>Карта путешествий</h2>
    
    <p class="first-paragraph">
        <span class="drop-cap">М</span>еста, которые мы выбираем для фотографий, многое говорят о наших приоритетах, мечтах и стремлениях. География @{username} — это карта души.
    </p>
    
    <p>
        {content.get('places', f'Каждое место в галерее @{username} имеет свою историю. От {", ".join(locations[:3])} — каждая локация оставила свой след в визуальной летописи.')}
    </p>
    
    <div style="margin: 2cm 0; padding: 1.5em; background: var(--soft-beige); border-radius: 12px;">
        <h3 style="margin-top: 0; color: var(--accent-warm);">Любимые места:</h3>
        {chr(10).join([f'<p style="margin: 0.5em 0; text-indent: 0;"><em>{location}</em></p>' for location in locations[:5]])}
    </div>
    
    <blockquote>
        "Путешествие начинается не с первого шага, а с первого взгляда на карту."
    </blockquote>
</div>

<!-- СООБЩЕСТВО -->
<div class="page">
    <div class="chapter-number">Глава четвертая</div>
    <h2>Цифровые связи</h2>
    
    <p class="first-paragraph">
        <span class="drop-cap">В</span> мире социальных сетей мы создаем новые формы близости и понимания. Сообщество вокруг @{username} — это особое пространство.
    </p>
    
    <p>
        {content.get('community', f'Вокруг профиля @{username} сформировалось сообщество людей, которых объединяет любовь к прекрасному. {format_statistics_creatively("followers", followers)} — это не просто цифра, это живые люди с собственными историями.')}
    </p>
    
    <blockquote>
        "Настоящие связи создаются не количеством подписчиков, а качеством взаимодействия."
    </blockquote>
</div>

<!-- ФИНАЛ -->
<div class="page">
    <div class="chapter-number">Эпилог</div>
    <h2>Что останется</h2>
    
    <p class="first-paragraph">
        <span class="drop-cap">В</span> эпоху цифровых технологий мы создаем новые формы памяти. Эта книга — попытка сохранить мгновения, которые делают нашу жизнь особенной.
    </p>
    
    <p>
        {content.get('legacy', f'История @{username} — это напоминание о том, что красота окружает нас повсюду. Нужно только научиться её замечать, ценить и делиться ею с другими.')}
    </p>
    
    <div class="dedication" style="margin-top: 3cm;">
        <strong>Конец первой главы.</strong><br>
        <em>История продолжается...</em>
    </div>
    
    <div style="position: absolute; bottom: 2cm; left: 50%; transform: translateX(-50%); text-align: center;">
        <p style="font-size: 10pt; color: var(--text-light); margin: 0;">
            Создано с любовью • Instagram Story Book<br>
            <small>Каждая история уникальна</small>
        </p>
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
