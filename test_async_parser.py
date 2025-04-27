import asyncio
import json
import time
from DeepSeekParseBankAsync import AsyncTextExtractor

async def test_batch_processing():
    # Создаем большой набор тестовых данных
    test_texts = [
        """
        Счет №{}-{} от 15.03.2024
        По договору №ДП-2024/{:03d} от 01.03.2024
        За поставку канцтоваров согласно накладной №ТН-{:03d}
        Сумма НДС: {:.2f} руб.
        За период 03.2024
        """.format(i, i+100, i, i, float(1000 + i))
        for i in range(1, 101)  # Генерируем 100 различных текстов
    ]

    # Создаем и обучаем экстрактор
    extractor = AsyncTextExtractor()
    
    # Данные для обучения
    training_data = [
        (
            """
            Счет №123-45 от 15.03.2024
            По договору №ДП-2024/03 от 01.03.2024
            За поставку канцтоваров согласно накладной №ТН-789
            Сумма НДС: 1250.50 руб.
            За период 03.2024
            """,
            {
                "за_что": "поставка канцтоваров",
                "номер_договора": "ДП-2024/03",
                "номер_счета": "123-45",
                "номер_накладной": "ТН-789",
                "номер_заказа": ""
            }
        ),
        (
            """
            Оплата по заказу №Order-456 
            от 20.03.2024
            НДС не облагается
            """,
            {
                "за_что": "оплата по заказу",
                "номер_договора": "",
                "номер_счета": "",
                "номер_накладной": "",
                "номер_заказа": "Order-456"
            }
        ),
        (
            """
            Счет-фактура №789 от 10.03.2024
            по договору поставки №2024-ABC
            За оказание консультационных услуг
            Сумма НДС (20%): 45890.00
            Период оказания услуг: январь 2024
            """,
            {
                "за_что": "консультационные услуги",
                "номер_договора": "2024-ABC",
                "номер_счета": "789",
                "номер_накладной": "",
                "номер_заказа": ""
            }
        )
    ]

    print("1. Обучение модели...")
    start_time = time.time()
    await extractor.train(training_data)
    train_time = time.time() - start_time
    print(f"Время обучения: {train_time:.2f} секунд")

    # Сохраняем модель
    print("\n2. Сохранение модели...")
    await extractor.save_model('async_model_test.pkl')

    # Загружаем модель
    print("\n3. Загрузка модели...")
    extractor = await AsyncTextExtractor.load_model('async_model_test.pkl')

    # Тестируем пакетную обработку
    print("\n4. Тестирование пакетной обработки...")
    print(f"Количество текстов для обработки: {len(test_texts)}")
    
    # Обработка всех текстов сразу
    start_time = time.time()
    results = await extractor.process_batch(test_texts)
    batch_time = time.time() - start_time
    
    print(f"\nВремя пакетной обработки: {batch_time:.2f} секунд")
    print(f"Среднее время на один текст: {(batch_time/len(test_texts)):.4f} секунд")

    # Выводим несколько примеров результатов
    print("\n5. Примеры результатов (первые 3):")
    for i, result in enumerate(results[:3], 1):
        print(f"\nРезультат {i}:")
        print("-" * 50)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        print("-" * 50)

    print(f"\nВсего обработано текстов: {len(results)}")

if __name__ == "__main__":
    asyncio.run(test_batch_processing())