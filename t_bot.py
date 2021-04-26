import logging
import requests
import json
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Updater,
    Filters,
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler,
    CallbackContext,
    MessageHandler,
)
from dotenv import load_dotenv
from datetime import datetime
import os
from typing import Dict

load_dotenv()
token = os.environ.get("api-token")
api = os.environ.get("api_url")

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)

FIRST, SECOND, COLOR, ADDRESS = range(4)
ONE, TWO, THREE = range(3)


def facts_to_str(user_data: Dict[str, str]) -> str:
    facts = list()

    for key, value in user_data.items():
        facts.append(f'{key} - {value}')

    return "\n".join(facts).join(['\n', '\n'])


def start(update: Update, context) -> int:
    user = update.message.from_user
    logger.info("User %s started the conversation.", user.first_name)
    keyboard = [
        [
            InlineKeyboardButton("Посмотреть объявления", callback_data=str('start_over')),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text("Начать?", reply_markup=reply_markup)
    return FIRST


def help(update, context):
    update.message.reply_text(
        "Я бот, который помогает Вам найти объявления о пропавших животных.")


def start_over(update: Update, context) -> int:
    query = update.callback_query
    query.answer()

    keyboard = [
        [
            InlineKeyboardButton("Потерянные", callback_data='0 [1]'),
            InlineKeyboardButton("Найденные", callback_data='0 [2]'),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(text="Выберите тип объявления:", reply_markup=reply_markup)

    return FIRST


def one(update: Update, context) -> int:
    query = update.callback_query
    query.answer()
    keyboard = [
        [
            InlineKeyboardButton("Собаки", callback_data='1 [1]'),
            InlineKeyboardButton("Кошки", callback_data='1 [2]'),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(
        text="Какой питомец?", reply_markup=reply_markup
    )

    text = query.data
    context.user_data["cat"] = text.split('[', 1)[1].split(']')[0]

    return FIRST


def end(update: Update, context) -> int:
    query = update.callback_query
    query.answer()
    text = query.data
    context.user_data["pet"] = text.split('[', 1)[1].split(']')[0]

    data = context.user_data

    if 'page' in data:
        page = int(data['page']) + 1
    else:
        page = 1
    context.user_data["page"] = page

    pets = get_pets(data['pet'], data['cat'], page)
    for pet in pets:
        created_date = datetime.utcfromtimestamp(int(pet['created_at'])).strftime('%Y-%m-%d %H:%M:%S')
        message = created_date + '\n' + pet['address'] + '\n' + pet['title'] + '\n' + pet[
            'body'] + '[.](https://propala.ru' + pet['image'] + ') \n [подробнее](' + pet['url'] + ')'
        context.bot.send_message(chat_id=update.effective_chat.id, parse_mode='markdown', text=message)

    keyboard = [
        [
            InlineKeyboardButton("Да.", callback_data='1 [' + str(data['pet']) + '][' + str(page) + ']'),
            InlineKeyboardButton("В начало.", callback_data='start_over'),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    context.bot.send_message(chat_id=update.effective_chat.id, text='Показать еще?', reply_markup=reply_markup)

    return FIRST
    # return ConversationHandler.END


def add_new(update: Update, context) -> int:
    query = update.callback_query
    query.answer()

    keyboard = [
        [
            InlineKeyboardButton("Потерянные", callback_data='add_pet [1]'),
            InlineKeyboardButton("Найденные", callback_data='add_pet [2]'),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(text="Выберите тип объявления:", reply_markup=reply_markup)

    return SECOND


def add_pet(update: Update, context) -> int:
    query = update.callback_query
    query.answer()
    keyboard = [
        [
            InlineKeyboardButton("Собаки", callback_data='add_color [1]'),
            InlineKeyboardButton("Кошки", callback_data='add_color [2]'),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(
        text="Какой питомец?", reply_markup=reply_markup
    )

    text = query.data
    context.user_data["ad_cat"] = text.split('[', 1)[1].split(']')[0]

    return COLOR


def add_color(update: Update, context) -> int:
    update.callback_query.message.edit_text(
        'Добавить цвет вашего питомца.'
    )
    return ADDRESS


def skip_color(update: Update, _: CallbackContext) -> int:
    user = update.message.from_user
    logger.info("User %s did not send a color.", user.first_name)
    update.message.reply_text(
        'Вы не ввели цвет вашего питомца. Желаете пропустить вопрос?'
    )

    return ADDRESS


def add_address(update: Update, context) -> int:
    return SECOND


def three(update: Update, context) -> int:
    query = update.callback_query
    query.answer()
    keyboard = [
        [
            InlineKeyboardButton("Нет, начать сначала.", callback_data=str(ONE)),
            InlineKeyboardButton("Да.", callback_data=str(TWO)),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(
        text="Разместить объявление?", reply_markup=reply_markup
    )
    text = query.data
    context.user_data["pet"] = text.split('[', 1)[1].split(']')[0]

    return SECOND


def get_pets(pet_id, cat_id, page):
    response = requests.get(
        api + 'pets/?pet_id={}&cat_id={}&page={}'.format(int(pet_id), int(cat_id), int(page)))
    api_response = json.loads(response.text)
    return api_response


def main() -> None:
    updater = Updater(token)

    dispatcher = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            FIRST: [
                CallbackQueryHandler(add_new, pattern='^' + str('add_new') + '$'),
                CallbackQueryHandler(start_over, pattern='^' + str('start_over') + '$'),
                CallbackQueryHandler(one, pattern='^' + str(ONE) + ''),
                CallbackQueryHandler(end, pattern='^' + str(TWO) + ''),
                CommandHandler('help', help)
            ],
            SECOND: [
                CallbackQueryHandler(add_new, pattern='^' + str('add_new') + '$'),
                CallbackQueryHandler(add_pet, pattern='^' + str('add_pet') + ''),
                CallbackQueryHandler(end, pattern='^' + str(TWO) + '$'),
            ],
            COLOR: [
                CallbackQueryHandler(add_color, pattern='^' + str('add_color') + ''),
                CommandHandler('skip', skip_color),
            ],
            ADDRESS: [
                CommandHandler('add_address', add_address),
            ],
        },
        fallbacks=[CommandHandler('start', start)],
    )

    dispatcher.add_handler(conv_handler)
    updater.start_polling()

    updater.idle()


if __name__ == '__main__':
    main()
