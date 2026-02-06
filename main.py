import os
import discord
from discord.ext import commands
from flask import Flask
from threading import Thread
import time

# --- إعداد سيرفر الويب (Flask) لتجاوز إغلاق Render ---
app = Flask('')

@app.route('/')
def home():
    return "<h1>البوت يعمل بنجاح! ✅</h1><p>تم تجاوز حظر IP بنجاح.</p>"

def run_flask():
    # Render يستخدم المنفذ 10000 افتراضياً
    app.run(host='0.0.0.0', port=10000)

def keep_alive():
    t = Thread(target=run_flask)
    t.daemon = True # لضمان إغلاق الخيط عند توقف البرنامج
    t.start()

# --- إعداد بوت ديسكورد ---
# تفعيل كافة الصلاحيات (Intents)
intents = discord.Intents.default()
intents.message_content = True  # ضروري لقراءة الرسائل
intents.members = True          # ضروري إذا كان البوت يرحب بالأعضاء

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print('---')
    print(f'Logged in as: {bot.user.name}')
    print(f'ID: {bot.user.id}')
    print('--- Status: Online ✅')

@bot.command()
async def ping(ctx):
    await ctx.send(f'🏓 Pong! Speed: {round(bot.latency * 1000)}ms')

# --- تشغيل البوت مع معالجة ذكية للأخطاء ---
if __name__ == "__main__":
    # 1. تشغيل السيرفر المساعد
    keep_alive()
    
    # 2. جلب التوكن من إعدادات البيئة (البيئة الآمنة)
    token = os.environ.get('TOKEN')
    
    if not token:
        print("❌ خطأ: TOKEN غير موجود في إعدادات Render (Environment Variables)")
    else:
        try:
            bot.run(token)
        except discord.errors.HTTPException as e:
            if e.status == 429:
                print("❌ خطأ 429: تم حظر الـ IP من قبل ديسكورد.")
                print("💡 الحل: اذهب لـ Render واعمل 'Clear Build Cache' فوراً.")
            else:
                print(f"❌ حدث خطأ غير متوقع: {e}")
