import io
import json
import os
import aiohttp
from datetime import datetime
from PIL import Image, ImageDraw
import discord
from discord.ext import commands
from flask import Flask
from threading import Thread

# إعداد خادم الويب الوهمي لمنع البوت من الانطفاء وحفظ النشاط 24/7
app = Flask('')

@app.route('/')
def home():
    return "Bot is online and running!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

DATA_FILE = "nitro_data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

@bot.event
async def on_ready():
    print(f"تم تسجيل الدخول بنجاح باسم: {bot.user.name}")

async def generate_profile_card(avatar_bytes: bytes, banner_bytes: bytes):
    avatar_img = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA")
    banner_img = Image.open(io.BytesIO(banner_bytes)).convert("RGBA")

    scale = 2
    card_width = 600 * scale
    banner_height = 220 * scale
    card_height = 320 * scale
    
    avatar_inner_size = 140 * scale
    border_thickness = 8 * scale
    avatar_outer_size = avatar_inner_size + (border_thickness * 2)

    banner_img = banner_img.resize((card_width, banner_height), Image.Resampling.LANCZOS)

    bg_color = (17, 17, 17, 255)
    card = Image.new("RGBA", (card_width, card_height), bg_color)
    card.paste(banner_img, (0, 0))

    def create_smooth_circle_mask(size):
        mask_scale = 4
        big_size = size * mask_scale
        mask = Image.new("L", (big_size, big_size), 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, big_size, big_size), fill=255)
        return mask.resize((size, size), Image.Resampling.LANCZOS)

    border_mask = create_smooth_circle_mask(avatar_outer_size)
    border_circle = Image.new("RGBA", (avatar_outer_size, avatar_outer_size), bg_color)
    
    avatar_outer_x = 30 * scale
    avatar_outer_y = banner_height - (avatar_outer_size // 2)
    card.paste(border_circle, (avatar_outer_x, avatar_outer_y), border_mask)

    avatar_img = avatar_img.resize((avatar_inner_size, avatar_inner_size), Image.Resampling.LANCZOS)
    avatar_mask = create_smooth_circle_mask(avatar_inner_size)
    
    avatar_inner_x = avatar_outer_x + border_thickness
    avatar_inner_y = avatar_outer_y + border_thickness
    card.paste(avatar_img, (avatar_inner_x, avatar_inner_y), avatar_mask)

    output = io.BytesIO()
    card.save(output, format="PNG")
    output.seek(0)
    return output

class ProfileCardView(discord.ui.View):
    def __init__(self, avatar_bytes: bytes, banner_bytes: bytes):
        super().__init__(timeout=None)
        self.avatar_bytes = avatar_bytes
        self.banner_bytes = banner_bytes

    @discord.ui.button(label="Br", style=discord.ButtonStyle.secondary)
    async def br_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        card_io = await generate_profile_card(self.avatar_bytes, self.banner_bytes)
        file_to_send = discord.File(card_io, filename="discord_profile.png")
        await interaction.followup.send(file=file_to_send, ephemeral=True)

@bot.command(name="نشر")
@commands.has_role(1513635397568303174)
async def nashar(ctx):
    if len(ctx.message.attachments) < 1:
        await ctx.send("يرجى إرفاق صورة (أو صورتين: الأفاتار والبنر) مع الأمر.", delete_after=6)
        return

    attachments = ctx.message.attachments
    avatar_attachment = attachments[0]
    banner_attachment = attachments[1] if len(attachments) > 1 else attachments[0]

    avatar_bytes = await avatar_attachment.read()
    banner_bytes = await banner_attachment.read()

    try:
        await ctx.message.delete()
    except Exception:
        pass

    view = ProfileCardView(avatar_bytes, banner_bytes)
    files_list = [discord.File(io.BytesIO(avatar_bytes), filename="avatar.png")]
    if len(attachments) > 1:
        files_list.append(discord.File(io.BytesIO(banner_bytes), filename="banner.png"))
        
    await ctx.send(files=files_list, view=view)

@nashar.error
async def nashar_error(ctx, error):
    if isinstance(error, commands.MissingRole):
        await ctx.send("عذراً، لا تمتلك الرول المطلوب لاستخدام أمر النشر.", delete_after=5)
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("عذراً، ليس لديك الصلاحيات الكافية.", delete_after=5)

@bot.command(name="ضبط_نيترو")
@commands.has_role(1513635397568303174)
async def set_nitro(ctx, member: discord.Member, target_date: str):
    try:
        datetime.strptime(target_date, "%Y-%m-%d")
        data = load_data()
        data[str(member.id)] = target_date
        save_data(data)
        await ctx.send(f"✅ تم حفظ تاريخ انتهاء النيترو للعضو {member.mention} بنجاح إلى: `{target_date}`")
    except ValueError:
        await ctx.send("خطأ في الصيغة. استخدم الشكل التالي:\n`!ضبط_نيترو @العضو 2026-10-15`", delete_after=10)

@set_nitro.error
async def set_nitro_error(ctx, error):
    if isinstance(error, commands.MissingRole):
        await ctx.send("عذراً، هذا الأمر مخصص للمشرفين أصحاب الرول المخصص فقط.", delete_after=5)

@bot.command(name="نيترو")
async def nitro_timer(ctx):
    data = load_data()
    user_id = str(ctx.author.id)
    
    if user_id not in data:
        await ctx.send("عذراً، لم يتم تسجيل تاريخ انتهاء نيترو خاص بك. اطلب من المشرف تسجيله.", delete_after=7)
        return
        
    try:
        target_date = data[user_id]
        target = datetime.strptime(target_date, "%Y-%m-%d")
        now = datetime.now()
        
        remaining = target - now
        if remaining.total_seconds() <= 0:
            await ctx.send("انتهت مدة اشتراك النيترو الخاص بك بالفعل! ⏳")
            return
            
        days = remaining.days
        weeks = days // 7
        remaining_days = days % 7
        hours = remaining.seconds // 3600
        
        time_text = []
        if weeks > 0:
            time_text.append(f"{weeks} أسبوع")
        if remaining_days > 0:
            time_text.append(f"{remaining_days} يوم")
        if hours > 0:
            time_text.append(f"{hours} ساعة")
            
        result_str = " و ".join(time_text) if time_text else "أقل من ساعة"
        await ctx.send(f"⏳ **{ctx.author.mention}، المتبقي حتى انتهاء النيترو:** {result_str}")
    except Exception:
        await ctx.send("حدث خطأ أثناء قراءة التاريخ.", delete_after=5)

@bot.command(name="مسح_فعلي")
@commands.has_permissions(manage_messages=True)
async def clear_messages(ctx, count: int = 10):
    if count < 1 or count > 100:
        await ctx.send("يرجى اختيار عدد بين 1 و 100.", delete_after=5)
        return
    try:
        await ctx.message.delete()
    except Exception:
        pass
    deleted = await ctx.channel.purge(limit=count)
    msg = await ctx.send(f"تم مسح {len(deleted)} رسالة.")
    await msg.delete(delay=3)

@bot.command(name="مسح")
async def clear_alias(ctx, count: int = 10):
    await clear_messages(ctx, count)

@clear_messages.error
async def clear_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("عذراً، لا تمتلك صلاحية مسح الرسائل.", delete_after=5)

# تشغيل نظام الحفاظ على النشاط والبوت معاً
keep_alive()
bot.run(os.getenv("DISCORD_TOKEN"))
