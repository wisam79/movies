from aiogram import Bot, Dispatcher, executor, types
import logging
import os
import sqlite3
from movie_api import get_movies_by_genre, search_movie, get_movie_details
import random

API_TOKEN = os.getenv("BOT_TOKEN")
logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# Connect to SQLite DB
conn = sqlite3.connect('movies.db')
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS favorites (
    user_id INTEGER,
    movie_id INTEGER,
    title TEXT,
    overview TEXT,
    rating REAL
)''')
conn.commit()

# Genre mapping
genre_map = {
    'أكشن': 28,
    'كوميديا': 35,
    'دراما': 18,
    'رعب': 27,
    'رومانسي': 10749
}

@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    await message.reply("مرحباً بك في MovieGenieBot!\n\nأوامر الاستخدام:\n/genre - اختر نوع الفيلم\n/search - ابحث عن فيلم\n/favorites - قائمة المفضلة\n/daily - اقتراح يومي\n/mood - اقتراح حسب المزاج")

@dp.message_handler(commands=['genre'])
async def genre_handler(message: types.Message):
    buttons = [types.KeyboardButton(text=key) for key in genre_map.keys()]
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True).add(*buttons)
    await message.reply("اختر نوع الفيلم:", reply_markup=keyboard)

@dp.message_handler(lambda msg: msg.text in genre_map)
async def show_movies(message: types.Message):
    movies = get_movies_by_genre(genre_map[message.text])
    reply = ""
    for m in movies[:5]:
        reply += f"\n*{m['title']}*\n{m['overview'][:150]}...\n⭐️ التقييم: {m.get('vote_average', 'غير متوفر')}\n/like_{m['id']}\n\n"
    await message.reply(reply or "لا توجد أفلام حالياً.", parse_mode='Markdown', reply_markup=types.ReplyKeyboardRemove())

@dp.message_handler(lambda msg: msg.text.startswith("/like_"))
async def add_to_favorites(message: types.Message):
    movie_id = int(message.text.split("_")[-1])
    details = get_movie_details(movie_id)
    user_id = message.from_user.id
    with sqlite3.connect('movies.db') as conn:
        c = conn.cursor()
        c.execute("INSERT INTO favorites (user_id, movie_id, title, overview, rating) VALUES (?, ?, ?, ?, ?)",
                  (user_id, movie_id, details['title'], details['overview'], details.get('vote_average')))
        conn.commit()
    await message.reply(f"تمت إضافة *{details['title']}* إلى المفضلة.", parse_mode='Markdown')

@dp.message_handler(commands=['favorites'])
async def show_favorites(message: types.Message):
    user_id = message.from_user.id
    with sqlite3.connect('movies.db') as conn:
        c = conn.cursor()
        c.execute("SELECT title, overview, rating FROM favorites WHERE user_id=? ORDER BY rowid DESC LIMIT 5", (user_id,))
        rows = c.fetchall()
    if not rows:
        await message.reply("قائمة المفضلة فارغة.")
        return
    reply = ""
    for title, overview, rating in rows:
        reply += f"\n*{title}*\n{overview[:150]}...\n⭐️ {rating or '؟'}\n\n"
    await message.reply(reply, parse_mode='Markdown')

@dp.message_handler(commands=['search'])
async def search_command(message: types.Message):
    await message.reply("أدخل اسم الفيلم للبحث عنه:")

@dp.message_handler(lambda message: message.reply_to_message and 'أدخل اسم الفيلم' in message.reply_to_message.text)
async def handle_search(message: types.Message):
    results = search_movie(message.text)
    if results:
        reply = ""
        for m in results[:5]:
            reply += f"*{m['title']}* ({m.get('release_date', '')[:4]})\n{m['overview'][:150]}...\n⭐️ {m.get('vote_average', '؟')}\n/like_{m['id']}\n\n"
    else:
        reply = "لم يتم العثور على نتائج."
    await message.reply(reply, parse_mode='Markdown')

@dp.message_handler(commands=['daily'])
async def daily_suggestion(message: types.Message):
    genre_id = random.choice(list(genre_map.values()))
    movie = random.choice(get_movies_by_genre(genre_id))
    reply = f"*{movie['title']}*\n{movie['overview'][:150]}...\n⭐️ التقييم: {movie.get('vote_average', '؟')}\n/like_{movie['id']}"
    await message.reply(reply, parse_mode='Markdown')

@dp.message_handler(commands=['mood'])
async def ask_mood(message: types.Message):
    await message.reply("كيف هو شعورك الآن؟ (مثال: طفشان، متوتر، سعيد...)")

@dp.message_handler(lambda m: m.reply_to_message and 'كيف هو شعورك' in m.reply_to_message.text)
async def mood_response(message: types.Message):
    mood = message.text.strip().lower()
    if 'طفشان' in mood:
        genre_id = 35
    elif 'متوتر' in mood:
        genre_id = 18
    elif 'حزين' in mood:
        genre_id = 10749
    else:
        genre_id = random.choice(list(genre_map.values()))
    movie = random.choice(get_movies_by_genre(genre_id))
    reply = f"*{movie['title']}*\n{movie['overview'][:150]}...\n⭐️ {movie.get('vote_average', '؟')}\n/like_{movie['id']}"
    await message.reply(reply, parse_mode='Markdown')

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
