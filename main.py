import os
import sys
import json
import platform
import base64
import re
import subprocess
from pathlib import Path
from io import BytesIO

try:
    import pandas as pd
except ImportError:
    print("[Ошибка] Не установлена библиотека pandas. Установите зависимости через 'pip install -r requirements.txt'.")
    sys.exit(1)
try:
    from jinja2 import Environment, FileSystemLoader, select_autoescape
except ImportError:
    print("[Ошибка] Не установлена библиотека jinja2. Установите зависимости через 'pip install -r requirements.txt'.")
    sys.exit(1)

DATA_DIR = Path('data')
TEMPLATES_DIR = Path('templates')
OUTPUT_DIR = Path('output')

# Создать output/ если не существует
OUTPUT_DIR.mkdir(exist_ok=True)

def scan_files(directory, exts):
    return sorted([f for f in directory.glob('*') if f.suffix.lower() in exts])

def print_menu(title, options):
    print(f"\n{'='*40}\n{title}\n{'='*40}")
    for i, opt in enumerate(options, 1):
        print(f"{i}. {opt}")
    print('-'*40)

def choose_option(options, prompt):
    while True:
        try:
            choice = int(input(prompt))
            if 1 <= choice <= len(options):
                return choice - 1
            else:
                print("Введите номер из списка.")
        except ValueError:
            print("Введите корректный номер.")

def parse_csv(path):
    df = pd.read_csv(path, encoding='utf-8')
    if not all(col in df.columns for col in ['invoice_id', 'date', 'customer', 'item_name', 'quantity', 'price']):
        print("[Ошибка] Некорректная структура CSV файла.")
        sys.exit(1)
    grouped = df.groupby(['invoice_id', 'date', 'customer'])
    checks = []
    for (invoice_id, date, customer), group in grouped:
        items = group[['item_name', 'quantity', 'price']].to_dict('records')
        total = sum(row['quantity'] * row['price'] for _, row in group.iterrows())
        checks.append({
            'invoice_id': str(invoice_id),
            'date': date,
            'customer': customer,
            'items': [{'name': it['item_name'], 'quantity': it['quantity'], 'price': it['price']} for it in items],
            'total': total
        })
    return checks

def parse_json(path):
    with open(path, encoding='utf-8') as f:
        data = json.load(f)
    checks = []
    for entry in data:
        if not all(k in entry for k in ['invoice_id', 'date', 'customer', 'items', 'total']):
            print("[Ошибка] Некорректная структура JSON файла.")
            sys.exit(1)
        checks.append(entry)
    return checks

def open_pdf(filepath):
    if platform.system() == 'Windows':
        os.startfile(filepath)
    elif platform.system() == 'Darwin':
        subprocess.run(['open', filepath])
    else:
        subprocess.run(['xdg-open', filepath])

def get_next_invoice_id(invoice_id):
    try:
        next_number = int(invoice_id)
    except (TypeError, ValueError):
        next_number = 1

    for existing_path in OUTPUT_DIR.glob("invoice_*.pdf"):
        match = re.fullmatch(r"invoice_(\d+)(?:_\d+)?\.pdf", existing_path.name)
        if match:
            next_number = max(next_number, int(match.group(1)) + 1)

    return str(next_number)

def main():
    # 1. Поиск файлов
    data_files = scan_files(DATA_DIR, {'.csv', '.json'})
    template_files = scan_files(TEMPLATES_DIR, {'.html'})
    if not data_files:
        print("[Ошибка] В папке data/ нет файлов .csv или .json. Добавьте данные и повторите запуск.")
        return
    if not template_files:
        print("[Ошибка] В папке templates/ нет файлов .html. Добавьте шаблоны и повторите запуск.")
        return

    # 2. Меню выбора файла данных
    print_menu("Выберите файл с данными", [f.name for f in data_files])
    data_idx = choose_option(data_files, "Введите номер файла: ")
    data_path = data_files[data_idx]

    # 3. Меню выбора шаблона
    print_menu("Выберите HTML-шаблон", [f.name for f in template_files])
    tmpl_idx = choose_option(template_files, "Введите номер шаблона: ")
    tmpl_path = template_files[tmpl_idx]

    # 4. Парсинг данных
    if data_path.suffix == '.csv':
        checks = parse_csv(data_path)
    else:
        checks = parse_json(data_path)
    if not checks:
        print("[Ошибка] Нет чеков в выбранном файле.")
        return

    # 5. Меню выбора чека
    print_menu("Выберите чек для генерации PDF", [f"{c['invoice_id']} | {c['customer']} | {c['date']}" for c in checks])
    check_idx = choose_option(checks, "Введите номер чека: ")
    check = checks[check_idx]

    # 6. Генерация PDF
    try:
        import qrcode
    except ImportError:
        print("[Ошибка] Не установлена библиотека qrcode. Установите зависимости через 'pip install -r requirements.txt'.")
        return

    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(['html'])
    )
    template = env.get_template(tmpl_path.name)
    try:
        from weasyprint import HTML

        while True:
            check['invoice_id'] = get_next_invoice_id(check['invoice_id'])
            qr_payload = f"Чек №{check['invoice_id']} | Дата: {check['date']} | Итого: {check['total']} руб."
            qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=6, border=2)
            qr.add_data(qr_payload)
            qr.make(fit=True)
            qr_buffer = BytesIO()
            qr.make_image(fill_color="black", back_color="white").save(qr_buffer, format="PNG")
            qr_code_base64 = "data:image/png;base64," + base64.b64encode(qr_buffer.getvalue()).decode("ascii")
            html_out = template.render(**check, qr_code_base64=qr_code_base64)
            pdf_content = HTML(string=html_out).write_pdf()
            pdf_path = OUTPUT_DIR / f"invoice_{check['invoice_id']}.pdf"
            try:
                with pdf_path.open("xb") as pdf_file:
                    pdf_file.write(pdf_content)
                break
            except FileExistsError:
                continue
        print(f"\n[Успех] PDF сохранён: {pdf_path}")
        open_pdf(str(pdf_path))
    except ImportError:
        print("[Ошибка] Не установлена библиотека weasyprint. Установите зависимости через 'pip install -r requirements.txt'.")
    except OSError as e:
        if 'gobject-2.0-0' in str(e) or 'GTK' in str(e):
            print("[Ошибка] Не найдена библиотека GTK3 для WeasyPrint.\n\nУстановите GTK3 для Windows одной из команд:\n  winget install tschoonj.GTKForWindows\nили скачайте GTK3 Runtime: https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases\nПосле установки перезапустите терминал.")
        else:
            print(f"[Ошибка] Не удалось сгенерировать PDF: {e}")

if __name__ == "__main__":
    main()
