import google.generativeai as genai
from app.config import settings

# инициализация
genai.configure(api_key=settings.GOOGLE_API_KEY)

def generate_text(prompt: str,
                  model: str = "gemini-2.0-flash-exp",
                  max_tokens: int = 1500) -> str:
    """Генерирует текст с помощью Google Gemini API"""
    try:
        # Создаем модель
        model_instance = genai.GenerativeModel(model)
        
        # Конфигурация генерации
        generation_config = genai.types.GenerationConfig(
            candidate_count=1,
            max_output_tokens=max_tokens,
            temperature=0.7,
        )
        
        # Добавляем системную инструкцию в начало промпта
        system_instruction = "Ты — талантливый рассказчик и писатель. Создавай увлекательные, красочные и эмоциональные тексты на русском языке.\n\n"
        full_prompt = system_instruction + prompt
        
        # Генерируем ответ
        response = model_instance.generate_content(
            full_prompt,
            generation_config=generation_config
        )
        
        return response.text if response.text else "Ошибка генерации текста"
        
    except Exception as e:
        print(f"Ошибка в generate_text: {e}")
        return f"Ошибка генерации: {str(e)}"
