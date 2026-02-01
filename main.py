import discord
from discord.ext import commands
from discord.ui import Button, View
import os
import re
from flask import Flask
from threading import Thread

# --- 1. نظام الحفاظ على البوت يعمل (Keep Alive) ---
app = Flask('')
@app.route('/')
def home(): return "✅ البوت يعمل وجاهز لخدمة القرآن الكريم"

def run():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    Thread(target=run).start()

# --- 2. إعدادات البوت ---
intents = discord.Intents.default()
intents.message_content = True 
bot = commands.Bot(command_prefix='!', intents=intents)

# --- 3. دالة البحث عن الصورة بناءً على الرقم ---
def find_image(number):
    image_folder = "images"
    if not os.path.exists(image_folder):
        return None
    for filename in os.listdir(image_folder):
        numbers_in_file = re.findall(r'\d+', filename)
        if any(int(n) == number for n in numbers_in_file):
            return os.path.join(image_folder, filename)
    return None

# --- 4. كلاس الأزرار للتنقل بين الصفحات ---
class QuranView(View):
    def __init__(self, current_page):
        super().__init__(timeout=None) # الأزرار لا تنتهي صلاحيتها
        self.current_page = current_page

    @discord.ui.button(label="⬅️ السابق", style=discord.ButtonStyle.grey)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page > 4:
            self.current_page -= 1
            await self.update_message(interaction)
        else:
            await interaction.response.send_message("⚠️ هذه هي الصفحة الأولى (4).", ephemeral=True)

    @discord.ui.button(label="التالي ➡️", style=discord.ButtonStyle.grey)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page < 607:
            self.current_page += 1
            await self.update_message(interaction)
        else:
            await interaction.response.send_message("⚠️ هذه هي الصفحة الأخيرة (607).", ephemeral=True)

    async def update_message(self, interaction: discord.Interaction):
        image_path = find_image(self.current_page)
        if image_path:
            file = discord.File(image_path, filename=f"{self.current_page}.jpg")
            await interaction.response.edit_message(content=f"📖 **الصفحة رقم: {self.current_page}**", attachments=[file], view=self)
        else:
            await interaction.response.send_message(f"❌ تعذر العثور على الصفحة {self.current_page}", ephemeral=True)

# --- 5. الأوامر ---
@bot.event
async def on_ready():
