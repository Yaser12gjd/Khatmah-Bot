import discord
from discord.ext import commands
import os
from flask import Flask
from threading import Thread

# --- 1. خادم الويب (لحل مشكلة Port في Render ومنع النوم) ---
app = Flask('')

@app.route('/')
def home():
    return "✅ البوت يعمل بنجاح 24/7!"

def run():
    # Render يبحث عن هذا المنفذ (Port) تحديداً
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- 2. إعدادات البوت الأساسية ---
intents = discord.Intents.default()
intents.message_content = True  # تذكر تفعيلها في Discord Developer Portal
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'-----------------------------------')
    print(f'✅ تم تسجيل الدخول باسم: {bot.user}')
    print(f'✅ البوت جاهز للاستخدام!')
    print(f'-----------------------------------')

# --- 3. أمر إرسال الصور (ترتيب) ---
@bot.command()
async def ترتيب(ctx, number: int):
    try:
        # تأكد أن مجلد الصور اسمه images وكل الصور بصيغة jpg
        image_path = f"./images/{number}.jpg"
        
        if os.path.exists(image_path):
            await ctx.send(file=discord.File(image_path))
        else:
            # إذا لم يجد jpg يجرب png
            image_path = f"./images/{number}.png"
            if os.path.exists(image_path):
                await ctx.send(file=discord.File(image_path))
            else:
                await ctx.send(f"❌ لم أجد الصورة رقم ({number}) في المجلد.")
    except Exception as e:
        await ctx.send(f"⚠️ حدث خطأ أثناء إرسال الصورة.")
        print(f"Error: {e}")

# --- 4. التشغيل ---
keep_alive()  # تشغيل خادم الويب أولاً

# الحصول على التوكن من إعدادات Render (Environment Variables)
token = os.environ.get('DISCORD_TOKEN')
if token:
    bot.run(token)
else:
    print("❌ خطأ: التوكن غير موجود في الإعدادات!")
