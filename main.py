import io
import json
import os
import asyncio
from datetime import datetime, timedelta
import aiohttp
from PIL import Image, ImageDraw
import discord
from discord.ext import commands
from flask import Flask
from threading import Thread
import yt_dlp
import random

# إعداد خادم الويب الوهمي للحفاظ على نشاط البوت 24/7
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
intents.voice_states = True

bot = commands.Bot(command_prefix=["!", "-"], intents=intents)

DATA_FILE = "nitro_data.json"
POINTS_FILE = "points_data.json"
SETTINGS_FILE = "settings.json"

def load_json(filename, default={}):
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return default
    return default

def save_json(filename, data):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

@bot.event
async def on_ready():
    print(f"تم تسجيل الدخول بنجاح باسم: {bot.user.name}")

# دالة توليد بطاقة البروفايل
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

# مساعدة لاحتساب الأشهر بدقة تقويمية
def add_months(sourcedate, months):
    month = sourcedate.month - 1 + months
    year = sourcedate.year + month // 12
    month = month % 12 + 1
    day = min(sourcedate.day, [31, 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month-1])
    return sourcedate.replace(year=year, month=month, day=day)

# ==================== 1. نظام النيترو والتواريخ ====================
@bot.group(name="نيترو", invoke_without_command=True)
async def nitro(ctx, member: discord.Member = None):
    target_member = member or ctx.author
    data = load_json(DATA_FILE)
    user_id = str(target_member.id)
    
    if user_id not in data:
        await ctx.send(f"عذراً، لم يتم تسجيل تاريخ انتهاء نيترو لـ {target_member.mention}.", delete_after=7)
        return
        
    try:
        target_date = data[user_id]
        target = datetime.strptime(target_date, "%Y-%m-%d")
        now = datetime.now()
        
        remaining = target - now
        if remaining.total_seconds() <= 0:
            await ctx.send(f"⏳ انتهت مدة اشتراك النيترو الخاص بـ {target_member.mention} بالفعل!")
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
        await ctx.send(f"⏳ **المتبقي حتى انتهاء نيترو {target_member.mention}:** {result_str} (ينتهي في `{target_date}`)")
    except Exception:
        await ctx.send("حدث خطأ أثناء قراءة التاريخ.", delete_after=5)

def parse_date(date_str: str):
    supported_formats = ["%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d"]
    for fmt in supported_formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    return None

@nitro.command(name="سنة")
@commands.has_role(1513635397568303174)
async def nitro_year(ctx, member: discord.Member, target_date: str = None):
    start_date = parse_date(target_date) if target_date else datetime.now()
    if not start_date and target_date:
        await ctx.send("❌ صيغة التاريخ غير صحيحة. استخدم: YYYY-MM-DD", delete_after=7)
        return
    end_date = add_months(start_date, 12)
    formatted_date = end_date.strftime("%Y-%m-%d")
    
    data = load_json(DATA_FILE)
    data[str(member.id)] = formatted_date
    save_json(DATA_FILE, data)
    await ctx.send(f"✅ تم ضبط نيترو (سنة) لـ {member.mention} حتى تاريخ: `{formatted_date}`")

@nitro.command(name="شهر")
@commands.has_role(1513635397568303174)
async def nitro_month(ctx, member: discord.Member, target_date: str = None):
    start_date = parse_date(target_date) if target_date else datetime.now()
    if not start_date and target_date:
        await ctx.send("❌ صيغة التاريخ غير صحيحة. استخدم: YYYY-MM-DD", delete_after=7)
        return
    end_date = add_months(start_date, 1)
    formatted_date = end_date.strftime("%Y-%m-%d")
    
    data = load_json(DATA_FILE)
    data[str(member.id)] = formatted_date
    save_json(DATA_FILE, data)
    await ctx.send(f"✅ تم ضبط نيترو (شهر) لـ {member.mention} حتى تاريخ: `{formatted_date}`")

@nitro.command(name="شهور")
@commands.has_role(1513635397568303174)
async def nitro_months(ctx, member: discord.Member, target_date: str = None):
    start_date = parse_date(target_date) if target_date else datetime.now()
    if not start_date and target_date:
        await ctx.send("❌ صيغة التاريخ غير صحيحة. استخدم: YYYY-MM-DD", delete_after=7)
        return
    end_date = add_months(start_date, 3)
    formatted_date = end_date.strftime("%Y-%m-%d")
    
    data = load_json(DATA_FILE)
    data[str(member.id)] = formatted_date
    save_json(DATA_FILE, data)
    await ctx.send(f"✅ تم ضبط نيترو (ثلاث شهور) لـ {member.mention} حتى تاريخ: `{formatted_date}`")

@nitro.error
async def nitro_error(ctx, error):
    if isinstance(error, commands.MissingRole):
        await ctx.send("عذراً، لا تمتلك الرول المطلوب لاستخدام هذا الأمر.", delete_after=5)

# ==================== 2. أمر النشر ====================
@bot.command(name="نشر")
@commands.has_any_role(1513635397568303174, 1550705477485068348)
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

    class ProfileCardView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=None)

        @discord.ui.button(label="Br", style=discord.ButtonStyle.secondary)
        async def br_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            await interaction.response.defer(ephemeral=True)
            card_io = await generate_profile_card(avatar_bytes, banner_bytes)
            file_to_send = discord.File(card_io, filename="discord_profile.png")
            await interaction.followup.send(file=file_to_send, ephemeral=True)

    view = ProfileCardView()
    files_list = [discord.File(io.BytesIO(avatar_bytes), filename="avatar.png")]
    if len(attachments) > 1:
        files_list.append(discord.File(io.BytesIO(banner_bytes), filename="banner.png"))
        
    await ctx.send(files=files_list, view=view)

@nashar.error
async def nashar_error(ctx, error):
    if isinstance(error, commands.MissingAnyRole):
        await ctx.send("عذراً، لا تمتلك الرول المطلوب لاستخدام أمر النشر.", delete_after=5)

# ==================== 3. أمر المسح ====================
@bot.command(name="مسح")
@commands.has_any_role(1513635397568303174, 1550710745183035483)
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

@clear_messages.error
async def clear_error(ctx, error):
    if isinstance(error, commands.MissingAnyRole):
        await ctx.send("عذراً، لا تمتلك الرول المطلوب لمسح الرسائل.", delete_after=5)

# ==================== 4. توزيع النقاط (-n) ====================
@bot.command(n