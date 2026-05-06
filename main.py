import discord
from discord.ext import commands
import random
import json
import os
import time

# ====== CONFIG ======
ADMIN_USER_ID = 123456789012345678  # 👈 PUT YOUR DISCORD USER ID HERE

# ====== SETUP ======
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ====== DATA ======
def load_data():
    if not os.path.exists("data.json"):
        return {}
    with open("data.json", "r") as f:
        return json.load(f)

def save_data(data):
    with open("data.json", "w") as f:
        json.dump(data, f)

def get_user(user_id):
    data = load_data()
    user_id = str(user_id)

    if user_id not in data:
        data[user_id] = {
            "coins": 100,
            "last_daily": 0
        }
        save_data(data)

    return data[user_id]

def update_user(user_id, user_data):
    data = load_data()
    data[str(user_id)] = user_data
    save_data(data)

# ====== SHOP ITEMS ======
shop = {
    "medkit": 200,
    "ammo": 150,
    "armor": 500
}

# ====== BLACKJACK ======
def draw_card():
    return random.randint(1, 11)

def hand_value(hand):
    return sum(hand)

# ====== EVENTS ======
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

# ====== COMMANDS ======

# 💰 Balance
@bot.command()
async def balance(ctx):
    user = get_user(ctx.author.id)
    await ctx.send(f"{ctx.author.name}, you have {user['coins']} coins 💰")

# 🎁 Daily reward
@bot.command()
async def daily(ctx):
    user = get_user(ctx.author.id)
    now = time.time()

    if now - user["last_daily"] < 86400:
        remaining = int(86400 - (now - user["last_daily"]))
        hours = remaining // 3600
        await ctx.send(f"You already claimed daily. Come back in {hours}h.")
        return

    reward = 100
    user["coins"] += reward
    user["last_daily"] = now
    update_user(ctx.author.id, user)

    await ctx.send(f"You claimed {reward} coins 🎁")

# 🛒 Shop
@bot.command()
async def shop_cmd(ctx):
    msg = "**🛒 Shop Items:**\n"
    for item, price in shop.items():
        msg += f"{item} - {price} coins\n"
    await ctx.send(msg)

# 💸 Buy item
@bot.command()
async def buy(ctx, item: str):
    item = item.lower()

    if item not in shop:
        await ctx.send("Item not found.")
        return

    user = get_user(ctx.author.id)
    price = shop[item]

    if user["coins"] < price:
        await ctx.send("Not enough coins.")
        return

    user["coins"] -= price
    update_user(ctx.author.id, user)

    await ctx.send(f"You bought {item} for {price} coins 🛒")

    # 🔔 Notify admin
    admin = await bot.fetch_user(ADMIN_USER_ID)
    await admin.send(
        f"{ctx.author.name} bought {item} for {price} coins."
    )

# 🎰 Blackjack
@bot.command()
async def blackjack(ctx, bet: int):
    user = get_user(ctx.author.id)

    if bet <= 0:
        await ctx.send("Bet must be more than 0.")
        return

    if bet > user["coins"]:
        await ctx.send("You don't have enough coins.")
        return

    player = [draw_card(), draw_card()]
    dealer = [draw_card(), draw_card()]

    await ctx.send(f"Your hand: {player} (Total: {hand_value(player)})")
    await ctx.send(f"Dealer shows: {dealer[0]}")

    while hand_value(player) < 21:
        await ctx.send("Type `hit` or `stand`")

        def check(m):
            return m.author == ctx.author and m.content.lower() in ["hit", "stand"]

        msg = await bot.wait_for("message", check=check)

        if msg.content.lower() == "hit":
            player.append(draw_card())
            await ctx.send(f"You drew {player[-1]} → Total: {hand_value(player)}")
        else:
            break

    while hand_value(dealer) < 17:
        dealer.append(draw_card())

    await ctx.send(f"Dealer hand: {dealer} (Total: {hand_value(dealer)})")

    player_total = hand_value(player)
    dealer_total = hand_value(dealer)

    if player_total > 21:
        user["coins"] -= bet
        await ctx.send(f"You bust! Lost {bet} coins.")
    elif dealer_total > 21 or player_total > dealer_total:
        user["coins"] += bet
        await ctx.send(f"You win! Gained {bet} coins 🎉")
    elif player_total == dealer_total:
        await ctx.send("It's a tie!")
    else:
        user["coins"] -= bet
        await ctx.send(f"Dealer wins! Lost {bet} coins.")

    update_user(ctx.author.id, user)

# ====== RUN ======
bot.run("MTUwMTU4OTE3MTI1OTcwMzU0MA.GvfAcM.NphYbJeD5l58EWuB848VO6twXQ8ZX4i1lN3fng")
