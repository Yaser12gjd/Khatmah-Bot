import discord
from discord.ext import commands
import os
from flask import Flask
from threading import Thread

# --- 1. كود فتح البوابة ومنع النوم (لحل مشكلة Render & Replit) ---
app = Flask('')

@app.route('/')
def home():
    return "✅ البوت يعمل بنجاح 24/7!"

def run():
    # Render يستخدم بورت 10000 افتراضياً
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- 2. إعدادات البوت الأساسية ---
intents = discord.Intents.default()
intents.message_content = True  # قراءة محتوى الرسائل
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'-----------------------------------')
    print(f'✅ تم تسجيل الدخول باسم: {bot.user}')
    print(f'✅ البوت جاهز لاستقبال الأوامر!')
    print(f'-----------------------------------')

# --- 3. أمر إرسال الصور (ترتيب) ---
@bot.command()
async def ترتيب(ctx, number: int):
    try:
        # البحث عن الصورة داخل مجلد images
        # يدعم صيغ jpg و png
        image_path = f"./images/{number}.jpg"
        
        if not os.path.exists(image_path):
            image_path = f"./images/{number}.png"

        if os.path.exists(image_path):
            await ctx.send(file=discord.File(image_path))
        else:
            await ctx.send(f"❌ عذراً، لم أجد الصورة رقم ({number}) في المجلد.")
    except Exception as e:
        await ctx.send(f"⚠️ حدث خطأ أثناء محاولة إرسال الصورة.")
        print(f"Error: {e}")

# --- 4. تشغيل السيرفر والبوت ---
keep_alive()

# تأكد من إضافة DISCORD_TOKEN في Environment Variables
token = os.environ.get('DISCORD_TOKEN')
if token:
    bot.run(token)
else:
    print("❌ خطأ: لم يتم العثور على التوكن (DISCORD_TOKEN) في الإعدادات!")
