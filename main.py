import discord
from discord.ext import commands
from discord.ui import Button, View
import os
import re
from flask import Flask
from threading import Thread

# --- 1. نظام الحفاظ على استمرارية البوت ---
app = Flask('')
@app.route('/')
def home(): return "✅ البوت يعمل وجاهز"

def run():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    Thread(target=run).start()

# --- 2. إعدادات البوت وقاعدة البيانات البسيطة ---
intents = discord.Intents.default()
intents.message_content = True 
bot = commands.Bot(command_prefix='!', intents=intents)

DB_FILE = "subscribers.txt"

def get_subs():
    if not os.path.exists(DB_FILE): return set()
    with open(DB_FILE, "r") as f:
        return set(line.strip() for line in f if line.strip())

def add_sub(user_id):
    subs = get_subs()
    subs.add(str(user_id))
    with open(DB_FILE, "w") as f:
        for s in subs: f.write(f"{s}\n")

# --- 3. البحث عن الصور ---
def find_image(number):
    image_folder = "images"
    if not os.path.exists(image_folder): return None
    for filename in os.listdir(image_folder):
        nums = re.findall(r'\d+', filename)
        if any(int(n) == number for n in nums):
            return os.path.join(image_folder, filename)
    return None

# --- 4. نظام الأزرار مع التنبيه التلقائي ---
class QuranView(View):
    def __init__(self, current_page):
        super().__init__(timeout=None)
        self.current_page = current_page

    async def notify_and_edit(self, interaction):
        image_path = find_image(self.current_page)
        if image_path:
            file = discord.File(image_path, filename=f"{self.current_page}.jpg")
            subs = get_subs()
            # المنشن سيظهر في محتوى الرسالة لكل من فعل التنبيهات
            mentions = " ".join([f"<@{s}>" for s in subs])
            content = f"📖 صفحة رقم: **{self.current_page}**\n🔔 تنبيه للمشتركين: {mentions}"
            await interaction.response.edit_message(content=content, attachments=[file], view=self)

    @discord.ui.button(label="⬅️ السابق", style=discord.ButtonStyle.grey)
    async def prev(self, interaction, button):
        if self.current_page > 4:
            self.current_page -= 1
            await self.notify_and_edit(interaction)

    @discord.ui.button(label="التالي ➡️", style=discord.ButtonStyle.grey)
    async def next(self, interaction, button):
        if self.current_page < 607:
            self.current_page += 1
            await self.notify_and_edit(interaction)

# --- 5. الأوامر ---
@bot.event
async def on_ready():
    print(f'✅ البوت متصل: {bot.user}')

@bot.command()
async def تفعيل(ctx):
    add_sub(ctx.author.id)
    await ctx.send(f"✅ تم تفعيل التنبيهات لـ {ctx.author.mention}. ستصلك الإشارات مع كل صفحة!")

@bot.command()
async def ترتيب(ctx, number: int):
    if 4 <= number <= 607:
        image_path = find_image(number)
        if image_path:
            subs = get_subs()
            mentions = " ".join([f"<@{s}>" for s in subs])
            content = f"📖 صفحة رقم: **{number}**\n🔔 تنبيه للمشتركين: {mentions}"
            await ctx.send(content=content, file=discord.File(image_path), view=QuranView(number))
    else:
        await ctx.send("⚠️ النطاق من 4 إلى 607.")

if __name__ == "__main__":
    keep_alive()
    bot.run(os.environ.get('DISCORD_TOKEN'))
