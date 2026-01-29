import discord
from discord.ext import tasks, commands
import datetime
import requests
import os

# جلب الإعدادات من Render
TOKEN = os.environ.get('DISCORD_TOKEN')
CHANNEL_ID = os.environ.get('CHANNEL_ID')

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

current_page = 1

def get_prayer_times():
    url = "https://api.aladhan.com/v1/timingsByCity?city=Riyadh&country=Saudi+Arabia&method=4"
    try:
        response = requests.get(url).json()
        return response['data']['timings']
    except:
        return None

@bot.event
async def on_ready():
    print(f'✅ البوت يعمل الآن باسم: {bot.user}')
    check_prayers.start()

@tasks.loop(minutes=1)
async def check_prayers():
    global current_page
    if not CHANNEL_ID: return

    now = datetime.datetime.now().strftime("%H:%M")
    prayers = get_prayer_times()
    
    target_prayers = ['Fajr', 'Dhuhr', 'Asr', 'Maghrib', 'Isha']
    
    if prayers and any(now == prayers[p] for p in target_prayers):
        channel = bot.get_channel(int(CHANNEL_ID))
        if channel:
            files = []
            for i in range(4): # إرسال 4 صفحات
                if current_page > 604: current_page = 1
                image_path = f"images/{current_page}.png"
                if os.path.exists(image_path):
                    files.append(discord.File(image_path))
                current_page += 1
            if files:
                await channel.send(content="📖 **حان وقت وردكم القرآني مع الأذان**", files=files)

bot.run(TOKEN)
