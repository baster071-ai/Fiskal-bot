import logging
import os
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

# --- KONFIGURACJA (Pobierane z Render) ---
# W Render ustawisz te zmienne środowiskowe, żeby kod ich nie widział w pliku
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
GROQ_API_KEY = os.getenv('GROQ_API_KEY')

# Baza kodów
MENU = {
    "focaccia": "1", "marinara": "2", "classica": "3", "diavola": "4",
    "napoli": "5", "vegetariana": "6", "carbonara": "7", "mortadella": "8",
    "capriciosa": "9", "pancetta e salame": "10", "don corleone": "11",
    "romana": "12", "quatro formaggi": "13", "montegusto": "14",
    "margheritta": "16", "carne": "17", "swojska": "19", "frutti di mare": "51",
    "hawajska": "85", "cotto e funghi": "93", "pepperoni": "94",
    "con pollo": "95", "al broccoli": "97", "pancetta e asparagi": "108",
    "anchois": "109", "anatra arrosto": "110",
    "vege": "56", "kurczak panuozzo": "56", "wedlina panuozzo": "56", "panuozzo": "56",
    "makaron z kurczakiem": "82", "makaron z boczkiem": "83",
    "makaron z krewetkami": "84", "makaron z feta": "111",
    "grecka": "98", "kurczak salatka": "100", "krewetka salatka": "34",
    "kubelek maly": "57", "kubelek sredni": "103", "kubelek duzy": "58",
    "frytki male": "44", "frytki duze": "45",
    "makaron z sosem": "112", "pizza dla dzieci": "113",
    "espresso": "35", "espresso doppio": "114", "americano": "36",
    "flat white": "37", "latte": "38", "latte macchiato": "39", "herbata": "40",
    "sok z owocow": "115", "sok z warzyw": "116", "mix sokow": "117"
}

def normalize_text(text):
    text = text.lower().strip()
    replacements = {'ą':'a', 'ć':'c', 'ę':'e', 'ł':'l', 'ń':'n', 'ó':'o', 'ś':'s', 'ź':'z', 'ż':'z'}
    for pl, eng in replacements.items():
        text = text.replace(pl, eng)
    return text

def process_order_text(user_text):
    items = [normalize_text(item) for item in user_text.replace('\n', ',').replace(' i ', ',').split(',') if item.strip()]
    response = "🍕 **Kody do nabicia:**\n\n"
    found_any = False
    
    for item in items:
        if not item:
            continue
        found = False
        for key, code in MENU.items():
            if item in key or key in item:
                response += f"• {item.title()} ➡️ Kod: **{code}**\n"
                found = True
                found_any = True
                break
        if not found:
            response += f"• {item.title()} ➡️ ❌ *Nie znaleziono w menu*\n"
            
    if not found_any:
        response = "Nie rozpoznałem żadnej pozycji. Spróbuj powiedzieć np.: 'Diavola, Frytki duże, Latte'"
    return response

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    response = process_order_text(update.message.text)
    await update.message.reply_text(response, parse_mode='Markdown')

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("🎤 Słucham... przetwarzam nagranie.")
    
    voice_file = await update.message.voice.get_file()
    file_path = f"voice_{update.message.from_user.id}.ogg"
    await voice_file.download_to_drive(file_path)
    
    try:
        # Używamy darmowego API Groq
        url = "https://api.groq.com/openai/v1/audio/transcriptions"
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}"}
        
        with open(file_path, "rb") as f:
            files = {
                "file": (file_path, f),
                "model": (None, "whisper-large-v3"),
                "language": (None, "pl"),
                "response_format": (None, "json")
            }
            response = requests.post(url, headers=headers, files=files)
            
        result = response.json()
        transcription = result.get("text", "")
        
        if not transcription:
            await msg.edit_text("❌ Nie udało się rozpoznać mowy. Spróbuj jeszcze raz.")
            return

        order_result = process_order_text(transcription)
        await msg.edit_text(f"🗣️ Usłyszałem: _{transcription}_\n\n{order_result}", parse_mode='Markdown')
        
    except Exception as e:
        await msg.edit_text("❌ Wystąpił błąd podczas przetwarzania dźwięku.")
        print(f"Błąd Groq: {e}")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

if __name__ == '__main__':
    print("Bot uruchomiony...")
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_text))
    application.add_handler(MessageHandler(filters.VOICE, handle_voice))
    application.run_polling()