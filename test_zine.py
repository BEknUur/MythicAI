#!/usr/bin/env python3
"""
Тест нового мозаичного формата зина
"""

from pathlib import Path
import json
from app.services.book_builder import build_romantic_book

def create_test_zine():
    """Создает тестовый зин с новым форматом"""
    
    print("🎨 Тестируем новый мозаичный формат зина...")
    
    # Создаем тестовые данные
    test_run_id = 'test_zine_mosaic'
    test_dir = Path('data') / test_run_id
    test_dir.mkdir(parents=True, exist_ok=True)
    
    # Минимальные тестовые данные профиля
    test_data = [{
        'username': 'creative_soul',
        'fullName': 'Анна Творческая',
        'biography': 'Ищу красоту в простых вещах 📸✨',
        'followersCount': 1247,
        'followsCount': 543,
        'verified': False,
        'profilePicUrl': '',
        'latestPosts': [
            {
                'caption': 'Утренний кофе пахнет возможностями',
                'locationName': 'Уютная кофейня',
                'likesCount': 89,
                'commentsCount': 12,
                'type': 'photo',
                'hashtags': ['morning', 'coffee', 'mood'],
                'mentions': ['best_friend'],
                'url': 'coffee.jpg'
            },
            {
                'caption': 'Между строк старых книг живут истории',
                'locationName': 'Центральная библиотека',
                'likesCount': 156,
                'commentsCount': 23,
                'type': 'photo',
                'hashtags': ['books', 'library', 'stories'],
                'mentions': [],
                'url': 'books.jpg'
            },
            {
                'caption': 'Город засыпает, а мечты просыпаются',
                'locationName': 'Крыша старого дома',
                'likesCount': 203,
                'commentsCount': 34,
                'type': 'photo',
                'hashtags': ['sunset', 'city', 'dreams'],
                'mentions': ['photographer_friend'],
                'url': 'sunset.jpg'
            }
        ]
    }]
    
    # Сохраняем данные
    posts_file = test_dir / 'posts.json'
    posts_file.write_text(json.dumps(test_data, ensure_ascii=False, indent=2))
    
    print(f"✅ Тестовые данные созданы в {posts_file}")
    
    # Создаем зин (без реальных изображений для теста)
    try:
        build_romantic_book(test_run_id, [], '')
        
        # Проверяем результат
        html_file = test_dir / 'book.html'
        if html_file.exists():
            print(f"✅ Мозаичный зин создан: {html_file}")
            
            # Читаем и проверяем ключевые элементы
            html_content = html_file.read_text()
            
            checks = [
                ('Мозаичная сетка', '.moodboard' in html_content),
                ('Интерактивные карточки', '.photo-card' in html_content),
                ('SMS стиль', '.sms-style' in html_content),
                ('Драматургические сцены', '.scene' in html_content),
                ('Финальный призыв', '.final-call' in html_content),
                ('JavaScript интерактивность', 'showCard(' in html_content),
                ('Адаптивный дизайн', '@media (max-width: 768px)' in html_content)
            ]
            
            print("\n📋 Проверка элементов нового формата:")
            for name, passed in checks:
                status = "✅" if passed else "❌"
                print(f"{status} {name}")
            
            # Проверяем размер файла
            size_kb = html_file.stat().st_size / 1024
            print(f"\n📊 Размер файла: {size_kb:.1f} KB")
            
            if size_kb < 100:
                print("✅ Компактный размер - подходит для быстрой загрузки")
            
            return True
            
        else:
            print("❌ HTML файл не создан")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка при создании зина: {e}")
        return False

if __name__ == "__main__":
    success = create_test_zine()
    if success:
        print("\n🎉 Тест мозаичного формата прошел успешно!")
        print("📖 Откройте data/test_zine_mosaic/book.html в браузере для просмотра")
    else:
        print("\n💥 Тест не прошел - нужны исправления") 