import discord
from discord.ext import commands
import asyncio
import os
import random
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from flask import Flask
from threading import Thread

# ==================== إعدادات الخادم للبقاء 24/7 (Render) ====================
app = Flask('')

@app.route('/')
def home():
    return "Bot is running 24/7!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# ==================== إعدادات البوت الأساسية ====================
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True
intents.voice_states = True

bot = commands.Bot(command_prefix=["!", "-"], intents=intents)

user_points = {}
user_inventory = {}
MASTER_ADMIN_ROLE = 1550706151308660856

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} (ID: {bot.user.id})')
    print('Bot is ready and running!')

def check_admin(ctx):
    return any(role.id == MASTER_ADMIN_ROLE for role in ctx.author.roles)

# ==================== 1. أوامر الإدارة والعقوبات (القائمة المنسدلة والفك اليدوي) ====================
class MuteSelect(discord.ui.Select):
    def __init__(self, target_member: discord.Member, is_timeout: bool):
        self.target_member = target_member
        self.is_timeout = is_timeout
        
        options = [
            discord.SelectOption(label="المشاكل", description="15 دقيقة", value="15_مشاكل", emoji="⚠️"),
            discord.SelectOption(label="ايحاءات جنسية", description="30 دقيقة", value="30_إيحاء جنسي", emoji="🔞"),
            discord.SelectOption(label="السب", description="40 دقيقة", value="40_السب", emoji="🔇"),
            discord.SelectOption(label="طاري الاهل", description="60 دقيقة", value="60_طاري أهل", emoji="🛡️"),
            discord.SelectOption(label="القذف", description="120 دقيقة", value="120_القذف", emoji="❌"),
        ]
        super().__init__(placeholder="اختر سبب العقوبة...", min_values=1, max_values=1, options=options, custom_id="mute_select_menu")

    async def callback(self, interaction: discord.Interaction):
        data = self.values[0].split("_")
        minutes = int(data[0])
        reason = data[1]

        try:
            if self.is_timeout:
                delta = discord.utils.utcnow() + discord.timedelta(minutes=minutes)
                await self.target_member.timeout(delta, reason=reason)
                await interaction.response.send_message(f"تم عمل اسكت للعضو {self.target_member.mention} بسبب **{reason}** لمدة {minutes} دقيقة.", ephemeral=False)
            else:
                await self.target_member.edit(mute=True, reason=reason)
                await interaction.response.send_message(f"تم إعطاء ميوت صوتي لـ {self.target_member.mention} بسبب **{reason}**.", ephemeral=False)
        except Exception as e:
            await interaction.response.send_message(f"حدث خطأ: تأكد أن رول البوت أعلى من رول العضو وأن البوت يمتلك صلاحيات كافية. ({e})", ephemeral=True)

class MuteSelectView(discord.ui.View):
    def __init__(self, target_member: discord.Member, is_timeout: bool):
        super().__init__(timeout=None)
        self.add_item(MuteSelect(target_member, is_timeout))

    @discord.ui.button(label="إلغاء", style=discord.ButtonStyle.danger, custom_id="cancel_mute_menu")
    async def cancel_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("تم إلغاء الأمر.", ephemeral=True)
        self.stop()

@bot.command(name="اسكت")
async def askat(ctx, member: discord.Member = None):
    if not check_admin(ctx):
        return await ctx.send("ليس لديك رول الإدارة المخصص لاستخدام هذا الأمر.", delete_after=5)
    if not member:
        return await ctx.send("الرجاء منشن العضو المستهدف.")
    view = MuteSelectView(member, is_timeout=True)
    await ctx.send(f"يرجي تحديد سبب العقوبه • {member.mention}:", view=view)

@bot.command(name="ميوت")
async def mute_voice(ctx, member: discord.Member = None):
    if not check_admin(ctx):
        return await ctx.send("ليس لديك رول الإدارة المخصص لاستخدام هذا الأمر.", delete_after=5)
    if not member:
        return await ctx.send("الرجاء منشن العضو المستهدف.")
    view = MuteSelectView(member, is_timeout=False)
    await ctx.send(f"يرجي تحديد سبب العقوبه • {member.mention}:", view=view)

@bot.command(name="فك")
async def unmute_timeout(ctx, member: discord.Member = None):
    if not check_admin(ctx):
        return await ctx.send("ليس لديك رول الإدارة المخصص لاستخدام هذا الأمر.", delete_after=5)
    if not member:
        return await ctx.send("الرجاء منشن العضو.")
    try:
        await member.timeout(None, reason=f"فك يدوي بواسطة {ctx.author}")
        await ctx.send(f"تم فك العقوبة الكتابية يدوياً عن {member.mention}.")
    except Exception as e:
        await ctx.send(f"تعذر فك العقوبة: {e}")

@bot.command(name="تكلم")
async def unmute_voice(ctx, member: discord.Member = None):
    if not check_admin(ctx):
        return await ctx.send("ليس لديك رول الإدارة المخصص لاستخدام هذا الأمر.", delete_after=5)
    if not member:
        return await ctx.send("الرجاء منشن العضو.")
    try:
        await member.edit(mute=False, reason=f"فك صوتي يدوي بواسطة {ctx.author}")
        await ctx.send(f"تم فك الميوت الصوتي يدوياً عن {member.mention}.")
    except Exception as e:
        await ctx.send(f"تعذر فك الميوت الصوتي: {e}")


# ==================== 2. أوامر النشر والتفاعل (!نشر و !لايك) ====================
@bot.command(name="نشر")
@commands.has_permissions(administrator=True)
async def broadcast(ctx, *, message: str):
    await ctx.message.delete()
    embed = discord.Embed(
        title="إعلان إداري", description=message, color=discord.Color.blue()
    )
    embed.set_footer(
        text=f"تم النشر بواسطة: {ctx.author.display_name}",
        icon_url=ctx.author.display_avatar.url,
    )
    await ctx.send(embed=embed)

@bot.command(name="لايك")
async def like(ctx, emoji: str = "👍"):
    try:
        await ctx.message.add_reaction(emoji)
    except Exception as e:
        await ctx.send(f"تعذر إضافة التفاعل: {e}")


# ==================== 3. أمر التقييم بتصميم البروفايل النظيف (البنر + الأفتار فقط) ====================
@bot.command(name="تقيم")
async def taqeem(ctx, member: discord.Member = None):
    target = member or ctx.author
    try:
        user_obj = await bot.fetch_user(target.id)
    except:
        user_obj = target

    width, height = 900, 520
    card = Image.new("RGBA", (width, height), (24, 25, 28, 255))
    draw = ImageDraw.Draw(card)

    # 1. وضع البنر في الأعلى بجودة عالية
    if user_obj.banner:
        banner_bytes = await user_obj.banner.read()
        banner_img = Image.open(BytesIO(banner_bytes)).convert("RGBA")
        banner_img = banner_img.resize((width, 320), Image.Resampling.LANCZOS)
        card.paste(banner_img, (0, 0))
    else:
        draw.rectangle([0, 0, width, 320], fill=(45, 47, 52, 255))

    # 2. خلفية المساحة السفلية السوداء بالكامل
    draw.rectangle([0, 320, width, height], fill=(18, 19, 22, 255))

    # 3. جلب وصنع الأفتار الدائري مع إطار متناسق وبجودة عالية
    avatar_bytes = await target.display_avatar.read()
    avatar_img = Image.open(BytesIO(avatar_bytes)).convert("RGBA")
    avatar_size, avatar_border = 180, 8
    avatar_img = avatar_img.resize((avatar_size, avatar_size), Image.Resampling.LANCZOS)
    
    mask = Image.new("L", (avatar_size, avatar_size), 0)
    draw_mask = ImageDraw.Draw(mask)
    draw_mask.ellipse((0, 0, avatar_size, avatar_size), fill=255)
    
    avatar_bg = Image.new("RGBA", (avatar_size + avatar_border*2, avatar_size + avatar_border*2), (18, 19, 22, 255))
    draw_abg = ImageDraw.Draw(avatar_bg)
    draw_abg.ellipse((0, 0, avatar_size + avatar_border*2, avatar_size + avatar_border*2), fill=(18, 19, 22, 255))
    
    card.paste(avatar_bg, (54, 220), avatar_bg)
    card.paste(avatar_img, (62, 228), mask)

    buffer = BytesIO()
    card.save(buffer, format="PNG", quality=95)
    buffer.seek(0)
    
    file = discord.File(buffer, filename="taqeem.png")
    await ctx.send(file=file)


# ==================== 4. نظام النقاط والتوزيع (-n) ====================
@bot.command(name="n")
async def distribute_points(ctx, amount: int = 0, member: discord.Member = None):
    if not check_admin(ctx):
        return await ctx.send("ليس لديك الصلاحية لتوزيع النقاط.", delete_after=5)
    if not member or amount <= 0:
        return await ctx.send("الاستخدام الصحيح: `-n [الرقم] [@العضو]`")
    
    user_points[member.id] = user_points.get(member.id, 0) + amount
    await ctx.send(f"تم إضافة `{amount}` نقطة إلى العضو {member.mention}. رصيده الحالي: `{user_points[member.id]}` نقطة.")


# ==================== 5. أمر سحب الأعضاء (-سحب) ====================
@bot.command(name="سحب")
async def pull_member(ctx, member: discord.Member = None):
    if not ctx.author.voice:
        return await ctx.send("يجب أن تكون في روم صوتي لتتمكن من استخدام أمر السحب.")
    if not member:
        return await ctx.send("الرجاء منشن العضو المراد سحبه.")
    if not member.voice:
        return await ctx.send("العضو المستهدف ليس في أي روم صوتي.")
    
    try:
        target_channel = ctx.author.voice.channel
        await member.move_to(target_channel, reason=f"سحب بواسطة {ctx.author}")
        await ctx.send(f"تم سحب العضو {member.mention} إلى رومك الصوتي بنجاح.")
    except Exception as e:
        await ctx.send(f"حدث خطأ أثناء محاولة سحب العضو: {e}")


# ==================== 6. لعبة الروليت (بدون إيموجيات، عجلة سوداء، أسماء بيضاء وأفتار بالوسط) ====================
class RouletteShopView(discord.ui.View):
    def __init__(self, user_id: int):
        super().__init__(timeout=60)
        self.user_id = user_id

    @discord.ui.button(label="قنبلة (10 نقاط)", style=discord.ButtonStyle.danger, custom_id="shop_bomb")
    async def buy_bomb(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("هذا المتجر ليس لك!", ephemeral=True)
        pts = user_points.get(self.user_id, 0)
        if pts < 10:
            return await interaction.response.send_message("ليس لديك نقاط كافية لشراء القنبلة.", ephemeral=True)
        user_points[self.user_id] -= 10
        inv = user_inventory.setdefault(self.user_id, {"bomb": 0, "shield": 0, "attack": 0})
        inv["bomb"] += 1
        await interaction.response.send_message("اشتريت قنبلة بنجاح!", ephemeral=True)

    @discord.ui.button(label="حماية (15 نقطة)", style=discord.ButtonStyle.primary, custom_id="shop_shield")
    async def buy_shield(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("هذا المتجر ليس لك!", ephemeral=True)
        pts = user_points.get(self.user_id, 0)
        if pts < 15:
            return await interaction.response.send_message("ليس لديك نقاط كافية لشراء الحماية.", ephemeral=True)
        user_points[self.user_id] -= 15
        inv = user_inventory.setdefault(self.user_id, {"bomb": 0, "shield": 0, "attack": 0})
        inv["shield"] += 1
        await interaction.response.send_message("اشتريت درع حماية بنجاح!", ephemeral=True)

    @discord.ui.button(label="هجمة عكسية (18 نقطة)", style=discord.ButtonStyle.success, custom_id="shop_attack")
    async def buy_attack(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("هذا المتجر ليس لك!", ephemeral=True)
        pts = user_points.get(self.user_id, 0)
        if pts < 18:
            return await interaction.response.send_message("ليس لديك نقاط كافية لشراء الهجمة.", ephemeral=True)
        user_points[self.user_id] -= 18
        inv = user_inventory.setdefault(self.user_id, {"bomb": 0, "shield": 0, "attack": 0})
        inv["attack"] += 1
        await interaction.response.send_message("اشتريت هجمة عكسية بنجاح!", ephemeral=True)

class RouletteMainView(discord.ui.View):
    def __init__(self, game_session):
        super().__init__(timeout=None)
        self.game_session = game_session

    @discord.ui.button(label="دخول", style=discord.ButtonStyle.success, custom_id="roulette_join")
    async def join_game(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user in self.game_session.players:
            return await interaction.response.send_message("أنت منضم مسبقاً في اللعبة!", ephemeral=True)
        self.game_session.players.append(interaction.user)
        await interaction.response.send_message(f"انضممت إلى لعبة الروليت بنجاح! (عدد اللاعبين: {len(self.game_session.players)})", ephemeral=True)

    @discord.ui.button(label="متجر الخصائص", style=discord.ButtonStyle.secondary, custom_id="roulette_shop")
    async def open_shop(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = RouletteShopView(interaction.user.id)
        await interaction.response.send_message("اختر ما تريد شراءه:", view=view, ephemeral=True)

    @discord.ui.button(label="الحقيبه", style=discord.ButtonStyle.secondary, custom_id="roulette_bag")
    async def open_inventory(self, interaction: discord.Interaction, button: discord.ui.Button):
        inv = user_inventory.get(interaction.user.id, {"bomb": 0, "shield": 0, "attack": 0})
        await interaction.response.send_message(f"حقيقتك:\nقنابل: {inv['bomb']}\nدروع حماية: {inv['shield']}\nهجمات عكسية: {inv['attack']}", ephemeral=True)

    @discord.ui.button(label="احصائيات", style=discord.ButtonStyle.secondary, custom_id="roulette_stats")
    async def open_stats(self, interaction: discord.Interaction, button: discord.ui.Button):
        pts = user_points.get(interaction.user.id, 0)
        await interaction.response.send_message(f"نقاطك الحالية: `{pts}` نقطة.", ephemeral=True)

class RouletteGameSession:
    def __init__(self, ctx):
        self.ctx = ctx
        self.players = []

def generate_roulette_image(players, center_avatar_bytes):
    size = 600
    img = Image.new("RGBA", (size, size), (0, 0, 0, 255))
    draw = ImageDraw.Draw(img)
    
    num_players = len(players) if players else 1
    angle_step = 360 / num_players
    
    try:
        font_player = ImageFont.truetype("arial.ttf", 22)
    except:
        font_player = ImageFont.load_default()

    for i, player in enumerate(players):
        start_angle = i * angle_step
        end_angle = (i + 1) * angle_step
        draw.pieslice([50, 50, size-50, size-50], start=start_angle, end=end_angle, fill=(15, 15, 15, 255), outline=(255, 255, 255, 255))
        
        import math
        mid_angle = math.radians(start_angle + (angle_step / 2))
        text_x = (size / 2) + 140 * math.cos(mid_angle)
        text_y = (size / 2) + 140 * math.sin(mid_angle)
        
        name_text = player.display_name[:10]
        draw.text((text_x - 30, text_y - 10), name_text, fill=(255, 255, 255, 255), font=font_player)

    if center_avatar_bytes:
        avatar = Image.open(BytesIO(center_avatar_bytes)).convert("RGBA")
        avatar_size = 140
        avatar = avatar.resize((avatar_size, avatar_size), Image.Resampling.LANCZOS)
        
        mask = Image.new("L", (avatar_size, avatar_size), 0)
        d_mask = ImageDraw.Draw(mask)
        d_mask.ellipse((0, 0, avatar_size, avatar_size), fill=255)
        
        offset = (size - avatar_size) // 2
        img.paste(avatar, (offset, offset), mask)

    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer

@bot.command(name="روليت")
async def roulette_game(ctx):
    if not check_admin(ctx):
        return await ctx.send("ليس لديك رول الإدارة المخصص لاستخدام هذا الأمر.", delete_after=5)
    
    session = RouletteGameSession(ctx)
    view = RouletteMainView(session)
    
    embed = discord.Embed(title="روليت", description="عدد اللاعبين: 0/50\nستبدأ اللعبة خلال 43 ثانية...", color=0x000000)
    msg = await ctx.send(embed=embed, view=view)
    
    for remaining in range(43, 0, -1):
        embed.description = f"عدد اللاعبين: {len(session.players)}/50\nستبدأ اللعبة خلال {remaining} seconds ..."
        try:
            await msg.edit(embed=embed)
        except:
            pass
        await asyncio.sleep(1)
        
    if len(session.players) < 2:
        return await ctx.send("❌ تم إلغاء الروليت لعدم اكتمال عدد اللاعبين.")
    
    await ctx.send("بدأ التحدي وتصفيات الروليت!")
    active_players = list(session.players)
    
    while len(active_players) > 1:
        attacker = random.choice(active_players)
        targets = [p for p in active_players if p != attacker]
        if not targets:
            break
        victim = random.choice(targets)
        
        try:
            avatar_bytes = await victim.display_avatar.read()
        except:
            avatar_bytes = None
            
        wheel_buffer = generate_roulette_image(active_players, avatar_bytes)
        file = discord.File(wheel_buffer, filename="roulette.png")
        await ctx.send(file=file)
        
        v_inv = user_inventory.setdefault(victim.id, {"bomb": 0, "shield": 0, "attack": 0})
        if v_inv["shield"] > 0:
            v_inv["shield"] -= 1
            await ctx.send(f"درع الحماية أنقذ {victim.mention}!")
            continue
            
        if v_inv["attack"] > 0:
            v_inv["attack"] -= 1
            active_players.remove(attacker)
            await ctx.send(f"انعكس الهجوم وانطرد {attacker.mention}!")
            continue
            
        active_players.remove(victim)
        await ctx.send(f"تم استبعاد {victim.mention} من الجولة.")
        await asyncio.sleep(2)
        
    winner = active_players[0]
    win_embed = discord.Embed(title="🏆 الفائز في الروليت!", description=f"مبروك الفوز يا {winner.mention}!", color=0xffd700)
    win_embed.set_image(url=winner.display_avatar.url)
    await ctx.send(embed=win_embed)

# ==================== تشغيل البوت ====================
if __name__ == "__main__":
    keep_alive()
    TOKEN = os.getenv("DISCORD_TOKEN")
    if not TOKEN:
        print("خطأ: يرجى تعيين رمز البوت (DISCORD_TOKEN) في بيئة التشغيل.")
    else:
        bot.run(TOKEN)