import os
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import ReplyKeyboardBuilder
import requests
import redis.asyncio as redis
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime, time
from dotenv import load_dotenv

# تحميل الإعدادات
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
TMDB_API_KEY = os.getenv("TMDB_API_KEY")
ADMIN_IDS = os.getenv("ADMIN_IDS", "").split(',')

# تكوين قاعدة البيانات
Base = declarative_base()
engine = create_engine(os.getenv("DATABASE_URL"))
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# نماذج قاعدة البيانات
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    username = Column(String(50))
    first_name = Column(String(50))
    last_name = Column(String(50))
    notifications = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class FavoriteMovie(Base):
    __tablename__ = "favorite_movies"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    movie_id = Column(Integer, nullable=False)
    movie_title = Column(String(100), nullable=False)
    added_at = Column(DateTime, default=datetime.utcnow)

# إنشاء الجداول
Base.metadata.create_all(bind=engine)

# خدمة TMDb
class TMDBService:
    BASE_URL = "https://api.themoviedb.org/3"
    
    @staticmethod
    async def get_movies(genre: str, mood: str = None):
        genres = {
            "أكشن": 28, "كوميدي": 35, "دراما": 18, 
            "رومانسي": 10749, "خيال علمي": 878
        }
        params = {
            'api_key': TMDB_API_KEY,
            'with_genres': genres.get(genre, 28),
            'language': 'ar'
        }
        try:
            response = requests.get(f"{TMDBService.BASE_URL}/discover/movie", params=params)
            movies = response.json().get('results', [])[:5]
            return [
                {
                    'id': m['id'],
                    'title': m.get('title', 'لا يوجد عنوان'),
                    'year': m.get('release_date', '')[:4],
                    'rating': m.get('vote_average', 0),
                    'poster': f"https://image.tmdb.org/t/p/w500{m['poster_path']}" if m.get('poster_path') else None
                } for m in movies
            ]
        except:
            return None
    
    @staticmethod
    async def search_movie(query: str):
        try:
            response = requests.get(
                f"{TMDBService.BASE_URL}/search/movie",
                params={
                    'api_key': TMDB_API_KEY,
                    'query': query,
                    'language': 'ar'
                }
            )
            movies = response.json().get('results', [])[:3]
            return [
                {
                    'id': m['id'],
                    'title': m.get('title', 'لا يوجد عنوان'),
                    'year': m.get('release_date', '')[:4]
                } for m in movies
            ]
        except:
            return None

# إنشاء البوت
bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
storage = RedisStorage(redis=redis.Redis())
dp = Dispatcher(storage=storage)

# لوحات المفاتيح
def main_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.row(
        types.KeyboardButton(text="🎬 اقتراح فيلم"),
        types.KeyboardButton(text="🔍 بحث عن فيلم")
    )
    builder.row(
        types.KeyboardButton(text="💖 قائمتي المفضلة"),
        types.KeyboardButton(text="⚙️ الإعدادات")
    )
    return builder.as_markup(resize_keyboard=True)

def genres_keyboard():
    builder = ReplyKeyboardBuilder()
    genres = ["أكشن", "كوميدي", "دراما", "رومانسي", "خيال علمي"]
    for genre in genres:
        builder.add(types.KeyboardButton(text=genre))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

# المعالجات الأساسية
@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer(
        "مرحباً بك في بوت أفلامي! 🎬\n"
        "يمكنني مساعدتك في إيجاد أفلام رائعة تناسب ذوقك.\n"
        "استخدم الأزرار أدناه للبدء:",
        reply_markup=main_keyboard()
    )

@dp.message(F.text == "🎬 اقتراح فيلم")
async def suggest_movie(message: types.Message):
    await message.answer("اختر نوع الفيلم:", reply_markup=genres_keyboard())

@dp.message(F.text.in_(["أكشن", "كوميدي", "دراما", "رومانسي", "خيال علمي"]))
async def send_movie_suggestion(message: types.Message):
    movies = await TMDBService.get_movies(message.text)
    if not movies:
        await message.answer("عذراً، لم أتمكن من العثور على أفلام.", reply_markup=main_keyboard())
        return
    
    response = "🎬 إليك بعض الاقتراحات:\n\n"
    for movie in movies:
        response += f"📽 {movie['title']} ({movie['year']})\n⭐ التقييم: {movie['rating']}/10\n\n"
    
    await message.answer(response, reply_markup=main_keyboard())
    
    if movies[0]['poster']:
        await message.answer_photo(movies[0]['poster'])

# الإشعارات اليومية
async def send_daily_notification():
    db = SessionLocal()
    users = db.query(User).filter(User.notifications == True).all()
    movies = await TMDBService.get_movies("أكشن")  # يمكن تغيير هذا لاختيار عشوائي
    
    if movies:
        for user in users:
            try:
                await bot.send_message(
                    user.telegram_id,
                    f"🎬 فيلم اليوم:\n{movies[0]['title']} ({movies[0]['year']})\n⭐ {movies[0]['rating']}/10",
                    reply_markup=main_keyboard()
                )
            except:
                pass

# التشغيل الرئيسي
async def main():
    scheduler = AsyncIOScheduler()
    scheduler.add_job(send_daily_notification, 'cron', hour=12, minute=0)
    scheduler.start()
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
