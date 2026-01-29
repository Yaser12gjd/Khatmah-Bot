import discord
from discord.ext import tasks, commands
import datetime
import requests
import os

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
    except: return None

@bot.event
async def on_ready():
    print(f'✅ البوت متصل ومستعد باسم: {bot.user}')
    if not check_prayers.is_running():
        check_prayers.start()

# --- أمر للتجربة الآن فوراً ---
@bot.command()
async def test(ctx):
    global current_page
    image_name = f"big-quran_compressed_page-{current_page:04d}.jpg"
    image_path = f"images/{image_name}"
    
    if os.path.exists(image_path):
        await ctx.send(content="📖 تجربة إرسال الصفحة الأولى:", file=discord.File(image_path))
    else:
        await ctx.send(f"❌ لم أجد الصورة في هذا المسار: {image_path}")

@tasks.loop(minutes=1)
async def check_prayers():
    global current_page
    if not CHANNEL_ID: return
    now = datetime.datetime.now().strftime("%H:%M")
    prayers = get_prayer_times()
    if prayers:
        target_times = {'Fajr': prayers['Fajr'], 'Dhuhr': prayers['Dhuhr'], 'Asr': prayers['Asr'], 'Maghrib': prayers['Maghrib'], 'Isha': prayers['Isha']}
        for prayer_name, prayer_time in target_times.items():
            if now == prayer_time:
                channel = bot.get_channel(int(CHANNEL_ID))
                if channel:
                    pages = 6 if prayer_name == 'Fajr' else 4
                    files = []
                    for _ in range(pages):
                        if current_page > 624: current_page = 1
                        path = f"images/big-quran_compressed_page-{current_page:04d}.jpg"
                        if os.path.exists(path): files.append(discord.File(path))
                        current_page += 1
                    if files: await channel.send(content=f"📖 ورد صلاة {prayer_name}", files=files)
                break

bot.run(TOKEN)
