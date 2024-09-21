import discord
import random
import asyncio
import json
import os
import pymysql
from discord.ext import commands
from discord.ui import Button, View
from dotenv import load_dotenv

load_dotenv()

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
client = commands.Bot(command_prefix="-", intents=intents)

# JSON file paths
ROLES_FILE_PATH = "roles.json"

# Database connection function
def get_db_connection():
    return pymysql.connect(
        host="mysql-3544ed60-famee-a7f1.e.aivencloud.com",
        user="avnadmin",
        password="AVNS_YSTlhvZwHiXNTEfuRXE",
        db="defaultdb",
        port=26213,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        ssl=False,
    )

# Database functions
def update_user_points(user_id, points_to_add, username=None):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            sql_check = "SELECT 1 FROM users WHERE id = %s"
            cursor.execute(sql_check, (user_id,))
            exists = cursor.fetchone()

            if exists:
                sql_update = "UPDATE users SET points = points + %s WHERE id = %s"
                cursor.execute(sql_update, (points_to_add, user_id))
            else:
                sql_insert = "INSERT INTO users (id, username, points) VALUES (%s, %s, %s)"
                cursor.execute(sql_insert, (user_id, username or "Unknown", points_to_add))

        connection.commit()
    finally:
        connection.close()

def get_user_points(user_id):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            sql = "SELECT points FROM users WHERE id = %s"
            cursor.execute(sql, (user_id,))
            result = cursor.fetchone()
            return result['points'] if result else 0
    finally:
        connection.close()

# Game state management
class PiratesGame:
    def __init__(self):
        self.players = []
        self.roles = {}
        self.votes = {}
        self.started = False
        self.traitors = 0
        self.cat = 0
        self.saver = None

    def reset(self):
        self.players = []
        self.roles = {}
        self.votes = {}
        self.started = False
        self.traitors = 0
        self.cat = 0
        self.saver = None
        self.save_roles_to_json()  # Clear roles in JSON when resetting the game

    def assign_roles(self):
        random.shuffle(self.players)
        num_players = len(self.players)

        num_traitors = 2 if num_players > 8 else 1
        num_cat = 1
        num_saver = 1
        num_workers = num_players - (num_traitors + num_cat + num_saver + 1)

        self.roles[self.players[0]] = "الكابتن"  # Captain
        self.roles.update({player: "عامل" for player in self.players[1:num_workers+1]})  # Workers
        self.roles.update({player: "خائن" for player in self.players[num_workers+1:num_workers+1+num_traitors]})  # Traitors
        self.roles[self.players[num_players-2]] = "القط"  # Cat
        self.roles[self.players[num_players-1]] = "المنقذ"  # Saver

        self.traitors = num_traitors
        self.cat = num_cat
        self.saver = self.players[num_players-1]

        self.save_roles_to_json()  # Save roles to JSON

    def save_roles_to_json(self):
        data = {
            "players": self.players,
            "roles": self.roles,
            "traitors": self.traitors,
            "cat": self.cat,
            "saver": self.saver
        }
        with open(ROLES_FILE_PATH, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=4)

    def load_roles_from_json(self):
        if os.path.exists(ROLES_FILE_PATH):
            with open(ROLES_FILE_PATH, "r", encoding="utf-8") as file:
                data = json.load(file)
                self.players = data.get("players", [])
                self.roles = data.get("roles", {})
                self.traitors = data.get("traitors", 0)
                self.cat = data.get("cat", 0)
                self.saver = data.get("saver", None)

    def get_role(self, player_id):
        return self.roles.get(player_id, "غير معروف")

    def add_vote(self, player_id, target_id):
        self.votes[player_id] = target_id

    def calculate_votes(self):
        vote_count = {}
        for voter, target in self.votes.items():
            role = self.get_role(voter)
            if role == "الكابتن":
                vote_count[target] = vote_count.get(target, 0) + 2
            else:
                vote_count[target] = vote_count.get(target, 0) + 1
        return vote_count

    async def eliminate_player(self, channel):
        vote_count = self.calculate_votes()
        if vote_count:
            target = max(vote_count, key=vote_count.get)
            if target:
                if self.saver and self.saver in self.players:
                    saver_user = client.get_user(self.saver)
                    if saver_user:
                        await saver_user.send(f'هل تريد إنقاذ <@{target}>؟ (نعم/لا)')
                        try:
                            response = await client.wait_for('message', check=lambda m: m.author == saver_user, timeout=15)
                            if response.content.strip().lower() == 'نعم':
                                await channel.send(f"تم إنقاذ اللاعب <@{target}>. لن يتم طرده.")
                                return None, None
                        except asyncio.TimeoutError:
                            pass

            self.players.remove(target)
            eliminated_role = self.roles.pop(target)
            self.save_roles_to_json()  # Update roles in JSON after elimination
            if eliminated_role == "خائن":
                self.traitors -= 1
            return target, eliminated_role
        return None, None

    def is_game_over(self):
        return self.traitors == 0 or len(self.players) <= 2

# Initialize game state
game = PiratesGame()

async def notify_roles():
    for player in game.players:
        role = game.get_role(player)
        user = client.get_user(player)
        if user:
            await user.send(f"دورك في اللعبة هو: **{role}**")

async def cat_phase():
    cat_player = next((p for p, role in game.roles.items() if role == "القط"), None)
    if cat_player:
        user = client.get_user(cat_player)
        if user:
            await user.send("أنت القط. يمكنك سؤال لاعب آخر عن دوره.")
            await asyncio.sleep(15)  # Give some time for the Cat to ask

async def traitor_phase(channel):
    traitor_players = [p for p, role in game.roles.items() if role == "خائن"]
    for traitor in traitor_players:
        user = client.get_user(traitor)
        if user:
            await user.send("أنت خائن. اختر لاعبًا لقتله.")
            await asyncio.sleep(15)  # Give some time for the Traitor to make a choice

async def start_game(channel):
    # Load roles if the game is restarted
    game.load_roles_from_json()

    if len(game.players) < 4:
        await channel.send("لا يوجد عدد كافٍ من اللاعبين لبدء اللعبة. الحد الأدنى هو 4 لاعبين.")
        return

    if not game.roles:  # Assign roles if they haven't been assigned yet
        game.assign_roles()
        await notify_roles()

    await cat_phase()  # Cat phase
    await traitor_phase(channel)  # Traitor phase

    while not game.is_game_over():
        game.votes = {}
        await channel.send("حان وقت التصويت! ناقشوا ثم صوتوا على الشخص الذي تريدون طرده.")

        for player in game.players:
            user = client.get_user(player)
            if user:
                await user.send("يرجى الرد بـ ID اللاعب الذي تريد التصويت لطرده (مثال: 123456789012345678).")
        
        await asyncio.sleep(30)  # Voting time

        eliminated_player, eliminated_role = await game.eliminate_player(channel)

        if eliminated_player:
            await channel.send(f"تم طرد اللاعب <@{eliminated_player}>.")
            if eliminated_role == "خائن":
                await channel.send("تم طرد خائن!")
            if game.is_game_over():
                break
        else:
            await channel.send("لم يتم طرد أي لاعب في هذه الجولة.")

    if game.traitors == 0:
        await channel.send("الكابتن، العمال، والقط قد فازوا!")
        for player in game.players:
            update_user_points(player, 3)
    else:
        await channel.send("الخونة قد فازوا!")
        for player in game.players:
            if game.get_role(player) == "خائن":
                update_user_points(player, 4)

    game.reset()

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith("-pirates"):
        if game.started:
            await message.channel.send("هناك لعبة بالفعل قيد التقدم!")
            return

        game.started = True
        embed = discord.Embed(title="لعبة القراصنة", description="اضغط 'دخول' للانضمام إلى اللعبة أو 'خروج' للانسحاب.", color=discord.Color.blue())
        embed.add_field(name="اللاعبين", value="لا يوجد لاعبين حتى الآن.")
        msg = await message.channel.send(embed=embed)

        join_btn = Button(label="دخول", style=discord.ButtonStyle.green)
        leave_btn = Button(label="خروج", style=discord.ButtonStyle.red)

        async def join_callback(interaction):
            await interaction.response.defer()  # Defer the response to avoid the 3-second limit

            if interaction.user.id not in game.players:
                if get_user_points(interaction.user.id) >= 2:
                    game.players.append(interaction.user.id)
                    update_user_points(interaction.user.id, -2)
                    embed.set_field_at(0, name="اللاعبين", value="\n".join([f"<@{player}>" for player in game.players]))
                    await msg.edit(embed=embed)
                    await interaction.followup.send("لقد انضممت إلى اللعبة!", ephemeral=True)
                else:
                    await interaction.followup.send("ليس لديك نقاط كافية للانضمام إلى اللعبة.", ephemeral=True)
            else:
                await interaction.followup.send("أنت بالفعل في اللعبة!", ephemeral=True)

        async def leave_callback(interaction):
            await interaction.response.defer()  # Defer the response to avoid the 3-second limit

            if interaction.user.id in game.players:
                game.players.remove(interaction.user.id)
                embed.set_field_at(0, name="اللاعبين", value="\n".join([f"<@{player}>" for player in game.players]) or "لا يوجد لاعبين حتى الآن.")
                await msg.edit(embed=embed)
                await interaction.followup.send("لقد انسحبت من اللعبة.", ephemeral=True)
            else:
                await interaction.followup.send("أنت لست في اللعبة.", ephemeral=True)

        join_btn.callback = join_callback
        leave_btn.callback = leave_callback

        view = View()
        view.add_item(join_btn)
        view.add_item(leave_btn)

        await msg.edit(view=view)

        await asyncio.sleep(30)  # Waiting time for players to join

        if len(game.players) < 4:
            await message.channel.send("لا يوجد عدد كافٍ من اللاعبين لبدء اللعبة. الحد الأدنى هو 4 لاعبين.")
            game.reset()
            return

        await start_game(message.channel)

DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
if not DISCORD_TOKEN:
    raise ValueError("No DISCORD_TOKEN environment variable set.")

client.run(DISCORD_TOKEN)