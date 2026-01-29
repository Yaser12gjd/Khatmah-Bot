import discord
from discord.ext import tasks, commands
from discord.ui import Button, View
import datetime
import requests
import os

TOKEN = os.environ.get('DISCORD_TOKEN')
CHANNEL_ID = os.environ.get('CHANNEL_ID')

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# متغيرات التحكم
current_page = 1
bot_active = True  # البوت يعمل بشكل افتراضي

def get_prayer_times():
    url = "https://api.aladhan.com/v1/timingsByCity?city=Riyadh&country=Saudi+Arabia&method=4"
    try:
        response = requests.get(url).json()
        return response['data']['timings']
    except: return None

# --- واجهة التحكم بالعربي ---
class ControlView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🛑 إيقاف كامل", style=discord.ButtonStyle.danger)
    async def stop_bot(self, interaction: discord.Interaction, button: discord.ui.Button):
        global bot_active
        bot_active = False
        await interaction.response.send_message("⚠️ تم إيقاف البوت بالكامل. لن يرسل أي ورد حتى يتم التشغيل يدوياً.", ephemeral=True)

    @discord.ui.button(label="✅ تشغيل البوت", style=discord.ButtonStyle.success)
    async def start_bot(self, interaction: discord.Interaction, button: discord.ui.Button):
        global bot_active
        bot_active = True
        await interaction.response.send_message("▶️ البوت يعمل الآن وسيرسل الورد مع الأذان القادم.", ephemeral=True)

@bot.command(name="اعدادات")
async def settings(ctx):
    embed = discord.Embed(title="⚙️ إعدادات بوت الختمة", description=f"الحالة الحالية: {'✅ يعمل' if bot_active else '🛑 متوقف'}", color=discord.Color.blue())
    await ctx.send(embed=embed, view=ControlView())

# --- خيار تجربة الصفحات بالترتيب ---
@bot.command(name="ترتيب")
async def check_order(ctx, page_num: int = None):
    global current_page
    target_page = page_num if page_num else current_page
    image_name = f"big-quran_compressed_page-{target_page:04d}.jpg"
    image_path = f"images/{image_name}"
    
    if os.path.exists(image_path):
        await ctx.send(content=f"🖼️ استعراض الصفحة رقم **({target_page})** للتأكد من الترتيب:", file=discord.File(image_path))
    else:
        await ctx.send(f"❌ لم أجد الصورة رقم {target_page}. تأكد من رفع الـ 624 صورة.")

@tasks.loop(minutes=1)
async def check_prayers():
    global current_page, bot_active
    if not CHANNEL_ID or not bot_active: return # الإيقاف الكامل هنا
    
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

@bot.event
async def on_ready():
    print(f'✅ البート متصل ومستعد باسم: {bot.user}')
    if not check_prayers.is_running(): check_prayers.start()

bot.run(TOKEN)
