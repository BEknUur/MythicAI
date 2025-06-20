import openai
import base64
from pathlib import Path
from app.config import settings
from typing import Optional
import logging

# Инициализация OpenAI
openai.api_key = settings.OPENAI_API_KEY
client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)

logger = logging.getLogger(__name__)

def generate_text(prompt: str,
                  model: str = "gpt-4o-mini",
                  max_tokens: int = 1500,
                  temperature: float = 0.8) -> str:
    """Генерирует текст с помощью OpenAI API"""
    try:
        # Системная инструкция для улучшения качества
        system_message = """Ты — талантливый писатель и поэт, создающий романтические книги на основе Instagram профилей. 

ВАЖНО:
- Пиши УНИКАЛЬНЫЕ тексты, избегай повторений и шаблонов
- Используй поэтичный, но живой язык
- Создавай эмоциональные, искренние истории
- Каждый текст должен быть особенным и неповторимым
- Фокусируйся на человеческих эмоциях и переживаниях
- Пиши на русском языке красиво и грамотно

Стиль: романтический, поэтичный, искренний, без клише."""

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt}
            ],
            max_tokens=max_tokens,
            temperature=temperature,
            presence_penalty=0.6,  # Уменьшает повторения
            frequency_penalty=0.3   # Поощряет разнообразие
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        logger.error(f"Ошибка в generate_text: {e}")
        return f"Ошибка генерации: {str(e)}"


def analyze_photo(image_path: Path, context: str = "") -> str:
    """Анализирует фотографию с помощью OpenAI Vision"""
    try:
        if not image_path.exists():
            return "Фотография недоступна для анализа"
            
        # Читаем и кодируем изображение
        with open(image_path, "rb") as image_file:
            image_data = base64.b64encode(image_file.read()).decode('utf-8')
        
        prompt = f"""Проанализируй эту фотографию для создания романтической книги.

Контекст: {context}

Опиши:
1. Что изображено на фото (композиция, освещение, настроение)
2. Какие эмоции передает снимок
3. Что можно сказать о человеке/моменте
4. Поэтическое описание (2-3 предложения)

Пиши поэтично, романтично, но искренне. Максимум 200 слов."""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_data}",
                                "detail": "high"
                            }
                        }
                    ]
                }
            ],
            max_tokens=300,
            temperature=0.7
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        logger.error(f"Ошибка анализа фото {image_path}: {e}")
        return f"Красивый момент, запечатленный навсегда"


def generate_unique_chapter(chapter_type: str, data: dict, previous_texts: list = None) -> str:
    """Генерирует уникальную главу, избегая повторений"""
    
    if previous_texts is None:
        previous_texts = []
    
    # Контекст для избежания повторений
    anti_repeat_context = ""
    if previous_texts:
        anti_repeat_context = f"\n\nИЗБЕГАЙ следующих фраз и идей (они уже использованы):\n{chr(10).join(previous_texts[-3:])}"
    
    prompts = {
        "intro": f"""Напиши уникальное введение для романтической книги об Instagram-профиле.

Данные:
- Имя: {data.get('username', 'Неизвестный')}  
- Подписчики: {data.get('followers', 0)}
- Био: {data.get('bio', 'Нет описания')}

Создай ОРИГИНАЛЬНЫЙ текст о том, как Instagram становится зеркалом души. 
Используй СВЕЖИЕ метафоры, избегай банальностей.
200-300 слов.{anti_repeat_context}""",

        "emotions": f"""Создай главу о эмоциональном мире человека через его Instagram.

Реальные подписи к постам:
{chr(10).join(data.get('captions', ['Нет подписей'])[:3])}

Напиши УНИКАЛЬНЫЙ анализ того, как эти слова раскрывают внутренний мир.
Каждое предложение должно быть особенным, неповторимым.
250-350 слов.{anti_repeat_context}""",

        "places": f"""Напиши главу о географии души через места в Instagram.

Места: {', '.join(data.get('locations', ['Разные уголки мира'])[:4])}

Создай ОРИГИНАЛЬНУЮ историю о том, как места формируют характер.
Используй НОВЫЕ образы и сравнения.
200-300 слов.{anti_repeat_context}""",

        "community": f"""Создай главу о цифровом сообществе и связях.

Подписчики: {data.get('followers', 0)}
Упоминания: {', '.join(data.get('mentioned_users', ['друзья'])[:3])}

Напиши СВЕЖИЙ взгляд на современные отношения через социальные сети.
Избегай клише про "цифровой мир".
250-350 слов.{anti_repeat_context}""",

        "legacy": f"""Создай заключительную главу о том, что останется.

Всего постов: {data.get('posts_count', 0)}
Лайки: {data.get('total_likes', 0)}

Напиши УНИКАЛЬНОЕ размышление о цифровом наследии и памяти.
Финал должен быть особенным, трогательным, неповторимым.
200-300 слов.{anti_repeat_context}"""
    }
    
    prompt = prompts.get(chapter_type, "Создай красивый текст для книги.")
    
    return generate_text(prompt, max_tokens=600, temperature=0.9)
