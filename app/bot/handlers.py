import telebot
import re

from telebot import custom_filters
from telebot.handler_backends import State, StatesGroup
from telebot.storage import StateMemoryStorage

from app.core.config import config
from app.core.logger import logger
from app.core.database import db

from app.parsers.qr_parser import scan_qr_from_bytes
from app.parsers.proverka_cheka_parser import ProverkaChekaParser
from app.fetchers.proverka_cheka_api import ProverkaChekaAPI
from app.exporters.google_auth import get_google_client
from app.exporters.spreadsheet import UserSpreadsheet

from datetime import datetime
from app.models.receipt import Receipt, ReceiptItem, StoreType, Unit

state_storage = StateMemoryStorage()
bot = telebot.TeleBot(config.BOT_TOKEN, state_storage=state_storage)

class UserRegistrationSteps(StatesGroup):
    waiting_for_email = State()
    waiting_for_sheet = State()

class ManualAddSteps(StatesGroup):
    waiting_for_store = State()
    waiting_for_sum = State()
    waiting_for_items = State()

def is_user_allowed(username: str) -> bool:
    if not username:
        return False
    whitelist = config.get_whitelisted_users()
    return username.lower() in whitelist

def extract_sheet_id(url: str) -> str:
    match = re.search(r"/d/([a-zA-Z0-9-_]+)", url)
    return match.group(1) if match else None

@bot.message_handler(commands=['start'])
def send_welcome(message):
    username = message.from_user.username
    tg_id = message.from_user.id

    if not is_user_allowed(username):
        logger.warning(f"Unauthorized access attempt by @{username} (ID: {tg_id})")
        bot.reply_to(message, "Извините, у вас нет доступа к этому боту.")
        return

    existing_user = db.get_user_by_tg_id(tg_id)
    if existing_user:
        email, sheet_id = existing_user

        if email and sheet_id:
            text = (
                f"С возвращением, @{username}! 👋\n\n"
                f"Твой профиль уже настроен.\n"
                f"📧 Твой Email: `{email}`\n"
                f"📊 [Твоя таблица с чеками](https://docs.google.com/spreadsheets/d/{sheet_id})\n\n"
                f"Просто отправляй мне фото QR-кодов или пересылай чеки на почту бота."
            )
            bot.send_message(message.chat.id, text, parse_mode="Markdown", disable_web_page_preview=True)

            bot.delete_state(tg_id, message.chat.id)
            return

    text = (
        f"Привет, @{username}! Добро пожаловать в ReceiptsHub 🧾\n\n"
        "Давай настроим твой профиль. Для начала напиши свой **Email**.\n"
        "(С этого адреса ты будешь пересылать мне электронные чеки)."
    )
    bot.send_message(message.chat.id, text, parse_mode="Markdown")
    bot.set_state(tg_id, UserRegistrationSteps.waiting_for_email, message.chat.id)


@bot.message_handler(state=UserRegistrationSteps.waiting_for_email)
def process_email_step(message):
    email = message.text.strip()
    tg_id = message.from_user.id

    if "@" not in email or "." not in email:
        bot.reply_to(message, "Похоже, это не email. Попробуй еще раз.")
        return

    with bot.retrieve_data(tg_id, message.chat.id) as data:
        data['email'] = email

    service_email = config.GOOGLE_SERVICE_EMAIL
    text = (
        f"Отлично! Твой email принят.\n\n"
        f"Теперь:\n"
        f"1. Создай новую таблицу в своем Google Drive.\n"
        f"2. Нажми «Настройки доступа» (Share) в правом верхнем углу.\n"
        f"3. Добавь этого пользователя как **Редактора**:\n"
        f"`{service_email}`\n"
        f"4. Скопируй ссылку на таблицу и пришли её мне."
    )
    bot.send_message(message.chat.id, text, parse_mode="Markdown")
    bot.set_state(tg_id, UserRegistrationSteps.waiting_for_sheet, message.chat.id)


@bot.message_handler(state=UserRegistrationSteps.waiting_for_sheet)
def process_sheet_step(message):
    url = message.text.strip()
    tg_id = message.from_user.id

    sheet_id = extract_sheet_id(url)
    if not sheet_id:
        bot.reply_to(message, "Не могу найти ID таблицы в ссылке. Убедись, что ты прислал полную ссылку (https://docs.google.com/spreadsheets/...).")
        return

    with bot.retrieve_data(tg_id, message.chat.id) as data:
        email = data.get('email')

    db.register_user(tg_id=tg_id, email=email, sheet_id=sheet_id)

    bot.delete_state(tg_id, message.chat.id)

    success_text = (
        "✅ **Регистрация успешно завершена!**\n\n"
        "Теперь ты можешь:\n"
        "1. Пересылать письма с чеками от магазинов (или ОФД) со своей почты на почту бота.\n"
        "2. Просто присылать мне фотографии QR-кодов с бумажных чеков прямо сюда.\n\n"
        "Я буду автоматически парсить их и заносить в твою таблицу."
    )
    bot.send_message(message.chat.id, success_text, parse_mode="Markdown", disable_web_page_preview=True)


@bot.message_handler(content_types=['photo', 'document'])
def handle_receipt_photo(message):
    tg_id = message.from_user.id

    user_data = db.get_user_by_tg_id(tg_id)
    if not user_data or not user_data[1]:
        bot.reply_to(message, "Пожалуйста, сначала настройте профиль с помощью команды /start.")
        return

    email, sheet_id = user_data

    msg_status = bot.reply_to(message, "Фото получено! Начинаю сканирование...")

    try:
        if message.content_type == 'photo':
            file_id = message.photo[-1].file_id
        elif message.content_type == 'document':
            if message.document.mime_type not in ['image/jpeg', 'image/png']:
                bot.edit_message_text("Пожалуйста, отправьте файл в формате JPG или PNG.", message.chat.id,
                                      msg_status.message_id)
                return
            file_id = message.document.file_id

        file_info = bot.get_file(file_id)
        downloaded_file = bot.download_file(file_info.file_path)

        raw_qr_string = scan_qr_from_bytes(downloaded_file)

        if not raw_qr_string:
            bot.edit_message_text(
                "Не удалось найти или прочитать QR-код.\n\n"
                "Советы:\n"
                "1. Разгладьте чек и убедитесь, что он хорошо освещен.\n"
                "2. Отправьте фото как **Файл/Документ** (без сжатия Telegram).",
                message.chat.id, msg_status.message_id, parse_mode="Markdown"
            )
            return

        logger.info(f"QR code recognized for tg_id={tg_id}: {raw_qr_string}")
        bot.edit_message_text("QR-код найден! Запрашиваю данные из ФНС...", message.chat.id, msg_status.message_id)

        json_response = ProverkaChekaAPI.get_receipt_from_raw(raw_qr_string)
        receipt = ProverkaChekaParser.parse(json_response)

        if not receipt:
            bot.edit_message_text("Данные чека еще не поступили в базу ФНС или чек некорректен. Попробуйте позже.",
                                  message.chat.id, msg_status.message_id)
            return

        saved = db.save_receipt(tg_id=tg_id, receipt=receipt)
        if not saved:
            bot.edit_message_text("Этот чек уже был добавлен ранее.", message.chat.id, msg_status.message_id)
            return

        g_client = get_google_client()
        doc = UserSpreadsheet(g_client, spreadsheet_id=sheet_id)
        receipts_page = doc.get_receipts_tab()
        receipts_page.append_nested_receipt(receipt)

        bot.edit_message_text(f"Чек на сумму **{receipt.total_sum} руб.** успешно добавлен в таблицу!",
                              message.chat.id, msg_status.message_id, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Error handling photo from tg_id={tg_id}: {e}")
        bot.edit_message_text("Произошла непредвиденная ошибка при обработке чека.", message.chat.id,
                              msg_status.message_id)


@bot.message_handler(commands=['add'])
def start_manual_add(message):
    tg_id = message.from_user.id

    user_data = db.get_user_by_tg_id(tg_id)
    if not user_data or not user_data[1]:
        bot.reply_to(message, "Пожалуйста, сначала настройте профиль с помощью команды /start.")
        return

    bot.reply_to(
        message,
        "📝 **Ручной ввод чека**\n\n"
        "Напиши **название магазина** (например, Пятёрочка, ВкусВилл, Аптека и т.д.):",
        parse_mode="Markdown"
    )
    bot.set_state(tg_id, ManualAddSteps.waiting_for_store, message.chat.id)


@bot.message_handler(state=ManualAddSteps.waiting_for_store)
def process_manual_store(message):
    tg_id = message.from_user.id
    store_name = message.text.strip()

    with bot.retrieve_data(tg_id, message.chat.id) as data:
        data['store_name'] = store_name

    bot.reply_to(
        message,
        "Отлично! Теперь введи **итоговую сумму** чека (только число, например: `1500.50`):",
        parse_mode="Markdown"
    )
    bot.set_state(tg_id, ManualAddSteps.waiting_for_sum, message.chat.id)


@bot.message_handler(state=ManualAddSteps.waiting_for_sum)
def process_manual_sum(message):
    tg_id = message.from_user.id

    try:
        total_sum = float(message.text.replace(',', '.').strip())
    except ValueError:
        bot.reply_to(message, "Пожалуйста, введи корректное число (например: 1500.50).")
        return

    with bot.retrieve_data(tg_id, message.chat.id) as data:
        data['total_sum'] = total_sum

    instruction = (
        "Сумма принята! 🛒\n\n"
        "Теперь введи список товаров. Каждый товар пиши с **новой строки** в формате:\n"
        "`Название - Цена - Количество`\n\n"
        "**Пример:**\n"
        "Молоко домик в деревне - 89.90 - 1\n"
        "Яблоки свежие - 120 - 1.5\n"
        "Пакет - 5 - 1"
    )
    bot.reply_to(message, instruction, parse_mode="Markdown")
    bot.set_state(tg_id, ManualAddSteps.waiting_for_items, message.chat.id)


@bot.message_handler(state=ManualAddSteps.waiting_for_items)
def process_manual_items(message):
    tg_id = message.from_user.id
    lines = message.text.strip().split('\n')

    msg_status = bot.reply_to(message, "Обрабатываю список товаров...")
    items = []

    for line in lines:
        if not line.strip():
            continue

        parts = [p.strip() for p in line.split('-')]

        if len(parts) >= 3:
            name = parts[0]
            try:
                price = float(parts[1].replace(',', '.'))
                qty = float(parts[2].replace(',', '.'))

                item_sum = round(price * qty, 2)

                unit = Unit.KG if qty % 1 != 0 else Unit.PC

                items.append(ReceiptItem(name=name, price=price, quantity=qty, sum=item_sum, unit=unit))
            except ValueError:
                bot.edit_message_text(f"❌ Ошибка в строке:\n`{line}`\nУбедись, что цена и количество — это числа.",
                                      message.chat.id, msg_status.message_id, parse_mode="Markdown")
                return
        else:
            bot.edit_message_text(f"❌ Неверный формат в строке:\n`{line}`\nНужно 3 элемента через дефис.",
                                  message.chat.id, msg_status.message_id, parse_mode="Markdown")
            return

    with bot.retrieve_data(tg_id, message.chat.id) as data:
        store_name = data['store_name']
        total_sum = data['total_sum']

    store_enum = StoreType.OTHER
    if "пятерочка" in store_name.lower():
        store_enum = StoreType.PYATEROCHKA
    elif "магнит" in store_name.lower():
        store_enum = StoreType.MAGNIT

    receipt_id = f"manual_{int(datetime.now().timestamp())}"
    receipt = Receipt(
        id=receipt_id,
        datetime=datetime.now(),
        store=store_enum,
        total_sum=total_sum,
        items=items,
        raw_data=f"Manual input: {store_name}"
    )

    user_data = db.get_user_by_tg_id(tg_id)
    _, sheet_id = user_data

    db.save_receipt(tg_id=tg_id, receipt=receipt)

    try:
        g_client = get_google_client()
        doc = UserSpreadsheet(g_client, spreadsheet_id=sheet_id)
        receipts_page = doc.get_receipts_tab()
        receipts_page.append_nested_receipt(receipt)

        bot.edit_message_text(f"✅ Чек из **{store_name}** на сумму **{total_sum} руб.** успешно добавлен!",
                              message.chat.id, msg_status.message_id, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error exporting manual receipt: {e}")
        bot.edit_message_text("⚠️ Чек сохранен в базу, но произошла ошибка при выгрузке в Google Таблицу.",
                              message.chat.id, msg_status.message_id)

    bot.delete_state(tg_id, message.chat.id)

bot.add_custom_filter(custom_filters.StateFilter(bot))

if __name__ == '__main__':
    logger.info("Starting Telegram bot (with onboarding)...")
    bot.infinity_polling()