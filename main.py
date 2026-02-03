import discord
from discord.ext import commands, tasks
import os
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
def home(): return "✅ البوت يعمل بنظام الورد الجماعي الثابت وتوقيت الرياض مضبوط"

def run():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    Thread(target=run).start()

# --- 2. الإعدادات والذاكرة والقناة المستهدفة ---
intents = discord.Intents.default()
intents.message_content = True 
bot = commands.Bot(command_prefix='!', intents=intents)

# 💡 ضع هنا رقم (ID) الروم الذي تريد أن يرسل فيه البوت
TARGET_CHANNEL_ID = 123456789012345678  # استبدل هذا الرقم بـ ID قناتك

DB_FILE = "subscribers.txt"
PAGE_FILE = "last_page.txt" 
CITY = "Riyadh"
COUNTRY = "Saudi Arabia"
METHOD = 4 # تقويم أم القرى

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
    except Exception as e:
        print(f"خطأ في جلب المواقيت: {e}")
        return None

def find_image(number):
    image_folder = "images"
    if not os.path.exists(image_folder): return None
    for filename in os.listdir(image_folder):
        nums = re.findall(r'\d+', filename)
        if any(int(n) == number for n in nums):
            return os.path.join(image_folder, filename)
    return None

# --- 4. فحص وقت الصلاة بالمنطقة الزمنية الصحيحة ---
@tasks.loop(seconds=30)
async def check_prayer_time():
    # ضبط المنطقة الزمنية على الرياض
    riyadh_tz = pytz.timezone('Asia/Riyadh')
    now = datetime.datetime.now(riyadh_tz).strftime("%H:%M")
    
    times = get_prayer_times()
    
    if times:
        prayers = {"Fajr":"الفجر", "Dhuhr":"الظهر", "Asr":"العصر", "Maghrib":"المغرب", "Isha":"العشاء"}
        for eng, arb in prayers.items():
            # توحيد صيغة الوقت لضمان التطابق
            p_time = datetime.datetime.strptime(times[eng], "%H:%M").strftime("%H:%M")
            
            if now == p_time:
                start_p = get_last_page()
                subs = get_subs()
                mentions = " ".join([f"<@{s}>" for s in subs])
                
                channel = bot.get_channel(TARGET_CHANNEL_ID)
                if channel:
                    end_p = min(start_p + 3, 607)
                    await channel.send(f"🕋 **حان الآن موعد أذان {arb} بتوقيت الرياض**\n📖 وردنا الجماعي: من صفحة {start_p} إلى {end_p}\n🔔 {mentions}")
                    
                    for i in range(start_p, end_p + 1):
                        path = find_image(i)
                        if path:
                            await channel.send(file=discord.File(path))
                    
                    # حفظ الصفحة التالية للأذان القادم
                    save_next_start_page(end_p)
                    # الانتظار دقيقة كاملة لمنع تكرار الإرسال في نفس الدقيقة
                    await asyncio.sleep(65)
                break

# --- 5. الأوامر ---
@bot.event
async def on_ready():
    print(f'✅ البوت يعمل بتوقيت الرياض المعتمد')
    if not check_prayer_time.is_running():
        check_prayer_time.start()

@bot.command()
async def تفعيل(ctx):
    add_sub(ctx.author.id)
    await ctx.send(f"✅ تم تفعيل التنبيهات لـ {ctx.author.mention}! ستصلك الصفحات الثابتة مع كل أذان.")

@bot.command()
async def تجربة(ctx):
    """أمر للتأكد من الصور والمنشن"""
    start_p = get_last_page()
    end_p = min(start_p + 3, 607)
    await ctx.send(f"🧪 **تجربة إرسال الورد (من صفحة {start_p} إلى {end_p})**")
    for i in range(start_p, end_p + 1):
        path = find_image(i)
        if path:
            await ctx.send(file=discord.File(path))

@bot.command()
async def مواقيت(ctx):
    times = get_prayer_times()
    if times:
        msg = f"🕌 **مواقيت الصلاة في الرياض (أم القرى):**\n🔹 الفجر: {times['Fajr']}\n🔹 الظهر: {times['Dhuhr']}\n🔹 العصر: {times['Asr']}\n🔹 المغرب: {times['Maghrib']}\n🔹 العشاء: {times['Isha']}"
        await ctx.send(msg)

if __name__ == "__main__":
    keep_alive()
    bot.run(os.environ.get('DISCORD_TOKEN'))
