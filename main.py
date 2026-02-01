import discord
from discord.ext import commands
import os
import re
from flask import Flask
from threading import Thread

# --- 1. خادم الويب (Keep Alive) ---
app = Flask('')
@app.route('/')
def home(): return "✅ البوت يعمل! النطاق: 4 إلى 607"

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

# --- 3. أمر الترتيب (البحث المرن) ---
@bot.command()
async def ترتيب(ctx, number: int):
    if number < 4 or number > 607:
        await ctx.send("⚠️ الترتيب من 4 إلى 607 فقط.")
        return

    image_folder = "images"
    if not os.path.exists(image_folder):
        await ctx.send("❌ لا يوجد مجلد باسم `images`. تأكد من اسم المجلد في GitHub!")
        return

    found = False
    target = str(number)
    
    for filename in os.listdir(image_folder):
        # يبحث عن الرقم ككلمة مستقلة في اسم الملف
        if re.search(rf'(?<!\d){target}(?!\d)', filename):
            image_path = os.path.join(image_folder, filename)
            await ctx.send(file=discord.File(image_path))
            found = True
            break
    
    if not found:
        await ctx.send(f"❌ لم أجد صورة تحتوي على الرقم ({number}). جرب أمر `!مجلد` للتأكد.")

# --- 4. أمر كشف محتوى المجلد (مهم جداً الآن) ---
@bot.command()
async def مجلد(ctx):
    path = "images"
    if os.path.exists(path):
        files = os.listdir(path)
        if not files:
            await ctx.send("📂 المجلد موجود لكنه **فارغ**!")
        else:
            # يرسل أول 15 اسم ملف موجود في المجلد
            names = "\n".join(files[:15])
            await ctx.send(f"📂 وجدنا {len(files)} ملف. هذه أول أسماء:\n```{names}```")
    else:
        # إذا لم يجد مجلد images، يطبع الملفات في المجلد الرئيسي
        main_files = os.listdir('.')
        await ctx.send(f"❌ لم أجد مجلد `images`. الملفات في الخارج هي: `{main_files}`")

# --- 5. التشغيل ---
if __name__ == "__main__":
    keep_alive()
    token = os.environ.get('DISCORD_TOKEN')
    bot.run(token)
