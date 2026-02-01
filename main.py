import discord
from discord.ext import commands
import os
import re
from flask import Flask
from threading import Thread

# --- 1. نظام منع النوم (Keep Alive) لضمان استمرار البوت في Render ---
app = Flask('')

@app.route('/')
def home():
    return "✅ البوت يعمل بنجاح! النطاق المعتمد: من 4 إلى 607"

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
    print(f'✅ البوت جاهز لاستقبال الأوامر (4-607)')
    print(f'-----------------------------------')

# --- 3. أمر الترتيب الذكي (يبحث عن الرقم داخل أي اسم ملف) ---
@bot.command()
async def ترتيب(ctx, number: int):
    if number < 4 or number > 607:
        await ctx.send("⚠️ الترتيب المتاح يبدأ من **4** وينتهي عند **607** فقط.")
        return

    try:
        image_folder = "images"
        if not os.path.exists(image_folder):
            await ctx.send("❌ مجلد images غير موجود في السيرفر!")
            return

        found = False
        target = str(number)
        
        # البحث عن الرقم ككلمة مستقلة داخل أسماء الملفات
        for filename in os.listdir(image_folder):
            #Regex يبحث عن الرقم بحيث لا يكون جزءاً من رقم آخر (مثلاً يجد 6 ولا يجدها داخل 66)
            if re.search(rf'(?<!\d){target}(?!\d)', filename):
                image_path = os.path.join(image_folder, filename)
                await ctx.send(file=discord.File(image_path))
                found = True
                break
        
        if not found:
            await ctx.send(f"❌ لم أجد أي صورة تحتوي على الرقم ({number}) في اسمها.")
            
    except Exception as e:
        await ctx.send(f"⚠️ حدث خطأ فني: {e}")

# --- 4. أمر الفحص المتقدم (لحل مشكلة عدم ظهور الصور) ---
@bot.command()
async def فحص(ctx):
    path = "images"
    if os.path.exists(path):
        files = os.listdir(path)
        if not files:
            await ctx.send("⚠️ المجلد `images` موجود لكنه **فارغ تماماً**! تأكد من عمل Commit
