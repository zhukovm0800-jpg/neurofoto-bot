import telebot
import requests
import time

BOT_TOKEN = "8679865262:AAGM38jAzyI3K89k3RGcRWMJUQMx6ehv6cQ"
REPLICATE_TOKEN = "r8_46s0fgGi8nCvNZKu0mRIFRxSI-IF0MQU0JLF8Q"
CRYPTO_PAY_TOKEN = "596191:AAS8rgB7h03sxYvibOLVQw41HZrjK3LMZYX"
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
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("⭐ 15 картинок — 50 Stars", callback_data="stars_15"))
    markup.add(telebot.types.InlineKeyboardButton("⭐ 50 картинок — 150 Stars", callback_data="stars_50"))
    bot.send_message(message.chat.id, "Выбери пакет:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("stars_"))
def send_invoice(call):
    packages = {"stars_15": (50, 15), "stars_150": (150, 50)}
    stars, images = packages[call.data]
    bot.send_invoice(
        call.message.chat.id,
        title=f"{images} картинок",
        description=f"Генерация {images} картинок в Нейро Фото",
        invoice_payload=f"{call.from_user.id}:{images}",
        provider_token="",
        currency="XTR",
        prices=[telebot.types.LabeledPrice(f"{images} картинок", stars)]
    )

@bot.pre_checkout_query_handler(func=lambda q: True)
def checkout(query):
    bot.answer_pre_checkout_query(query.id, ok=True)

@bot.message_handler(content_types=["successful_payment"])
def payment_done(message):
    payload = message.successful_payment.invoice_payload
    user_id, images = payload.split(":")
    user = get_user(int(user_id))
    user["images"] += int(images)
    bot.send_message(message.chat.id, f"✅ Оплачено! Добавлено {images} картинок. Баланс: {user['images']}")


@bot.callback_query_handler(func=lambda call: call.data.startswith("buy_"))
def create_invoice(call):
    packages = {"buy_15": (1, 15), "buy_50": (3, 50)}
    amount, images = packages[call.data]
    import requests as req
    r = req.post("https://pay.crypt.bot/api/createInvoice", 
        headers={"Crypto-Pay-API-Token": CRYPTO_PAY_TOKEN},
        json={"asset": "USDT", "amount": str(amount), 
              "description": f"{images} картинок для @neurofoto_ru_bot",
              "payload": f"{call.from_user.id}:{images}"})
    url = r.json()["result"]["bot_invoice_url"]
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("💎 Оплатить", url=url))
    bot.send_message(call.message.chat.id, f"Счёт на {amount} USDT за {images} картинок:", reply_markup=markup)

    

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
@bot.message_handler(commands=["add"])
def add_images(message):
    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.chat.id, "❌ Нет доступа.")
        return
    user = get_user(message.from_user.id)
    user["images"] += 15
    bot.send_message(message.chat.id, f"✅ Добавлено 15 картинок! Баланс: {user['images']}")

@bot.message_handler(func=lambda m: True)
def handle(message):
    generate_image(message)


import threading

def check_payments():
    import requests as req
    import time
    paid_ids = set()
    while True:
        r = req.get("https://pay.crypt.bot/api/getInvoices",
            headers={"Crypto-Pay-API-Token": CRYPTO_PAY_TOKEN},
            params={"status": "paid"})
        for inv in r.json().get("result", {}).get("items", []):
            if inv["invoice_id"] not in paid_ids:
                paid_ids.add(inv["invoice_id"])
                user_id, images = inv["payload"].split(":")
                user = get_user(int(user_id))
                user["images"] += int(images)
                bot.send_message(int(user_id), f"✅ Оплата получена! Добавлено {images} картинок. Баланс: {user['images']}")

threading.Thread(target=check_payments, daemon=True).start()


print("Бот запущен!")
bot.polling(none_stop=True)
