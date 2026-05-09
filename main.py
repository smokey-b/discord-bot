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

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)

# ================= DATA =================
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

        save_data()

    # Fix older accounts automatically
    if "premium_points" not in data[uid]:
        data[uid]["premium_points"] = 0

    if "inventory" not in data[uid]:
        data[uid]["inventory"] = {
            "xanax": 0,
            "donator pack": 0
        }

    save_data()

    return data[uid]

def update_user(user_id, user_data):

    data[str(user_id)] = user_data

    save_data()

# ================= SHOP =================
shop = {
    "xanax": 5000,
    "donator pack": 70000
}

# ================= BLACKJACK =================

def create_deck():

    suits = ["♠", "♥", "♦", "♣"]

    ranks = {
        "A": 11,
        "2": 2,
        "3": 3,
        "4": 4,
        "5": 5,
        "6": 6,
        "7": 7,
        "8": 8,
        "9": 9,
        "10": 10,
        "J": 10,
        "Q": 10,
        "K": 10
    }

    deck = []

    for suit in suits:
        for rank, value in ranks.items():
            deck.append((rank, suit, value))

    random.shuffle(deck)

    return deck

def calculate_hand(hand):

    value = sum(card[2] for card in hand)

    aces = sum(
        1 for card in hand if card[0] == "A"
    )

    while value > 21 and aces:

        value -= 10
        aces -= 1

    return value

def format_hand(hand):

    return " ".join(
        [f"{c[0]}{c[1]}" for c in hand]
    )

class BlackjackView(discord.ui.View):

    def __init__(self, ctx, bet, user_data):

        super().__init__(timeout=120)

        self.ctx = ctx
        self.bet = bet
        self.user_data = user_data

        self.deck = create_deck()

        self.hands = [
            [self.deck.pop(), self.deck.pop()]
        ]

        self.current_hand = 0

        self.dealer = [
            self.deck.pop(),
            self.deck.pop()
        ]

        for item in self.children:
            if item.label == "Repeat Bet":
                item.disabled = True

    def current(self):
        return self.hands[self.current_hand]

    def get_message(self):

        hand = self.current()

        return (
            f"🃏 Hand "
            f"{self.current_hand + 1}/"
            f"{len(self.hands)}\n\n"

            f"Your Hand:\n"
            f"{format_hand(hand)} "
            f"({calculate_hand(hand)})\n\n"

            f"Dealer Shows:\n"
            f"{self.dealer[0][0]}"
            f"{self.dealer[0][1]}"
        )

    async def end_game(self, interaction):

        while calculate_hand(self.dealer) < 17:
            self.dealer.append(
                self.deck.pop()
            )

        dealer_val = calculate_hand(
            self.dealer
        )

        total_change = 0

        results = []

        for hand in self.hands:

            player_val = calculate_hand(hand)

            # Bust
            if player_val > 21:

                results.append(
                    f"{format_hand(hand)} "
                    f"→ Bust ❌"
                )

            # Win
            elif (
                dealer_val > 21
                or player_val > dealer_val
            ):

                # Blackjack payout
                if (
                    player_val == 21
                    and len(hand) == 2
                ):

                    win = int(self.bet * 2.5)

                    total_change += win

                    results.append(
                        f"{format_hand(hand)} "
                        f"→ Blackjack 🎉"
                    )

                else:

                    win = self.bet * 2

                    total_change += win

                    results.append(
                        f"{format_hand(hand)} "
                        f"→ Win 🎉"
                    )

            # Push
            elif player_val == dealer_val:

                total_change += self.bet

                results.append(
                    f"{format_hand(hand)} "
                    f"→ Push 🤝"
                )

            # Lose
            else:

                results.append(
                    f"{format_hand(hand)} "
                    f"→ Lose ❌"
                )

        self.user_data["coins"] += total_change

        update_user(
            self.ctx.author.id,
            self.user_data
        )

        for item in self.children:

            if item.label != "Repeat Bet":
                item.disabled = True

        for item in self.children:

            if item.label == "Repeat Bet":
                item.disabled = False

        text = (
            f"Dealer Hand:\n"
            f"{format_hand(self.dealer)} "
            f"({dealer_val})\n\n"
        )

        text += "\n".join(results)

        text += (
            f"\n\n💰 Balance: "
            f"{self.user_data['coins']}"
        )

        await interaction.response.edit_message(
            content=text,
            view=self
        )

    # ================= BUTTONS =================

    @discord.ui.button(
        label="Hit",
        style=discord.ButtonStyle.green
    )
    async def hit(
        self,
        interaction,
        button
    ):

        if interaction.user != self.ctx.author:
            return await interaction.response.send_message(
                "Not your game!",
                ephemeral=True
            )

        hand = self.current()

        hand.append(
            self.deck.pop()
        )

        if calculate_hand(hand) > 21:

            if self.current_hand + 1 < len(self.hands):

                self.current_hand += 1

                await interaction.response.edit_message(
                    content=self.get_message(),
                    view=self
                )

            else:

                await self.end_game(
                    interaction
                )

        else:

            await interaction.response.edit_message(
                content=self.get_message(),
                view=self
            )

    @discord.ui.button(
        label="Stand",
        style=discord.ButtonStyle.red
    )
    async def stand(
        self,
        interaction,
        button
    ):

        if interaction.user != self.ctx.author:
            return await interaction.response.send_message(
                "Not your game!",
                ephemeral=True
            )

        if self.current_hand + 1 < len(self.hands):

            self.current_hand += 1

            await interaction.response.edit_message(
                content=self.get_message(),
                view=self
            )

        else:

            await self.end_game(
                interaction
            )

    @discord.ui.button(
        label="Double",
        style=discord.ButtonStyle.blurple
    )
    async def double(
        self,
        interaction,
        button
    ):

        if interaction.user != self.ctx.author:
            return await interaction.response.send_message(
                "Not your game!",
                ephemeral=True
            )

        if self.user_data["coins"] < self.bet:
            return await interaction.response.send_message(
                "Not enough coins!",
                ephemeral=True
            )

        self.user_data["coins"] -= self.bet

        self.bet *= 2

        hand = self.current()

        hand.append(
            self.deck.pop()
        )

        if self.current_hand + 1 < len(self.hands):

            self.current_hand += 1

            await interaction.response.edit_message(
                content=self.get_message(),
                view=self
            )

        else:

            await self.end_game(
                interaction
            )

    @discord.ui.button(
        label="Split",
        style=discord.ButtonStyle.gray
    )
    async def split(
        self,
        interaction,
        button
    ):

        if interaction.user != self.ctx.author:
            return await interaction.response.send_message(
                "Not your game!",
                ephemeral=True
            )

        hand = self.current()

        if (
            len(hand) != 2
            or hand[0][2] != hand[1][2]
        ):

            return await interaction.response.send_message(
                "Cannot split!",
                ephemeral=True
            )

        if self.user_data["coins"] < self.bet:
            return await interaction.response.send_message(
                "Not enough coins!",
                ephemeral=True
            )

        self.user_data["coins"] -= self.bet

        new_hand1 = [
            hand[0],
            self.deck.pop()
        ]

        new_hand2 = [
            hand[1],
            self.deck.pop()
        ]

        self.hands = [
            new_hand1,
            new_hand2
        ]

        self.current_hand = 0

        await interaction.response.edit_message(
            content=self.get_message(),
            view=self
        )

    @discord.ui.button(
        label="Repeat Bet",
        style=discord.ButtonStyle.secondary
    )
    async def repeat_bet(
        self,
        interaction,
        button
    ):

        if interaction.user != self.ctx.author:
            return await interaction.response.send_message(
                "Not your game!",
                ephemeral=True
            )

        user = get_user(
            interaction.user.id
        )

        if user["coins"] < self.bet:
            return await interaction.response.send_message(
                "Not enough coins!",
                ephemeral=True
            )

        user["coins"] -= self.bet

        update_user(
            interaction.user.id,
            user
        )

        new_view = BlackjackView(
            self.ctx,
            self.bet,
            user
        )

        await interaction.response.edit_message(
            content=new_view.get_message(),
            view=new_view
        )

# ================= WHEEL =================

class SpinAgainView(discord.ui.View):

    def __init__(self, ctx):

        super().__init__(timeout=120)

        self.ctx = ctx

    @discord.ui.button(
        label="Spin Again",
        style=discord.ButtonStyle.green
    )
    async def spin_again(
        self,
        interaction,
        button
    ):

        if interaction.user != self.ctx.author:
            return await interaction.response.send_message(
                "Not your spin!",
                ephemeral=True
            )

        user = get_user(
            interaction.user.id
        )

        if user["premium_points"] < 1:
            return await interaction.response.send_message(
                "Need 1 premium point.",
                ephemeral=True
            )

        user["premium_points"] -= 1

        # ================= NEW ODDS =================
        roll = random.randint(1, 1000)

        # 25% Nothing
        if roll <= 250:
            prize = "Nothing ❌"

        # 55% 1 Xanax
        elif roll <= 800:

            user["inventory"]["xanax"] += 1

            prize = "1 Xanax 💊"

        # 12% 2 Xanax
        elif roll <= 920:

            user["inventory"]["xanax"] += 2

            prize = "2 Xanax 💊💊"

        # 6% 5 Xanax
        elif roll <= 980:

            user["inventory"]["xanax"] += 5

            prize = "5 Xanax 💊💊💊💊💊"

        # 1.8% 20 Xanax
        elif roll <= 998:

            user["inventory"]["xanax"] += 20

            prize = "20 Xanax 💊🔥"

        # 0.2% Donator Pack
        else:

            user["inventory"]["donator pack"] += 1

            prize = "Donator Pack 📦 (ULTRA RARE)"

        update_user(
            interaction.user.id,
            user
        )

        await interaction.response.edit_message(
            content=(
                f"🎡 {interaction.user.name} "
                f"spun again!\n\n"
                f"Prize: {prize}"
            ),
            view=self
        )

# ================= EVENTS =================

@bot.event
async def on_ready():

    print(f"Logged in as {bot.user}")

# ================= COMMANDS =================

@bot.command()
async def checkbalance(ctx, member: discord.Member):

    user = get_user(member.id)

    await ctx.send(
        f"💰 {member.name} has {user['coins']} coins\n"
        f"💎 Premium Points: {user['premium_points']}\n"
        f"💊 Xanax: {user['inventory']['xanax']}\n"
        f"📦 Donator Packs: {user['inventory']['donator pack']}"
    )
    
@bot.command()
async def balance(ctx):

    user = get_user(ctx.author.id)

    await ctx.send(
        f"{ctx.author.name} "
        f"has {user['coins']} coins 💰"
    )

@bot.command()
async def inventory(ctx):

    user = get_user(ctx.author.id)

    inv = user["inventory"]

    await ctx.send(
        f"📦 Inventory for "
        f"{ctx.author.name}\n\n"

        f"💊 Xanax: "
        f"{inv['xanax']}\n"

        f"📦 Donator Pack: "
        f"{inv['donator pack']}\n\n"

        f"💎 Premium Points: "
        f"{user['premium_points']}"
    )

@bot.command()
async def daily(ctx):

    user = get_user(ctx.author.id)

    now = time.time()

    if now - user["last_daily"] < 86400:

        return await ctx.send(
            "Come back later ⏳"
        )

    user["coins"] += 1000

    user["last_daily"] = now

    update_user(
        ctx.author.id,
        user
    )

    await ctx.send(
        "You got 1000 coins 🎁"
    )

@bot.command()
async def shop_cmd(ctx):

    msg = "**🛒 Shop:**\n"

    for item, price in shop.items():

        msg += (
            f"{item} "
            f"- {price} coins\n"
        )

    await ctx.send(msg)

@bot.command()
async def buy(ctx, *, item: str):

    item = item.lower().strip()

    if item not in shop:
        return await ctx.send(
            "Item not found."
        )

    user = get_user(ctx.author.id)

    price = shop[item]

    if user["coins"] < price:
        return await ctx.send(
            "Not enough coins."
        )

    user["coins"] -= price

    user["inventory"][item] += 1

    update_user(
        ctx.author.id,
        user
    )

    await ctx.send(
        f"You bought {item}"
    )

@bot.command()
async def convert(ctx, amount: int):

    user = get_user(ctx.author.id)

    if amount <= 0:
        return await ctx.send(
            "Invalid amount."
        )

    if user["inventory"]["xanax"] < amount:
        return await ctx.send(
            "Not enough Xanax."
        )

    user["inventory"]["xanax"] -= amount

    user["premium_points"] += amount

    update_user(
        ctx.author.id,
        user
    )

    await ctx.send(
        f"Converted {amount} Xanax "
        f"into {amount} premium points 💎"
    )

@bot.command()
async def wheel(ctx):

    user = get_user(ctx.author.id)

    if user["premium_points"] < 1:
        return await ctx.send(
            "Need 1 premium point."
        )

    user["premium_points"] -= 1

    # ================= NEW ODDS =================
    roll = random.randint(1, 1000)

    # 25% Nothing
    if roll <= 250:
        prize = "Nothing ❌"

    # 55% 1 Xanax
    elif roll <= 800:

        user["inventory"]["xanax"] += 1

        prize = "1 Xanax 💊"

    # 12% 2 Xanax
    elif roll <= 920:

        user["inventory"]["xanax"] += 2

        prize = "2 Xanax 💊💊"

    # 6% 5 Xanax
    elif roll <= 980:

        user["inventory"]["xanax"] += 5

        prize = "5 Xanax 💊💊💊💊💊"

    # 1.8% 20 Xanax
    elif roll <= 998:

        user["inventory"]["xanax"] += 20

        prize = "20 Xanax 💊🔥"

    # 0.2% Donator Pack
    else:

        user["inventory"]["donator pack"] += 1

        prize = "Donator Pack 📦 (ULTRA RARE)"

    update_user(
        ctx.author.id,
        user
    )

    view = SpinAgainView(ctx)

    await ctx.send(
        f"🎡 {ctx.author.name} "
        f"spun the wheel!\n\n"
        f"Prize: {prize}",
        view=view
    )

@bot.command()
async def top(ctx):

    sorted_users = sorted(
        data.items(),
        key=lambda x: x[1]["coins"],
        reverse=True
    )

    msg = "**🏆 Leaderboard:**\n"

    for i, (uid, udata) in enumerate(
        sorted_users[:10],
        start=1
    ):

        try:

            user = await bot.fetch_user(
                int(uid)
            )

            name = user.name

        except:

            name = "Unknown"

        msg += (
            f"{i}. {name} "
            f"— {udata['coins']} coins\n"
        )

    await ctx.send(msg)

@bot.command()
@cooldown(1, 3, BucketType.user)
async def blackjack(ctx, bet: int):

    user = get_user(ctx.author.id)

    if bet <= 0 or bet > user["coins"]:

        return await ctx.send(
            "Invalid bet."
        )

    user["coins"] -= bet

    update_user(
        ctx.author.id,
        user
    )

    view = BlackjackView(
        ctx,
        bet,
        user
    )

    await ctx.send(
        view.get_message(),
        view=view
    )

# ================= ADMIN =================

@bot.command()
async def addcoins(
    ctx,
    member: discord.Member,
    amount: int
):

    if ctx.author.id != ADMIN_USER_ID:
        return

    user = get_user(member.id)

    user["coins"] += amount

    update_user(
        member.id,
        user
    )

    await ctx.send(
        f"Added {amount} coins "
        f"to {member.name}"
    )

@bot.command()
async def addpp(
    ctx,
    member: discord.Member,
    amount: int
):

    if ctx.author.id != ADMIN_USER_ID:
        return

    user = get_user(member.id)

    user["premium_points"] += amount

    update_user(
        member.id,
        user
    )

    await ctx.send(
        f"Added {amount} premium points "
        f"to {member.name}"
    )

@bot.command()
async def removeitem(
    ctx,
    member: discord.Member,
    item: str,
    amount: int
):

    if ctx.author.id != ADMIN_USER_ID:
        return

    item = item.lower().strip()

    user = get_user(member.id)

    if item not in user["inventory"]:
        return await ctx.send(
            "Invalid item."
        )

    if amount <= 0:
        return await ctx.send(
            "Invalid amount."
        )

    if user["inventory"][item] < amount:
        return await ctx.send(
            f"User only has "
            f"{user['inventory'][item]}"
        )

    user["inventory"][item] -= amount

    update_user(
        member.id,
        user
    )

    await ctx.send(
        f"Removed {amount} {item} "
        f"from {member.name}"
    )

@bot.command()
async def commands(ctx):

    await ctx.send("""
🎮 USER COMMANDS

!balance
!daily
!shop_cmd
!buy <item>
!inventory
!convert <amount>
!wheel
!blackjack <bet>
!top

👑 ADMIN COMMANDS

!addcoins @user <amount>
!addpp @user <amount>
!removeitem @user <item> <amount>
""")

# ================= RUN =================

TOKEN = os.getenv("TOKEN")

bot.run(TOKEN)
