import telebot
import requests
import time

BOT_TOKEN = "8679865262:AAGM38jAzyI3K89k3RGcRWMJUQMx6ehv6cQ"
REPLICATE_TOKEN = "r8_46s0fgGi8nCvNZKu0mRIFRxSI-IF0MQU0JLF8Q"
ADMIN_ID = 504424806
bot = telebot.TeleBot(BOT_TOKEN)
users = {}

def get_user(user_id):
    if user_id not in users:
        users[user_id] = {"images": 0}
    return users[user_id]

@bot.message_handler(commands=["start"])
def start(message):
    get_user(message.from_user.id)
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Создать фото", "Баланс", "Купить")
    bot.send_message(message.chat.id, "Привет! Я Нейро Фото!\n\n15 картинок = 100 рублей\n\nОпиши что хочешь увидеть!", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "Баланс")
def balance(message):
    user = get_user(message.from_user.id)
    bot.send_message(message.chat.id, f"У тебя картинок: {user['images']}")

@bot.message_handler(func=lambda m: m.text == "Купить")
def buy(message):
    bot.send_message(message.chat.id, "Переведи 100 рублей на карту: 2200 0000 0000 0000\nПосле оплаты напиши @admin с чеком")

@bot.message_handler(func=lambda m: m.text == "Создать фото")
def ask_prompt(message):
    msg = bot.send_message(message.chat.id, "Опиши что хочешь увидеть:")
    bot.register_next_step_handler(msg, generate_image)

def generate_image(message):
    user = get_user(message.from_user.id)
    if user["images"] <= 0:
        bot.send_message(message.chat.id, "У тебя нет картинок! Нажми Купить")
        return
    bot.send_message(message.chat.id, "Создаю картинку, подожди...")
    try:
        headers = {"Authorization": f"Bearer {REPLICATE_TOKEN}", "Content-Type": "application/json"}
        data = {"version": "black-forest-labs/flux-schnell", "input": {"prompt": message.text, "num_outputs": 1}}
        response = requests.post("https://api.replicate.com/v1/predictions", headers=headers, json=data)
        prediction_id = response.json()["id"]
        for _ in range(30):
            time.sleep(2)
            result = requests.get(f"https://api.replicate.com/v1/predictions/{prediction_id}", headers=headers).json()
            if result["status"] == "succeeded":
                user["images"] -= 1
                bot.send_photo(message.chat.id, result["output"][0], caption=f"Готово! Осталось: {user['images']}")
                return
            elif result["status"] == "failed":
                break
        bot.send_message(message.chat.id, "Ошибка. Попробуй ещё раз.")
    except Exception:
        bot.send_message(message.chat.id, "Что-то пошло не так. Попробуй ещё раз.")

@bot.message_handler(func=lambda m: True)
def handle(message):
    generate_image(message)
@bot.message_handler(commands=["add"])
def add_images(message):
    if message.from_user.id == message.chat.id:
        user = get_user(message.from_user.id)
        user["images"] += 15
        bot.send_message(message.chat.id, f"Добавлено 15 картинок! Баланс: {user['images']}")

print("Бот запущен!")
bot.polling(none_stop=True)
