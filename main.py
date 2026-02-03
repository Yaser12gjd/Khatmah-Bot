import discord
from discord.ext import commands, tasks
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
def home(): return "✅ البوت يعمل بنظام تعدد السيرفرات المتطور"

def run():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    Thread(target=run).start()

# --- 2. الإعدادات والذاكرة ---
intents = discord.Intents.default()
intents.message_content = True 
intents.members = True # مهم لجلب قائمة الأعضاء للمنشن
bot = commands.Bot(command_prefix='!', intents=intents)

DB_FILE = "subscribers.txt"
PAGE_FILE = "last_page.txt"
CHANNELS_FILE = "channels.json"

# دالة لجلب القنوات المحفوظة لكل سيرفر
def load_channels():
    if not os.path.exists(CHANNELS_FILE): return {}
    try:
        with open(CHANNELS_FILE, "r") as f:
            return json.load(f)
    except: return {}

def save_channel(guild_id, channel_id):
    channels = load_channels()
    channels[str(guild_id)] = channel_id
    with open(CHANNELS_FILE, "w") as f:
        json.dump(channels, f)

def get_subs():
    if not os.path.exists(DB_FILE): return set()
    with open(DB_FILE, "r") as f:
        return set(line.strip() for line in f if line.strip())

def add_sub(user_id):
    subs = get_subs()
    subs.add(str(user_id))
    with open(DB_FILE, "w") as f:
        for s in subs: f.write(f"{s}\n")

def get_last_page():
    if not os.path.exists(PAGE_FILE): return 4
    with open(PAGE_FILE, "r") as f:
        try: return int(f.read().strip())
        except: return 4

def save_next_start_page(last_sent):
    next_p = last_sent + 1
    if next_p > 607: next_p = 4
    with open(PAGE_FILE, "w") as f:
        f.write(str(next_p))
    return next_p

# --- 3. جلب مواقيت الصلاة بتوقيت الرياض ---
def get_prayer_times():
    try:
        url = "http://api.aladhan.com/v1/timingsByCity?city=Riyadh&country=Saudi+Arabia&method=4"
        response = requests.get(url).json()
        return response['data']['timings']
    except: return None

def find_image(number):
    image_folder = "images"
    if not os.path.exists(image_folder): return None
    for filename in os.listdir(image_folder):
        nums = re.findall(r'\d+', filename)
        if any(int(n) == number for n in nums):
            return os.path.join(image_folder, filename)
    return None

# --- 4. المهمة التلقائية (الأذان لجميع السيرفرات) ---
@tasks.loop(seconds=35)
async def check_prayer_time():
    riyadh_tz = pytz.timezone('Asia/Riyadh')
    now = datetime.datetime.now(riyadh_tz).strftime("%H:%M")
    times = get_prayer_times()
    
    if times:
        prayers = {"Fajr":"الفجر", "Dhuhr":"الظهر", "Asr":"العصر", "Maghrib":"المغرب", "Isha":"العشاء"}
        for eng, arb in prayers.items():
            p_time = datetime.datetime.strptime(times[eng], "%H:%M").strftime("%H:%M")
            
            if now == p_time:
                start_p = get_last_page()
                end_p = min(start_p + 3, 607)
                subs = get_subs()
                channels = load_channels() # جلب قائمة القنوات لكل السيرفرات
                
                # إرسال لكل سيرفر قام بضبط القناة
                for guild_id_str, channel_id in channels.items():
                    channel = bot.get_channel(int(channel_id))
                    if channel:
                        # منشن المشتركين الموجودين في هذا السيرفر فقط
                        mentions = " ".join([f"<@{s}>" for s in subs if channel.guild.get_member(int(s))])
                        
                        await channel.send(f"🕋 **حان الآن موعد أذان {arb} بتوقيت الرياض**\n📖 وردنا الجماعي: صفحات {start_p} إلى {end_p}\n🔔 {mentions}")
                        
                        for i in range(start_p, end_p + 1):
                            path = find_image(i)
                            if path: await channel.send(file=discord.File(path))
                
                save_next_start_page(end_p)
                await asyncio.sleep(65)
                break

# --- 5. الأوامر ---
@bot.event
async def on_ready():
    print(f'✅ البوت متصل في {len(bot.guilds)} سيرفرات')
    if not check_prayer_time.is_running():
        check_prayer_time.start()

@bot.command()
@commands.has_permissions(administrator=True)
async def ضبط(ctx):
    """تحديد القناة الحالية لإرسال الورد والأذان"""
    save_channel(ctx.guild.id, ctx.channel.id)
    await ctx.send(f"✅ تم ضبط قناة **{ctx.channel.name}** بنجاح لتكون قناة القرآن والأذان في هذا السيرفر.")

@bot.command()
async def تفعيل(ctx):
    """تفعيل المنشن للمستخدم"""
    add_sub(ctx.author.id)
    await ctx.send(f"✅ {ctx.author.mention} تم تفعيل التنبيهات لك!")

@bot.command()
async def تجربة(ctx):
    """تجربة الإرسال يدوياً"""
    start_p = get_last_page()
    end_p = min(start_p + 3, 607)
    await ctx.send(f"🧪 تجربة الورد لصفحات: {start_p}-{end_p}")
    for i in range(start_p, end_p + 1):
        path = find_image(i)
        if path: await ctx.send(file=discord.File(path))

if __name__ == "__main__":
    keep_alive()
    bot.run(os.environ.get('DISCORD_TOKEN'))
