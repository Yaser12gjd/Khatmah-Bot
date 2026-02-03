import discord
from discord.ext import commands, tasks
from discord.ui import Button, View
import os
import re
import requests
from datetime import datetime
from flask import Flask
from threading import Thread

# --- 1. خادم الويب (Keep Alive) ---
app = Flask('')
@app.route('/')
def home(): return "✅ البوت يعمل - نظام 4 صفحات مع كل أذان"

def run():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    Thread(target=run).start()

# --- 2. إعدادات البوت وملفات الذاكرة ---
intents = discord.Intents.default()
intents.message_content = True 
bot = commands.Bot(command_prefix='!', intents=intents)

DB_FILE = "subscribers.txt"
PAGE_FILE = "last_page.txt" 
CITY = "Riyadh"
COUNTRY = "Saudi Arabia"
METHOD = 4 # أم القرى

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

# --- 4. كلاس الأزرار المتطور ---
class QuranView(View):
    def __init__(self, current_page, start_page):
        super().__init__(timeout=None)
        self.current_page = current_page
        self.start_page = start_page
        self.end_page = min(start_page + 3, 607) # نظام الـ 4 صفحات

    async def update_msg(self, interaction):
        path = find_image(self.current_page)
        if path:
            subs = get_subs()
            mentions = " ".join([f"<@{s}>" for s in subs])
            content = f"📖 ورد الأذان الحالي (من {self.start_page} إلى {self.end_page})\n✅ أنت الآن في صفحة: **{self.current_page}**\n🔔 {mentions}"
            await interaction.response.edit_message(
                content=content,
                attachments=[discord.File(path)], view=self
            )

    @discord.ui.button(label="⬅️ السابق", style=discord.ButtonStyle.grey)
    async def prev(self, interaction, button):
        if self.current_page > self.start_page:
            self.current_page -= 1
            await self.update_msg(interaction)
        else:
            await interaction.response.send_message("⚠️ هذه بداية الورد لهذا الأذان.", ephemeral=True)

    @discord.ui.button(label="التالي ➡️", style=discord.ButtonStyle.primary)
    async def next(self, interaction, button):
        if self.current_page < self.end_page:
            self.current_page += 1
            await self.update_msg(interaction)
        else:
            await interaction.response.send_message("⚠️ انتهى ورد هذا الأذان (4 صفحات). تقبل الله.", ephemeral=True)

# --- 5. فحص وقت الصلاة وإرسال الـ 4 صفحات ---
@tasks.loop(seconds=40)
async def check_prayer_time():
    now = datetime.now().strftime("%H:%M")
    times = get_prayer_times()
    
    if times:
        prayers = {"Fajr":"الفجر", "Dhuhr":"الظهر", "Asr":"العصر", "Maghrib":"المغرب", "Isha":"العشاء"}
        for eng, arb in prayers.items():
            if now == times[eng]:
                start_p = get_last_page()
                image_path = find_image(start_p)
                
                subs = get_subs()
                mentions = " ".join([f"<@{s}>" for s in subs])
                
                for guild in bot.guilds:
                    channel = discord.utils.get(guild.text_channels, name="القرآن") or guild.text_channels[0]
                    if channel and image_path:
                        end_p = min(start_p + 3, 607)
                        content = f"🕋 **حان الآن موعد أذان {arb} بتوقيت الرياض**\n📖 وردكم الآن: **4 صفحات** (من {start_p} إلى {end_p})\n🔔 {mentions}"
                        await channel.send(content=content, file=discord.File(image_path), view=QuranView(start_p, start_p))
                
                # حفظ الصفحة التي سيبدأ منها الأذان القادم (بعد 4 صفحات)
                save_next_start_page(min(start_p + 3, 607))
                
                import asyncio
                await asyncio.sleep(65) 
                break

# --- 6. الأوامر ---
@bot.event
async def on_ready():
    print(f'✅ نظام الـ 4 صفحات جاهز للعمل')
    if not check_prayer_time.is_running():
        check_prayer_time.start()

@bot.command()
async def تفعيل(ctx):
    add_sub(ctx.author.id)
    await ctx.send(f"✅ تم التفعيل! سيصلك منشن مع **4 صفحات** من القرآن عند كل أذان.")

@bot.command()
async def ترتيب(ctx, number: int):
    if 4 <= number <= 607:
        path = find_image(number)
        if path:
            subs = get_subs()
            mentions = " ".join([f"<@{s}>" for s in subs])
            await ctx.send(content=f"📖 صفحة: **{number}**\n🔔 {mentions}", file=discord.File(path), view=QuranView(number, number))

@bot.command()
async def مواقيت(ctx):
    times = get_prayer_times()
    if times:
        msg = f"🕌 **مواقيت الصلاة بالرياض:**\n🔹 الفجر: {times['Fajr']}\n🔹 الظهر: {times['Dhuhr']}\n🔹 العصر: {times['Asr']}\n🔹 المغرب: {times['Maghrib']}\n🔹 العشاء: {times['Isha']}"
        await ctx.send(msg)

if __name__ == "__main__":
    keep_alive()
    bot.run(os.environ.get('DISCORD_TOKEN'))
