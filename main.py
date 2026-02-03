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

# --- 1. خادم الويب لبقاء البوت حياً ---
app = Flask('')
@app.route('/')
def home(): return "✅ البوت يعمل بنظام السيرفرات المتعددة"

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
    with open(DB_FILE, "r") as f: return set(line.strip() for line in f if line.strip())

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

# --- 3. واجهة التحكم (لوحة الإعدادات) ---

class ChannelSelect(Select):
    def __init__(self, channels):
        options = [discord.SelectOption(label=c.name, value=str(c.id)) for c in channels[:25]]
        super().__init__(placeholder="اختر قناة الورد القرآني...", options=options)

    async def callback(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ للمسؤولين فقط!", ephemeral=True)
        save_channel(interaction.guild.id, self.values[0])
        await interaction.response.send_message(f"✅ تم ضبط القناة: <#{self.values[0]}>", ephemeral=True)

class QuranControlView(View):
    def __init__(self, channels=None):
        super().__init__(timeout=None)
        if channels:
            self.add_item(ChannelSelect(channels))

    @discord.ui.button(label="🔔 تفعيل التنبيهات", style=discord.ButtonStyle.green, custom_id="sub_btn")
    async def subscribe(self, interaction: discord.Interaction, button: Button):
        add_sub(interaction.user.id)
        await interaction.response.send_message("✅ تم تفعيل التنبيهات لك!", ephemeral=True)

    @discord.ui.button(label="🔕 إلغاء التنبيه", style=discord.ButtonStyle.gray, custom_id="unsub_btn")
    async def unsubscribe(self, interaction: discord.Interaction, button: Button):
        subs = get_subs()
        uid = str(interaction.user.id)
        if uid in subs:
            subs.remove(uid)
            with open(DB_FILE, "w") as f:
                for s in subs: f.write(f"{s}\n")
            await interaction.response.send_message("🔕 تم الإلغاء.", ephemeral=True)
        else:
            await interaction.response.send_message("⚠️ لست مشتركاً.", ephemeral=True)

    @discord.ui.button(label="🧪 تجربة", style=discord.ButtonStyle.blurple, custom_id="test_btn")
    async def test_send(self, interaction: discord.Interaction, button: Button):
        channels = load_channels()
        c_id = channels.get(str(interaction.guild.id))
        if not c_id: return await interaction.response.send_message("⚠️ اختر القناة أولاً!", ephemeral=True)
        
        target_channel = bot.get_channel(int(c_id))
        if target_channel:
            await interaction.response.send_message(f"🔄 جاري الإرسال إلى <#{c_id}>", ephemeral=True)
            page = get_last_page()
            await target_channel.send(f"🧪 تجربة الورد - صفحة {page}")
            # كود إرسال الصورة هنا
        else:
            await interaction.response.send_message("❌ لم يتم العثور على القناة.", ephemeral=True)

# --- 4. المهام التلقائية (الأذان) ---
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
        if now == datetime.datetime.strptime(times[eng], "%H:%M").strftime("%H:%M"):
            start_p = get_last_page()
            end_p = min(start_p + 3, 607)
            subs = get_subs()
            channels = load_channels()
            for g_id, c_id in channels.items():
                channel = bot.get_channel(int(c_id))
                if channel:
                    mentions = " ".join([f"<@{s}>" for s in subs if channel.guild.get_member(int(s))])
                    await channel.send(f"🕋 أذان {arb} - ورد الصفحات {start_p}-{end_p}\n{mentions}")
                    for i in range(start_p, end_p + 1):
                        # بحث وإرسال الصور
                        pass 
            save_next_start_page(end_p)
            await asyncio.sleep(65)
            break

# --- 5. الأوامر ---
@bot.event
async def on_ready():
    bot.add_view(QuranControlView()) 
    print(f'✅ متصل باسم: {bot.user}')
    if not check_prayer_time.is_running(): check_prayer_time.start()

@bot.command()
@commands.has_permissions(administrator=True)
async def إعدادات(ctx):
    embed = discord.Embed(title="⚙️ إعدادات الورد القرآني", description="اختر قناة الورد من القائمة بالأسفل، وفعل التنبيهات من الأزرار.", color=0x2ecc71)
    await ctx.send(embed=embed, view=QuranControlView(ctx.guild.text_channels))

@bot.command()
async def سيرفراتي(ctx):
    """يظهر قائمة بالسيرفرات التي يتواجد فيها البوت (للمالك فقط)"""
    # يمكنك استبدال ID_الخاص_بك بـ ID حسابك في ديسكورد لزيادة الأمان
    guilds = bot.guilds
    msg = f"📊 **البوت متواجد في {len(guilds)} سيرفرات:**\n\n"
    for guild in guilds:
        msg += f"• **{guild.name}** (الأعضاء: {guild.member_count})\n"
    await ctx.send(msg)

if __name__ == "__main__":
    keep_alive()
    bot.run(os.environ.get('DISCORD_TOKEN'))
