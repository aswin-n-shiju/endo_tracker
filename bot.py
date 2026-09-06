import os
import json
from datetime import datetime
from dotenv import load_dotenv
import telebot
import google.generativeai as genai
from pyairtable import Api

load_dotenv()

bot = telebot.TeleBot(os.getenv("TELEGRAM_BOT_TOKEN"))
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Using 1.5-flash so you never hit the free-tier quota limits
model = genai.GenerativeModel("gemini-1.5-flash", generation_config={"response_mime_type": "application/json"})

airtable = Api(os.getenv("AIRTABLE_API_KEY"))
table = airtable.table(os.getenv("AIRTABLE_BASE_ID"), os.getenv("AIRTABLE_TABLE_NAME"))
ALLOWED_USERS = [int(i.strip()) for i in os.getenv("ALLOWED_TELEGRAM_IDS", "").split(",") if i.strip()]

@bot.message_handler(commands=['start'])
def start_cmd(message):
    if message.from_user.id in ALLOWED_USERS:
        bot.reply_to(message, "🦷 **EndoTrack Ready**\nSend clinic summaries here.")

@bot.message_handler(func=lambda msg: True)
def process_message(message):
    if message.from_user.id not in ALLOWED_USERS:
        return
    status = bot.reply_to(message, "⚙️ Parsing...")
    
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    EXTRACTION_PROMPT = f"""
    Extract dental clinic data into this JSON schema:
    {{
      "Date": string (YYYY-MM-DD format. If message mentions a day like 'yesterday' or 'Aug 12', calculate that date based on today: {today_str}. If no date mentioned, strictly use {today_str}),
      "Clinic": string, "Patients": integer, "Procedures": string,
      "Total_Fee": integer, "Paid": integer, "Balance": integer, "Notes": string
    }}
    Rules: If Paid is missing, assume 0. If Balance is missing, Balance = Total_Fee - Paid.
    """

    try:
        response = model.generate_content(f"{EXTRACTION_PROMPT}\n\nText:\n\"{message.text}\"")
        data = json.loads(response.text)
        
        status_label = "Settled" if data.get("Balance", 0) == 0 else "Pending"
        
        row = {
            "Date": data.get("Date", today_str),
            "Clinic": data.get("Clinic", "Unknown"),
            "Patients": int(data.get("Patients", 1)),
            "Procedures": data.get("Procedures", "N/A"),
            "Total_Fee": int(data.get("Total_Fee", 0)),
            "Paid": int(data.get("Paid", 0)),
            "Balance": int(data.get("Balance", 0)),
            "Status": status_label,
            "Notes": data.get("Notes", "")
        }
        
        table.create(row)
        
        bot.edit_message_text(f"✅ **Saved for {row['Date']}:** {data.get('Clinic')} | Bal: ₹{data.get('Balance')}", chat_id=message.chat.id, message_id=status.message_id)
    except Exception as err:
        bot.edit_message_text(f"❌ Error saving to Airtable.\n`{str(err)}`", chat_id=message.chat.id, message_id=status.message_id)

if __name__ == "__main__":
    bot.infinity_polling()