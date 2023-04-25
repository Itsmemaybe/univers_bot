import logging

from telegram.ext import MessageHandler, filters, ConversationHandler
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram import ReplyKeyboardMarkup
from telegram import ReplyKeyboardRemove
from bs4 import BeautifulSoup
import requests
import wikipedia
import re
import random
import sys

wikipedia.set_lang("ru")

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}

TOKEN = '6257684322:AAGBcB-V-IzlQv6K_p4CZdepkauItfERjl4'

# Запускаем логгирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG
)

logger = logging.getLogger(__name__)
reply_keyboard = [['/help', '/close'],
                  ['/set', '/unset'],
                  ['/choosing_the_best'],
                  ['/pogoda'],
                  ['/info_from_wiki'],
                  ['/prepare_for_6_task_in_ege_rus']]
markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=False)

REMIND = ''
flag = False
ans = 'nothing'


def getwiki(s):
    try:
        ny = wikipedia.page(s)
        # Получаем первую тысячу символов
        wikitext = ny.content[:1000]
        # Разделяем по точкам
        wikimas = wikitext.split('.')
        # Отбрасываем всЕ после последней точки
        wikimas = wikimas[:-1]
        # Создаем пустую переменную для текста
        wikitext2 = ''
        # Проходимся по строкам, где нет знаков «равно» (то есть все, кроме заголовков)
        for x in wikimas:
            if not ('==' in x):
                # Если в строке осталось больше трех символов, добавляем ее к нашей переменной и возвращаем утерянные при разделении строк точки на место
                if (len((x.strip())) > 3):
                    wikitext2 = wikitext2 + x + '.'
            else:
                break
        # Теперь при помощи регулярных выражений убираем разметку
        wikitext2 = re.sub('\([^()]*\)', '', wikitext2)
        wikitext2 = re.sub('\([^()]*\)', '', wikitext2)
        wikitext2 = re.sub('\{[^\{\}]*\}', '', wikitext2)
        # Возвращаем текстовую строку
        return wikitext2
    # Обрабатываем исключение, которое мог вернуть модуль wikipedia при запросе
    except Exception as e:
        return 'В энциклопедии нет информации об этом'


def weather(city):
    city = city.replace(" ", "+")
    res = requests.get(
        f'https://www.google.com/search?q={city}&oq={city}'
        f'&aqs=chrome.0.35i39l2j0l4j46j69i60.6128j1j7&sourceid=chrome&ie=UTF-8', headers=headers)
    soup = BeautifulSoup(res.text, 'html.parser')
    location = soup.select('#wob_loc')[0].getText().strip()
    time = soup.select('#wob_dts')[0].getText().strip()
    info = soup.select('#wob_dc')[0].getText().strip()
    weather = soup.select('#wob_tm')[0].getText().strip()
    return f'{location},\n{time},\n{info},\n{weather}°C'


def random_word_rule():
    file = open('rules_for_6_task_in_rusege.txt', encoding='utf-8').readlines()
    list_of_words = list(map(lambda x: x.rstrip(), file))
    print(list_of_words)
    return random.choice(list_of_words)


async def alarm(context: ContextTypes.DEFAULT_TYPE) -> None:
    global REMIND
    """Отправляем напоминание"""
    job = context.job
    await context.bot.send_message(job.chat_id, text=f"Биииип! {job.data / 60} минут прошло! {REMIND}")


def remove_job_if_exists(name: str, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Удаляем старые задачи"""
    current_jobs = context.job_queue.get_jobs_by_name(name)
    if not current_jobs:
        return False
    for job in current_jobs:
        job.schedule_removal()
    return True


async def set_timer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global REMIND
    """Добавляем задачу в очередь"""
    chat_id = update.effective_message.chat_id
    try:
        due = float(context.args[0]) * 60
        REMIND = ' '.join(context.args[1:])
        if due < 0:
            await update.effective_message.reply_text("Прости! Я не могу напомнить тебе это в прошлом!")
            return

        job_removed = remove_job_if_exists(str(chat_id), context)
        context.job_queue.run_once(alarm, due, chat_id=chat_id, name=str(chat_id), data=due)

        text = "Напоминане установлено!"
        if job_removed:
            text += "Старые напоминания удалены"
        await update.effective_message.reply_text(text)

    except (IndexError, ValueError):
        await update.effective_message.reply_text("Напиши /set {время, через которое тебе нужно напомнить в минутах} "
                                                  "{что именно тебе нужно напомнить}")


async def unset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Если пользователь передумал - удаляем задачу"""
    chat_id = update.message.chat_id
    job_removed = remove_job_if_exists(str(chat_id), context)
    text = "Напоминание удалено!" if job_removed else "У вас нет активных напоминаний"
    await update.message.reply_text(text)


# Определяем функцию-обработчик сообщений.
async def hand_text(update, context):
    mes = str(update.message.text).lower()
    print(mes)
    if 'погод' in mes:
        pogoda()
    elif 'егэ' in mes or 'ударения' in mes or 'русский' in mes:
        prepare_for_6_task_in_ege_rus()
    elif 'помни' in mes:
        set()
    elif 'выбор' in mes or 'выбрать' in mes:
        choosing_the_best()
    else:
        await update.message.reply_text('К сожалению, я не смог понять, что вы имели ввиду. Попробуйте воспользоваться клавиатрой')


async def start(update, context):
    await update.message.reply_text(
        "Привет, я твой личный NAB - дружелюбный сосед-помощник. Чего бы ты сейчас хотел?",
        reply_markup=markup
    )


async def help(update, context):
    await update.message.reply_text(
        "NAB - дружелюбный сосед-помощник. Выбери необходимую функцию в выпадающем меню или напиши сообщение с твоим "
        "желанием. Я постараюсь понять тебя\n "
        "/set {время, через которое тебе нужно напомнить в минутах} "
        "{что именно тебе нужно напомнить} - напиши это и я напомню тебе о чем-то важном\n "
        "/unset - удалить существующее напоминание\n"
        "/choosing_the_best - поможет сделать самый ответсвенный выбор в вашей жизни\n "
        "/pogoda - подскажет погоду в твоем городе, чтобы ты, не дай Мерлин, под дождь не попал\n"
        "/prepare_for_6_task_in_ege_rus - ненавязчивое напоминание, что до егэ по русскому чуть больше месяца, а ты все еще говоришь дешивизнА")


async def stop(update, context):
    await update.message.reply_text("Всего доброго!")
    return ConversationHandler.END


async def choosing_the_best(update, context):
    await update.message.reply_text("Отправь мне список того, из чего собираешься выбирать "
                                    "Пример: Гарри Поттер, Голодные игры, Дивергент, Бегущий в лабиринте")
    return 1


async def first_response(update, context): \
        # Сохраняем ответ в словаре.
    context.user_data['choises'] = update.message.text.split(', ')
    await update.message.reply_text(
        f"А теперь просто выбирай один из двух(пиши 1 - если выбераешь первый вариант, 2 - если второй\n"
        f"{context.user_data['choises'][0]} или {context.user_data['choises'][1]}")
    return 2


async def second_response(update, context):
    global flag, ans
    choise = update.message.text
    print('sdsd')
    logger.info(choise)
    if choise == '1':
        context.user_data['choises'].pop(1)
    elif choise == '2':
        context.user_data['choises'].pop(0)
    else:
        await update.message.reply_text(
            f"Тебе нужно выбрать один из двух(пиши 1 - если выбераешь первый вариант, 2 - если второй\n"
            f"{context.user_data['choises'][0]} или {context.user_data['choises'][1]}")
        return 2
    # Используем user_data в ответе.
    if len(context.user_data['choises']) >= 2:
        await update.message.reply_text(
            f"{context.user_data['choises'][0]} или {context.user_data['choises'][1]}")
    else:
        flag = True
    if flag:
        ans = context.user_data['choises'][0]
        await update.message.reply_text(
            f"Ваш выбор - {ans}!")
        context.user_data.clear()  # очищаем словарь с пользовательскими данными
        return ConversationHandler.END
    else:
        return 2


async def close_keyboard(update, context):
    await update.message.reply_text(
        "Ok",
        reply_markup=ReplyKeyboardRemove()
    )


async def pogoda(update, context):
    await update.message.reply_text('Введите город, в котором хотите узнать погоду')
    return 1


async def first_response1(update, context):
    context.user_data['pogoda'] = update.message.text
    try:
        await update.message.reply_text(
            weather(context.user_data['pogoda'] + " weather"))
        return ConversationHandler.END
    except Exception:
        await update.message.reply_text(
            "Кажется, вы ошиблись в написании города, попробуйте еще раз")
        return 1


async def info_from_wiki(update, context):
    await update.message.reply_text('Введите слово, о котором вы хотите узнать самую достоверную '
                                    'информацию, полученную с сайта Wikipedia')
    return 1


async def first_response2(update, context):
    context.user_data['wiki'] = update.message.text
    try:
        await update.message.reply_text(
            getwiki(context.user_data['wiki']))
        return ConversationHandler.END
    except Exception:
        await update.message.reply_text(
            "Кажется, вы написали что-то такое, о чем не занет даже википедия...")
        return ConversationHandler.END


async def prepare_for_6_task_in_ege_rus(update, context):
    await update.message.reply_text(f'Ваш шаг на пути к сотке по русскому: {random_word_rule()}')


def main():
    # Создаём объект Application.
    application = Application.builder().token(TOKEN).build()

    # Диалог для функции choosing_the_best
    conv_handler_for_choise = ConversationHandler(
        # Точка входа в диалог.
        # В данном случае — команда /choosing_the_best. Она задаёт первый вопрос.
        entry_points=[CommandHandler('choosing_the_best', choosing_the_best)],
        # Состояние внутри диалога.
        states={
            1: [MessageHandler(filters.TEXT & ~filters.COMMAND, first_response)],
            2: [MessageHandler(filters.TEXT & ~filters.COMMAND, second_response)]
        },
        # Точка прерывания диалога. В данном случае — команда /stop.
        fallbacks=[CommandHandler('stop', stop)]
    )
    application.add_handler(conv_handler_for_choise)

    conv_handler_for_pogoda = ConversationHandler(
        # Точка входа в диалог.
        # В данном случае — команда /pogoda. Она задаёт первый вопрос.
        entry_points=[CommandHandler('pogoda', pogoda)],
        # Состояние внутри диалога.
        states={
            1: [MessageHandler(filters.TEXT & ~filters.COMMAND, first_response1)]
        },
        # Точка прерывания диалога. В данном случае — команда /stop.
        fallbacks=[CommandHandler('stop', stop)]
    )
    application.add_handler(conv_handler_for_pogoda)

    conv_handler_for_wiki = ConversationHandler(
        # Точка входа в диалог.
        # В данном случае — команда /info_from_wiki. Она задаёт первый вопрос.
        entry_points=[CommandHandler('info_from_wiki', info_from_wiki)],
        # Состояние внутри диалога.
        states={
            1: [MessageHandler(filters.TEXT & ~filters.COMMAND, first_response2)]
        },
        # Точка прерывания диалога. В данном случае — команда /stop.
        fallbacks=[CommandHandler('stop', stop)]
    )
    application.add_handler(conv_handler_for_wiki)

    # Вспомогательне команды
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help))
    application.add_handler(CommandHandler("close", close_keyboard))

    # Основыные возможности бота
    application.add_handler(CommandHandler("set", set_timer))
    application.add_handler(CommandHandler("unset", unset))
    application.add_handler(CommandHandler("choosing_the_best", choosing_the_best))
    application.add_handler(CommandHandler("pogoda", pogoda))
    application.add_handler(CommandHandler("info_from_wiki", info_from_wiki))
    application.add_handler(CommandHandler("prepare_for_6_task_in_ege_rus", prepare_for_6_task_in_ege_rus))

    # Запуск
    application.run_polling()
    text_handler = MessageHandler(filters.TEXT, hand_text)

    # Регистрируем обработчик в приложении.
    application.add_handler(text_handler)
    application.run_polling()


if __name__ == '__main__':
    try:
        main()
    except Exception:
        sys.exit(0)
