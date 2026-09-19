import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import os
import random
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

# ==================== قاعدة بيانات مؤقتة للنقاط والخصائص ====================
# لتخزين النقاط: user_points[user_id] = points
user_points = {}
# لتخزين حقيبة اللاعبين في الروليت: inventory[user_id] = {"bomb": 0, "shield": 0, "attack": 0}
user_inventory = {}

# الإيموجيات الافتراضية لأمر !لايك (يمكن تعديلها)
default_likes = ["❤️", "🔥"]

# ==================== الأحداث الأساسية ====================
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} (ID: {bot.user.id})')
    print('Bot is ready and running!')

# ==================== 1. أوامر الإدارة والعقوبات (!اسكت, !ميوت, !فك, !تكلم) ====================
# رولات الإدارة والميوت
MUTE_ROLES = [
    1513635397568303174,
    1513655846968496128,
    1513655977931702322,
    1550711376995950592,
    1513655552700317926
]

def check_mute_role(interaction: discord.Interaction):
    return any(role.id in MUTE_ROLES for role in interaction.user.roles)

class MuteReasonView(discord.ui.View):
    def __init__(self, target_member: discord.Member, is_timeout: bool):
        super().__init__(timeout=60)
        self.target_member = target_member
        self.is_timeout = is_timeout

    async def apply_punishment(self, interaction: discord.Interaction, minutes: int, reason: str):
        if self.is_timeout:
            delta = discord.utils.utcnow() + discord.timedelta(minutes=minutes)
            await self.target_member.timeout(delta, reason=reason)
            await interaction.response.send_message(f" تم عمل `اسكت` (Timeout) للأعضاء {self.target_member.mention} بسبب **{reason}** لمدة {minutes} دقيقة.", ephemeral=True)
        else:
            await self.target_member.edit(mute=True, reason=reason)
            await interaction.response.send_message(f" تم إعطاء `ميوت` صوتي لـ {self.target_member.mention} بسبب **{reason}**.", ephemeral=True)

    @discord.ui.button(label="مشاكل (15د)", style=discord.ButtonStyle.secondary)
    async def btn_issues(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.apply_punishment(interaction, 15, "مشاكل")

    @discord.ui.button(label="السب (40د)", style=discord.ButtonStyle.secondary)
    async def btn_spam(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.apply_punishment(interaction, 40, "السب")

    @discord.ui.button(label="طاري أهل (60د)", style=discord.ButtonStyle.secondary)
    async def btn_family(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.apply_punishment(interaction, 60, "طاري أهل")

    @discord.ui.button(label="إيحاء جنسي (30د)", style=discord.ButtonStyle.secondary)
    async def btn_nsfw(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.apply_punishment(interaction, 30, "إيحاء جنسي")

    @discord.ui.button(label="القذف (120د)", style=discord.ButtonStyle.danger)
    async def btn_qadh(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.apply_punishment(interaction, 120, "القذف")

    @discord.ui.button(label="إلغاء", style=discord.ButtonStyle.success)
    async def btn_cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(" تم إلغاء الأمر.", ephemeral=True)
        self.stop()

@bot.command(name="اسكت")
async def askat(ctx, member: discord.Member = None):
    if not any(role.id in MUTE_ROLES for role in ctx.author.roles):
        return await ctx.send("ليس لديك الرول المناسب لاستخدام هذا الأمر.", delete_after=5)
    if not member:
        return await ctx.send("الرجاء منشن العضو المستهدف.")
    view = MuteReasonView(member, is_timeout=True)
    await ctx.send(f"اختر سبب `اسكت` للعضو {member.mention}:", view=view)

@bot.command(name="ميوت")
async def mute_voice(ctx, member: discord.Member = None):
    if not any(role.id in MUTE_ROLES for role in ctx.author.roles):
        return await ctx.send("ليس لديك الرول المناسب لاستخدام هذا الأمر.", delete_after=5)
    if not member:
        return await ctx.send("الرجاء منشن العضو المستهدف.")
    view = MuteReasonView(member, is_timeout=False)
    await ctx.send(f"اختر سبب `الميوت الصوتي` للعضو {member.mention}:", view=view)

@bot.command(name="فك")
async def unmute_timeout(ctx, member: discord.Member = None):
    if not any(role.id in MUTE_ROLES for role in ctx.author.roles):
        return await ctx.send("ليس لديك الرول المناسب لاستخدام هذا الأمر.", delete_after=5)
    if not member:
        return await ctx.send("الرجاء منشن العضو.")
    await member.timeout(None, reason=f"بواسطة {ctx.author}")
    await ctx.send(f" تم فك العقوبة الكتابية (Timeout) عن {member.mention}.")

@bot.command(name="تكلم")
async def unmute_voice(ctx, member: discord.Member = None):
    if not any(role.id in MUTE_ROLES for role in ctx.author.roles):
        return await ctx.send("ليس لديك الرول المناسب لاستخدام هذا الأمر.", delete_after=5)
    if not member:
        return await ctx.send("الرجاء منشن العضو.")
    await member.edit(mute=False, reason=f"بواسطة {ctx.author}")
    await ctx.send(f" تم فك الميوت الصوتي عن {member.mention}.")


# ==================== 2. أمر المسح (!مسح) ====================
@bot.command(name="مسح")
@commands.has_permissions(manage_messages=True)
async def purge(ctx, amount: int = 10):
    await ctx.channel.purge(limit=amount + 1)
    msg = await ctx.send(f" تم مسح {amount} رسالة بنجاح.", delete_after=3)


# ==================== 3. أمر النشر (!نشر مع زر Br الأسود) ====================
PUBLISH_ROLES = [
    1513635397568303174,
    1513655846968496128,
    1513655977931702322,
    1550705477485068348
]

class BrButtonView(discord.ui.View):
    def __init__(self, banner_url: str, avatar_url: str):
        super().__init__(timeout=None)
        self.banner_url = banner_url
        self.avatar_url = avatar_url

    @discord.ui.button(label="Br", style=discord.ButtonStyle.secondary, custom_id="br_button")
    async def br_action(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title="معاينة البروفايل (Banner & Avatar)", color=0x000000)
        if self.banner_url:
            embed.set_image(url=self.banner_url)
        if self.avatar_url:
            embed.set_thumbnail(url=self.avatar_url)
        embed.set_footer(text=f"بواسطة: {interaction.user.name}", icon_url=interaction.user.display_avatar.url)
        await interaction.response.send_message(embed=embed, ephemeral=False)

@bot.command(name="نشر")
async def nashir(ctx, banner_url: str = None, avatar_url: str = None):
    if not any(role.id in PUBLISH_ROLES for role in ctx.author.roles):
        return await ctx.send("ليس لديك الصلاحية لاستخدام أمر النشر.", delete_after=5)
    if not banner_url or not avatar_url:
        return await ctx.send("الرجاء إرفاق رابط البنر ورابط الأفتار بالشكل الصحيح مع الأمر.")
    
    view = BrButtonView(banner_url, avatar_url)
    embed = discord.Embed(description="اختر زر **Br** أدناه لعرض البروفايل بالكامل:", color=0x000000)
    embed.set_image(url=banner_url)
    embed.set_thumbnail(url=avatar_url)
    await ctx.send(embed=embed, view=view)


# ==================== 4. أمر التقيم واللايك (!تقيم, !لايك) ====================
@bot.command(name="لايك")
async def custom_likes(ctx, like1: str = None, like2: str = None):
    if not any(role.id == 1513635397568303174 for role in ctx.author.roles):
        return await ctx.send("ليس لديك رول استخدام أمر !لايك.", delete_after=5)
    if not like1 or not like2:
        return await ctx.send("الرجاء تحديد إيموجيين (مثال: `-لايك 👍 ❤️`).")
    global default_likes
    default_likes = [like1, like2]
    await ctx.send(f" تم تحديث إيموجيات اللايك التلقائية لتصبح: {like1} و {like2}")

@bot.command(name="تقيم")
async def taqeem(ctx, member: discord.Member = None):
    target = member or ctx.author
    embed = discord.Embed(title=f"تقييم البروفايل: {target.name}", color=0x2b2d31)
    embed.set_thumbnail(url=target.display_avatar.url)
    if target.banner:
        embed.set_image(url=target.banner.url)
    embed.add_field(name="الاسم", value=target.mention, inline=True)
    
    msg = await ctx.send(embed=embed)
    for emoji in default_likes:
        try:
            await msg.add_reaction(emoji)
        except:
            pass


# ==================== 5. نظام النقاط والتوزيع (-n) ====================
POINTS_ROLES = [
    1513635397568303174,
    1513655552700317926,
    1513655846968496128,
    1513655977931702322
]

@bot.command(name="n")
async def distribute_points(ctx, amount: int = 0, member: discord.Member = None):
    if not any(role.id in POINTS_ROLES for role in ctx.author.roles):
        return await ctx.send("ليس لديك الصلاحية لتوزيع النقاط.", delete_after=5)
    if not member or amount <= 0:
        return await ctx.send("الاستخدام الصحيح: `-n [الرقم] [@العضو]`")
    
    user_points[member.id] = user_points.get(member.id, 0) + amount
    await ctx.send(f" تم إضافة `{amount}` نقطة إلى العضو {member.mention}. رصيده الحالي: `{user_points[member.id]}` نقطة.")


# ==================== 6. أمر سحب الأعضاء (-سحب) ====================
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
        await ctx.send(f" تم سحب العضو {member.mention} إلى رومك الصوتي بنجاح.")
    except Exception as e:
        await ctx.send(f" حدث خطأ أثناء محاولة سحب العضو: {e}")


# ==================== 7. تشغيل الأغاني (ش [اسم الاغنيه]) ====================
@bot.command(name="ش")
async def play_song(ctx, *, song_name: str = None):
    if not ctx.author.voice:
        return await ctx.send("يجب أن تكون متصلاً بروم صوتي لتشغيل الأغاني!")
    if not song_name:
        return await ctx.send("الرجاء كتابة اسم الأغنية أو الرابط بعد الأمر (مثال: `ش [اسم الاغنيه]`).")
    
    voice_channel = ctx.author.voice.channel
    if not ctx.voice_client:
        await voice_channel.connect()
    
    await ctx.send(f" جاري البحث عن وتجهيز الأغنية: **{song_name}** 🎵")


# ==================== 8. لعبة الروليت المتقدمة (!روليت) ====================
ROULETTE_ROLES = [
    1513635397568303174,
    1513655552700317926,
    1513655846968496128,
    1550711376995950592
]

class RouletteShopView(discord.ui.View):
    def __init__(self, user_id: int):
        super().__init__(timeout=60)
        self.user_id = user_id

    @discord.ui.button(label="قنبلة (10 نقاط)", style=discord.ButtonStyle.danger)
    async def buy_bomb(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("هذا المتجر ليس لك!", ephemeral=True)
        pts = user_points.get(self.user_id, 0)
        if pts < 10:
            return await interaction.response.send_message("ليس لديك نقاط كافية لشراء القنبلة (تحتاج 10 نقاط).", ephemeral=True)
        user_points[self.user_id] -= 10
        inv = user_inventory.setdefault(self.user_id, {"bomb": 0, "shield": 0, "attack": 0})
        inv["bomb"] += 1
        await interaction.response.send_message(" اشتريت **قنبلة** بنجاح!", ephemeral=True)

    @discord.ui.button(label="حماية (15 نقطة)", style=discord.ButtonStyle.primary)
    async def buy_shield(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("هذا المتجر ليس لك!", ephemeral=True)
        pts = user_points.get(self.user_id, 0)
        if pts < 15:
            return await interaction.response.send_message("ليس لديك نقاط كافية لشراء الحماية (تحتاج 15 نقطة).", ephemeral=True)
        user_points[self.user_id] -= 15
        inv = user_inventory.setdefault(self.user_id, {"bomb": 0, "shield": 0, "attack": 0})
        inv["shield"] += 1
        await interaction.response.send_message(" اشتريت **درع حماية** بنجاح!", ephemeral=True)

    @discord.ui.button(label="هجمة عكسية (18 نقطة)", style=discord.ButtonStyle.success)
    async def buy_attack(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("هذا المتجر ليس لك!", ephemeral=True)
        pts = user_points.get(self.user_id, 0)
        if pts < 18:
            return await interaction.response.send_message("ليس لديك نقاط كافية لشراء الهجمة (تحتاج 18 نقطة).", ephemeral=True)
        user_points[self.user_id] -= 18
        inv = user_inventory.setdefault(self.user_id, {"bomb": 0, "shield": 0, "attack": 0})
        inv["attack"] += 1
        await interaction.response.send_message(" اشتريت **هجمة عكسية** بنجاح!", ephemeral=True)

class RouletteMainView(discord.ui.View):
    def __init__(self, game_session):
        super().__init__(timeout=None)
        self.game_session = game_session

    @discord.ui.button(label="دخول", style=discord.ButtonStyle.success, emoji="📥")
    async def join_game(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user in self.game_session.players:
            return await interaction.response.send_message("أنت منضم مسبقاً في اللعبة!", ephemeral=True)
        self.game_session.players.append(interaction.user)
        await interaction.response.send_message(f" انضمرت إلى لعبة الروليت بنجاح! (عدد اللاعبين: {len(self.game_session.players)})", ephemeral=True)

    @discord.ui.button(label="متجر الخصائص", style=discord.ButtonStyle.secondary, emoji="🛒")
    async def open_shop(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = RouletteShopView(interaction.user.id)
        await interaction.response.send_message(" مرحباً بك في متجر الروليت! اختر ما تريد شراءه:", view=view, ephemeral=True)

    @discord.ui.button(label="الحقيبه", style=discord.ButtonStyle.secondary, emoji="🎒")
    async def open_inventory(self, interaction: discord.Interaction, button: discord.ui.Button):
        inv = user_inventory.get(interaction.user.id, {"bomb": 0, "shield": 0, "attack": 0})
        await interaction.response.send_message(f" حقيبتك:\n💣 قنابل: {inv['bomb']}\n🛡️ دروع حماية: {inv['shield']}\n⚔️ هجمات عكسية: {inv['attack']}", ephemeral=True)

    @discord.ui.button(label="احصائيات", style=discord.ButtonStyle.secondary, emoji="ℹ️")
    async def open_stats(self, interaction: discord.Interaction, button: discord.ui.Button):
        pts = user_points.get(interaction.user.id, 0)
        await interaction.response.send_message(f" نقاطك الحالية: `{pts}` نقطة.", ephemeral=True)

class RouletteGameSession:
    def __init__(self, ctx):
        self.ctx = ctx
        self.players = []

@bot.command(name="روليت")
async def roulette_game(ctx):
    if not any(role.id in ROULETTE_ROLES for role in ctx.author.roles):
        return await ctx.send("ليس لديك الرول المناسب لبدء لعبة الروليت.", delete_after=5)
    
    session = RouletteGameSession(ctx)
    view = RouletteMainView(session)
    
    embed = discord.Embed(title="روليت", description="عدد اللاعبين: 0/50\nستبدأ اللعبة خلال 43 ثانية...", color=0x000000)
    msg = await ctx.send(embed=embed, view=view)
    
    # عد تنازلي لمدة 43 ثانية لانضمام اللاعبين
    for remaining in range(43, 0, -1):
        embed.description = f"عدد اللاعبين: {len(session.players)}/50\nستبدأ اللعبة خلال {remaining} seconds ..."
        try:
            await msg.edit(embed=embed)
        except:
            pass
        await asyncio.sleep(1)
        
    if len(session.players) < 2:
        return await ctx.send("❌ تم إلغاء الروليت لعدم اكتمال عدد اللاعبين (يجب لاعبين اثنين على الأقل).")
    
    await ctx.send(" بدأ التحدي وتصفيات الروليت!")
    
    active_players = list(session.players)
    
    while len(active_players) > 1:
        attacker = random.choice(active_players)
        targets = [p for p in active_players if p != attacker]
        if not targets:
            break
        victim = random.choice(targets)
        
        # فحص الحماية لدى الضحية
        v_inv = user_inventory.setdefault(victim.id, {"bomb": 0, "shield": 0, "attack": 0})
        if v_inv["shield"] > 0:
            v_inv["shield"] -= 1
            await ctx.send(f"🛡️ حاول {attacker.mention} طرد {victim.mention}، لكن درع الحماية أنقذه!")
            continue
            
        # فحص الهجمة العكسية
        if v_inv["attack"] > 0:
            v_inv["attack"] -= 1
            active_players.remove(attacker)
            await ctx.send(f"⚔️ استخدم {victim.mention} هجمة عكسية، فانعكس الطرد وانطرد المهاجم {attacker.mention}!")
            continue
            
        # الطرد العادي أو القنبلة
        a_inv = user_inventory.setdefault(attacker.id, {"bomb": 0, "shield": 0, "attack": 0})
        if a_inv["bomb"] > 0:
            a_inv["bomb"] -= 1
            # طرد شخصين إذا تفرتو
            active_players.remove(victim)
            removed_count = 1
            if active_players:
                victim2 = random.choice([p for p in active_players if p != attacker])
                active_players.remove(victim2)
                removed_count = 2
            await ctx.send(f"💣 استخدم {attacker.mention} **قنبلة** وأطاح بـ {removed_count} من اللاعبين!")
        else:
            active_players.remove(victim)
            await ctx.send(f"❌ قام {attacker.mention} بطرد {victim.mention} من الجولة.")
            
        await asyncio.sleep(2)
        
    winner = active_players[0]
    win_embed = discord.Embed(title="🏆 الفائز في الروليت!", description=f"مبروك الفوز يا {winner.mention}!", color=0xffd700)
    win_embed.set_image(url=winner.display_avatar.url)
    await ctx.send(embed=win_embed)

# ==================== تشغيل البوت ====================
if __name__ == "__main__":
    keep_alive()
    TOKEN = os.getenv("DISCORD_TOKEN")  # ضع التوكن هنا أو في متغيرات البيئة على Render
    if not TOKEN:
        print("خطأ: يرجى تعيين رمز البوت (DISCORD_TOKEN) في بيئة التشغيل.")
    else:
        bot.run(TOKEN)