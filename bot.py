import os
import json
import logging
import dotenv
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler
from telegram.ext.filters import User


dotenv.load_dotenv()
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

BOT_TOKEN: str = os.getenv("BOT_TOKEN")
ALLOWED_USERS: list = json.loads(os.getenv('ALLOWED_USERS'))
COOKIES: dict = {
    'PHPSESSID': os.getenv('PHPSESSID'),
    'access_token': os.getenv('ACCESS_TOKEN'),
    'refresh_token': os.getenv('REFRESH_TOKEN'),
    'socket_token': os.getenv('SOCKET_TOKEN')
}


def epoch_to_datetime(epoch_time: int) -> datetime:
    """
    Конвертировать эпохальное время в обычное.
    """
    human_time = datetime.fromtimestamp(epoch_time)
    format_time = human_time.strftime("%d.%m %H:%M:%S")
    return format_time


def get_creation_date(file: os.path) -> datetime:
    """
    Показать время изменения файлов.
    """
    path = os.path.join(os.getcwd(), 'reports', file)
    creation_date = os.path.getmtime(path)
    human_time = epoch_to_datetime(creation_date)
    return human_time


def get_orgs_list():
    """
    Получить список организаций из json файла.
    """
    with open('organisations.json', 'r', encoding='utf-8') as f:
        data = json.load(f)['orgList']

    orgs = list()
    for org in data:
        is_available = data[org]['is_available']
        name = data[org]['name']
        if is_available:
            changed_name = name.replace(os.getenv('NAME'), 'ГАПОУ МО')
            orgs.append(changed_name)
    return orgs


def get_name(file):
    """
    Получить имя организации.
    """
    with open('organisations.json', 'r', encoding='utf-8', ) as f:
        orgs = json.load(f)['orgList']

    filename = file.split('.xlsx')[0]
    for org in orgs:
        if orgs[org]['uuid'] == filename:
            return orgs[org]['name']


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Команда бота /status. Показывает список организаций, которые
    пригласили наш аккаунт к себе в личный кабинет.
    """
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text='\n'.join(["✅" + i for i in get_orgs_list()])
    )


async def reports(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Команда бота /reports. Высылает в одном сообщении список всех файлов
    в .zip формате.
    """
    file_to_send = os.path.join(os.getcwd(), 'archive', 'spo2.zip')
    with open(file_to_send, 'rb') as file:
        epoch_time = os.path.getmtime(file_to_send)
        human_time = epoch_to_datetime(epoch_time)

        await context.bot.send_document(
            chat_id=update.effective_chat.id,
            document=file,
            caption=f'спо2 от {human_time}'
        )


if __name__ == '__main__':
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    start_handler = CommandHandler(
        'status', status, filters=User(ALLOWED_USERS)
    )
    reports_handler = CommandHandler(
        'reports', reports, filters=User(ALLOWED_USERS)
    )
    application.add_handler(start_handler)
    application.add_handler(reports_handler)
    application.run_polling()
