import asyncio
import datetime
import io
import json
import os
import random
import aiohttp
import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFilter, ImageFont

POINTS_FILE = "points.json"


def load_json(filename):
  if not os.path.exists(filename):
    return {}
  with open(filename, "r", encoding="utf-8") as f:
    try:
      return json.load(f)
    except:
      return {}


def save_json(filename, data):
  with open(filename, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=4)
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
@bot.command(name="تقيم")
async def rate_profile(ctx, member: discord.Member = None):
  if member is None:
    member = ctx.author

  user = await bot.fetch_user(member.id)
  loading_msg = await ctx.send("جاري تصميم بطاقة البروفايل...")

  async with aiohttp.ClientSession() as session:
    avatar_url = (
        user.display_avatar.with_size(512).url
        if user.display_avatar
        else None
    )
    avatar_image = None
    if avatar_url:
      async with session.get(avatar_url) as resp:
        if resp.status == 200:
          avatar_image = Image.open(io.BytesIO(await resp.read())).convert(
              "RGBA"
          )

    banner_url = user.banner.with_size(512).url if user.banner else None
    banner_image = None
    if banner_url:
      async with session.get(banner_url) as resp:
        if resp.status == 200:
          banner_image = Image.open(io.BytesIO(await resp.read())).convert(
              "RGBA"
          )

  card_width, card_height = 700, 400
  card = Image.new("RGBA", (card_width, card_height), (35, 39, 42, 255))
  draw = ImageDraw.Draw(card)

  if banner_image:
    banner_image = banner_image.resize((card_width, 180))
    card.paste(banner_image, (0, 0))
  else:
    draw.rectangle([0, 0, card_width, 180], fill=(88, 101, 242, 255))

  draw.rectangle([0, 180, card_width, card_height], fill=(47, 49, 54, 255))

  if avatar_image:
    avatar_image = avatar_image.resize((120, 120))
    mask = Image.new("L", (120, 120), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.ellipse((0, 0, 120, 120), fill=255)
    card.paste(avatar_image, (30, 120), mask)

  try:
    font_name = ImageFont.truetype("arial.ttf", 28)
    font_sub = ImageFont.truetype("arial.ttf", 18)
  except:
    font_name = ImageFont.load_default()
    font_sub = ImageFont.load_default()

  draw.text(
      (170, 230), f"الاسم: {user.name}", fill=(255, 255, 255, 255), font=font_name
  )
  draw.text(
      (170, 270),
      f"الاسم الظاهر: {member.display_name}",
      fill=(185, 187, 190, 255),
      font=font_sub,
  )

  buffer = io.BytesIO()
  card.save(buffer, format="PNG")
  buffer.seek(0)

  file = discord.File(buffer, filename="profile_card.png")
  await ctx.send(file=file)
  await loading_msg.delete()
class RouletteShopView(discord.ui.View):

  def __init__(self):
    super().__init__(timeout=30)
    self.players = []
    self.inventory = {}

  @discord.ui.button(label="انضمام للروليت", style=discord.ButtonStyle.green, row=0)
  async def join_btn(
      self, interaction: discord.Interaction, button: discord.ui.Button
  ):
    user = interaction.user
    if user not in self.players:
      self.players.append(user)
      if str(user.id) not in self.inventory:
        self.inventory[str(user.id)] = {
            "bomb": 0,
            "shield": False,
            "counter": False,
        }
      await interaction.response.send_message(
          "تم انضمامك للروليت بنجاح", ephemeral=True
      )
    else:
      await interaction.response.send_message(
          "أنت منضم بالفعل", ephemeral=True
      )

  @discord.ui.button(
      label="شراء قنبلة (10 نقاط)", style=discord.ButtonStyle.blurple, row=1
  )
  async def buy_bomb(
      self, interaction: discord.Interaction, button: discord.ui.Button
  ):
    user = interaction.user
    if user not in self.players:
      await interaction.response.send_message(
          "يجب الانضمام للروليت أولاً للشراء", ephemeral=True
      )
      return
    points_data = load_json(POINTS_FILE)
    uid = str(user.id)
    current_pts = points_data.get(uid, 0)
    if current_pts < 10:
      await interaction.response.send_message(
          f"نقاطك غير كافية! رصيدك: {current_pts}", ephemeral=True
      )
      return
    points_data[uid] = current_pts - 10
    save_json(POINTS_FILE, points_data)
    self.inventory[uid]["bomb"] += 1
    await interaction.response.send_message(
        f"تم شراء قنبلة بنجاح. رصيدك: {points_data[uid]}", ephemeral=True
    )

  @discord.ui.button(
      label="شراء حماية (15 نقطة)", style=discord.ButtonStyle.blurple, row=1
  )
  async def buy_shield(
      self, interaction: discord.Interaction, button: discord.ui.Button
  ):
    user = interaction.user
    if user not in self.players:
      await interaction.response.send_message(
          "يجب الانضمام للروليت أولاً للشراء", ephemeral=True
      )
      return
    uid = str(user.id)
    if self.inventory[uid]["shield"]:
      await interaction.response.send_message(
          "أنت تمتلك حماية بالفعل", ephemeral=True
      )
      return
    points_data = load_json(POINTS_FILE)
    current_pts = points_data.get(uid, 0)
    if current_pts < 15:
      await interaction.response.send_message(
          f"نقاطك غير كافية! رصيدك: {current_pts}", ephemeral=True
      )
      return
    points_data[uid] = current_pts - 15
    save_json(POINTS_FILE, points_data)
    self.inventory[uid]["shield"] = True
    await interaction.response.send_message(
        f"تم شراء حماية بنجاح. رصيدك: {points_data[uid]}", ephemeral=True
    )

  @discord.ui.button(
      label="شراء هجمة (12 نقطة)", style=discord.ButtonStyle.blurple, row=1
  )
  async def buy_counter(
      self, interaction: discord.Interaction, button: discord.ui.Button
  ):
    user = interaction.user
    if user not in self.players:
      await interaction.response.send_message(
          "يجب الانضمام للروليت أولاً للشراء", ephemeral=True
      )
      return
    uid = str(user.id)
    if self.inventory[uid]["counter"]:
      await interaction.response.send_message(
          "أنت تمتلك هجمة بالفعل", ephemeral=True
      )
      return
    points_data = load_json(POINTS_FILE)
    current_pts = points_data.get(uid, 0)
    if current_pts < 12:
      await interaction.response.send_message(
          f"نقاطك غير كافية! رصيدك: {current_pts}", ephemeral=True
      )
      return
    points_data[uid] = current_pts - 12
    save_json(POINTS_FILE, points_data)
    self.inventory[uid]["counter"] = True
    await interaction.response.send_message(
        f"تم شراء هجمة بنجاح. رصيدك: {points_data[uid]}", ephemeral=True
    )


@bot.command(name="روليت")
async def roulette(ctx):
  view = RouletteShopView()
  msg = await ctx.send(
      "بدأت لعبة الروليت ومتجر الأدوات! أمامك 30 ثانية للانضمام أو الشراء:",
      view=view,
  )
  await asyncio.sleep(30)
  for child in view.children:
    child.disabled = True
  try:
    await msg.edit(view=view)
  except:
    pass

  players = view.players
  inventory = view.inventory
  if len(players) < 2:
    await ctx.send("لا يوجد عدد كافٍ من اللاعبين لبدء الروليت (الحد الأدنى 2).")
    return

  await ctx.send(f"انتهى وقت التسجيل! بدأت المعركة بين {len(players)} لاعبين.")

  while len(players) > 1:
    current_player = players[0]
    uid_current = str(current_player.id)
    has_bomb = inventory.get(uid_current, {}).get("bomb", 0) > 0

    class GameActionSelect(discord.ui.Select):

      def __init__(self):
        options = []
        if has_bomb:
          options.append(
              discord.SelectOption(
                  label="استخدام قنبلة",
                  value="bomb",
                  description="طرد لاعبين اثنين عشوائياً",
              )
          )
        for p in players:
          if p.id != current_player.id:
            options.append(
                discord.SelectOption(
                    label=f"طرد {p.display_name}", value=str(p.id)
                )
            )
        super().__init__(
            placeholder=f"دور {current_player.display_name} - اختر إجراءً",
            options=options,
        )

      async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != current_player.id:
          await interaction.response.send_message(
              "ليس دورك الآن", ephemeral=True
          )
          return
        val = self.values[0]
        if val == "bomb":
          inventory[uid_current]["bomb"] -= 1
          targets = [p for p in players if p.id != current_player.id]
          eliminated_count = min(2, len(targets))
          eliminated = random.sample(targets, eliminated_count)
          for e in eliminated:
            players.remove(e)
          names = ", ".join([e.mention for e in eliminated])
          await interaction.response.send_message(
              f"قام {current_player.mention} بتفعيل القنبلة وطرد: {names}",
              ephemeral=False,
          )
        else:
          target_id = int(val)
          target = discord.utils.get(players, id=target_id)
          if target:
            t_uid = str(target.id)
            if inventory.get(t_uid, {}).get("shield", False):
              await interaction.response.send_message(
                  f"فشل الطرد! {target.mention} يمتلك درع حماية.",
                  ephemeral=False,
              )
            elif inventory.get(t_uid, {}).get("counter", False):
              players.remove(current_player)
              await interaction.response.send_message(
                  f"ارتدت الهجمة! {target.mention} لديه هجمة، فانطرد المهاجم"
                  f" {current_player.mention}!",
                  ephemeral=False,
              )
            else:
              players.remove(target)
              await interaction.response.send_message(
                  f"قام {current_player.mention} بطرد {target.mention} من"
                  " اللعبة!",
                  ephemeral=False,
              )
        self.view.stop()

    class GameActionView(discord.ui.View):

      def __init__(self):
        super().__init__(timeout=25)
        self.add_item(GameActionSelect())

      async def on_timeout(self):
        self.stop()

    action_view = GameActionView()
    await ctx.send(
        f"دور اللاعب {current_player.mention}: لديك 25 ثانية للاختيار!",
        view=action_view,
    )
    await action_view.wait()

    if current_player in players:
      players.append(players.pop(0))
    await asyncio.sleep(2)

  winner = players[0]
  loading_msg = await ctx.send("جاري تصميم بطاقة الفائز النهائي...")

  async with aiohttp.ClientSession() as session:
    avatar_url = (
        winner.display_avatar.with_size(512).url
        if winner.display_avatar
        else None
    )
    winner_avatar = None
    if avatar_url:
      async with session.get(avatar_url) as resp:
        if resp.status == 200:
          winner_avatar = Image.open(io.BytesIO(await resp.read())).convert(
              "RGBA"
          )

  width, height = 700, 400
  card = Image.new("RGBA", (width, height), (15, 15, 20, 255))
  draw = ImageDraw.Draw(card)

  try:
    font_title = ImageFont.truetype("arial.ttf", 38)
    font_server = ImageFont.truetype("arial.ttf", 34)
    font_winner = ImageFont.truetype("arial.ttf", 24)
  except:
    font_title = ImageFont.load_default()
    font_server = ImageFont.load_default()
    font_winner = ImageFont.load_default()

  draw.text((40, 25), "nylo", fill=(255, 255, 255, 255), font=font_server)
  draw.text((540, 25), "روليت", fill=(255, 255, 255, 255), font=font_title)

  if winner_avatar:
    avatar_size = 160
    winner_avatar = winner_avatar.resize((avatar_size, avatar_size))
    glow_size = avatar_size + 50
    glow = Image.new("RGBA", (glow_size, glow_size), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    glow_draw.ellipse((0, 0, glow_size, glow_size), fill=(255, 255, 255, 120))
    glow = glow.filter(ImageFilter.GaussianBlur(20))
    x_pos = (width - avatar_size) // 2
    y_pos = 110
    card.paste(glow, (x_pos - 25, y_pos - 25), glow)
    mask = Image.new("L", (avatar_size, avatar_size), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.ellipse((0, 0, avatar_size, avatar_size), fill=255)
    card.paste(winner_avatar, (x_pos, y_pos), mask)

  text_bbox = draw.textbbox((0, 0), winner.display_name, font=font_winner)
  text_width = text_bbox[2] - text_bbox[0]
  draw.text(
      ((width - text_width) // 2, 310),
      winner.display_name,
      fill=(255, 255, 255, 255),
      font=font_winner,
  )

  buffer = io.BytesIO()
  card.save(buffer, format="PNG")
  buffer.seek(0)
  file = discord.File(buffer, filename="roulette_winner.png")
  await ctx.send(
      f"مبروك الفوز! الفائز الأخير في الروليت هو: {winner.mention}", file=file
  )
  await loading_msg.delete()
class MuteCancelView(discord.ui.View):

  def __init__(self, member: discord.Member):
    super().__init__(timeout=None)
    self.member = member

  @discord.ui.button(label="إلغاء", style=discord.ButtonStyle.red)
  async def cancel_mute(
      self, interaction: discord.Interaction, button: discord.ui.Button
  ):
    try:
      await self.member.timeout(None, reason="تم إلغاء الميوت")
      for child in self.children:
        child.disabled = True
      await interaction.response.edit_message(
          content=f"تم إلغاء الميوت عن {self.member.mention}", view=self
      )
    except Exception as e:
      await interaction.response.send_message(
          f"حدث خطأ: {str(e)}", ephemeral=True
      )


@bot.command(name="اسكت")
@commands.has_permissions(moderate_members=True)
async def mute_member(ctx, member: discord.Member, minutes: int = 5):
  try:
    duration = datetime.timedelta(minutes=minutes)
    await member.timeout(
        duration, reason=f"بواسطة الأمر من قِبل {ctx.author}"
    )
    view = MuteCancelView(member)
    msg = (
        f"تم إخراس العضو {member.mention} لمدة {minutes} دقائق. اضغط على زر إلغاء"
        " لإلغاء الميوت."
    )
    await ctx.send(msg, view=view)
  except Exception as e:
    await ctx.send(f"تعذر تطبيق الميوت: {e}")
