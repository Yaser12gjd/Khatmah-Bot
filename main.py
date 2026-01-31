import discord
from discord.ext import commands
import os
from flask import Flask
from threading import Thread

# --- 1. منع البوت من النوم ---
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
    print(f'✅ البوت جاهز! الترتيب من 4 إلى 607')

# --- 3. أمر الترتيب الذكي (يبحث عن بداية الاسم) ---
@bot.command()
async def ترتيب(ctx, number: int):
    if number < 4 or number > 607:
        await ctx.send("⚠️ الترتيب المتاح من **4** إلى **607** فقط.")
        return

    try:
        found = False
        image_folder = "images"
        
        # البحث عن أي ملف يبدأ بالرقم المطلوب
        for filename in os.listdir(image_folder):
            # التأكد أن الملف يبدأ بالرقم ويتبعه نقطة أو مسافة أو كلمة
            if filename.startswith(str(number)) and (filename[len(str(number))].lower() in ['.', ' ', '_'] or len(filename) == len(str(number))):
                image_path = os.path.join(image_folder, filename)
                await ctx.send(file=discord.File(image_path))
                found = True
                break
        
        if not found:
            await ctx.send(f"❌ لم أجد صورة تبدأ بالرقم {number}.")
            
    except Exception as e:
        print(f"Error: {e}")
        await ctx.send("⚠️ حدث خطأ أثناء البحث عن الصورة.")

# --- 4. التشغيل ---
if __name__ == "__main__":
    keep_alive()
    token = os.environ.get('DISCORD_TOKEN')
    bot.run(token)
