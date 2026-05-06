import discord
from discord.ext import commands
import random
import json
import os
import time

# ================= CONFIG =================
ADMIN_USER_ID = 980819870495166474

# ================= SETUP =================
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ================= DATA =================
DATA_FILE = "data.json"

def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

data = load_data()

def get_user(user_id):
    uid = str(user_id)
    if uid not in data:
        data[uid] = {"coins": 1000, "last_daily": 0}
        save_data()
    return data[uid]

def update_user(user_id, user_data):
    data[str(user_id)] = user_data
    save_data()

# ================= SHOP =================
shop = {
    "xanax": 5000,
    "donator pack": 70000,
    "test": 1
}

# ================= BLACKJACK =================
def create_deck():
    deck = []
    suits = ["♠", "♥", "♦", "♣"]
    ranks = {
        "A": 11, "2": 2, "3": 3, "4": 4, "5": 5,
        "6": 6, "7": 7, "8": 8, "9": 9, "10": 10,
        "J": 10, "Q": 10, "K": 10
    }
    for suit in suits:
        for rank, value in ranks.items():
            deck.append((rank, suit, value))
    random.shuffle(deck)
    return deck

def calculate_hand(hand):
    value = sum(card[2] for card in hand)
    aces = sum(1 for card in hand if card[0] == "A")
    while value > 21 and aces:
        value -= 10
        aces -= 1
    return value

def format_hand(hand):
    return " ".join([f"{c[0]}{c[1]}" for c in hand])

class BlackjackView(discord.ui.View):
    def __init__(self, ctx, bet, user_data):
        super().__init__(timeout=40)
        self.ctx = ctx
        self.bet = bet
        self.user_data = user_data
        self.deck = create_deck()

        self.hands = [[self.deck.pop(), self.deck.pop()]]
        self.current_hand = 0
        self.dealer = [self.deck.pop(), self.deck.pop()]

    def current(self):
        return self.hands[self.current_hand]

    def get_message(self):
        hand = self.current()
        return (
            f"Hand {self.current_hand+1}/{len(self.hands)}\n"
            f"Your: {format_hand(hand)} ({calculate_hand(hand)})\n"
            f"Dealer: {self.dealer[0][0]}{self.dealer[0][1]}"
        )

    async def end_game(self, interaction):
        while calculate_hand(self.dealer) < 17:
            self.dealer.append(self.deck.pop())

        dealer_val = calculate_hand(self.dealer)
        total_change = 0
        results = []

        for hand in self.hands:
            player_val = calculate_hand(hand)

            if player_val > 21:
                results.append(f"{format_hand(hand)} → Bust ❌")
                total_change -= self.bet
            elif dealer_val > 21 or player_val > dealer_val:
                if player_val == 21 and len(hand) == 2:
                    win = int(self.bet * 1.5)
                    results.append(f"{format_hand(hand)} → Blackjack! 🎉 (+{win})")
                    total_change += win
                else:
                    results.append(f"{format_hand(hand)} → Win 🎉 (+{self.bet})")
                    total_change += self.bet
            elif player_val == dealer_val:
                results.append(f"{format_hand(hand)} → Push 🤝")
            else:
                results.append(f"{format_hand(hand)} → Lose ❌")
                total_change -= self.bet

        self.user_data["coins"] += total_change
        update_user(self.ctx.author.id, self.user_data)

        for item in self.children:
            item.disabled = True

        text = f"Dealer: {format_hand(self.dealer)} ({dealer_val})\n\n"
        text += "\n".join(results)
        text += f"\n\n💰 Balance: {self.user_data['coins']}"

        await interaction.response.edit_message(content=text, view=self)

    @discord.ui.button(label="Hit", style=discord.ButtonStyle.green)
    async def hit(self, interaction, button):
        if interaction.user != self.ctx.author:
            return await interaction.response.send_message("Not your game!", ephemeral=True)

        hand = self.current()
        hand.append(self.deck.pop())

        if calculate_hand(hand) > 21:
            if self.current_hand + 1 < len(self.hands):
                self.current_hand += 1
                await interaction.response.edit_message(content=self.get_message(), view=self)
            else:
                await self.end_game(interaction)
        else:
            await interaction.response.edit_message(content=self.get_message(), view=self)

    @discord.ui.button(label="Stand", style=discord.ButtonStyle.red)
    async def stand(self, interaction, button):
        if interaction.user != self.ctx.author:
            return await interaction.response.send_message("Not your game!", ephemeral=True)

        if self.current_hand + 1 < len(self.hands):
            self.current_hand += 1
            await interaction.response.edit_message(content=self.get_message(), view=self)
        else:
            await self.end_game(interaction)

    @discord.ui.button(label="Double", style=discord.ButtonStyle.blurple)
    async def double(self, interaction, button):
        if interaction.user != self.ctx.author:
            return await interaction.response.send_message("Not your game!", ephemeral=True)

        if self.user_data["coins"] < self.bet:
            return await interaction.response.send_message("Not enough coins!", ephemeral=True)

        self.user_data["coins"] -= self.bet
        self.bet *= 2

        hand = self.current()
        hand.append(self.deck.pop())

        if self.current_hand + 1 < len(self.hands):
            self.current_hand += 1
            await interaction.response.edit_message(content=self.get_message(), view=self)
        else:
            await self.end_game(interaction)

    @discord.ui.button(label="Split", style=discord.ButtonStyle.gray)
    async def split(self, interaction, button):
        if interaction.user != self.ctx.author:
            return await interaction.response.send_message("Not your game!", ephemeral=True)

        hand = self.current()

        if len(hand) != 2 or hand[0][2] != hand[1][2]:
            return await interaction.response.send_message("Cannot split!", ephemeral=True)

        if self.user_data["coins"] < self.bet:
            return await interaction.response.send_message("Not enough coins!", ephemeral=True)

        self.user_data["coins"] -= self.bet

        new_hand1 = [hand[0], self.deck.pop()]
        new_hand2 = [hand[1], self.deck.pop()]

        self.hands = [new_hand1, new_hand2]
        self.current_hand = 0

        await interaction.response.edit_message(content=self.get_message(), view=self)

# ================= COMMANDS =================

@bot.command()
async def balance(ctx):
    user = get_user(ctx.author.id)
    await ctx.send(f"{ctx.author.name}, you have {user['coins']} coins 💰")

@bot.command()
async def daily(ctx):
    user = get_user(ctx.author.id)
    now = time.time()

    if now - user["last_daily"] < 86400:
        return await ctx.send("Come back later ⏳")

    user["coins"] += 1000
    user["last_daily"] = now
    update_user(ctx.author.id, user)

    await ctx.send("You got 1000 coins 🎁")

@bot.command()
async def shop_cmd(ctx):
    msg = "**🛒 Shop:**\n"
    for item, price in shop.items():
        msg += f"{item} - {price} coins\n"
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
    update_user(ctx.author.id, user)

    await ctx.send(f"You bought {item}")

    admin = await bot.fetch_user(ADMIN_USER_ID)
    await admin.send(f"{ctx.author} bought {item} for {price}")

@bot.command()
async def top(ctx):
    sorted_users = sorted(data.items(), key=lambda x: x[1]["coins"], reverse=True)

    msg = "**🏆 Leaderboard:**\n"
    for i, (uid, udata) in enumerate(sorted_users[:10], start=1):
        try:
            user = await bot.fetch_user(int(uid))
            name = user.name
        except:
            name = "Unknown"
        msg += f"{i}. {name} — {udata['coins']} coins\n"

    await ctx.send(msg)

@bot.command()
async def blackjack(ctx, bet: int):
    user = get_user(ctx.author.id)

    if bet <= 0 or bet > user["coins"]:
        return await ctx.send("Invalid bet.")

    user["coins"] -= bet
    update_user(ctx.author.id, user)

    view = BlackjackView(ctx, bet, user)
    await ctx.send(view.get_message(), view=view)

@bot.command()
async def addcoins(ctx, member: discord.Member, amount: int):
    if ctx.author.id != ADMIN_USER_ID:
        return await ctx.send("No permission.")

    user = get_user(member.id)
    user["coins"] += amount
    update_user(member.id, user)

    await ctx.send(f"Added {amount} coins to {member.name}")

# ================= RUN =================
TOKEN = os.getenv("TOKEN")
bot.run(TOKEN)
