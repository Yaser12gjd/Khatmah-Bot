import discord
from discord.ext import tasks, commands
from discord.ui import Button, View
import datetime
import requests
import os

# --- الإعدادات الأساسية ---
TOKEN = os.environ.get('DISCORD_TOKEN')
# تثبيت القناة لضمان عدم ضياعها عند إعادة تشغيل السيرفر المجاني
STABLE_CHANNEL_ID = 1332768565507522580 

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# متغيرات التحكم بالصور
current_page = 1
total_pages = 604  # تأكد من عدد صفحات ملفك الجديد
bot_active = True 

def get_prayer_times():
    # توقيت الرياض
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
            await interaction.response.send_message("❌ تم إلغاء اشتراكك في التنبيهات.", ephemeral=True)
        else:
            await interaction.user.add_roles(role)
            await interaction.response.send_message("✅ تم اشتراكك! سيصلك منشن مع كل ورد.", ephemeral=True)

@bot.command(name="تفعيل")
async def setup(ctx):
    embed = discord.Embed(title="📖 تفعيل بوت الختمة", description="اضغط على الزر أدناه للحصول على رول (ختمة القرآن) لتصلك منشنات الورد مع كل صلاة.", color=discord.Color.green())
    await ctx.send(embed=embed, view=RoleView())

@bot.command(name="ترتيب")
async def check_order(ctx, page_num: int = None):
    global current_page
    target = page_num if page_num else current_page
    # المسار المحدث بناءً على اسم الملف الجديد في مجلد images1
    image_path = f"images1/standard39-2-1(pdfgear.com)_page-{target:04d}.jpg"
    
    if os.path.exists(image_path):
        await ctx.send(content=f"🖼️ استعراض الصفحة رقم **({target})**:", file=discord.File(image_path))
    else:
        await
