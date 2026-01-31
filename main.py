import discord
from discord.ext import commands
import os
import re
from flask import Flask
from threading import Thread

# --- 1. خادم الويب (Keep Alive) لمنع البوت من النوم في Render ---
app = Flask('')

@app.route('/')
def home():
    return "✅ البوت يعمل بنجاح! النطاق: من 4 إلى 607"

def run():
    # Render يستخدم المنفذ 10000 افتراضياً
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- 2. إعدادات البوت ---
intents = discord.Intents.default()
intents.message_content = True 
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'-----------------------------------')
    print(f'✅ تم تسجيل الدخول باسم: {bot.user}')
    print(f'✅ النطاق المعتمد: من 4 إلى 607')
    print(f'-----------------------------------')

# --- 3. أمر الترتيب الذكي (يبحث عن الرقم بدقة داخل اسم الملف) ---
@bot.command()
async def ترتيب(ctx, number: int):
    # التأكد من أن الرقم بين 4 و 607
    if number < 4 or number > 607:
        await ctx.send("⚠️ الترتيب المتاح يبدأ من **4** وينتهي عند **607** فقط.")
        return

    try:
        image_folder = "images"
        if not os.path.exists(image_folder):
            await ctx.send("❌ مجلد images غير موجود في GitHub!")
            return

        found = False
        target = str(number)
        
        # البحث في جميع ملفات المجلد
        for filename in os.listdir(image_folder):
            # استخدام Regex للبحث عن الرقم ككلمة مستقلة (عشان ما يرسل 44 لما تطلب 4)
            if re.search(rf'(?<!\d){target}(?!\d)', filename):
                image_path = os.path.join(image_folder, filename)
                await ctx.send(file=discord.File(image_path))
                found = True
                break
        
        if not found:
            await ctx.send(f"❌ لم أجد أي صورة تحتوي على الرقم ({number}) في اسمها داخل المجلد.")
            
    except Exception as e:
        print(f"Error: {e}")
        await ctx.send(f"⚠️ حدث خطأ فني: {e}")

# --- 4. أمر الفحص (للتأكد من الأسماء التي يراها البوت) ---
@bot.command()
async def فحص(ctx):
    if os.path.exists('images'):
        files = os.listdir('images')[:10]  # يعرض أول 10 ملفات فقط
        await ctx.send(f"✅ المجلد موجود. عينة من الملفات: {files}")
