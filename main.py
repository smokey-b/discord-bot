import discord
from discord.ext import commands
import random
import json
import os
import time

# ================= CONFIG =================
ADMIN_USER_ID = 980819870495166474  # 🔴 PUT YOUR DISCORD ID HERE

# ================= SETUP =================
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ================= DATA SYSTEM =================
def load_data():
    if not os.path.exists("data.json"):
        return {}
    try:
        with open("data.json", "r") as f:
            return json.load(f)
    except:
        return {}

def save_data(data):
    with open("data.json", "w") as f:
        json.dump(data, f)

def get_user(user_id):
    data = load_data()
    user_id = str(user_id)

    if user_id not in data:
        data[user_id] = {
            "coins": 1000,
            "last_daily": 0
        }
        save_data(data)

    return data[user_id]

def update_user(user_id, user_data):
    data = load_data()
    data[str(user_id)] = user_data
    save_data(data)

# ================= SHOP =================
shop = {
    "xanax": 5000,
    "donator pack": 70000,
    "Test": 1,
}

# ================= BLACKJACK HELPERS =================
def draw_card():
    return random.randint(1, 11)

def hand_value(hand):
    return sum(hand)

# ================= BLACKJACK BUTTONS =================
class BlackjackView(discord.ui.View):
    def __init__(self, ctx, player, dealer, bet, user_data):
        super().__init__(timeout=30)
        self.ctx = ctx
        self.player = player
        self.dealer = dealer
        self.bet = bet
        self.user_data = user_data
        self.ended = False

    async def finish(self, interaction, text, change):
        if self.ended:
            return
        self.ended = True

        self.user_data["coins"] += change
        update_user(self.ctx.author.id, self.user_data)

        for item in self.children:
            item.disabled = True

        await interaction.response.edit_message(content=text, view=self)
        self.stop()

    @discord.ui.button(label="Hit", style=discord.ButtonStyle.green)
    async def hit(self, interaction: discord.Interaction, button: discord.ui.Button):

        if interaction.user != self.ctx.author:
            await interaction.response.send_message("Not your game!", ephemeral=True)
            return

        self.player.append(draw_card())

        if hand_value(self.player) > 21:
            await self.finish(interaction, f"You bust! ❌\n{self.player}", -self.bet)
        else:
            await interaction.response.edit_message(
                content=f"Your hand: {self.player} ({hand_value(self.player)})\nDealer: {self.dealer[0]}",
                view=self
            )

    @discord.ui.button(label="Stand", style=discord.ButtonStyle.red)
    async def stand(self, interaction: discord.Interaction, button: discord.ui.Button):

        if interaction.user != self.ctx.author:
            await interaction.response.send_message("Not your game!", ephemeral=True)
            return

        while hand_value(self.dealer) < 17:
            self.dealer.append(draw_card())

        p = hand_value(self.player)
        d = hand_value(self.dealer)

        if d > 21 or p > d:
            await self.finish(interaction, f"You win! 🎉 Dealer: {self.dealer}", self.bet)
        elif p == d:
            await self.finish(interaction, f"Tie! Dealer: {self.dealer}", 0)
        else:
            await self.finish(interaction, f"You lose! ❌ Dealer: {self.dealer}", -self.bet)

# ================= EVENTS =================
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

# ================= COMMANDS =================

@bot.command()
async def balance(ctx):
    user = get_user(ctx.author.id)
    msg = await ctx.send(f"{ctx.author.name}, you have {user['coins']} coins 💰")
    await msg.delete(delay=10)
    await ctx.message.delete(delay=10)

@bot.command()
async def daily(ctx):
    user = get_user(ctx.author.id)
    now = time.time()

    if now - user["last_daily"] < 86400:
        await ctx.send("Come back later.", delete_after=5)
        return

    user["coins"] += 1000
    user["last_daily"] = now
    update_user(ctx.author.id, user)

    await ctx.send("You got 1000 coins 🎁", delete_after=5)

@bot.command()
async def shop_cmd(ctx):
    msg = "**🛒 Shop:**\n"
    for item, price in shop.items():
        msg += f"{item} - {price}\n"
    await ctx.send(msg, delete_after=10)

@bot.command()
async def buy(ctx, *, item: str):
    item = item.lower().strip()

    if item not in shop:
        await ctx.send("Item not found.", delete_after=5)
        return

    user = get_user(ctx.author.id)
    price = shop[item]

    if user["coins"] < price:
        await ctx.send("Not enough coins.", delete_after=5)
        return

    user["coins"] -= price
    update_user(ctx.author.id, user)

    await ctx.send(f"You bought {item}", delete_after=5)

    admin = await bot.fetch_user(ADMIN_USER_ID)
    await admin.send(f"{ctx.author} bought {item} for {price}")

@bot.command()
async def blackjack(ctx, bet: int):
    user = get_user(ctx.author.id)

    if bet <= 0 or bet > user["coins"]:
        await ctx.send("Invalid bet.", delete_after=5)
        return

    player = [draw_card(), draw_card()]
    dealer = [draw_card(), draw_card()]

    view = BlackjackView(ctx, player, dealer, bet, user)

    await ctx.send(
        f"Your hand: {player} ({hand_value(player)})\nDealer: {dealer[0]}",
        view=view
    )

@bot.command()
async def commands(ctx):
    await ctx.send("""
!balance  
!daily  
!shop_cmd  
!buy <item>  
!blackjack <bet>  
!addcoins @user <amount>  
!clear <amount>
""", delete_after=15)

@bot.command()
async def addcoins(ctx, member: discord.Member, amount: int):

    if ctx.author.id != ADMIN_USER_ID:
        await ctx.send("No permission.", delete_after=5)
        return

    user = get_user(member.id)
    user["coins"] += amount
    update_user(member.id, user)

    await ctx.send(f"Added {amount} coins to {member.name}", delete_after=5)

@bot.command()
async def clear(ctx, amount: int = 10):

    if ctx.author.id != ADMIN_USER_ID:
        await ctx.send("No permission.")
        return

    try:
        deleted = await ctx.channel.purge(limit=amount + 1)
        msg = await ctx.send(f"Cleared {len(deleted)-1} messages")
        await msg.delete(delay=3)
    except:
        await ctx.send("Missing permissions.")

# ================= RUN =================
TOKEN = os.getenv("TOKEN")
bot.run(TOKEN)
