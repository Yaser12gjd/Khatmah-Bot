import discord
from discord.ext import commands, tasks
import os
import re
import requests
from datetime import datetime
from flask import Flask
from threading import Thread

# --- 1. نظام الحفاظ على البوت ---
app = Flask('')
@app.route('/')
def home(): return "✅ البوت يعمل - نظام الورد الثابت"

def run():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    Thread(target=run).start()

# --- 2. الإعدادات والذاكرة ---
intents = discord.Intents.default()
intents.message_content = True 
bot = commands.Bot(command_prefix='!', intents=intents)

DB_FILE = "subscribers.txt"
PAGE_FILE = "last_page.txt" 
CITY = "Riyadh"
COUNTRY = "Saudi Arabia"
METHOD = 4 

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

# --- 3. جلب المواقيت والبحث عن الصور ---
def get_prayer_times():
    try:
        url = f"http://api.aladhan.com/v1/timingsByCity?city={CITY}&country={COUNTRY}&method={METHOD}"
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

# --- 4. فحص وقت الصلاة وإرسال الصفحات ثابتة ---
@tasks.loop(seconds=40)
async def check_prayer_time():
    now = datetime.now().strftime("%H:%M")
    times = get_prayer_times()
    
    if times:
        prayers = {"Fajr":"الفجر", "Dhuhr":"الظهر", "Asr":"العصر", "Maghrib":"المغرب", "Isha":"العشاء"}
        for eng, arb in prayers.items():
            if now == times[eng]:
                start_p = get_last_page()
                subs = get_subs()
                mentions = " ".join([f"<@{s}>" for s in subs])
                
                for guild in bot.guilds:
                    channel = discord.utils.get(guild.text_channels, name="القرآن") or guild.text_channels[0]
                    if channel:
                        end_p = min(start_p + 3, 607)
                        await channel.send(f"🕋 **حان الآن موعد أذان {arb} بتوقيت الرياض**\n📖 وردكم الثابت: من صفحة {start_p} إلى {end_p}\n🔔 {mentions}")
                        
                        # إرسال الـ 4 صفحات كملفات تحت بعضها
                        for i in range(start_p, end_p + 1):
                            path = find_image(i)
                            if path:
                                await channel.send(file=discord.File(path))
                
                save_next_start_page(min(start_p + 3, 607))
                import asyncio
                await asyncio.sleep(65) 
                break

# --- 5. الأوامر ---
@bot.event
async def on_ready():
    print(f'✅ البوت يعمل بنظام الصور الثابتة (4 صفحات)')
    if not check_prayer_time.is_running():
        check_prayer_time.start()

@bot.command()
async def تفعيل(ctx):
    add_sub(ctx.author.id)
    await ctx.send(f"✅ تم التفعيل! ستصلك الـ 4 صفحات مباشرة مع كل أذان.")

@bot.command()
async def تجربة(ctx):
    start_p = get_last_page()
    end_p = min(start_p + 3, 607)
    await ctx.send(f"🧪 **تجربة إرسال الورد الثابت (من {start_p} إلى {end_p})**")
    for i in range(start_p, end_p + 1):
        path = find_image(i)
        if path:
            await ctx.send(file=discord.File(path))

@bot.command()
async def مواقيت(ctx):
    times = get_prayer_times()
    if times:
        msg = f"🕌 **مواقيت الصلاة بالرياض:**\n🔹 الفجر: {times['Fajr']}\n🔹 الظهر: {times['Dhuhr']}\n🔹 العصر: {times['Asr']}\n🔹 المغرب: {times['Maghrib']}\n🔹 العشاء: {times['Isha']}"
        await ctx.send(msg)

if __name__ == "__main__":
    keep_alive()
    bot.run(os.environ.get('DISCORD_TOKEN'))
