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
def home(): 
    return "✅ بوت ختمة يعمل ومستعد لرمضان - الرابط نشط"

def run():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- 2. إعدادات البوت ---
intents = discord.Intents.default()
intents.message_content = True 
intents.members = True 
bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

CHANNELS_FILE = "channels.json"
PAGE_FILE = "last_page.txt"
ROLE_NAME = "ختمة"

# وظائف إدارة البيانات
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

def save_page(page_num):
    with open(PAGE_FILE, "w") as f: f.write(str(page_num))

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
            return await interaction.response.send_message("❌ هذا الأمر للمسؤولين فقط!", ephemeral=True)
        save_channel(interaction.guild.id, self.values[0])
        await interaction.response.send_message(f"✅ تم ضبط القناة بنجاح للورد اليومي!", ephemeral=True)

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
            await interaction.response.send_message(f"✅ تم منحك رتبة {ROLE_NAME} لتصلك تنبيهات الورد!", ephemeral=True)
        except:
            await interaction.response.send_message("❌ فشل منح الرتبة. تأكد أن رتبة البوت في الإعدادات أعلى من رتبة ختمة.", ephemeral=True)

    @discord.ui.button(label="🧪 تجربة الإرسال", style=discord.ButtonStyle.blurple, custom_id="test_btn")
    async def test(self, interaction: discord.Interaction, button: Button):
        channels = load_channels()
        c_id = channels.get(str(interaction.guild.id))
        if not c_id: return await interaction.response.send_message("⚠️ حدد القناة أولاً من القائمة!", ephemeral=True)
        
        await interaction.response.defer(ephemeral=True)
        chan = bot.get_channel(int(c_id))
        if chan:
            role = discord.utils.get(interaction.guild.roles, name=ROLE_NAME)
            mention = role.mention if role else f"@{ROLE_NAME}"
            page = get_last_page()
            path = find_image(page)
            
            await chan.send(f"🔔 {mention}\n📖 **تجربة إرسال الورد**\n📄 رقم الصفحة الحالية في النظام: **{page}**")
            if path: 
                await chan.send(file=discord.File(path))
            await interaction.followup.send("✅ تمت التجربة وظهر المنشن برقم الصفحة!", ephemeral=True)

# --- 4. نظام الأذان التلقائي ---
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
        # التأكد من مطابقة الوقت
        p_time = datetime.datetime.strptime(times[eng], "%H:%M").strftime("%H:%M")
        if now == p_time:
            start_p = get_last_page()
            end_p = min(start_p + 3, 607)
            channels = load_channels()
            
            for g_id, c_id in channels.items():
                channel = bot.get_channel(int(c_id))
                if channel:
                    role = discord.utils.get(channel.guild.roles, name=ROLE_NAME)
                    mention = role.mention if role else f"@{ROLE_NAME}"
                    await channel.send(f"🕋 **حان الآن موعد أذان {arb} بتوقيت الرياض**\n🔔 {mention}\n📖 وردكم الآن من صفحة **{start_p}** إلى **{end_p}**")
                    for i in range(start_p, end_p + 1):
                        p = find_image(i)
                        if p: await channel.send(file=discord.File(p))
            
            next_start = end_p + 1
            if next_start > 607: next_start = 4
            save_page(next_start)
            await asyncio.sleep(65) # منع التكرار في نفس الدقيقة
            break

# --- 5. الأوامر ---
@bot.event
async def on_ready():
    print(f'✅ البوت أونلاين باسم: {bot.user}')
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
        except: pass
            
    embed = discord.Embed(title="⚙️ لوحة تحكم بوت ختمة", color=0x2ecc71)
    embed.description = "1. اختر القناة المخصصة للورد من القائمة.\n2. اطلب من الأعضاء ضغط زر التنبيهات.\n3. سيتم الإرسال تلقائياً مع الأذان."
    await ctx.send(embed=embed, view=QuranControlView(ctx.guild.text_channels))

@bot.command()
@commands.has_permissions(administrator=True)
async def تصفير(ctx):
    save_page(4)
    await ctx.send("🔄 **تمت إعادة ضبط الورد!**\nسيبدأ البوت من **الصفحة الأولى (سورة البقرة)** عند الموعد القادم.")

@bot.command()
async def سيرفراتي(ctx):
    # متاح فقط لصاحب البوت أو المسؤولين لمتابعة الانتشار
    if ctx.author.guild_permissions.administrator:
        guilds = bot.guilds
        msg = f"📊 البوت موجود حالياً في **{len(guilds)}** سيرفر.\n"
        await ctx.send(msg)

@bot.command()
async def فحص(ctx):
    await ctx.send(f"✅ البوت متصل واستجابة الشبكة ممتازة. الصفحة القادمة: {get_last_page()}")

# --- 6. التشغيل النهائي ---
if __name__ == "__main__":
    keep_alive()
    token = os.environ.get('DISCORD_TOKEN')
    if token:
        bot.run(token)
    else:
        print("❌ خطأ: لم يتم العثور على DISCORD_TOKEN في المتغيرات البيئية!")
