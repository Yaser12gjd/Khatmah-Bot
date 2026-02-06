import discord
from discord.ext import commands, tasks
from discord.ui import Button, View, Select
import os
import json
import re
import requests
import datetime
import pytz
import asyncio
from flask import Flask
from threading import Thread

# --- 1. خادم الويب لبقاء البوت حياً (Keep Alive) ---
app = Flask('')
@app.route('/')
def home(): return "✅ البوت يعمل بنظام الورد والأذان"

def run():
    # Render يطلب تشغيل السيرفر على بورت 10000 افتراضياً
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- 2. إعدادات البوت والذاكرة ---
intents = discord.Intents.default()
intents.message_content = True 
intents.members = True 
bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

CHANNELS_FILE = "channels.json"
PAGE_FILE = "last_page.txt"
ROLE_NAME = "ختمة"

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

def find_image(number):
    image_folder = "images"
    if not os.path.exists(image_folder): return None
    for filename in os.listdir(image_folder):
        nums = re.findall(r'\d+', filename)
        if any(int(n) == number for n in nums):
            return os.path.join(image_folder, filename)
    return None

# --- 3. واجهة التحكم (القائمة والأزرار) ---
class ChannelSelect(Select):
    def __init__(self, channels):
        options = [discord.SelectOption(label=c.name[:25], value=str(c.id)) for c in channels[:25]]
        super().__init__(placeholder="اختر قناة الورد القرآني...", options=options)

    async def callback(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ للمسؤولين فقط!", ephemeral=True)
        save_channel(interaction.guild.id, self.values[0])
        await interaction.response.send_message(f"✅ تم ضبط القناة بنجاح!", ephemeral=True)

class QuranControlView(View):
    def __init__(self, channels=None):
        super().__init__(timeout=None)
        if channels:
            self.add_item(ChannelSelect(channels))

    @discord.ui.button(label="🔔 تفعيل التنبيهات", style=discord.ButtonStyle.green, custom_id="sub_role_btn")
    async def subscribe(self, interaction: discord.Interaction, button: Button):
        role = discord.utils.get(interaction.guild.roles, name=ROLE_NAME)
        if not role:
            return await interaction.response.send_message(f"⚠️ رتبة '{ROLE_NAME}' غير موجودة، اكتب !إعدادات أولاً.", ephemeral=True)
        try:
            await interaction.user.add_roles(role)
            await interaction.response.send_message(f"✅ تم منحك رتبة {ROLE_NAME}!", ephemeral=True)
        except:
            await interaction.response.send_message("❌ فشل منح الرتبة، تأكد أن رتبة البوت أعلى من رتبة ختمة.", ephemeral=True)

    @discord.ui.button(label="🧪 تجربة", style=discord.ButtonStyle.blurple, custom_id="test_btn")
    async def test(self, interaction: discord.Interaction, button: Button):
        channels = load_channels()
        c_id = channels.get(str(interaction.guild.id))
        if not c_id: return await interaction.response.send_message("⚠️ اختر القناة أولاً!", ephemeral=True)
        
        await interaction.response.defer(ephemeral=True)
        chan = bot.get_channel(int(c_id))
        if chan:
            page = get_last_page()
            path = find_image(page)
            await chan.send(f"🧪 تجربة الورد - صفحة {page}")
            if path: await chan.send(file=discord.File(path))
            await interaction.followup.send("✅ تمت التجربة!", ephemeral=True)

# --- 4. المهمة التلقائية (الأذان) ---
@tasks.loop(minutes=1)
async def check_prayer_time():
    tz = pytz.timezone('Asia/Riyadh')
    now = datetime.datetime.now(tz).strftime("%H:%M")
    try:
        url = "http://api.aladhan.com/v1/timingsByCity?city=Riyadh&country=Saudi+Arabia&method=4"
        res = requests.get(url, timeout=10).json()
        times = res['data']['timings']
    except: return

    prayers = {"Fajr":"الفجر", "Dhuhr":"الظهر", "Asr":"العصر", "Maghrib":"المغرب", "Isha":"العشاء"}
    for eng, arb in prayers.items():
        if now == datetime.datetime.strptime(times[eng], "%H:%M").strftime("%H:%M"):
            start_p = get_last_page()
            end_p = min(start_p + 3, 607)
            channels = load_channels()
            for g_id, c_id in channels.items():
                channel = bot.get_channel(int(c_id))
                if channel:
                    role = discord.utils.get(channel.guild.roles, name=ROLE_NAME)
                    mention = role.mention if role else f"@{ROLE_NAME}"
                    await channel.send(f"🕋 موعد أذان {arb}\n📖 الورد: {start_p}-{end_p}\n🔔 {mention}")
                    for i in range(start_p, end_p + 1):
                        p = find_image(i)
                        if p: await channel.send(file=discord.File(p))
            save_next_start_page(end_p)
            await asyncio.sleep(61)
            break

# --- 5. الأحداث والأوامر ---
@bot.event
async def on_ready():
    print(f'✅ البوت متصل الآن: {bot.user}')
    bot.add_view(QuranControlView())
    if not check_prayer_time.is_running():
        check_prayer_time.start()

@bot.command()
@commands.has_permissions(administrator=True)
async def إعدادات(ctx):
    role = discord.utils.get(ctx.guild.roles, name=ROLE_NAME)
    if not role:
        try:
            role = await ctx.guild.create_role(name=ROLE_NAME, color=discord.Color.gold(), mentionable=True)
            await ctx.send(f"✅ تم إنشاء رتبة **{ROLE_NAME}**.")
        except:
            await ctx.send("❌ فشل إنشاء الرتبة، ارفع رتبة البوت للأعلى.")
            
    embed = discord.Embed(title="⚙️ لوحة تحكم الورد القرآني", description="اختر القناة من القائمة وفعل التنبيهات.", color=0x2ecc71)
    await ctx.send(embed=embed, view=QuranControlView(ctx.guild.text_channels))

# --- تشغيل البوت ---
if __name__ == "__main__":
    keep_alive()
    token = os.environ.get('DISCORD_TOKEN')
    if token:
        try:
            bot.run(token)
        except Exception as e:
            print(f"❌ خطأ: {e}")
    else:
        print("❌ خطأ: لم يتم العثور على التوكن!")
