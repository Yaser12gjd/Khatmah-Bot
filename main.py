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

# --- 1. خادم الويب ---
app = Flask('')
@app.route('/')
def home(): return "✅ البوت يعمل بنظام الرتب (Role System)"

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

# --- 3. مكونات لوحة التحكم ---

class ChannelSelect(Select):
    def __init__(self, channels):
        options = [discord.SelectOption(label=c.name, value=str(c.id)) for c in channels[:25]]
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

    @discord.ui.button(label="🔔 تفعيل التنبيهات", style=discord.ButtonStyle.green, custom_id="sub_btn_role")
    async def subscribe(self, interaction: discord.Interaction, button: Button):
        role = discord.utils.get(interaction.guild.roles, name=ROLE_NAME)
        if not role:
            return await interaction.response.send_message("⚠️ رتبة 'ختمة' غير موجودة، اطلب من المسؤول كتابة !إعدادات مرة أخرى.", ephemeral=True)
        
        await interaction.user.add_roles(role)
        await interaction.response.send_message(f"✅ تم إعطاؤك رتبة **{ROLE_NAME}** وتفعيل التنبيهات!", ephemeral=True)

    @discord.ui.button(label="🔕 إلغاء التنبيه", style=discord.ButtonStyle.gray, custom_id="unsub_btn_role")
    async def unsubscribe(self, interaction: discord.Interaction, button: Button):
        role = discord.utils.get(interaction.guild.roles, name=ROLE_NAME)
        if role in interaction.user.roles:
            await interaction.user.remove_roles(role)
            await interaction.response.send_message("🔕 تم سحب الرتبة وإلغاء التنبيهات.", ephemeral=True)
        else:
            await interaction.response.send_message("⚠️ أنت لا تملك الرتبة أصلاً.", ephemeral=True)

# --- 4. المهمة التلقائية ---
@tasks.loop(seconds=45)
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
        if now == datetime.datetime.strptime(times[eng], "%H:%M").strftime("%H:%M"):
            start_p = get_last_page()
            end_p = min(start_p + 3, 607)
            channels = load_channels()
            
            worked = False
            for g_id, c_id in channels.items():
                channel = bot.get_channel(int(c_id))
                if channel:
                    worked = True
                    role = discord.utils.get(channel.guild.roles, name=ROLE_NAME)
                    mention = role.mention if role else "@ختمة"
                    
                    await channel.send(f"🕋 **حان الآن موعد أذان {arb} بتوقيت الرياض**\n📖 الورد: {start_p} إلى {end_p}\n🔔 {mention}")
                    for i in range(start_p, end_p + 1):
                        path = find_image(i)
                        if path: await channel.send(file=discord.File(path))
            
            if worked:
                save_next_start_page(end_p)
                await asyncio.sleep(90)
            break

# --- 5. الأوامر ---
@bot.event
async def on_ready():
    bot.add_view(QuranControlView()) 
    if not check_prayer_time.is_running(): check_prayer_time.start()
    print(f'✅ Bot Online: {bot.user}')

@bot.command()
@commands.has_permissions(administrator=True)
async def إعدادات(ctx):
    # إنشاء الرتبة إذا لم تكن موجودة
    role = discord.utils.get(ctx.guild.roles, name=ROLE_NAME)
    if not role:
        try:
            role = await ctx.guild.create_role(name=ROLE_NAME, color=discord.Color.green(), mentionable=True)
            await ctx.send(f"✅ تم إنشاء رتبة **{ROLE_NAME}** تلقائياً.")
        except:
            await ctx.send("❌ فشل إنشاء الرتبة، تأكد من صلاحيات البوت (Manage Roles).")

    embed = discord.Embed(title="⚙️ لوحة تحكم الورد القرآني", 
                          description=f"المسؤول يختار القناة، والأعضاء يضغطون الزر للحصول على رتبة **{ROLE_NAME}**.", 
                          color=0x2ecc71)
    await ctx.send(embed=embed, view=QuranControlView(ctx.guild.text_channels))

@bot.command()
async def سيرفراتي(ctx):
    try: await ctx.message.delete()
    except: pass
    msg = f"📊 إحصائيات السيرفرات: {len(bot.guilds)}\n"
    for g in bot.guilds: msg += f"• {g.name} ({g.member_count})\n"
    try: await ctx.author.send(msg)
    except: await ctx.send("⚠️ الخاص مغلق.", delete_after=5)

if __name__ == "__main__":
    keep_alive()
    bot.run(os.environ.get('DISCORD_TOKEN'))
