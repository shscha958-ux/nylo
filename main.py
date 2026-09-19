import io
import json
import os
import random
import asyncio
from datetime import datetime, timedelta
from PIL import Image, ImageDraw
import discord
from discord.ext import commands
from flask import Flask
from threading import Thread

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

# تعريف الرولات المعتمدة للأوامر بناءً على طلبك
ROLES = {
    "admin_control": [1513635397568303174],
    "nashar": [1513635397568303174, 1550705477485068348],
    "clear": [1513635397568303174, 1550710745183035483],
    "n_command": [1550711376995950592, 1513635397568303174, 1513655552700317926],
    "roulette": [1550711376995950592, 1513635397568303174],
    "askat": [1550711376995950592, 1513655552700317926, 1513655846968496128, 1513655977931702322],
    "mute": [1513655977931702322, 1513655846968496128, 1513635397568303174, 1513655552700317926],
    "unmute_speak": [1513655552700317926, 1513635397568303174, 1513655846968496128, 1550711376995950592, 1513655977931702322],
    "like": [1513635397568303174]
}

def has_any_role(role_list_key):
    async def predicate(ctx):
        allowed_roles = ROLES.get(role_list_key, [])
        if any(role.id in allowed_roles for role in ctx.author.roles):
            return True
        raise commands.MissingRole(allowed_roles[0])
    return commands.check(predicate)

def load_json(filename):
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}

def save_json(filename, data):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

@bot.event
async def on_ready():
    print(f"Bot logged in successfully as: {bot.user.name}")

# ==================== نظام النيترو وتواريخه ====================
@bot.command(name="ضبط")
@has_any_role("admin_control")
async def set_nitro_dynamic(ctx, member: discord.Member, period_type: str, date_str: str):
    supported_formats = ["%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d"]
    parsed_date = None
    
    for fmt in supported_formats:
        try:
            parsed_date = datetime.strptime(date_str, fmt)
            break
        except ValueError:
            continue
            
    if not parsed_date:
        await ctx.send("خطأ في صيغة التاريخ. استخدم: YYYY-MM-DD", delete_after=7)
        return

    target_date = parsed_date
    period_lower = period_type.lower()
    
    if "سنة" in period_lower or "year" in period_lower:
        target_date = parsed_date + timedelta(days=365)
    elif "شهور" in period_lower or "3" in period_lower:
        target_date = parsed_date + timedelta(days=90)
    elif "شهر" in period_lower or "month" in period_lower:
        target_date = parsed_date + timedelta(days=30)
    else:
        await ctx.send("يرجى تحديد المدة بشكل صحيح: سنة ، شهر ، أو شهور.", delete_after=7)
        return

    data = load_json(DATA_FILE)
    data[str(member.id)] = target_date.strftime("%Y-%m-%d")
    save_json(DATA_FILE, data)
    
    await ctx.send(f"تم ضبط نيترو ({period_type}) للعضو {member.mention} لينتهي بتاريخ: {target_date.strftime('%Y-%m-%d')}")

@bot.command(name="نيترو")
async def check_nitro(ctx, sub_type: str = "شهر"):
    data = load_json(DATA_FILE)
    user_id = str(ctx.author.id)
    
    if user_id not in data:
        await ctx.send("عذراً، ليس لديك تاريخ نيترو مسجل.", delete_after=6)
        return
        
    target = datetime.strptime(data[user_id], "%Y-%m-%d")
    now = datetime.now()
    remaining = target - now
    
    if remaining.total_seconds() <= 0:
        await ctx.send("انتهت مدة اشتراك النيترو الخاص بك!")
        return
        
    await ctx.send(f"المتبقي لانتهاء اشتراك النيترو: {remaining.days} يوم و {remaining.seconds // 3600} ساعة.")

# ==================== نظام النشر وبطاقة البروفايل ====================
async def generate_profile_card(avatar_bytes: bytes, banner_bytes: bytes):
    avatar_img = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA")
    banner_img = Image.open(io.BytesIO(banner_bytes)).convert("RGBA")
    scale = 2
    card_width, banner_height, card_height = 600 * scale, 220 * scale, 320 * scale
    avatar_inner_size, border_thickness = 140 * scale, 8 * scale
    avatar_outer_size = avatar_inner_size + (border_thickness * 2)

    banner_img = banner_img.resize((card_width, banner_height), Image.Resampling.LANCZOS)
    card = Image.new("RGBA", (card_width, card_height), (17, 17, 17, 255))
    card.paste(banner_img, (0, 0))

    def create_mask(size):
        mask = Image.new("L", (size * 4, size * 4), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, size * 4, size * 4), fill=255)
        return mask.resize((size, size), Image.Resampling.LANCZOS)

    card.paste(Image.new("RGBA", (avatar_outer_size, avatar_outer_size), (17, 17, 17, 255)), (30 * scale, banner_height - (avatar_outer_size // 2)), create_mask(avatar_outer_size))
    card.paste(avatar_img.resize((avatar_inner_size, avatar_inner_size), Image.Resampling.LANCZOS), (30 * scale + border_thickness, banner_height - (avatar_outer_size // 2) + border_thickness), create_mask(avatar_inner_size))

    output = io.BytesIO()
    card.save(output, format="PNG")
    output.seek(0)
    return output

class ProfileView(discord.ui.View):
    def __init__(self, av_bytes, ban_bytes, target_user):
        super().__init__(timeout=None)
        self.av_bytes = av_bytes
        self.ban_bytes = ban_bytes
        self.target_user = target_user
        self.likes = 0

    @discord.ui.button(label="❤️ 0", style=discord.ButtonStyle.danger)
    async def like_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.likes += 1
        button.label = f"❤️ {self.likes}"
        await interaction.response.edit_message(view=self)

@bot.command(name="نشر")
@has_any_role("nashar")
async def nashar(ctx):
    if not ctx.message.attachments:
        await ctx.send("يرجى إرفاق صورة البروفايل أو البنر.", delete_after=5)
        return
    av_bytes = await ctx.message.attachments[0].read()
    ban_bytes = await ctx.message.attachments[1].read() if len(ctx.message.attachments) > 1 else av_bytes
    try:
        await ctx.message.delete()
    except:
        pass
    view = ProfileView(av_bytes, ban_bytes, ctx.author)
    card_io = await generate_profile_card(av_bytes, ban_bytes)
    await ctx.send(file=discord.File(card_io, "profile.png"), view=view)

@bot.command(name="تقيم")
async def evaluate_profile(ctx):
    member = ctx.author
    asset = member.avatar.url if member.avatar else member.default_avatar.url
    async with aiohttp.ClientSession() as session:
        async with session.get(asset) as resp:
            if resp.status == 200:
                av_bytes = await resp.read()
                card_io = await generate_profile_card(av_bytes, av_bytes)
                view = ProfileView(av_bytes, av_bytes, member)
                await ctx.send(file=discord.File(card_io, "eval.png"), view=view)

# ==================== الأوامر الإدارية والمسح ====================
@bot.command(name="مسح")
@has_any_role("clear")
async def clear_msgs(ctx, count: int = 10):
    try:
        await ctx.message.delete()
    except:
        pass
    deleted = await ctx.channel.purge(limit=count)
    await ctx.send(f"تم مسح {len(deleted)} رسالة.", delete_after=3)

# ==================== نظام النقاط والـ -n ====================
@bot.command(name="n")
@has_any_role("n_command")
async def manage_points(ctx, amount: int, member: discord.Member = None):
    points_data = load_json(POINTS_FILE)
    if not member:
        member = ctx.author
    
    uid = str(member.id)
    points_data[uid] = points_data.get(uid, 0) + amount
    save_json(POINTS_FILE, points_data)
    await ctx.send(f"تم تحديث نقاط العضو {member.mention} بمقدار {amount}. مجموع نقاطه: {points_data[uid]}")

# ==================== لعبة الروليت ====================
@bot.command(name="روليت")
@has_any_role("roulette")
async def roulette_game(ctx):
    if not ctx.author.voice or not ctx.author.voice.channel:
        await ctx.send("يجب أن تكون في روم صوتي لبدء الروليت!", delete_after=5)
        return
        
    members = ctx.author.voice.channel.members
    if len(members) < 2:
        await ctx.send("يجب تواجد شخصين على الأقل في الروم الصوتي.", delete_after=5)
        return

    await ctx.send("بدأت لعبة الروليت الصوتي! يتم اختيار شخص عشوائي للطرد حتى يتبقى الفائز الأخير...")
    game_members = list(members)
    
    while len(game_members) > 1:
        victim = random.choice(game_members)
        game_members.remove(victim)
        try:
            await victim.move_to(None)
            await ctx.send(f"تم طرد العضو {victim.mention} من الروليت! الباقون: {len(game_members)}")
        except:
            pass
        await asyncio.sleep(3)
        
    winner = game_members[0]
    points_data = load_json(POINTS_FILE)
    points_data[str(winner.id)] = points_data.get(str(winner.id), 0) + 50
    save_json(POINTS_FILE, points_data)
    await ctx.send(f"مبروك للفائز بالروليت {winner.mention}! حصل على 50 نقطة.")

# ==================== نظام الاسكات والميوت بالأسباب ====================
REASONS_MAPPING = {
    "1": ("طاري اهل", timedelta(minutes=15)),
    "2": ("سب", timedelta(minutes=40)),
    "3": ("قذف", timedelta(minutes=120))
}

@bot.command(name="اسكت")
@has_any_role("askat")
async def mute_chat(ctx, member: discord.Member, choice: str = None):
    if not choice or choice not in REASONS_MAPPING:
        options_text = "\n".join([f"**{k}** - {v[0]} (