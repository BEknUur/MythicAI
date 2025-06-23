import openai
import base64
from pathlib import Path
from app.config import settings
from typing import Optional
import logging
import random

# Инициализация OpenAI
openai.api_key = settings.OPENAI_API_KEY
client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)

logger = logging.getLogger(__name__)

# Автоматическое удаление клише
CLICHE_FILTERS = [
    "мягкие оттенки", "резкие тени", "атмосфера", "ощущение",
    "передает эмоции", "придает глубину", "создает настроение",
    "особая атмосфера", "уникальная история", "снимок показывает"
]

def strip_cliches(text: str) -> str:
    """Убирает шаблонные фразы из текста"""
    for cliche in CLICHE_FILTERS:
        text = text.replace(cliche, "")
    # Убираем двойные пробелы
    text = " ".join(text.split())
    return text

def generate_text(prompt: str,
                  model: str = "gpt-3.5-turbo",
                  max_tokens: int = 1500,
                  temperature: float = 0.8) -> str:
    """Генерирует текст с помощью OpenAI API"""
    try:
        # Система для коротких ярких мыслей
        system_message = """Ты — мастер коротких ярких текстов для визуальных зинов.

ФОРМАТ: 1 яркая мысль + 1 сенсорная деталь. Максимум 2-3 предложения.

СТРОГО ЗАПРЕЩЕНО:
- "мягкие оттенки", "резкие тени", "атмосфера", "ощущение"
- "передает эмоции", "придает глубину", "создает настроение"
- Длинные описания и рассуждения

ОБЯЗАТЕЛЬНО:
- Конкретная сенсорная деталь (звук, запах, касание, вкус)
- Одна яркая эмоциональная мысль
- Живой разговорный язык
- SMS-стиль для диалогов

ПРИМЕРЫ ХОРОШИХ ТЕКСТОВ:
"Пахнет кофе и недосказанностью."
"— Опять покупаешь эту ленту?"
"Руки дрожат от холода или волнения."

ЯЗЫК: только русский, очень живой."""

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt}
            ],
            max_tokens=max_tokens,
            temperature=temperature,
            presence_penalty=0.9,
            frequency_penalty=0.8
        )
        
        result = response.choices[0].message.content.strip()
        return strip_cliches(result)  # Автоматически убираем клише
        
    except Exception as e:
        logger.error(f"Ошибка в generate_text: {e}")
        return f"Ошибка генерации: {str(e)}"


def analyze_photo_for_card(image_path: Path, context: str = "", card_type: str = "micro") -> str:
    """Анализирует фотографию для карточки-триггера"""
    try:
        if not image_path.exists():
            return "Кадр исчез"
            
        with open(image_path, "rb") as image_file:
            image_data = base64.b64encode(image_file.read()).decode('utf-8')
        
        # Микро-форматы для карточек
        card_styles = {
            "micro": """Создай микро-сценку (максимум 3 строки):

1 конкретная деталь + 1 диалог-реплика

Формат:
[Сенсорная деталь]
— Короткая реплика

Пример:
Руки пахнут типографской краской.
— Ты опять всю ночь читал?""",

            "trigger": """Одна яркая мысль-триггер:

Что ПЕРВОЕ приходит в голову при взгляде на фото?
Одно предложение + одна сенсорная деталь.

Без описаний - только эмоция!""",

            "sms": """SMS-переписка по фото:

— Реплика 1 (что мог написать герой)
— Ответ (что мог ответить друг)

Живо, коротко, как настоящие SMS."""
        }
        
        style = card_styles.get(card_type, card_styles["micro"])
        
        prompt = f"""{style}

Контекст: {context}

НЕ используй клише! Будь конкретным и живым.
Максимум 50 слов."""

        response = client.chat.completions.create(
            model="gpt-4o",
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
            max_tokens=100,
            temperature=0.8
        )
        
        result = response.choices[0].message.content.strip()
        return strip_cliches(result)
        
    except Exception as e:
        logger.error(f"Ошибка анализа фото {image_path}: {e}")
        return f"Молчание."


def generate_scene_chapter(scene_type: str, data: dict, all_images: list) -> str:
    """Генерирует сцену для драматургической структуры"""
    
    username = data.get('username', 'Неизвестный')
    followers = data.get('followers', 0)
    captions = data.get('captions', ['Без слов'])
    
    # Рандомизируем изображения для разнообразия
    shuffled_images = all_images.copy()
    random.shuffle(shuffled_images)
    
    scenes = {
        "hook": f"""ЗАВЯЗКА. Первое впечатление от @{username}.

Напиши как дневниковую запись:
"Наткнулся на этот профиль..."

1 яркая мысль + 1 сенсорная деталь.
Максимум 3 предложения.

НЕ используй клише! Будь живым и конкретным.""",

        "conflict": f"""ВНУТРЕННИЙ КОНФЛИКТ. Противоречие.

Реальная подпись: "{captions[0]}"

Покажи противоречие между радужным контентом и тревожным подтекстом.

SMS-стиль:
— Что написано
— Что на самом деле

Максимум 4 строки.""",

        "turn": f"""ПОВОРОТ. Момент озарения.

Один кадр изменил все понимание.

Напиши:
1 конкретная деталь места
1 момент осознания

Без философии! Конкретно и ярко.
Максимум 3 предложения.""",

        "climax": f"""КУЛЬМИНАЦИЯ. Отклик подписчиков.

{followers} человек отреагировали на откровенность.

Формат - цитаты комментариев:
— Комментарий 1
— Комментарий 2
— Что изменилось

Живые голоса, не рассуждения!""",

        "epilogue": f"""ЭПИЛОГ-ПРИГЛАШЕНИЕ.

Финальный крючок для читателя.

Закончи приглашением:
"Листаю ленту в поиске..."

1 конкретный образ + призыв к действию.
Максимум 2 предложения."""
    }
    
    prompt = scenes.get(scene_type, "Напиши живо и коротко.")
    
    result = generate_text(prompt, max_tokens=150, temperature=0.9)
    return strip_cliches(result)


# Функция для обратной совместимости
def analyze_photo(image_path: Path, context: str = "", photo_index: int = 0) -> str:
    """Обратная совместимость - теперь создает карточки"""
    card_types = ["micro", "trigger", "sms"]
    card_type = card_types[photo_index % len(card_types)]
    return analyze_photo_for_card(image_path, context, card_type)


def generate_unique_chapter(chapter_type: str, data: dict, previous_texts: list = None) -> str:
    """Обратная совместимость - теперь создает сцены"""
    scene_mapping = {
        "intro": "hook",
        "emotions": "conflict", 
        "places": "turn",
        "community": "climax",
        "legacy": "epilogue"
    }
    
    scene_type = scene_mapping.get(chapter_type, "hook")
    all_images = data.get('photo_analyses', [])
    
    return generate_scene_chapter(scene_type, data, all_images)
