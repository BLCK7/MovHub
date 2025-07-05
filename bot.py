import os
import logging
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters
)

# Logging sozlamalari
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Sozlamalar
TOKEN = "8030808703:AAHF4B8rTPyq4P8_ynQ_tdqts2gM8Ws-8P0"
ADMIN_ID = 5982232938
MOVIES_FOLDER = "movies"

# Kino bazasi {code: {title, filename, genre}}
movies_db = {}

def scan_movies_folder():
    """Scan the movies folder and add movie files to database"""
    if not os.path.exists(MOVIES_FOLDER):
        os.makedirs(MOVIES_FOLDER)
        logger.info(f"Created movies folder: {MOVIES_FOLDER}")
        return

    for filename in os.listdir(MOVIES_FOLDER):
        if filename.lower().endswith(('.mp4', '.mov', '.avi', '.mkv')):
            code = os.path.splitext(filename)[0]
            if code.isdigit() and code not in movies_db:
                movies_db[code] = {
                    'title': f"Movie {code}",
                    'filename': os.path.join(MOVIES_FOLDER, filename),
                    'genre': "Unknown"
                }

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    scan_movies_folder()
    await update.message.reply_text(
        "🎬 Movie Bot - Welcome!\n\n"
        f"📂 Total movies: {len(movies_db)}\n"
        "🔍 Send movie code (e.g., 100)\n"
        "📋 /list - Show all movies\n"
        "➕ Send video file to add new movie"
    )

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming video files"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Only admin can add movies!")
        return

    video = update.message.video or (update.message.document if update.message.document.mime_type.startswith('video/') else None)
    if not video:
        return

    context.user_data['new_movie'] = {
        'file_id': video.file_id,
        'file_name': video.file_name or f"{video.file_unique_id}.mp4"
    }
    
    await update.message.reply_text("📝 Please send the movie code (numbers only):")

async def handle_movie_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process movie code input"""
    if 'new_movie' not in context.user_data:
        return

    code = update.message.text.strip()
    if not code.isdigit():
        await update.message.reply_text("❌ Code must be numbers only! Try again:")
        return

    context.user_data['new_movie']['code'] = code
    await update.message.reply_text("🎬 Now send the movie title:")

async def handle_movie_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process movie title input"""
    if 'new_movie' not in context.user_data or 'code' not in context.user_data['new_movie']:
        return

    context.user_data['new_movie']['title'] = update.message.text
    await update.message.reply_text("🎭 Now send the movie genre:")

async def handle_movie_genre(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Finalize movie adding process"""
    if 'new_movie' not in context.user_data:
        return

    data = context.user_data['new_movie']
    code = data['code']
    genre = update.message.text
    
    os.makedirs(MOVIES_FOLDER, exist_ok=True)
    
    try:
        file = await context.bot.get_file(data['file_id'])
        file_ext = os.path.splitext(data['file_name'])[1] or '.mp4'
        file_path = os.path.join(MOVIES_FOLDER, f"{code}{file_ext}")
        await file.download_to_drive(file_path)
        
        movies_db[code] = {
            'title': data['title'],
            'filename': file_path,
            'genre': genre
        }
        
        await update.message.reply_text(
            f"✅ Movie added!\n\n"
            f"🔢 Code: {code}\n"
            f"🎬 Title: {data['title']}\n"
            f"🎭 Genre: {genre}\n"
            f"📁 File: {os.path.basename(file_path)}"
        )
    except Exception as e:
        logger.error(f"Error adding movie: {e}")
        await update.message.reply_text("❌ Failed to add movie!")
    finally:
        context.user_data.pop('new_movie', None)

async def send_movie(update: Update, context: ContextTypes.DEFAULT_TYPE, code: str):
    """Send movie file to user"""
    if code not in movies_db:
        await update.message.reply_text("❌ Movie not found!")
        return

    movie = movies_db[code]
    try:
        with open(movie['filename'], 'rb') as file:
            await update.message.reply_video(
                video=file,
                caption=f"🎬 {movie['title']}\n🔢 Code: {code}\n🎭 Genre: {movie['genre']}"
            )
    except Exception as e:
        logger.error(f"Error sending movie: {e}")
        await update.message.reply_text("❌ Error sending movie!")

async def list_movies(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all available movies"""
    if not movies_db:
        await update.message.reply_text("📭 No movies available!")
        return

    response = "📋 Movie List:\n\n"
    for code, movie in movies_db.items():
        response += f"🎬 {movie['title']} ({movie['genre']}) - Code: {code}\n"

    await update.message.reply_text(response)

async def handle_normal_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle normal text messages"""
    text = update.message.text.strip()
    if text.isdigit():
        await send_movie(update, context, text)
    else:
        await update.message.reply_text(
            "❌ Invalid input. Try:\n"
            "📋 /list - Show movies\n"
            "🔢 Send movie code (e.g., 100)\n"
            "➕ Send video to add movie (admin)"
        )

def main():
    os.makedirs(MOVIES_FOLDER, exist_ok=True)
    scan_movies_folder()

    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("list", list_movies))
    
    # Video fayllar uchun handler
    application.add_handler(MessageHandler(
        filters.VIDEO | (filters.Document.VIDEO & ~filters.COMMAND),
        handle_video
    ))
    
    # Matn xabarlar uchun handler
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        lambda update, context: (
            handle_movie_genre(update, context) if 'new_movie' in context.user_data and 'title' in context.user_data['new_movie'] else
            handle_movie_title(update, context) if 'new_movie' in context.user_data and 'code' in context.user_data['new_movie'] else
            handle_movie_code(update, context) if 'new_movie' in context.user_data else
            handle_normal_message(update, context)
        )
    ))

    application.run_polling()

if __name__ == "__main__":
    main()