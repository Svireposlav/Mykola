from google import genai

# ВСТАВЬТЕ СЮДА ВАШ КЛЮЧ ОТ GOOGLE GEMINI
API_KEY = "AIzaSyDLhjG0c4sHnj2lG4U-cqTOnL6-go0GqCQ"

client = genai.Client(api_key=API_KEY)

print("Проверяю доступные модели...\n")
try:
    # Получаем список всех моделей
    models = client.models.list()
    
    print(f"Найдено моделей: {len(models)}\n")
    print("Список доступных моделей (ищем 'flash' или 'pro'):")
    print("-" * 50)
    
    count = 0
    for model in models:
        # В новой библиотеке имя модели находится прямо в атрибуте .name
        name = model.name
        
        # Фильтруем только нужные нам модели (текстовые)
        if 'flash' in name.lower() or 'pro' in name.lower():
            print(f"✅ {name}")
            count += 1
            
    if count == 0:
        print("❌ Не найдено моделей flash или pro. Попробуйте посмотреть весь список ниже:")
        for model in models[:10]: # Покажем первые 10 любых моделей
            print(f"   - {model.name}")

except Exception as e:
    print(f"❌ Ошибка подключения: {e}")
    print("Проверьте, правильно ли вы вставили API ключ.")