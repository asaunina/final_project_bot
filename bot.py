import random
from pymorphy2 import MorphAnalyzer
import pandas as pd
import matplotlib.pyplot as plt
import telebot
from telebot import types
import emoji
import flask
import zipfile
morph = MorphAnalyzer()

with zipfile.ZipFile('tolstoy.zip', 'r') as zip_ref:
    zip_ref.extractall()

fin_df = pd.read_csv('final_tolstoy.csv', sep='@')

# Создаем бота
TOKEN = '77145425750:AAEzomyfMGxVLpL9aCME-d6DMJa0Nt54Dt0'
WEBHOOK_HOST = 'asaunina.pythonanywhere.com'
WEBHOOK_PORT = '443'

bot = telebot.TeleBot(TOKEN, threaded=False)

WEBHOOK_URL_BASE = "https://{}:{}".format(WEBHOOK_HOST, WEBHOOK_PORT)
WEBHOOK_URL_PATH = "/{}/".format(TOKEN)

bot.remove_webhook()

bot.set_webhook(url=WEBHOOK_URL_BASE+WEBHOOK_URL_PATH)

app = flask.Flask(__name__)

# Нужные словарики для учета нужной информации
guessed_person = {}
guessed_model = {}
total_plays = {}
cur_sents = {}
generated_not_played = {}
real_not_played = {}


# Начинаем диалог с ботом с кнопкой, с помощью которой можно приступить к игре
@bot.message_handler(commands=['start'])
def start_message(message):
    # добавляем клавиатуру
    keyboard = types.InlineKeyboardMarkup()
    # и кнопку
    button = types.InlineKeyboardButton(text="Начнем игру!", callback_data="button")
    keyboard.add(button)

    # отправляем сообщение пользователю
    bot.send_message(message.chat.id, emoji.emojize("Привет! :smiling_face_with_open_hands: Давай поиграем!\n"
                     "Я буду присылать тебе два предложения. Одно из них -- из текстов Л.Н. Толстого. "
                     "Второе -- сгенеированное компьютером. Ты должен угадать, какое предложение сгенерировано.\n\n"
                     ":white_question_mark: Если вдруг тебе нужно будет напомнить правила, можешь ввести команду /help.\n\n"
                     ":chart_increasing: Чтобы посмотреть статистику, введи команду /stats :chart_decreasing:\n\n"
                     "Удачи! :smiling_face_with_open_hands:\n\n"
                     "Нажми на кнопку, когда будешь готов к игре!"), reply_markup=keyboard)


# Страшная длиннющая функция обрабатывающая ответы на кнопки...
@bot.callback_query_handler(func=lambda call: True)
def guess(call):
    if call.message:
        # если ответили на кнопку "играть"
        if call.data == "button":
            # если все еще есть предложения
            try:
                # добавляем в словарь с "несыгранными" предложениями "несыгранные" данным пользователем предложения
                if call.message.chat.id not in generated_not_played:
                    generated_not_played[call.message.chat.id] = list(fin_df['sentence'][(fin_df['generated'] == 1)])
                if call.message.chat.id not in real_not_played:
                    real_not_played[call.message.chat.id] = list(fin_df['sentence'][(fin_df['generated'] == 0)])

                # выбираем случайные два предложения: настоящее и сгенерированное
                sent1 = random.choice(generated_not_played[call.message.chat.id])
                sent2 = random.choice(real_not_played[call.message.chat.id])

                # удаляем их из "несыгранных"
                generated_not_played[call.message.chat.id].remove(sent1)
                real_not_played[call.message.chat.id].remove(sent2)

                # создаем список из этих предложений
                sents = [sent1, sent2]

                bot.send_message(call.message.chat.id, "Вот два предложения!")

                # случайным образом выбираем первое
                fst = random.choice(sents)

                # и остается второе
                sents.remove(fst)

                # в текущих предложениях у пользователя фиксируем порядок
                cur_sents[call.message.chat.id] = [fst, ' '.join(sents)]

                bot.send_message(call.message.chat.id, f"Первое предложение:\n\n{fst}")
                bot.send_message(call.message.chat.id, f"Второе предложение:\n\n{' '.join(sents)}")

                # добавляем клавиатуру с кнопками -- первое или второе сгенерированное
                keyboard = types.InlineKeyboardMarkup()

                button1 = types.InlineKeyboardButton(text="Первое", callback_data="1")
                button2 = types.InlineKeyboardButton(text="Второе", callback_data="2")

                keyboard.add(button1)
                keyboard.add(button2)

                bot.send_message(call.message.chat.id, f"Какое предложение сгенерировано компьютером?",
                                 reply_markup=keyboard)

            # если предложения закончились
            except:
                bot.send_message(call.message.chat.id, f"Ой, вы достигли конца игры! Поздравляем!")

        # если пользователь выбрал первое как сгенерированное
        elif call.data == '1':

            bot.send_message(call.message.chat.id, "Принято!")
            bot.send_message(call.message.chat.id, "Вот что думает модель:")

            # смотрим на то, что думает модель
            mod_guess1 = list(fin_df['model'][(fin_df['sentence'] == cur_sents[call.message.chat.id][0])])[0]
            mod_guess2 = list(fin_df['model'][(fin_df['sentence'] == cur_sents[call.message.chat.id][1])])[0]
            if mod_guess1 == 0:
                bot.send_message(call.message.chat.id, "Модель считает первое предложение настоящим")
            else:
                bot.send_message(call.message.chat.id, "Модель считает первое предложение сгенерированным компьютером")

            # смотрим, что на самом деле
            actual1 = list(fin_df['generated'][(fin_df['sentence'] == cur_sents[call.message.chat.id][0])])[0]
            actual2 = list(fin_df['generated'][(fin_df['sentence'] == cur_sents[call.message.chat.id][1])])[0]

            # дальше условия: если пользователь (не) угадал и модель (не) угадала
            # еще добавляем к количеству угаданных моделью и пользователем
            if actual1 == 0:
                if mod_guess1 == 0:
                    bot.send_message(call.message.chat.id, emoji.emojize("На самом деле первое предложение настоящее! "
                                                                         "Вы не угадали :slightly_frowning_face: Модель ответила правильно\n\n"
                                                                         "Модель 1️⃣ - 0️⃣ Ты"))
                    if call.message.chat.id not in guessed_model:
                        guessed_model[call.message.chat.id] = 1
                    else:
                        guessed_model[call.message.chat.id] += 1
                else:
                    bot.send_message(call.message.chat.id, emoji.emojize("На самом деле первое предложение настоящее! "
                                                                         "Вы не угадали :slightly_frowning_face: Модель тоже ошиблась\n\n"
                                                                         "Модель 0️⃣ - 0️⃣ Ты"))
            else:
                if mod_guess1 == 0:
                    bot.send_message(call.message.chat.id,
                                     emoji.emojize("На самом деле первое предложение сгенерированное! "
                                                   "Вы угадали! :party_popper: Модель ошиблась\n\n"
                                                   "Модель 0️⃣ - 1️⃣ Ты"))
                    if call.message.chat.id not in guessed_person:
                        guessed_person[call.message.chat.id] = 1
                    else:
                        guessed_person[call.message.chat.id] += 1
                else:
                    bot.send_message(call.message.chat.id,
                                     emoji.emojize("На самом деле первое предложение сгенерированное! "
                                                   "Вы угадали! :party_popper: Модель тоже правильно ответила\n\n"
                                                   "Модель 1️⃣ - 1️⃣ Ты"))
                    if call.message.chat.id not in guessed_person:
                        guessed_person[call.message.chat.id] = 1
                    else:
                        guessed_person[call.message.chat.id] += 1
                    if call.message.chat.id not in guessed_model:
                        guessed_model[call.message.chat.id] = 1
                    else:
                        guessed_model[call.message.chat.id] += 1

            # добавляем количество игр
            if call.message.chat.id not in total_plays:
                total_plays[call.message.chat.id] = 1
            else:
                total_plays[call.message.chat.id] += 1

            # создаем клавиатуру с кнопкой, чтобы поиграть еще
            keyboard = types.InlineKeyboardMarkup()
            button = types.InlineKeyboardButton(text="Поиграем еще!", callback_data="button")
            keyboard.add(button)
            bot.send_message(call.message.chat.id, "Хочешь поиграть еще??", reply_markup=keyboard)

        # то же самое, если пользователь выбрал второе предложение
        elif call.data == '2':

            bot.send_message(call.message.chat.id, "Принято!")
            bot.send_message(call.message.chat.id, "Вот что думает модель:")

            mod_guess1 = list(fin_df['model'][(fin_df['sentence'] == cur_sents[call.message.chat.id][0])])[0]
            mod_guess2 = list(fin_df['model'][(fin_df['sentence'] == cur_sents[call.message.chat.id][1])])[0]

            if mod_guess2 == 0:
                bot.send_message(call.message.chat.id, "Модель считает второе предложение настоящим")
            else:
                bot.send_message(call.message.chat.id, "Модель считает второе предложение сгенерированным компьютером")

            actual1 = list(fin_df['generated'][(fin_df['sentence'] == cur_sents[call.message.chat.id][0])])[0]
            actual2 = list(fin_df['generated'][(fin_df['sentence'] == cur_sents[call.message.chat.id][1])])[0]

            if actual2 == 0:
                if mod_guess2 == 0:
                    bot.send_message(call.message.chat.id, emoji.emojize("На самом деле второе предложение настоящее! "
                                                                         "Вы не угадали :slightly_frowning_face: Модель ответила правильно\n\n"
                                                                         "Модель 1️⃣ - 0️⃣ Ты"))
                    if call.message.chat.id not in guessed_model:
                        guessed_model[call.message.chat.id] = 1
                    else:
                        guessed_model[call.message.chat.id] += 1
                else:
                    bot.send_message(call.message.chat.id, emoji.emojize("На самом деле второе предложение настоящее! "
                                                                         "Вы не угадали :slightly_frowning_face: Модель тоже ошиблась\n\n"
                                                                         "Модель 0️⃣ - 0️⃣ Ты"))
            else:
                if mod_guess2 == 0:
                    bot.send_message(call.message.chat.id,
                                     emoji.emojize("На самом деле второе предложение сгенерированное! "
                                                   "Вы угадали! :party_popper: Модель ошиблась\n\n"
                                                   "Модель 0️⃣ - 1️⃣ Ты"))
                    if call.message.chat.id not in guessed_person:
                        guessed_person[call.message.chat.id] = 1
                    else:
                        guessed_person[call.message.chat.id] += 1
                else:
                    bot.send_message(call.message.chat.id,
                                     emoji.emojize("На самом деле второе предложение сгенерированное! "
                                                   "Вы угадали! :party_popper: Модель тоже правильно ответила\n\n"
                                                   "Модель 1️⃣ - 1️⃣ Ты"))
                    if call.message.chat.id not in guessed_person:
                        guessed_person[call.message.chat.id] = 1
                    else:
                        guessed_person[call.message.chat.id] += 1
                    if call.message.chat.id not in guessed_model:
                        guessed_model[call.message.chat.id] = 1
                    else:
                        guessed_model[call.message.chat.id] += 1

            if call.message.chat.id not in total_plays:
                total_plays[call.message.chat.id] = 1
            else:
                total_plays[call.message.chat.id] += 1

            keyboard = types.InlineKeyboardMarkup()
            button = types.InlineKeyboardButton(text="Поиграем еще!", callback_data="button")
            keyboard.add(button)
            bot.send_message(call.message.chat.id, emoji.emojize("Хочешь поиграть еще? :smiling_face_with_open_hands:"),
                             reply_markup=keyboard)


# Присылаем статистику с двумя картинками и с тремя циферками!
# Предлагаем играть еще :)))))
@bot.message_handler(commands=['stats'])
def send_statistics(message):
    # чтобы согласовать с числом
    sentencee = morph.parse('предложение')[0]
    fois = morph.parse('раз')[0]
    # сами числа
    g_p = guessed_person[message.chat.id]
    g_m = guessed_model[message.chat.id]
    t_p = total_plays[message.chat.id]

    # немного статистики
    bot.send_message(message.from_user.id, f'Всего ты играл {t_p} {fois.make_agree_with_number(t_p).word}')
    bot.send_message(message.from_user.id, f'Ты угадал {g_p} {sentencee.make_agree_with_number(g_p).word}')
    bot.send_message(message.from_user.id, f'Модель угадала {g_m} {sentencee.make_agree_with_number(g_m).word}')

    # строим первый график!
    labels = [
        'Модель', 'Пользователь'
    ]

    info = [
        guessed_model[message.chat.id], guessed_person[message.chat.id]
    ]

    # круговая (? -- pie!) диаграмма с процентным соотношением правильных ответов модели и пользователя
    fig, ax = plt.subplots()
    ax.set_title('Статистика')
    ax.pie(x=info, labels=labels, autopct='%1.f%%', colors=['#DE3163', '#FF7F50'])
    fig.savefig(f'{message.chat.id}stats.png')
    plt.clf()

    # отправляем фоточку
    photo = open(f'{message.chat.id}stats.png', 'rb')
    bot.send_photo(message.chat.id, photo)

    # второй график!
    info1 = [
        total_plays[message.chat.id] - guessed_model[message.chat.id], guessed_model[message.chat.id]
    ]

    info2 = [
        total_plays[message.chat.id] - guessed_person[message.chat.id], guessed_person[message.chat.id]
    ]

    fig, (ax1, ax2) = plt.subplots(nrows=1, ncols=2, figsize=(10, 6))

    ax1.barh(['Неправильные', 'Правильные'], info1, color='#DE3163')

    ax1.set_xticks(range(0, total_plays[message.chat.id], 1))

    ax1.invert_xaxis()

    ax1.set_title('Модель')

    ax2.barh(['Неправильные', 'Правильные'], info2, color='#FF7F50')

    ax2.set_xticks(range(0, total_plays[message.chat.id], 1))

    ax2.yaxis.set_label_position("right")
    ax2.yaxis.tick_right()

    ax2.set_title('Ты')

    fig.suptitle('Кто лучше: ты или модель?', weight='bold')

    fig.tight_layout()

    fig.savefig(f'{message.chat.id}beautiful.png')
    plt.clf()

    # этот график содержит два подграфика: статистика правильных/неправильных для модели и для пользователя

    beautiful = open(f'{message.chat.id}beautiful.png', 'rb')
    bot.send_photo(message.chat.id, beautiful)

    # снова предлагаем поиграть!!!!
    keyboard = types.InlineKeyboardMarkup()
    button = types.InlineKeyboardButton(text="Поиграем еще!", callback_data="button")
    keyboard.add(button)
    bot.send_message(message.chat.id, emoji.emojize("Хочешь поиграть еще? :smiling_face_with_open_hands:"),
                     reply_markup=keyboard)


# Функция help: для напоминания правил игры! Снова предлагаем играть :))))
@bot.message_handler(commands=['help'])
def helping(message):
    bot.send_message(message.from_user.id, emoji.emojize("Напоминаю правила игры! "
                                                         "Я присылаю тебе два предложения."
                                                         " Одно из них -- из текстов Л.Н. Толстого. "
                                                         "Второе -- сгенеированное компьютером. "
                                                         "Ты должен угадать, какое предложение сгенерировано."))

    keyboard = types.InlineKeyboardMarkup()

    # добавляем на нее кнопки
    button = types.InlineKeyboardButton(text="Играем!", callback_data="button")
    keyboard.add(button)

    # отправляем сообщение пользователю
    bot.send_message(message.chat.id, emoji.emojize("Нажми на кнопку, когда будешь готов к игре!"),
                     reply_markup=keyboard)


# Чтобы работало :)
bot.infinity_polling()


@app.route('/', methods=['GET', 'HEAD'])
def index():
    return 'ok'


@app.route(WEBHOOK_URL_PATH, methods=['POST'])
def webhook():
    if flask.request.headers.get('content-type') == 'application/json':
        json_string = flask.request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return ''
    else:
        flask.abort(403)
