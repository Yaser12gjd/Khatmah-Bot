import discord
from discord.ext import tasks, commands
import datetime
import requests
import os

# --- الإعدادات (تأخذ من Render) ---
TOKEN = os.environ.get('DISCORD_TOKEN')
CHANNEL_ID = os.environ.get('CHANNEL_ID')

# إعدادات البوت الأساسية
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# المتغير الذي يحدد الصفحة الحالية (سيبدأ من 1)
current_page = 1

def get_prayer_times():
    """جلب مواقيت الصلاة لمدينة الرياض عبر API خارجي"""
    url = "https://api.aladhan.com/v1/timingsByCity?city=Riyadh&country=Saudi+Arabia&method=4"
    try:
        response = requests.get(url).json()
        return response['data']['timings']
    except Exception as e:
        print(f"خطأ في جلب المواقيت: {e}")
        return None

@bot.event
async def on_ready():
    print(f'✅ البوت متصل ومستعد باسم: {bot.user}')
    check_prayers.start()

@tasks.loop(minutes=1)
async def check_prayers():
    global current_page
    
    # التأكد من وجود رقم القناة
    if not CHANNEL_ID:
        return

    # التوقيت الحالي
    now = datetime.datetime.now().strftime("%H:%M")
    prayers = get_prayer_times()
    
    if prayers:
        # قائمة الصلوات المستهدفة
        target_times = {
            'Fajr': prayers['Fajr'],
            'Dhuhr': prayers['Dhuhr'],
            'Asr': prayers['Asr'],
            'Maghrib': prayers['Maghrib'],
            'Isha': prayers['Isha']
        }

        # التحقق إذا كان الوقت الحالي هو وقت أذان
        for prayer_name, prayer_time in target_times.items():
            if now == prayer_time:
                channel = bot.get_channel(int(CHANNEL_ID))
                if channel:
                    # صلاة الفجر ترسل 6 صفحات، والباقي 4 صفحات
                    pages_to_send = 6 if prayer_name == 'Fajr' else 4
                    
                    files = []
                    for i in range(pages_to_send):
                        # العودة للصفحة الأولى إذا اكتمل الختم (624 صفحة)
                        if current_page > 624:
                            current_page = 1
                        
                        # مسار الصورة (تأكد من وجود مجلد images وصيغة jpg)
                        image_path = f"images/{current_page}.jpg"
                        
                        if os.path.exists(image_path):
                            files.append(discord.File(image_path))
                        
                        current_page += 1
                    
                    if files:
                        await channel.send(
                            content=f"📖 **وردكم القرآني لصلاة {prayer_name} ({pages_to_send} صفحات)**\nتقبل الله منا ومنكم صالح الأعمال.",
                            files=files
                        )
                break # التوقف بعد العثور على الصلاة الحالية

bot.run(TOKEN)
