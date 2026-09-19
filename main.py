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

def add_months(sourcedate, months):
    month = sourcedate.month - 1 + months
    year = sourcedate.year + month // 12
    month = month % 12 + 1
    days_in_month = [31, 29 if (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    day = min(sourcedate.day, days_in_month[month-1])
    return sourcedate.replace(year=year, month=month, day=day)
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

@bot.command(name="n")
@commands.has_any_role(1550711376995950592, 1513635397568303174, 1513655552700317926)
async def distribute_points(ctx, points: int, member: discord.Member):
    points_data = load_json(POINTS_FILE)
    user_id = str(member.id)
    current_points = points_data.get(user_id, 0)
    points_data[user_id] = current_points + points
    save_json(POINTS_FILE, points_data)
    await ctx.send(f"✅ تم إضافة `{points}` نقطة لـ {member.mention}. رصيده الحالي: `{points_data[user_id]}` نقطة.")

@distribute_points.error
async def distribute_points_error(ctx, error):
    if isinstance(error, commands.MissingAnyRole):
        await ctx.send("عذراً، لا تمتلك الصلاحية لتوزيع النقاط.", delete_after=5)
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("الاستخدام الصحيح: `-n <النقاط> @العضو`", delete_after=5)
class RouletteJoinView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=30)
        self.players = []

    @discord.ui.button(label="انضمام للروليت 🎲", style=discord.ButtonStyle.green)
    async def join_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user in self.players:
            await interaction.response.send_message("أنت منضم بالفعل!", ephemeral=True)
        else:
            self.players.append(interaction.user)
            await interaction.response.send_message("✅ تم انضمامك للروليت بنجاح!", ephemeral=True)

@bot.command(name="روليت")
@commands.has_any_role(1550711376995950592, 1513635397568303174)
async def roulette_game(ctx):
    view = RouletteJoinView()
    msg = await ctx.send("🎮 **بدأت لعبة الروليت التفاعلية!** اضغط على الزر أدناه للانضمام (الوقت المتبقي: 30 ثانية):", view=view)
    
    await asyncio.sleep(30)
    
    for child in view.children:
        child.disabled = True
    try:
        await msg.edit(view=view)
    except Exception:
        pass

    players = view.players
    if len(players) < 2:
        await ctx.send("❌ لا يوجد عدد كافٍ من اللاعبين لبدء الروليت (يجب أن يكونوا 2 على الأقل).")
        return

    await ctx.send(f"🎲 **بدأت المعركة بين {len(players)} لاعبين!** سيتناوبون على طرد بعضهم البعض حتى يبقى فائز واحد.")
    
    while len(players) > 1:
        current_player = players[0]
        
        class EliminateSelect(discord.ui.Select):
            def __init__(self):
                opts = [discord.SelectOption(label=p.display_name, value=str(p.id)) for p in players if p.id != current_player.id]
                super().__init__(placeholder=f"دور {current_player.display_name} - اختر شخصاً لطرده", options=opts)
            
            async def callback(self, interaction: discord.Interaction):
                if interaction.user.id != current_player.id:
                    await interaction.response.send_message("❌ ليس دورك الآن!", ephemeral=True)
                    return
                target_id = int(self.values[0])
                target = discord.utils.get(players, id=target_id)
                if target:
                    players.remove(target)
                    self.view.selected_target = target
                    await interaction.response.send_message(f"❌ قام {current_player.mention} بطرد {target.mention} من اللعبة! 🚪", ephemeral=False)
                    self.view.stop()

        class EliminateView(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=25)
                self.selected_target = None
                self.add_item(EliminateSelect())
            
            async def on_timeout(self):
                self.selected_target = None
                self.stop()

        elim_view = EliminateView()
        await ctx.send(f"⏳ دور اللاعب {current_player.mention}: لديك 25 ثانية لاختيار شخص لطرده!", view=elim_view)
        
        await elim_view.wait()
        
        if elim_view.selected_target is None and current_player in players:
            other_players = [p for p in players if p.id != current_player.id]
            if other_players:
                eliminated = random.choice(other_players)
                players.remove(eliminated)
                await ctx.send(f"⏰ انتهى وقت {current_player.mention}! تم طرد {eliminated.mention} تلقائياً.")
        
        if current_player in players:
            players.append(players.pop(0))
        
        await asyncio.sleep(2)

    winner = players[0]
    points_data = load_json(POINTS_FILE)
    w_id = str(winner.id)
    points_data[w_id] = points_data.get(w_id, 0) + 50
    save_json(POINTS_FILE, points_data)

    await ctx.send(f"👑 **انتهت اللعبة! الفائز الأخير هو {winner.mention}** وحصل على 50 نقطة 🎉")

@roulette_game.error
async def roulette_error(ctx, error):
    if isinstance(error, commands.MissingAnyRole):
        await ctx.send("عذراً، لا تمتلك الرول المطلوب لبدء الروليت.", delete_after=5)
class MuteReasonSelect(discord.ui.Select):
    def __init__(self, member: discord.Member):
        self.target_member = member
        options = [
            discord.SelectOption(label="سبب مشاكل", description="ميوت لمدة 15 دقيقة", emoji="⚠️", value="15"),
            discord.SelectOption(label="طاري اهل", description="ميوت لمدة 40 دقيقة", emoji="🚫", value="40"),
            discord.SelectOption(label="سب", description="ميوت لمدة 64 دقيقة", emoji="🛑", value="64"),
            discord.SelectOption(label="قذف", description="ميوت لمدة 120 دقيقة", emoji="⏳", value="120")
        ]
        super().__init__(placeholder="اختر سبب الاسكات...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        minutes = int(self.values[0])
        reason = [o.label for o in self.options if o.value == self.values[0]][0]
        
        try:
            duration = timedelta(minutes=minutes)
            await self.target_member.timeout(duration, reason=reason)
            await interaction.response.send_message(f"✅ تم إسكات {self.target_member.mention} لمدة {minutes} دقيقة بسبب: **{reason}**", ephemeral=False)
        except Exception as e:
            await interaction.response.send_message(f"❌ حدث خطأ أثناء تطبيق الإسكات: {e}", ephemeral=True)

class MuteReasonView(discord.ui.View):
    def __init__(self, member: discord.Member):
        super().__init__(timeout=60)
        self.add_item(MuteReasonSelect(member))

@bot.command(name="اسكت")
@commands.has_any_role(1550711376995950592, 1513655552700317926, 1513655846968496128, 1513655977931702322)
async def askat(ctx, member: discord.Member):
    view = MuteReasonView(member)
    await ctx.send(f"اختر سبب إسكات العضو {member.mention}:", view=view)

@askat.error
async def askat_error(ctx, error):
    if isinstance(error, commands.MissingAnyRole):
        await ctx.send("عذراً، لا تمتلك الصلاحية لاستخدام أمر `!اسكت`.", delete_after=5)
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("الاستخدام الصحيح: `!اسكت @العضو`", delete_after=5)

@bot.command(name="تكلم")
@commands.has_any_role(1513655977931702322, 1513635397568303174, 1513655846968496128, 1550711376995950592, 1513655552700317926)
async def talk(ctx, member: discord.Member):
    try:
        await member.timeout(None, reason="فك الاسكات بواسطة المشرف")
        await ctx.send(f"✅ تم فك الإسكات عن {member.mention} بنجاح.")
    except Exception as e:
        await ctx.send(f"❌ حدث خطأ: {e}", delete_after=5)

@talk.error
async def talk_error(ctx, error):
    if isinstance(error, commands.MissingAnyRole):
        await ctx.send("عذراً، لا تمتلك الصلاحية لاستخدام أمر `!تكلم`.", delete_after=5)

class VoiceMuteReasonSelect(discord.ui.Select):
    def __init__(self, member: discord.Member):
        self.target_member = member
        options = [
            discord.SelectOption(label="سبب مشاكل", description="ميوت صوتي", emoji="⚠️", value="سبب مشاكل"),
            discord.SelectOption(label="طاري اهل", description="ميوت صوتي", emoji="🚫", value="طاري اهل"),
            discord.SelectOption(label="سب", description="ميوت صوتي", emoji="🛑", value="سب"),
            discord.SelectOption(label="قذف", description="ميوت صوتي", emoji="⏳", value="قذف")
        ]
        super().__init__(placeholder="اختر سبب الميوت الصوتي...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        reason = self.values[0]
        if not self.target_member.voice or not self.target_member.voice.channel:
            await interaction.response.send_message(f"❌ العضو {self.target_member.mention} ليس في روم صوتي.", ephemeral=True)
            return
        try:
            await self.target_member.edit(mute=True, reason=reason)
            await interaction.response.send_message(f"✅ تم عمل ميوت صوتي لـ {self.target_member.mention} بسبب: **{reason}**", ephemeral=False)
        except Exception as e:
            await interaction.response.send_message(f"❌ حدث خطأ أثناء تطبيق الميوت الصوتي: {e}", ephemeral=True)

class VoiceMuteReasonView(discord.ui.View):
    def __init__(self, member: discord.Member):
        super().__init__(timeout=60)
        self.add_item(VoiceMuteReasonSelect(member))

@bot.command(name="ميوت")
@commands.has_any_role(1513655977931702322, 1513655846968496128, 1513635397568303174, 1513655552700317926)
async def voice_mute(ctx, member: discord.Member):
    view = VoiceMuteReasonView(member)
    await ctx.send(f"اختر سبب الميوت الصوتي للعضو {member.mention}:", view=view)

@voice_mute.error
async def voice_mute_error(ctx, error):
    if isinstance(error, commands.MissingAnyRole):
        await ctx.send("عذراً، لا تمتلك الصلاحية للميوت الصوتي.", delete_after=5)

@bot.command(name="فك")
@commands.has_any_role(1513655552700317926, 1513635397568303174, 1513655846968496128, 1513655977931702322)
async def voice_unmute(ctx, member: discord.Member):
    if not member.voice or not member.voice.channel:
        await ctx.send(f"❌ العضو {member.mention} ليس في روم صوتي.", delete_after=5)
        return
    try:
        await member.edit(mute=False, reason="فك الميوت الصوتي بواسطة المشرف")
        await ctx.send(f"✅ تم فك الميوت الصوتي عن {member.mention}")
    except Exception as e:
        await ctx.send(f"❌ حدث خطأ: {e}", delete_after=5)

@voice_unmute.error
async def voice_unmute_error(ctx, error):
    if isinstance(error, commands.MissingAnyRole):
        await ctx.send("عذراً، لا تمتلك الصلاحية لفك الميوت الصوتي.", delete_after=5)

@bot.command(name="سحب")
async def drag_member(ctx, member: discord.Member):
    if not ctx.author.voice or not ctx.author.voice.channel:
        await ctx.send("❌ يجب أن تكون في روم صوتي لتتمكن من سحب الأعضاء.", delete_after=5)
        return
    if not member.voice or not member.voice.channel:
        await ctx.send(f"❌ العضو {member.mention} ليس في أي روم صوتي.", delete_after=5)
        return
    
    target_channel = ctx.author.voice.channel
    try:
        await member.move_to(target_channel, reason=f"سحب بواسطة {ctx.author}")
        await ctx.send(f"✅ تم سحب {member.mention} إلى رومك الصوتي بنجاح.")
    except Exception as e:
        await ctx.send(f"❌ حدث خطأ أثناء السحب: {e}", delete_after=5)
@bot.command(name="ش")
async def play_music(ctx, *, query: str):
    if not ctx.author.voice or not ctx.author.voice.channel:
        await ctx.send("❌ يجب أن تكون متصلاً بروم صوتي لتشغيل الأغاني.", delete_after=5)
        return

    voice_channel = ctx.author.voice.channel
    if ctx.voice_client is None:
        try:
            vc = await voice_channel.connect()
        except Exception as e:
            await ctx.send(f"❌ لم أتمكن من الاتصال بالروم: {e}", delete_after=5)
            return
    else:
        vc = ctx.voice_client

    await ctx.send(f"🔍 جاري البحث والتشغيل لـ: `{query}` ...")

    ydl_opts = {'format': 'bestaudio', 'noplaylist': True}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch:{query}", download=False)
            if 'entries' in info:
                info = info['entries'][0]
            url = info['url']
            title = info.get('title', 'أغنية')

        FFMPEG_OPTIONS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}
        source = discord.FFmpegPCMAudio(url, **FFMPEG_OPTIONS)
        
        if vc.is_playing():
            vc.stop()
            
        vc.play(source, after=lambda e: print(f'Player error: {e}') if e else None)
        await ctx.send(f"🎶 يتم الآن تشغيل: **{title}**")
    except Exception as e:
        await ctx.send(f"❌ حدث خطأ أثناء تشغيل الأغنية: {e}", delete_after=5)

@bot.command(name="لايك")
@commands.has_role(1513635397568303174)
async def set_like_emoji(ctx, emoji: str):
    settings = load_json(SETTINGS_FILE)
    settings["like_emoji"] = emoji
    save_json(SETTINGS_FILE, settings)
    await ctx.send(f"✅ تم تحديث إيموجي التقييم/اللايك إلى: {emoji}")

@set_like_emoji.error
async def set_like_emoji_error(ctx, error):
    if isinstance(error, commands.MissingRole):
        await ctx.send("عذراً، لا تمتلك الصلاحية لتغيير إيموجي اللايك.", delete_after=5)

@bot.command(name="تقيم")
async def rate_profile(ctx):
    user = ctx.author
    avatar_asset = user.display_avatar.with_size(512)
    avatar_bytes = await avatar_asset.read()
    
    banner_bytes = avatar_bytes
    if user.banner:
        banner_asset = user.banner.with_size(512)
        banner_bytes = await banner_asset.read()

    card_io = await generate_profile_card(avatar_bytes, banner_bytes)
    
    try:
        await ctx.message.delete()
    except Exception:
        pass

    file = discord.File(card_io, filename="profile_rating.png")
    sent_msg = await ctx.send(file=file)

    settings = load_json(SETTINGS_FILE)
    emoji = settings.get("like_emoji", "❤️")
    try:
        await sent_msg.add_reaction(emoji)
    except Exception:
        pass

keep_alive()
bot.run(os.getenv("DISCORD_TOKEN"))
