# PDF Generator: Генератор PDF-чеков из CSV/JSON

## Описание
Учебное консольное приложение на Python для генерации PDF-чеков из данных формата CSV или JSON на основе HTML-шаблонов.

## Установка зависимостей

1. Установите Python 3.8+
2. Установите зависимости:

```
pip install -r requirements.txt
```

3. **Для Windows:**
   - Для работы WeasyPrint требуется GTK3. Установите его одной из команд:
     - Через winget:
       ```
       winget install tschoonj.GTKForWindows
       ```
     - Или скачайте [GTK3 Runtime](https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases) и установите вручную.
   - После установки перезапустите терминал/командную строку.

## Запуск

```
python main.py
```

## Структура проекта

- `data/` — входные файлы с данными (CSV и JSON)
- `templates/` — HTML-шаблоны чеков
- `output/` — папка для сохранения готовых PDF
- `main.py` — основной исполняемый скрипт
- `requirements.txt` — зависимости
- `README.md` — инструкция
