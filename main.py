import discord
from discord.ext import commands, tasks
from discord.ui import Button, View
import os
import json
import re
import requests
import datetime
import pytz
import asyncio
from flask import Flask
from threading import Thread

# --- 1. خادم الويب ---
app = Flask('')
@app.route('/')
def home(): return "✅ البوت يعمل بنظام الأزرار المتطور"

def run():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    Thread(target=run).start()

# --- 2. الإعدادات والذاكرة ---
intents = discord.Intents.default()
intents.message_content = True 
intents.members = True 
bot = commands.Bot(command_prefix='!', intents=intents)

DB_FILE = "subscribers.txt"
PAGE_FILE = "last_page.txt"
CHANNELS_FILE = "channels.json"

def get_subs():
    if not os.path.exists(DB_FILE): return set()
    with open(DB_FILE, "r") as f:
        return set(line.strip() for line in f if line.strip())

def add_sub(user_id):
    subs = get_subs()
    subs.add(str(user_id))
    with open(DB_FILE, "w") as f:
        for s in subs: f.write(f"{s}\n")

def load_channels():
    if not os.path.exists(CHANNELS_FILE): return {}
    try:
        with open(CHANNELS_FILE, "r") as f: return json.load(f)
    except: return {}

def save_channel(guild_id, channel_id):
    channels = load_channels()
    channels[str(guild_id)] = channel_id
    with open(CHANNELS_FILE, "w") as f: json.dump(channels, f)

def get_last_page():
    if not os.path.exists(PAGE_FILE): return 4
    with open(PAGE_FILE, "r") as f:
        try: return int(f.read().strip())
        except: return 4

def save_next_start_page(last_sent):
    next_p = last_sent + 1
    if next_p > 607: next_p = 4
    with open(PAGE_FILE, "w") as f: f.write(str(next_p))
    return next_p

# --- 3. كلاس الأزرار (التفعيل والإلغاء) ---
class SetupView(View):
    def __init__(self):
        super().__init__(timeout=None) # الزر لا ينتهي وقته

    @discord.ui.button(label="🔔 تفعيل التنبيهات", style=discord.ButtonStyle.green, custom_id="sub_button")
    async def subscribe(self, interaction: discord.Interaction, button: Button):
        add_sub(interaction.user.id)
        await interaction.response.send_message(f"✅ تم تفعيل تنبيهات الأذان والورد لك يا {interaction.user.mention}", ephemeral=True)

    @discord.ui.button(label="🔕 إلغاء التنبيه", style=discord.ButtonStyle.red, custom_id="unsub_button")
    async def unsubscribe(self, interaction: discord.Interaction, button: Button):
        subs = get_subs()
        user_id = str(interaction.user.id)
        if user_id in subs:
            subs.remove(user_id)
            with open(DB_FILE, "w") as f:
                for s in subs: f.write(f"{s}\n")
            await interaction.response.send_message("🔕 تم إلغاء اشتراكك في التنبيهات.", ephemeral=True)
        else:
            await interaction.response.send_message("⚠️ أنت غير مشترك أصلاً.", ephemeral=True)

# --- 4. المهام التلقائية ---
@tasks.loop(seconds=35)
async def check_prayer_time():
    tz = pytz.timezone('Asia/Riyadh')
    now = datetime.datetime.now(tz).strftime("%H:%M")
    
    try:
        url = "http://api.aladhan.com/v1/timingsByCity?city=Riyadh&country=Saudi+Arabia&method=4"
        times = requests.get(url).json()['data']['timings']
    except: return

    prayers = {"Fajr":"الفجر", "Dhuhr":"الظهر", "Asr":"العصر", "Maghrib":"المغرب", "Isha":"العشاء"}
    for eng, arb in prayers.items():
        p_time = datetime.datetime.strptime(times[eng], "%H:%M").strftime("%H:%M")
        if now == p_time:
            start_p = get_last_page()
            end_p = min(start_p + 3, 607)
            subs = get_subs()
            channels = load_channels()
            
            for g_id, c_id in channels.items():
                channel = bot.get_channel(int(c_id))
                if channel:
                    mentions = " ".join([f"<@{s}>" for s in subs if channel.guild.get_member(int(s))])
                    await channel.send(f"🕋 **حان الآن موعد أذان {arb} بتوقيت الرياض**\n📖 وردكم: من صفحة {start_p} إلى {end_p}\n🔔 {mentions}")
                    for i in range(start_p, end_p + 1):
                        image_folder = "images"
                        for filename in os.listdir(image_folder):
                            if any(int(n) == i for n in re.findall(r'\d+', filename)):
                                await channel.send(file=discord.File(os.path.join(image_folder, filename)))
            
            save_next_start_page(end_p)
            await asyncio.sleep(65)
            break

# --- 5. الأوامر ---
@bot.event
async def on_ready():
    bot.add_view(SetupView()) # تجعل الأزرار تعمل حتى بعد إعادة تشغيل البوت
    print(f'✅ البوت يعمل بنظام الأزرار')
    if not check_prayer_time.is_running(): check_prayer_time.start()

@bot.command()
@commands.has_permissions(administrator=True)
async def ضبط(ctx):
    save_channel(ctx.guild.id, ctx.channel.id)
    embed = discord.Embed(title="🕌 نظام ختم القرآن الكريم", 
                          description="اضغط على الأزرار أدناه للتحكم في تنبيهات الأذان والورد اليومي الخاص بك.", 
                          color=discord.Color.blue())
    await ctx.send(embed=embed, view=SetupView())

@bot.command()
async def تجربة(ctx):
    start_p = get_last_page()
    end_p = min(start_p + 3, 607)
    await ctx.send(f"🧪 تجربة الورد لصفحات: {start_p}-{end_p}")
    # (كود البحث عن الصور وإرسالها كما هو سابقاً)
