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

# --- 1. خادم الويب (Keep Alive) ---
app = Flask('')
@app.route('/')
def home(): return "✅ Bot is Running"

def run():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    Thread(target=run).start()

# --- 2. الإعدادات والذاكرة ---
intents = discord.Intents.default()
intents.message_content = True 
intents.members = True 
bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

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

def find_image(number):
    image_folder = "images"
    if not os.path.exists(image_folder): return None
    for filename in os.listdir(image_folder):
        nums = re.findall(r'\d+', filename)
        if any(int(n) == number for n in nums):
            return os.path.join(image_folder, filename)
    return None

# --- 3. مكونات لوحة التحكم ---

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

    @discord.ui.button(label="🧪 تجربة الإرسال", style=discord.ButtonStyle.blurple, custom_id="test_btn")
    async def test_send(self, interaction: discord.Interaction, button: Button):
        channels = load_channels()
        c_id = channels.get(str(interaction.guild.id))
        if not c_id: return await interaction.response.send_message("⚠️ اختر القناة أولاً من القائمة!", ephemeral=True)
        
        target_channel = bot.get_channel(int(c_id))
        if target_channel:
            await interaction.response.defer(ephemeral=True)
            start_p = get_last_page()
            await target_channel.send(f"🧪 **تجربة نظام الورد - صفحة {start_p}**")
            path = find_image(start_p)
            if path:
                await target_channel.send(file=discord.File(path))
            await interaction.followup.send(f"✅ تم إرسال التجربة إلى <#{c_id}>", ephemeral=True)

# --- 4. المهام التلقائية (الأذان) ---
@tasks.loop(seconds=40)
async def check_prayer_time():
    riyadh_tz = pytz.timezone('Asia/Riyadh')
    now = datetime.datetime.now(riyadh_tz).strftime("%H:%M")
    
    try:
        url = "http://api.aladhan.com/v1/timingsByCity?city=Riyadh&country=Saudi+Arabia&method=4"
        r = requests.get(url, timeout=10).json()
        times = r['data']['timings']
    except: return

    prayers = {"Fajr":"الفجر", "Dhuhr":"الظهر", "Asr":"العصر", "Maghrib":"المغرب", "Isha":"العشاء"}
    for eng, arb in prayers.items():
        p_time = datetime.datetime.strptime(times[eng], "%H:%M").strftime("%H:%M")
        if now == p_time:
            # حماية إضافية ضد التكرار: البوت ينتظر عشوائياً بين 1-5 ثواني
            # إذا أرسلت نسخة واحدة، لن ترسل الأخرى بسبب sleep الطويل في النهاية
            start_p = get_last_page()
            end_p = min(start_p + 3, 607)
            subs = get_subs()
            channels = load_channels()
            
            sent_in_any = False
            for g_id, c_id in channels.items():
                channel = bot.get_channel(int(c_id))
                if channel:
                    sent_in_any = True
                    mentions = " ".join([f"<@{s}>" for s in subs if channel.guild.get_member(int(s))])
                    await channel.send(f"🕋 **حان الآن موعد أذان {arb} بتوقيت الرياض**\n📖 الورد: {start_p} إلى {end_p}\n🔔 {mentions}")
                    for i in range(start_p, end_p + 1):
                        path = find_image(i)
                        if path: await channel.send(file=discord.File(path))
            
            if sent_in_any:
                save_next_start_page(end_p)
                await asyncio.sleep(80) # انتظار طويل لضمان عدم تكرار الدقيقة
            break

# --- 5. الأوامر والأحداث ---
@bot.event
async def on_ready():
    bot.add_view(QuranControlView()) 
    if not check_prayer_time.is_running():
        check_prayer_time.start()
    print(f'✅ Logged in as {bot.user}')

@bot.event
async def on_message(message):
    if message.author == bot.user: return
    await bot.process_commands(message)

@bot.command()
@commands.has_permissions(administrator=True)
async def إعدادات(ctx):
    embed = discord.Embed(title="⚙️ إعدادات نظام القرآن الكريم", 
                          description="المسؤول يختار القناة، والأعضاء يفعلون التنبيهات من الأزرار.", 
                          color=0x2ecc71)
    await ctx.send(embed=embed, view=QuranControlView(ctx.guild.text_channels))

@bot.command()
async def سيرفراتي(ctx):
    """يرسل القائمة في الخاص فقط"""
    guilds = bot.guilds
    msg = f"📊 **إحصائيات السيرفرات ({len(guilds)}):**\n"
    for g in guilds:
        msg += f"• {g.name} ({g.member_count} عضو)\n"
    
    try:
        await ctx.author.send(msg)
        await ctx.send("✅ تم إرسال القائمة إلى رسائلك الخاصة.", delete_after=5)
    except:
        await ctx.send("⚠️ عذراً، يجب فتح الرسائل الخاصة (DM) لاستلام القائمة.")

if __name__ == "__main__":
    keep_alive()
    bot.run(os.environ.get('DISCORD_TOKEN'))
