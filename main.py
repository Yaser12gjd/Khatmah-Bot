import discord
from discord.ext import commands
import os
from flask import Flask
from threading import Thread

# --- 1. خادم الويب (لمنع البوت من النوم في Render) ---
app = Flask('')

@app.route('/')
def home():
    return "✅ البوت يعمل بنجاح! النطاق الحالي: من 4 إلى 607"

def run():
    # Render يستخدم المنفذ 10000 بشكل افتراضي
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

# --- 3. أمر الترتيب الذكي (يبحث عن الرقم في بداية اسم الملف) ---
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
        # البحث عن أي ملف يبدأ بالرقم المطلوب (يتجاهل بقية الاسم)
        for filename in os.listdir(image_folder):
            # نتحقق إذا كان الملف يبدأ بالرقم ويتبعه نقطة أو مسافة (مثلاً 4.jpg أو 4 image.png)
            if filename.startswith(str(number)):
                # نتحقق أن الرقم هو فعلاً الرقم المطلوب وليس جزءاً من رقم أكبر (مثلاً لا نأخذ 44 عند طلب 4)
                name_parts = filename.split('.')
                pure_name = name_parts[0].split(' ')[0].split('_')[0].split('-')[0]
                
                if pure_name == str(number):
                    image_path = os.path.join(image_folder, filename)
                    await ctx.send(file=discord.File(image_path))
                    found = True
                    break
        
        if not found:
            await ctx.send(f"❌ لم أجد صورة تبدأ بالرقم ({number}) داخل مجلد images.")
            
    except Exception as e:
        print(f"Error: {e}")
        await ctx.send("⚠️ حدث خطأ فني أثناء جلب الصورة.")

# --- 4. تشغيل البوت ---
if __name__ == "__main__":
    keep_alive()  # تشغيل المنبه لمنع النوم
    token = os.environ.get('DISCORD_TOKEN')
    if token:
        bot.run(token)
    else:
        print("❌ خطأ: التوكن مفقود! تأكد من إضافته في Environment Variables في Render.")
