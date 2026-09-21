import io
import json
import os
from datetime import datetime, timedelta
from PIL import Image, ImageOps, ImageDraw, ImageFont
import discord
from discord.ext import commands
import aiohttp
from flask import Flask
from threading import Thread

# 1. إعداد خادم الويب الوهمي لمنع البوت من الانطفاء (Render 24/7)
app = Flask('')

@app.route('/')
def home():
    return "Bot is online and running!"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run_flask)
    t.start()

# 2. إعدادات بوت ديسكورد
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
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

# --- قوائم الرولات والمجموعات ---
ALLOWED_ROLE_IDS = {
    1513635397568303174,
    1513655552700317926,
    1513655846968496128,
    1513655977931702322,
    1550705477485068348
}

NASHAR_ROLES = [
    1550705477485068348,
    1513655846968496128,
    1513655977931702322,
    1513635397568303174,
    1513655552700317926
]

CLEAR_ROLES = [
    1513655552700317926,
    1513635397568303174,
    1550710745183035483,
    1513655977931702322,
    1513655846968496128
]

def has_nashar_role():
    async def predicate(ctx):
        if any(role.id in NASHAR_ROLES for role in ctx.author.roles):
            return True
        raise commands.MissingRole("رول نشر مطلوب")
    return commands.check(predicate)

def has_clear_role():
    async def predicate(ctx):
        if any(role.id in CLEAR_ROLES for role in ctx.author.roles):
            return True
        raise commands.MissingRole("رول مسح مطلوب")
    return commands.check(predicate)

# --- 1. واجهة وأمر US (دمج البنر مع قالب template.png) ---
class MatchView(discord.ui.View):
    def __init__(self, banner_bytes, av1_bytes, av2_bytes):
        super().__init__(timeout=180)
        self.banner_bytes = banner_bytes
        self.av1_bytes = av1_bytes
        self.av2_bytes = av2_bytes

    @discord.ui.button(label="Br", style=discord.ButtonStyle.secondary, custom_id="fixed_ephemeral_match")
    async def merge_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(thinking=True, ephemeral=True)

        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            template_path = os.path.join(current_dir, "template.png")

            if not os.path.exists(template_path):
                await interaction.followup.send("عذراً، ملف template.png غير موجود في المجلد!", ephemeral=True)
                return

            template = Image.open(template_path).convert("RGBA")
            banner = Image.open(io.BytesIO(self.banner_bytes)).convert("RGBA")
            av1 = Image.open(io.BytesIO(self.av1_bytes)).convert("RGBA")
            av2 = Image.open(io.BytesIO(self.av2_bytes)).convert("RGBA")

            width, height = template.size

            banner_height = int(height * 0.61)
            banner_resized = banner.resize((width, banner_height), Image.Resampling.LANCZOS)
            
            result_img = Image.new("RGBA", (width, height), (0, 0, 0, 255))
            result_img.paste(banner_resized, (0, 0))

            size1 = int(width * 0.23)
            x1, y1 = int(width * 0.040), int(height * 0.405)

            size2 = int(width * 0.26)
            x2, y2 = int(width * 0.280), int(height * 0.325)

            def place_avatar_with_frame(avatar, size, x, y):
                mask = Image.new('L', (size, size), 0)
                draw = ImageDraw.Draw(mask)
                draw.ellipse((0, 0, size, size), fill=255)
                fit_img = ImageOps.fit(avatar, (size, size), centering=(0.5, 0.5))
                fit_img.putalpha(mask)

                frame_size = size + 12
                framed = Image.new("RGBA", (frame_size, frame_size), (0, 0, 0, 0))
                draw_f = ImageDraw.Draw(framed)
                draw_f.ellipse((0, 0, frame_size, frame_size), fill=(0, 0, 0, 255))
                framed.paste(fit_img, (6, 6), fit_img)
                
                return framed, (x - 6, y - 6)

            av1_framed, pos1 = place_avatar_with_frame(av1, size1, x1, y1)
            av2_framed, pos2 = place_avatar_with_frame(av2, size2, x2, y2)

            result_img.paste(av1_framed, pos1, av1_framed)
            result_img.paste(av2_framed, pos2, av2_framed)

            output = io.BytesIO()
            result_img.save(output, format="PNG", compress_level=1)
            output.seek(0)

            file = discord.File(output, filename="match_result.png")
            await interaction.followup.send(file=file, ephemeral=True)

        except Exception as e:
            await interaction.followup.send(f"حدث خطأ أثناء المعالجة: {e}", ephemeral=True)

@bot.command(name="us")
async def us_command(ctx):
    user_role_ids = {role.id for role in ctx.author.roles}
    if not user_role_ids.intersection(ALLOWED_ROLE_IDS):
        try:
            await ctx.message.delete()
        except:
            pass
        await ctx.send("عذراً، أنت لا تمتلك الصلاحية لاستخدام هذا الأمر.", delete_after=5)
        return

    if len(ctx.message.attachments) < 3:
        try:
            await ctx.message.delete()
        except:
            pass
        return

    banner_url = ctx.message.attachments[0].url
    avatar1_url = ctx.message.attachments[1].url
    avatar2_url = ctx.message.attachments[2].url

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(banner_url) as resp:
                banner_bytes = await resp.read()
            async with session.get(avatar1_url) as resp:
                av1_bytes = await resp.read()
            async with session.get(avatar2_url) as resp:
                av2_bytes = await resp.read()
    except Exception:
        return

    try:
        await ctx.message.delete()
    except:
        pass

    view = MatchView(banner_bytes, av1_bytes, av2_bytes)
    files = [
        await ctx.message.attachments[0].to_file(),
        await ctx.message.attachments[1].to_file(),
        await ctx.message.attachments[2].to_file()
    ]
    await ctx.send(files=files, view=view)


# --- 2. توليد بطاقة البروفايل (أمر تقيم و نشر) ---
async def generate_profile_card(avatar_bytes: bytes, banner_bytes: bytes, display_name: str, username: str, is_solid_bg: bool = False):
    avatar_img = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA")

    scale = 2
    card_width = 600 * scale
    banner_height = 220 * scale
    card_height = 340 * scale
    
    avatar_inner_size = 140 * scale
    border_thickness = 8 * scale
    avatar_outer_size = avatar_inner_size + (border_thickness * 2)

    bg_color = (0, 0, 0, 255)
    card = Image.new("RGBA", (card_width, card_height), bg_color)

    if not is_solid_bg and banner_bytes:
        banner_img = Image.open(io.BytesIO(banner_bytes)).convert("RGBA")
        banner_img = banner_img.resize((card_width, banner_height), Image.Resampling.LANCZOS)
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

    draw = ImageDraw.Draw(card)
    
    try:
        font_name = ImageFont.truetype("arial.ttf", 26 * scale)
        font_username = ImageFont.truetype("arial.ttf", 18 * scale)
    except IOError:
        font_name = ImageFont.load_default()
        font_username = ImageFont.load_default()

    text_x = avatar_outer_x + avatar_outer_size + (20 * scale)
    text_y = avatar_outer_y + (30 * scale)

    draw.text((text_x, text_y), display_name, fill=(255, 255, 255, 255), font=font_name)
    draw.text((text_x, text_y + (38 * scale)), f"@{username}", fill=(170, 170, 170, 255), font=font_username)

    output = io.BytesIO()
    card.save(output, format="PNG")
    output.seek(0)
    return output

class ProfileCardView(discord.ui.View):
    def __init__(self, avatar_bytes: bytes, banner_bytes: bytes, author_display_name: str, author_username: str):
        super().__init__(timeout=None)
        self.avatar_bytes = avatar_bytes
        self.banner_bytes = banner_bytes
        self.author_display_name = author_display_name
        self.author_username = author_username

    @discord.ui.button(label="Br", style=discord.ButtonStyle.secondary)
    async def br_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        try:
            card_io = await generate_profile_card(
                self.avatar_bytes, 
                self.banner_bytes, 
                self.author_display_name, 
                self.author_username, 
                is_solid_bg=False
            )
            file_to_send = discord.File(card_io, filename="discord_profile.png")
            await interaction.followup.send(file=file_to_send, ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"حدث خطأ أثناء إنشاء البطاقة: {e}", ephemeral=True)

@bot.command(name="نشر")
@has_nashar_role()
async def nashar(ctx):
    if len(ctx.message.attachments) < 2:
        await ctx.send("❌ يجب إرفاق **صورتين** مع الأمر:\n1. الصورة الأولى: **الأفتار**\n2. الصورة الثانية: **البنر**", delete_after=10)
        return

    avatar_attachment = ctx.message.attachments[0]
    banner_attachment = ctx.message.attachments[1]

    avatar_bytes = await avatar_attachment.read()
    banner_bytes = await banner_attachment.read()

    try:
        await ctx.message.delete()
    except Exception:
        pass

    avatar_file = discord.File(io.BytesIO(avatar_bytes), filename="avatar.png")
    banner_file = discord.File(io.BytesIO(banner_bytes), filename="banner.png")
    
    view = ProfileCardView(avatar_bytes, banner_bytes, ctx.author.display_name, ctx.author.name)
    await ctx.send(files=[avatar_file, banner_file], view=view)

@nashar.error
async def nashar_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send("عذراً، هذا الأمر مخصص للأشخاص الذين يحملون الرولات المعتمدة فقط.", delete_after=5)

@bot.command(name="تقيم")
async def taqeem(ctx, member: discord.Member = None):
    target = member or ctx.author
    try:
        fetched_user = await bot.fetch_user(target.id)
    except Exception:
        fetched_user = target

    try:
        banner_bytes = None
        is_solid = True

        if fetched_user.banner:
            banner_asset = fetched_user.banner.with_size(512)
            banner_bytes = await banner_asset.read()
            is_solid = False

        avatar_asset = target.display_avatar.with_size(256)
        avatar_bytes = await avatar_asset.read()

        card_io = await generate_profile_card(
            avatar_bytes,
            banner_bytes,
            target.display_name,
            target.name,
            is_solid_bg=is_solid
        )
        
        file_to_send = discord.File(card_io, filename="taqeem_profile.png")
        await ctx.send(file=file_to_send)
    except Exception as e:
        await ctx.send(f"حدث خطأ أثناء إنشاء بطاقة التقييم: {e}", delete_after=7)


# --- 3. أوامر ضبط وتتبع النيترو ---
@bot.command(name="ضبط")
@commands.has_role(1513635397568303174)
async def set_nitro(ctx, member: discord.Member, target_date: str):
    try:
        datetime.strptime(target_date, "%Y-%m-%d")
        data = load_data()
        data[str(member.id)] = target_date
        save_data(data)
        await ctx.send(f"✅ تم حفظ تاريخ بداية النيترو للعضو {member.mention} بنجاح إلى: `{target_date}`")
    except ValueError:
        await ctx.send("خطأ في الصيغة. استخدم الشكل التالي:\n`!ضبط @العضو 2026-06-07`", delete_after=10)

@set_nitro.error
async def set_nitro_error(ctx, error):
    if isinstance(error, commands.MissingRole):
        await ctx.send("عذراً، أمر `!ضبط` مخصص فقط للأشخاص الذين يحملون الرول المعتمد.", delete_after=5)

async def calculate_nitro_time(ctx, duration_type):
    data = load_data()
    user_id = str(ctx.author.id)
    
    if user_id not in data:
        await ctx.send("عذراً، لم يتم تسجيل تاريخ النيترو الخاص بك. اطلب من المشرف ضبطه باستخدام أمر `!ضبط`.", delete_after=7)
        return
        
    try:
        start_date_str = data[user_id]
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
        
        if duration_type == "year":
            try:
                target_date = start_date.replace(year=start_date.year + 1)
            except ValueError:
                target_date = start_date + timedelta(days=365)
            period_name = "سنة"
        elif duration_type == "month":
            target_date = start_date + timedelta(days=30)
            period_name = "شهر"
        elif duration_type == "months":
            target_date = start_date + timedelta(days=90)
            period_name = "ثلاثة أشهر"
        else:
            return

        now = datetime.now()
        remaining = target_date - now
        
        if remaining.total_seconds() <= 0:
            await ctx.send(f"انتهت مدة اشتراك النيترو ({period_name}) الخاص بك بالفعل! ⏳")
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
        await ctx.send(f"⏳ **{ctx.author.mention}، المتبقي حتى انتهاء اشتراك ({period_name}):** {result_str}")
    except Exception as e:
        await ctx.send(f"حدث خطأ أثناء حساب التاريخ: {e}", delete_after=5)

@bot.command(name="نيترو")
async def nitro_group(ctx, sub_command: str = None, *, args=None):
    if sub_command == "سنه":
        await calculate_nitro_time(ctx, "year")
    elif sub_command == "شهر":
        await calculate_nitro_time(ctx, "month")
    elif sub_command == "شهور":
        await calculate_nitro_time(ctx, "months")
    else:
        await ctx.send("يرجى تحديد النوع بشكل صحيح:\n`!نيترو سنه`\n`!نيترو شهر`\n`!نيترو شهور`", delete_after=7)


# --- 4. أوامر مسح الرسائل ---
@bot.command(name="مسح_فعلي")
@has_clear_role()
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
@has_clear_role()
async def clear_alias(ctx, count: int = 10):
    await clear_messages(ctx, count)

@clear_messages.error
async def clear_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send("عذراً، هذا الأمر مخصص فقط للأشخاص الذين يحملون الرولات المعتمدة لمسح الرسائل.", delete_after=5)


if __name__ == "__main__":
    keep_alive()
    bot.run(os.getenv("DISCORD_TOKEN"))