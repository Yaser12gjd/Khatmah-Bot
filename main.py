import discord
from discord.ext import commands
import os
from flask import Flask
from threading import Thread

# --- 1. خادم الويب (Keep Alive) لمنع البوت من النوم ---
app = Flask('')

@app.route('/')
def home():
    return "✅ البوت يعمل! النطاق الحالي: من 4 إلى 607"

def run():
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
    print(f'✅ متصل باسم: {bot.user}')
    print(f'✅ النطاق المعتمد: من 4 إلى 607')
    print(f'-----------------------------------')

# --- 3. أمر الترتيب (من 4 إلى 607) ---
@bot.command()
async def ترتيب(ctx, number: int):
    # التأكد أن الرقم يبدأ من 4 وينتهي عند 607
    if number < 4 or number > 607:
        await ctx.send("⚠️ الترتيب المتاح يبدأ من **4** وينتهي عند **607** فقط.")
        return

    try:
        found = False
        # يدعم البحث عن الصورة بصيغ مختلفة (jpg, png, jpeg...)
        for ext in ['jpg', 'png', 'jpeg', 'JPG', 'PNG', 'webp']:
            image_path = f"images/{number}.{ext}"
            
            if os.path.exists(image_path):
                await ctx.send(file=discord.File(image_path))
                found = True
                break
        
        if not found:
            await ctx.send(f"❌ لم أجد الصورة رقم ({number}) في المجلد. تأكد أنك رفعتها باسم `{number}.jpg` داخل مجلد images.")
            
    except Exception as e:
        print(f"Error: {e}")
        await ctx.send("⚠️ حدث خطأ أثناء إرسال الصورة.")

# --- 4. تشغيل البوت ---
if __name__ == "__main__":
    keep_alive()  # تشغيل المنبه لمنع البوت من الإغلاق
    token = os.environ.get('DISCORD_TOKEN')
    if token:
        bot.run(token)
    else:
        print("❌ خطأ: التوكن مفقود! تأكد من إضافته في Environment Variables في Render.")
