import discord
from discord.ext import commands
import os
import re
from flask import Flask
from threading import Thread

# --- 1. خادم الويب (Keep Alive) ---
app = Flask('')
@app.route('/')
def home(): return "✅ البوت يعمل وجاهز للقرآن الكريم"

def run():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    Thread(target=run).start()

# --- 2. إعدادات البوت ---
intents = discord.Intents.default()
intents.message_content = True 
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'✅ متصل باسم: {bot.user}')

# --- 3. أمر الترتيب الذكي (يعالج الأصفار والأسماء الطويلة) ---
@bot.command()
async def ترتيب(ctx, number: int):
    # النطاق المطلوب
    if number < 4 or number > 607:
        await ctx.send("⚠️ النطاق المتاح من 4 إلى 607 فقط.")
        return

    image_folder = "images"
    if not os.path.exists(image_folder):
        await ctx.send("❌ مجلد images غير موجود.")
        return

    found = False
    
    # البحث في المجلد عن اسم الملف الذي يحتوي على الرقم
    for filename in os.listdir(image_folder):
        # استخراج كافة الأرقام من اسم الملف (مثلاً سيستخرج 96 من page-0096)
        numbers_in_file = re.findall(r'\d+', filename)
        
        # تحويل الأرقام المستخرجة إلى أرقام حقيقية (لحذف الأصفار الزائدة)
        # ومقارنتها بالرقم الذي كتبه المستخدم
        if any(int(n) == number for n in numbers_in_file):
            image_path = os.path.join(image_folder, filename)
            await ctx.send(file=discord.File(image_path))
            found = True
            break
    
    if not found:
        await ctx.send(f"❌ لم أجد ملفاً يطابق الرقم {number} (حتى مع البحث المتقدم).")

# --- 4. أمر المجلد (للتأكد) ---
@bot.command()
async def مجلد(ctx):
    path = "images"
    if os.path.exists(path):
        files = os.listdir(path)
        await ctx.send(f"📂 المجلد يحتوي على {len(files)} ملف. مثال: `{files[0]}`")
    else:
        await ctx.send("❌ المجلد غير موجود.")

# --- 5. التشغيل ---
if __name__ == "__main__":
    keep_alive()
    token = os.environ.get('DISCORD_TOKEN')
    bot.run(token)
