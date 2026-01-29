import discord
from discord.ext import tasks, commands
from discord.ui import Button, View
import datetime
import requests
import os

TOKEN = os.environ.get('DISCORD_TOKEN')
# في السيرفرات المتعددة، سنستخدم قاعدة بيانات بسيطة أو متغيرات لحفظ القنوات
server_channels = {} 

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
bot = commands.Bot(command_prefix='!', intents=intents)

current_page = 1

def get_prayer_times():
    url = "https://api.aladhan.com/v1/timingsByCity?city=Riyadh&country=Saudi+Arabia&method=4"
    try:
        response = requests.get(url).json()
        return response['data']['timings']
    except: return None

# --- واجهة الاشتراك في التنبيهات ---
class RoleView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🔔 اشترك في التنبيهات", style=discord.ButtonStyle.success, custom_id="join_khatmah")
    async def join_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        role = discord.utils.get(interaction.guild.roles, name="ختمة القرآن")
        if not role:
            role = await interaction.guild.create_role(name="ختمة القرآن", mentionable=True)
        
        if role in interaction.user.roles:
            await interaction.user.remove_roles(role)
            await interaction.response.send_message("❌ تم إلغاء اشتراكك في تنبيهات الورد.", ephemeral=True)
        else:
            await interaction.user.add_roles(role)
            await interaction.response.send_message("✅ تم اشتراكك! سيصلك منشن مع كل ورد قرآني.", ephemeral=True)

@bot.command(name="تفعيل")
@commands.has_permissions(administrator=True)
async def setup(ctx):
    # إنشاء الرول إذا لم يكن موجوداً
    role = discord.utils.get(ctx.guild.roles, name="ختمة القرآن")
    if not role:
        await ctx.guild.create_role(name="ختمة القرآن", mentionable=True)
    
    server_channels[str(ctx.guild.id)] = ctx.channel.id
    embed = discord.Embed(title="📖 تفعيل بوت الختمة", description="اضغط على الزر أدناه للحصول على رول (ختمة القرآن) لتصلك منشنات الورد مع كل صلاة.", color=discord.Color.green())
    await ctx.send(embed=embed, view=RoleView())

@tasks.loop(minutes=1)
async def check_prayers():
    global current_page
    now = datetime.datetime.now().strftime("%H:%M")
    prayers = get_prayer_times()
    
    if prayers:
        target_times = {'Fajr': prayers['Fajr'], 'Dhuhr': prayers['Dhuhr'], 'Asr': prayers['Asr'], 'Maghrib': prayers['Maghrib'], 'Isha': prayers['Isha']}
        for prayer_name, prayer_time in target_times.items():
            if now == prayer_time:
                for guild_id, channel_id in server_channels.items():
                    channel = bot.get_channel(channel_id)
                    if channel:
                        role = discord.utils.get(channel.guild.roles, name="ختمة القرآن")
                        mention = role.mention if role else ""
                        
                        pages = 6 if prayer_name == 'Fajr' else 4
                        files = []
                        temp_page = current_page
                        for _ in range(pages):
                            if temp_page > 624: temp_page = 1
                            path = f"images/big-quran_compressed_page-{temp_page:04d}.jpg"
                            if os.path.exists(path): files.append(discord.File(path))
                            temp_page += 1
                        
                        if files:
                            await channel.send(content=f"{mention} 📖 ورد صلاة {prayer_name}", files=files)
                
                # تحديث الصفحة العامة بعد الإرسال لكل السيرفرات
                current_page += (6 if prayer_name == 'Fajr' else 4)
                if current_page > 624: current_page = 1
                break

@bot.event
async def on_ready():
    print(f'✅ البوت متصل ومستعد: {bot.user}')
    if not check_prayers.is_running(): check_prayers.start()

bot.run(TOKEN)
