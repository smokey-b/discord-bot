# ================= IMPORTS =================
import discord
from discord.ext import commands
from discord.ext.commands import cooldown, BucketType
import random
import json
import os
import time

# ================= CONFIG =================
ADMIN_USER_ID = 980819870495166474
DATA_FILE = "data.json"

# ================= SETUP =================
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ================= DATA SYSTEM =================
def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

data = load_data()

def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

def get_user(user_id):
    uid = str(user_id)

    if uid not in data:
        data[uid] = {
            "coins": 1000,
            "premium_points": 0,
            "last_daily": 0,
            "inventory": {
                "xanax": 0,
                "donator pack": 0
            }
        }

    return data[uid]

def update_user(user_id, user_data):
    data[str(user_id)] = user_data
    save_data()

# ================= SHOP =================
shop = {
    "xanax": 5000,
    "donator pack": 70000
}

# ================= BLACKJACK HELPERS =================
def create_deck():
    suits = ["♠", "♥", "♦", "♣"]
    ranks = {
        "A": 11, "2": 2, "3": 3, "4": 4, "5": 5,
        "6": 6, "7": 7, "8": 8, "9": 9, "10": 10,
        "J": 10, "Q": 10, "K": 10
    }

    deck = []
    for s in suits:
        for r, v in ranks.items():
            deck.append((r, s, v))

    random.shuffle(deck)
    return deck

def hand_value(hand):
    value = sum(c[2] for c in hand)
    aces = sum(1 for c in hand if c[0] == "A")

    while value > 21 and aces:
        value -= 10
        aces -= 1

    return value

def format_hand(hand):
    return " ".join([f"{c[0]}{c[1]}" for c in hand])

# ================= BLACKJACK =================
class BlackjackView(discord.ui.View):
    def __init__(self, ctx, bet, user):
        super().__init__(timeout=120)
        self.ctx = ctx
        self.bet = bet
        self.user = user

        self.deck = create_deck()
        self.player = [self.deck.pop(), self.deck.pop()]
        self.dealer = [self.deck.pop(), self.deck.pop()]

    def resolve(self, interaction):

        while hand_value(self.dealer) < 17:
            self.dealer.append(self.deck.pop())

        p = hand_value(self.player)
        d = hand_value(self.dealer)

        if p > 21:
            result = "Bust ❌"
        elif d > 21 or p > d:
            self.user["coins"] += self.bet * 2
            result = "Win 🎉"
        elif p == d:
            self.user["coins"] += self.bet
            result = "Push 🤝"
        else:
            result = "Lose ❌"

        update_user(self.ctx.author.id, self.user)

        for item in self.children:
            item.disabled = True

        return f"""
🃏 Player: {format_hand(self.player)} ({p})
🤖 Dealer: {format_hand(self.dealer)} ({d})

Result: {result}
💰 Balance: {self.user['coins']}
"""

    @discord.ui.button(label="Hit", style=discord.ButtonStyle.green)
    async def hit(self, interaction, button):

        if interaction.user != self.ctx.author:
            return await interaction.response.send_message("Not your game!", ephemeral=True)

        self.player.append(self.deck.pop())

        if hand_value(self.player) > 21:
            await interaction.response.edit_message(content=self.resolve(interaction), view=self)
        else:
            await interaction.response.edit_message(
                content=f"{format_hand(self.player)} ({hand_value(self.player)})",
                view=self
            )

    @discord.ui.button(label="Stand", style=discord.ButtonStyle.red)
    async def stand(self, interaction, button):

        if interaction.user != self.ctx.author:
            return await interaction.response.send_message("Not your game!", ephemeral=True)

        await interaction.response.edit_message(content=self.resolve(interaction), view=self)

# ================= WHEEL =================
class SpinAgainView(discord.ui.View):
    def __init__(self, ctx):
        super().__init__(timeout=120)
        self.ctx = ctx

    @discord.ui.button(label="Spin Again", style=discord.ButtonStyle.green)
    async def spin_again(self, interaction, button):

        if interaction.user != self.ctx.author:
            return await interaction.response.send_message("Not your spin!", ephemeral=True)

        user = get_user(interaction.user.id)

        if user["premium_points"] < 1:
            return await interaction.response.send_message("Need 1 premium point.", ephemeral=True)

        user["premium_points"] -= 1

        roll = random.randint(1, 1000)

        if roll <= 400:
            prize = "Nothing ❌"

        elif roll <= 750:
            user["inventory"]["xanax"] += 1
            prize = "1 Xanax 💊"

        elif roll <= 900:
            user["inventory"]["xanax"] += 2
            prize = "2 Xanax 💊💊"

        elif roll <= 970:
            user["inventory"]["xanax"] += 5
            prize = "5 Xanax 💊💊💊💊💊"

        elif roll <= 995:
            user["inventory"]["xanax"] += 20
            prize = "20 Xanax 💊🔥"

        else:
            user["inventory"]["donator pack"] += 1
            prize = "Donator Pack 📦"

        update_user(interaction.user.id, user)

        await interaction.response.edit_message(
            content=f"🎡 Result:\n{prize}",
            view=self
        )

# ================= EVENTS =================
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

# ================= COMMANDS =================

@bot.command()
async def balance(ctx):
    user = get_user(ctx.author.id)
    await ctx.send(f"{user['coins']} coins 💰")

@bot.command()
async def inventory(ctx):
    user = get_user(ctx.author.id)
    inv = user["inventory"]

    await ctx.send(
        f"""
💊 Xanax: {inv['xanax']}
📦 Donator Pack: {inv['donator pack']}
💎 Premium Points: {user['premium_points']}
"""
    )

@bot.command()
async def daily(ctx):
    user = get_user(ctx.author.id)
    now = time.time()

    if now - user["last_daily"] < 86400:
        return await ctx.send("Cooldown ⏳")

    user["coins"] += 1000
    user["last_daily"] = now
    update_user(ctx.author.id, user)

    await ctx.send("+1000 coins 🎁")

@bot.command()
async def shop_cmd(ctx):
    msg = "**🛒 Shop:**\n"
    for item, price in shop.items():
        msg += f"{item} - {price}\n"
    await ctx.send(msg)

@bot.command()
async def buy(ctx, *, item: str):
    item = item.lower().strip()

    if item not in shop:
        return await ctx.send("Item not found.")

    user = get_user(ctx.author.id)
    price = shop[item]

    if user["coins"] < price:
        return await ctx.send("Not enough coins.")

    user["coins"] -= price
    user["inventory"][item] += 1
    update_user(ctx.author.id, user)

    await ctx.send(f"You bought {item}")

@bot.command()
async def convert(ctx, amount: int):
    user = get_user(ctx.author.id)

    if user["inventory"]["xanax"] < amount:
        return await ctx.send("Not enough Xanax")

    user["inventory"]["xanax"] -= amount
    user["premium_points"] += amount
    update_user(ctx.author.id, user)

    await ctx.send(f"Converted {amount}")

@bot.command()
async def wheel(ctx):
    user = get_user(ctx.author.id)

    if user["premium_points"] < 1:
        return await ctx.send("Need PP")

    user["premium_points"] -= 1

    roll = random.randint(1, 1000)

    if roll <= 400:
        prize = "Nothing ❌"
    elif roll <= 750:
        user["inventory"]["xanax"] += 1
        prize = "1 Xanax 💊"
    elif roll <= 900:
        user["inventory"]["xanax"] += 2
        prize = "2 Xanax 💊💊"
    elif roll <= 970:
        user["inventory"]["xanax"] += 5
        prize = "5 Xanax 💊💊💊💊💊"
    elif roll <= 995:
        user["inventory"]["xanax"] += 20
        prize = "20 Xanax 💊"
    else:
        user["inventory"]["donator pack"] += 1
        prize = "Donator Pack 📦"

    update_user(ctx.author.id, user)

    await ctx.send(prize, view=SpinAgainView(ctx))

@bot.command()
async def top(ctx):
    sorted_users = sorted(data.items(), key=lambda x: x[1]["coins"], reverse=True)

    msg = "🏆 Leaderboard:\n"

    for i, (uid, u) in enumerate(sorted_users[:10], 1):
        msg += f"{i}. {uid} — {u['coins']}\n"

    await ctx.send(msg)

@bot.command()
async def blackjack(ctx, bet: int):
    user = get_user(ctx.author.id)

    if bet > user["coins"]:
        return await ctx.send("Not enough coins")

    user["coins"] -= bet
    update_user(ctx.author.id, user)

    view = BlackjackView(ctx, bet, user)

    await ctx.send(
        f"{format_hand(view.player)} ({hand_value(view.player)})",
        view=view
    )

@bot.command()
async def commands(ctx):
    await ctx.send("""
!balance
!daily
!shop_cmd
!buy
!inventory
!convert
!wheel
!blackjack
!top
""")

# ================= RUN =================
bot.run(os.getenv("TOKEN"))
