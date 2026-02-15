import discord
from discord.ext import commands, tasks
from discord.ui import Button, View, Select
import os, json, re, requests, datetime, pytz, asyncio
from flask import Flask
from threading import Thread

# --- 1. خادم الويب (Keep Alive) ---
app = Flask('')
@app.route('/')
def home(): 
    return "✅ بوت ختمة الاحترافي (Starter) يعمل بنشاط 24/7"

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
last_sent_minute = "" 

# إدارة البيانات
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
    if not os.path.exists(PAGE_FILE): return 1 
    try:
        with open(PAGE_FILE, "r") as f:
            content = f.read().strip()
            return int(content) if content else 1
    except: return 1

def save_page(page_num):
    with open(PAGE_FILE, "w") as f: f.write(str(page_num))

# دالة البحث مع معادلة التصحيح (+3)
def find_image(quran_page):
    image_folder = "images"
    if not os.path.exists(image_folder): return None
    
    file_number = quran_page + 3
    
    for filename in os.listdir(image_folder):
        nums = re.findall(r'\d+', filename)
        if nums and int(nums[0]) == file_number:
            return os.path.join(image_folder, filename)
    return None

# --- 3. واجهة التحكم (View) ---
class QuranControlView(View):
    def __init__(self, channels=None):
        super().__init__(timeout=None)
        if channels:
            options = [discord.SelectOption(label=c.name[:25], value=str(c.id)) for c in channels[:25]]
            self.add_item(ChannelSelect(options))

    @discord.ui.button(label="🔔 تفعيل التنبيهات", style=discord.ButtonStyle.green, custom_id="sub_btn_final")
    async def subscribe(self, interaction: discord.Interaction, button: Button):
        role = discord.utils.get(interaction.guild.roles, name=ROLE_NAME)
        if not role:
            return await interaction.response.send_message(f"⚠️ رتبة '{ROLE_NAME}' غير موجودة.", ephemeral=True)
        try:
            await interaction.user.add_roles(role)
            await interaction.response.send_message(f"✅ تم تفعيل تنبيهاتك!", ephemeral=True)
        except:
            await interaction.response.send_message("❌ ارفع رتبة البوت فوق رتبة ختمة.", ephemeral=True)

    @discord.ui.button(label="🧪 تجربة الإرسال", style=discord.ButtonStyle.blurple, custom_id="test_btn_final")
    async def test(self, interaction: discord.Interaction, button: Button):
        # --- تحديث: منع الأعضاء العاديين من التجربة ---
        if not (interaction.user.guild_permissions.manage_channels or interaction.user.guild_permissions.administrator):
            return await interaction.response.send_message("⚠️ عذراً، تجربة الإرسال متاحة للمودات والمسؤولين فقط.", ephemeral=True)

        channels = load_channels()
        c_id = channels.get(str(interaction.guild.id))
        if not c_id: return await interaction.response.send_message("⚠️ اختر القناة أولاً!", ephemeral=True)
        
        await interaction.response.defer(ephemeral=True)
        chan = bot.get_channel(int(c_id))
        if chan:
            role = discord.utils.get(interaction.guild.roles, name=ROLE_NAME)
            mention = role.mention if role else f"@{ROLE_NAME}"
            page = get_last_page()
            path = find_image(page)
            await chan.send(f"🔔 {mention}\n📖 **تجربة الورد** - صفحة: {page}")
            if path: await chan.send(file=discord.File(path))
            await interaction.followup.send("✅ تمت التجربة!", ephemeral=True)

class ChannelSelect(Select):
    def __init__(self, options):
        super().__init__(placeholder="اختر قناة الورد...", options=options, custom_id="select_chan_final")

    async def callback(self, interaction: discord.Interaction):
        # --- تحديث: منع الأعضاء العاديين من تغيير القناة ---
        if not (interaction.user.guild_permissions.manage_channels or interaction.user.guild_permissions.administrator):
            return await interaction.response.send_message("⚠️ عذراً، تغيير القناة متاح للمودات والمسؤولين فقط.", ephemeral=True)
        
        save_channel(interaction.guild.id, self.values[0])
        await interaction.response.send_message(f"✅ تم ضبط القناة!", ephemeral=True)

# --- 4. نظام الأذان التلقائي ---
@tasks.loop(seconds=30)
async def check_prayer_time():
    global last_sent_minute
    tz = pytz.timezone('Asia/Riyadh')
    now_str = datetime.datetime.now(tz).strftime("%H:%M")
    
    if now_str == last_sent_minute: return

    try:
        url = "http://api.aladhan.com/v1/timingsByCity?city=Riyadh&country=Saudi+Arabia&method=4"
        res = requests.get(url, timeout=10).json()
        times = res['data']['timings']
    except: return

    prayers = {"Fajr":"الفجر", "Dhuhr":"الظهر", "Asr":"العصر", "Maghrib":"المغرب", "Isha":"العشاء"}
    for eng, arb in prayers.items():
        p_time = datetime.datetime.strptime(times[eng], "%H:%M").strftime("%H:%M")
        if now_str == p_time:
            last_sent_minute = now_str
            start_p = get_last_page()
            end_p = min(start_p + 3, 604)
            channels = load_channels()
            
            for g_id, c_id in channels.items():
                channel = bot.get_channel(int(c_id))
                if channel:
                    role = discord.utils.get(channel.guild.roles, name=ROLE_NAME)
                    mention = role.mention if role else f"@{ROLE_NAME}"
                    await channel.send(f"🕋 **حان الآن موعد أذان {arb} بتوقيت الرياض**\n🔔 {mention}\n📖 وردكم من صفحة **{start_p}** إلى **{end_p}**")
                    for i in range(start_p, end_p + 1):
                        img_path = find_image(i)
                        if img_path: await channel.send(file=discord.File(img_path))
            
            save_page(end_p + 1 if end_p < 604 else 1)
            await bot.change_presence(activity=discord.Game(name=f"الورد القادم: ص {end_p + 1}"))
            break

# --- 5. الأحداث والأوامر ---
@bot.event
async def on_ready():
    print(f'✅ البوت يعمل بخطة Starter: {bot.user}')
    bot.add_view(QuranControlView())
    if not check_prayer_time.is_running():
        check_prayer_time.start()
    await bot.change_presence(activity=discord.Game(name=f"الورد القادم: ص {get_last_page()}"))

@bot.command()
@commands.has_permissions(manage_channels=True)
async def إعدادات(ctx):
    role = discord.utils.get(ctx.guild.roles, name=ROLE_NAME)
    if not role:
        try: await ctx.guild.create_role(name=ROLE_NAME, color=discord.Color.gold(), mentionable=True)
        except: pass
    embed = discord.Embed(title="⚙️ لوحة تحكم بوت ختمة", color=0x2ecc71)
    await ctx.send(embed=embed, view=QuranControlView(ctx.guild.text_channels))

@bot.command()
@commands.has_permissions(administrator=True)
async def تعديل(ctx, num: int):
    save_page(num)
    await bot.change_presence(activity=discord.Game(name=f"الورد القادم: ص {num}"))
    await ctx.send(f"✅ تم التعديل. الورد القادم سيبدأ من صفحة **{num}**\n(ملاحظة: البوت سيسحب آلياً ملف رقم {num+3} ليتطابق مع المحتوى).")

@bot.command()
async def سيرفراتي(ctx):
    try: await ctx.message.delete()
    except: pass
    if not ctx.author.guild_permissions.administrator: return
    guilds = bot.guilds
    msg = f"📊 **قائمة السيرفرات ({len(guilds)}):**\n\n"
    for g in guilds:
        msg += f"🔹 **{g.name}** | الأعضاء: `{g.member_count}`\n"
    try: await ctx.author.send(msg)
    except: await ctx.send("❌ الخاص مغلق!", delete_after=5)

@bot.command()
async def فحص(ctx):
    tz = pytz.timezone('Asia/Riyadh')
    now = datetime.datetime.now(tz).strftime("%H:%M:%S")
    await ctx.send(f"🟢 **البوت يعمل بنجاح (Starter)**\n⏰ توقيت الرياض: `{now}`\n📄 الصفحة القادمة: `{get_last_page()}`\n🖼️ الملف المسحوب: `{get_last_page()+3}`")

if __name__ == "__main__":
    keep_alive()
    bot.run(os.environ.get('DISCORD_TOKEN'))
