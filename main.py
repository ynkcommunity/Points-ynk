import discord
import random
import asyncio
import aiohttp
import io
import urllib.parse
import os
import pymysql
import logging
import traceback
import json
from datetime import datetime, timedelta
from discord.ext import tasks
import time
from keep_alive import keep_alive
import aiomysql
import string


intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
client = discord.Client(intents=intents)

allowed_server_id = 1267826514695557132
allowed_channel_id = 1278306906036899860
allowed_channel_id2 = 1267858595802779648
special_role_id = 1267858307864072244
gif_perm_role_id = 1277640648077611051 
ticket_channel_id = 1267858549225029633

hat_options = ['Sun Hat', 'Beanie', 'Baseball Cap', 'Fedora', 'Beret']
top_options = ['T-Shirt', 'Hoodie', 'Blouse', 'Tank Top', 'Sweater']
bottom_options = ['Jeans', 'Shorts', 'Skirt', 'Trousers', 'Leggings']
dress_options = ['Evening Gown', 'Sundress', 'Cocktail Dress', 'Mini Dress']
shoe_options = ['Sneakers', 'Sandals', 'Boots', 'Heels', 'Flats']
color_options = [
    'Red', 'Blue', 'Green', 'Yellow', 'Pink', 'Black', 'White', 'Purple'
]


EMOJI_REACTIONS_FILE = "emoji_reactions.json"
GIF_USAGE_FILE = "gif_usage.json"

bot_owner_id = 464920565107523584


steal_attempts_file = "steal_attempts.json"
steal_victims_file = "steal_victims.json"
# Global dictionary to store item prices
item_prices = {
    1: 50,   # GIF Permission
    2: 300,  # Custom Emoji Reaction
    3: 150,  # ProBot Credits
    4: 15,   # Lawyer
    5: 10,   # Shield
    6: 15, 
    7: 2
}
# Initialize JSON files if they don't exist
if not os.path.exists(steal_attempts_file):
    with open(steal_attempts_file, 'w') as f:
        json.dump({}, f)

if not os.path.exists(steal_victims_file):
    with open(steal_victims_file, 'w') as f:
        json.dump({}, f)
with open('emoji_data.json', 'r') as file:
    emoji_data = json.load(file)['emoji_data']
def load_steal_attempts():
    try:
        with open(steal_attempts_file, 'r') as f:
            data = json.load(f)
            if not isinstance(data, dict):
                data = {}
    except (json.JSONDecodeError, FileNotFoundError):
        data = {}
        with open(steal_attempts_file, 'w') as f:
            json.dump(data, f, indent=4)
    return data

def load_steal_victims():
    try:
        with open(steal_victims_file, 'r') as f:
            data = json.load(f)
            if not isinstance(data, dict):
                data = {}
    except (json.JSONDecodeError, FileNotFoundError):
        data = {}
        with open(steal_victims_file, 'w') as f:
            json.dump(data, f, indent=4)
    return data

# Save steal attempts data
def save_steal_attempts(data):
    with open(steal_attempts_file, 'w') as f:
        json.dump(data, f, indent=4)


# Save steal victims data
def save_steal_victims(data):
    with open(steal_victims_file, 'w') as f:
        json.dump(data, f, indent=4)

def get_db_connection():
    try:
        connection = pymysql.connect(
            host="mysql-3544ed60-famee-a7f1.e.aivencloud.com",
            user="avnadmin",
            password="AVNS_YSTlhvZwHiXNTEfuRXE",
            db="defaultdb",
            port=26213,
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor,
            ssl=False,
        )
        return connection
    except pymysql.MySQLError as e:
        logger.error(f"Database connection failed: {e}")
        return None
def get_top_users(limit=15):
    # Function to retrieve the top users from the database
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            sql = "SELECT id, points FROM users ORDER BY points DESC LIMIT %s"
            cursor.execute(sql, (limit,))
            result = cursor.fetchall()
            return result
    finally:
        connection.close()

async def handle_setprice_command(message):
    # Check if the user is an admin or authorized to change prices
    if message.author.id != bot_owner_id and not any(
            role.id == 1267858269888839721 for role in message.author.roles):
        await message.channel.send(
            "You don't have permission to use this command.")
        return

    try:
        # Extract the item index and new price from the command
        _, item_index_str, new_price_str = message.content.split()
        item_index = int(item_index_str)
        new_price = int(new_price_str)

        # Check if the item index is valid
        if item_index not in item_prices:
            await message.channel.send(f"{message.author.mention}, رقم العنصر غير صالح.")
            return

        # Update the item price
        item_prices[item_index] = new_price
        await message.channel.send(f"{message.author.mention}, تم تحديث سعر العنصر رقم {item_index} إلى {new_price} نقاط.")
    
    except (ValueError, IndexError):
        await message.channel.send(f"{message.author.mention}, يرجى استخدام الصيغة الصحيحة: `-setprice <رقم العنصر> <السعر الجديد>`.")
async def handle_top_command(message):
    # Fetch the top users from the database
    top_users = get_top_users()
    if not top_users:
        await message.channel.send("No users found.")
        return

    # Create an embed for the top users
    embed = discord.Embed(
        title="Top 15 Users by Points",
        description="Here are the top 15 users with the most points:",
        color=discord.Color.gold()
    )

    for i, user in enumerate(top_users, start=1):
        user_id = user["id"]
        points = user["points"]

        # Construct a silent mention that links to the user's profile
        user_mention = f"<@{user_id}>"

        embed.add_field(
            name=f"{i}. {user_mention}",
            value=f"Points: {points}",
            inline=False
        )

    # Send the embed in the chat
    await message.channel.send(embed=embed)


# Update daily usage to include 'bonus'
def load_daily_usage():
    with open('daily_usage.json', 'r') as file:
        daily_usage_data = json.load(file)['daily_usage']
    
    return {str(record['user_id']): record for record in daily_usage_data}

def save_daily_usage(usage):
    # Load existing daily usage data from JSON file
    with open('daily_usage.json', 'r') as file:
        daily_usage_data = json.load(file)['daily_usage']
    
    # Create a dictionary for easy lookup of existing records by user_id
    daily_usage_dict = {record['user_id']: record for record in daily_usage_data}

    # Update or add new records from the `usage` dictionary
    for user_id, data in usage.items():
        daily_usage_dict[user_id] = {
            "user_id": user_id,
            "daily": data.get('daily', False),
            "special": data.get('special', False),
            "risk": data.get('risk', False),
            "quests": data.get('quests', False),
            "bonus": data.get('bonus', False)  # Ensure 'bonus' is part of the daily tracking
        }

    # Convert the dictionary back to a list
    updated_daily_usage_data = list(daily_usage_dict.values())

    # Save the updated daily usage data back to the JSON file
    with open('daily_usage.json', 'w') as file:
        json.dump({"daily_usage": updated_daily_usage_data}, file, indent=4)

    print("Daily usage data saved successfully.")

def get_user_data(user_id):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            sql = """
            SELECT lawyer, lawyer_expiry, shield, shield_expiry, rage_mode, rage_mode_expiry, rage_steals, rage_vulnerabilities,
                   emoji, emoji_expiry, family, family_active, in_bank, bags
            FROM users 
            WHERE id = %s
            """
            cursor.execute(sql, (user_id,))
            result = cursor.fetchone()
            if result:
                return {
                    "lawyer": result['lawyer'],
                    "lawyer_expiry": result['lawyer_expiry'],
                    "shield": result['shield'],
                    "shield_expiry": result['shield_expiry'],
                    "rage_mode": result['rage_mode'],
                    "rage_mode_expiry": result['rage_mode_expiry'],
                    "rage_steals": result['rage_steals'],
                    "rage_vulnerabilities": result['rage_vulnerabilities'],
                    "emoji": result['emoji'],
                    "emoji_expiry": result['emoji_expiry'],
                    "family": result['family'],
                    "family_active": result.get('family_active', 'No'),
                    "in_bank": result['in_bank'],  # New field for points in the bank
                    "bags": result['bags']         # New field for bags
                }
            else:
                return {
                    "lawyer": 0,
                    "lawyer_expiry": None,
                    "shield": 0,
                    "shield_expiry": None,
                    "rage_mode": 0,
                    "rage_mode_expiry": None,
                    "rage_steals": 0,
                    "rage_vulnerabilities": 0,
                    "emoji": None,
                    "emoji_expiry": None,
                    "family": None,
                    "family_active": 'No',
                    "in_bank": 0,  # Default value for points in the bank
                    "bags": 0      # Default value for bags
                }
    finally:
        connection.close()



def update_user_data(user_id, lawyer=None, lawyer_expiry=None, shield=None, shield_expiry=None, 
                     rage_mode=None, rage_mode_expiry=None, rage_steals=None, rage_vulnerabilities=None,
                     bags=None, in_bank=None):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            updates = []
            values = []
            
            # Update fields if they are provided
            if lawyer is not None:
                updates.append("lawyer = %s")
                values.append(lawyer)
            if lawyer_expiry is not None:
                updates.append("lawyer_expiry = %s")
                values.append(lawyer_expiry)
            if shield is not None:
                updates.append("shield = %s")
                values.append(shield)
            if shield_expiry is not None:
                updates.append("shield_expiry = %s")
                values.append(shield_expiry)
            if rage_mode is not None:
                updates.append("rage_mode = %s")
                values.append(rage_mode)
            if rage_mode_expiry is not None:
                updates.append("rage_mode_expiry = %s")
                values.append(rage_mode_expiry)
            if rage_steals is not None:
                updates.append("rage_steals = %s")
                values.append(rage_steals)
            if rage_vulnerabilities is not None:
                updates.append("rage_vulnerabilities = %s")
                values.append(rage_vulnerabilities)
            
            # New fields for bags and in_bank
            if bags is not None:
                updates.append("bags = %s")
                values.append(bags)
            if in_bank is not None:
                updates.append("in_bank = %s")
                values.append(in_bank)

            # Update the SQL query
            if updates:
                sql = f"UPDATE users SET {', '.join(updates)} WHERE id = %s"
                values.append(user_id)
                cursor.execute(sql, tuple(values))
        connection.commit()
    finally:
        connection.close()

def save_emoji_reactions(user_id, emoji, additional_days=7):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            now = datetime.now()
            end_time = now + timedelta(days=additional_days)

            # Check if the user already has an emoji reaction
            sql_check = "SELECT emoji_expiry FROM users WHERE id = %s"
            cursor.execute(sql_check, (user_id,))
            result = cursor.fetchone()

            if result:
                # If the user already has a reaction, extend the emoji expiry
                existing_expiry = result['emoji_expiry']
                if existing_expiry and existing_expiry > now:
                    end_time = existing_expiry + timedelta(days=additional_days)

            # Update the user's emoji and emoji expiry
            sql = """
            UPDATE users
            SET emoji = %s, emoji_expiry = %s
            WHERE id = %s
            """
            cursor.execute(sql, (emoji, end_time, int(user_id)))
        connection.commit()
    finally:
        connection.close()


async def handle_buy_command(message):
    user_id = str(message.author.id)
    current_points = get_user_points(user_id)
    now = datetime.now()

    try:
        item_index = int(message.content.split()[1])
    except (IndexError, ValueError):
        await message.channel.send(f"{message.author.mention}, يرجى تحديد رقم العنصر بشكل صحيح.")
        return

    if item_index not in item_prices:
        await message.channel.send(f"{message.author.mention}, هذا الرقم غير صالح. يرجى اختيار عنصر من القائمة.")
        return

    item_price = item_prices[item_index]

    if current_points < item_price:
        await message.channel.send(f"{message.author.mention}, ليس لديك نقاط كافية.")
        return

    # Handle different items based on the index
    if item_index == 1:  # GIF Permission
        gif_usage = load_gif_usage()
        expiry_time = now + timedelta(hours=96)

        # Extend existing GIF permission if the user already has it
        if user_id in gif_usage:
            current_expiry = datetime.fromisoformat(gif_usage[user_id])
            if current_expiry > now:
                expiry_time = current_expiry + timedelta(hours=96)

        gif_usage[user_id] = expiry_time.isoformat()
        save_gif_usage(gif_usage)

        gif_role_id = 1277640648077611051  
        
        # Fetch the guild, role, and member
        guild = client.get_guild(allowed_server_id)
        role = guild.get_role(gif_role_id)
        member = guild.get_member(int(user_id))
        
        if role and member:
            # Check if the member already has the role
            if role not in member.roles:
                try:
                    # Add the role if the member doesn't have it
                    await member.add_roles(role)
                    await message.channel.send(f"{message.author.mention} تم منحك إذن GIF!")
                except Exception as e:
                    # Handle and log any errors during role assignment
                    print(f"Error assigning role: {e}")
            else:
                await message.channel.send(f"{message.author.mention} لديك بالفعل إذن GIF!")

        update_user_points(user_id, -item_price)
        await message.channel.send(f"{message.author.mention} لقد اشتريت إذن GIF! (ينتهي في {expiry_time})")

    elif item_index == 2:  # Custom Emoji Reaction
        update_user_points(user_id, -item_price)
        await message.channel.send(f"{message.author.mention}, الرجاء إدخال الإيموجي الذي تريد إضافته كرده فعل تلقائية لرسائلك.")
        
        def check(m):
            return m.author == message.author and m.channel == message.channel

        try:
            msg = await client.wait_for('message', check=check, timeout=30)
            emoji = msg.content
            save_emoji_reactions(user_id, emoji, additional_days=7)
            await message.channel.send(
                f"{message.author.mention} لقد تم تعيين الإيموجي الخاص بك إلى {emoji}. سيتم إضافته تلقائيًا على رسائلك لمدة 7 أيام!"
            )
        except asyncio.TimeoutError:
            await message.channel.send(
                "لقد استغرقت وقتًا طويلاً للرد. يرجى محاولة شراء العنصر مرة أخرى."
            )

    elif item_index == 3:  # ProBot Credits
        update_user_points(user_id, -item_price)
    
        # Send receipt to the bot owner
        bot_owner = client.get_user(bot_owner_id)
        
        if bot_owner:
            await bot_owner.send(
                f"User {message.author.mention} has purchased 100k Probot Credit for {item_price} points."
            )
        
        await message.channel.send(
            f"{message.author.mention} لقد تم شراء 100,000 من رصيد ProBot بنجاح! يرجى الذهاب إلى <#1267858549225029633> للمطالبة برصيدك."
        )

    elif item_index == 4:  # Lawyer
        user_data = get_user_data(user_id)
        expiry_time = now + timedelta(hours=48)
        if user_data.get('lawyer_expiry') and user_data['lawyer_expiry'] > now:
            expiry_time = user_data['lawyer_expiry'] + timedelta(hours=48)
        update_user_data(user_id, lawyer=user_data.get('lawyer', 0) + 1, lawyer_expiry=expiry_time)
        update_user_points(user_id, -item_price)
        await message.channel.send(f"{message.author.mention} لقد اشتريت محاميًا! (ينتهي في {expiry_time})")

    elif item_index == 5:  # Shield
        user_data = get_user_data(user_id)
        expiry_time = now + timedelta(hours=48)
        if user_data.get('shield_expiry') and user_data['shield_expiry'] > now:
            expiry_time = user_data['shield_expiry'] + timedelta(hours=48)
        update_user_data(user_id, shield=1, shield_expiry=expiry_time)
        update_user_points(user_id, -item_price)
        await message.channel.send(f"{message.author.mention} لقد اشتريت درعًا! (ينتهي في {expiry_time})")

    elif item_index == 6:  # Rage Mode
        user_data = get_user_data(user_id)
        expiry_time = now + timedelta(hours=48)
        if user_data.get('rage_mode_expiry') and user_data['rage_mode_expiry'] > now:
            expiry_time = user_data['rage_mode_expiry'] + timedelta(hours=48)
        update_user_data(
            user_id, 
            rage_mode=1, 
            rage_mode_expiry=expiry_time, 
            rage_steals=5, 
            rage_vulnerabilities=5
        )
        update_user_points(user_id, -item_price)
        await message.channel.send(f"{message.author.mention} لقد اشتريت وضع الغضب! (ينتهي في {expiry_time})")

    elif item_index == 7:  # Buying Bags
        user_data = get_user_data(user_id)
        current_bags = user_data.get('bags', 0)
        new_bags = current_bags + 1
        update_user_data(user_id, bags=new_bags)  # Increment the number of bags
        update_user_points(user_id, -item_price)  # Deduct the points
        await message.channel.send(f"{message.author.mention} لقد اشتريت حقيبة! لديك الآن {new_bags} حقيبة/حقائب.")

    
def get_top_users(limit=15):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # Fetch username and points from the users table, ordering by points
            sql = "SELECT username, points FROM users ORDER BY points DESC LIMIT %s"
            cursor.execute(sql, (limit,))
            result = cursor.fetchall()
            return result
    finally:
        connection.close()

async def handle_top_command(message):
    top_users = get_top_users()
    if not top_users:
        await message.channel.send("No users found.")
        return

    embed = discord.Embed(
        title="Top 15 Users by Points",
        description="Here are the top 15 users with the most points:",
        color=discord.Color.gold()
    )

    for i, user in enumerate(top_users, start=1):
        username = user["username"]
        points = user["points"]

        embed.add_field(
            name=f"{i}. @{username}",  # Use the username from the database
            value=f"Points: {points}",
            inline=False
        )

    await message.channel.send(embed=embed)

def load_emoji_reactions():
    connection = get_db_connection()
    now = datetime.now()
    emoji_reactions = {}

    try:
        with connection.cursor() as cursor:
            # Fetch emoji reactions that have not yet expired
            sql = """
            SELECT id, emoji, emoji_expiry
            FROM users
            WHERE emoji IS NOT NULL AND emoji_expiry IS NOT NULL AND emoji_expiry > %s
            """
            cursor.execute(sql, (now,))
            results = cursor.fetchall()

            # Store valid emoji reactions in a dictionary
            emoji_reactions = {
                str(row['id']): row['emoji'] for row in results  # Using 'id' instead of 'user_id'
            }
    finally:
        connection.close()

    return emoji_reactions

def load_gif_usage():
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            sql = "SELECT * FROM gif_usage"
            cursor.execute(sql)
            results = cursor.fetchall()
            return {str(row['user_id']): row['end_time'].isoformat() for row in results}
    finally:
        connection.close()


def save_gif_usage(usage):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            for user_id, end_time in usage.items():
                sql = """
                INSERT INTO gif_usage (user_id, end_time)
                VALUES (%s, %s)
                ON DUPLICATE KEY UPDATE
                end_time = VALUES(end_time)
                """
                cursor.execute(sql, (int(user_id), end_time))
        connection.commit()
    finally:
        connection.close()

async def reduce_gif_time():
    while True:
        await asyncio.sleep(3600)  # Check every hour
        gif_usage = load_gif_usage()
        now = datetime.now()
        users_to_remove = []

        for user_id, end_time_str in gif_usage.items():
            end_time = datetime.fromisoformat(end_time_str)
            if now >= end_time:
                users_to_remove.append(user_id)

        if users_to_remove:
            guild = client.get_guild(allowed_server_id)
            if guild:
                for user_id in users_to_remove:
                    member = guild.get_member(int(user_id))
                    if member:
                        role = guild.get_role(gif_perm_role_id)
                        if role:
                            await member.remove_roles(role)
                            await member.send(
                                "Your GIF/picture permission has expired and the role has been removed."
                            )
                    del gif_usage[user_id]

            save_gif_usage(gif_usage)

async def handle_manual_reset_vc(message):
    notification_channel = message.guild.get_channel(1278306906036899860)
    role_id = 1278375524368125962
    role_mention = f"<@&{role_id}>"

    if message.author.id == bot_owner_id:
        await reset_vc_data()  # Add 'await' here
        await message.channel.send(f"{message.author.mention}, VC data has been manually reset.")
        await notification_channel.send(f"{role_mention}, the VC data has been manually reset by {message.author.mention}.")
    else:
        await message.channel.send(f"{message.author.mention}, you do not have permission to use this command.")
async def handle_manual_reset_daily(message):
    notification_channel = message.guild.get_channel(1278306906036899860)
    role_id = 1278375524368125962
    role_mention = f"<@&{role_id}>"

    if message.author.id == bot_owner_id:
        with open(steal_attempts_file, 'w') as f:
            json.dump({}, f)
        with open(steal_victims_file, 'w') as f:
            json.dump({}, f)
        print("Steal data reset.")
        reset_daily_usage()
        await message.channel.send(f"{message.author.mention}, daily usage has been manually reset.")
        await notification_channel.send(f"{role_mention}, the daily usage has been manually reset by {message.author.mention}.")
    else:
        await message.channel.send(f"{message.author.mention}, you do not have permission to use this command.")

@client.event
async def on_ready():
    print(f'Logged in as {client.user.name} ({client.user.id})')
    client.loop.create_task(reduce_gif_time())
    daily_reset.start() 
    cleanup_expired_emoji_reactions.start()
    print("Bot is ready and all tasks are initialized.")

def generate_random_password(length=10):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

async def get_or_create_user(user_id, username):
    connection = get_db_connection()
    password = generate_random_password()  # Generate a new password
    
    try:
        with connection.cursor() as cursor:
            # SQL to insert a new user or update the username if user already exists
            sql = """
                INSERT INTO users (id, username, points, password) 
                VALUES (%s, %s, 0, %s) 
                ON DUPLICATE KEY UPDATE username = %s
            """
            cursor.execute(sql, (user_id, username, password, username))
            connection.commit()
    finally:
        connection.close()




def update_user_points(user_id, points_to_add, username=None):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # Check if the user already exists
            sql_check = "SELECT points FROM users WHERE id = %s"
            cursor.execute(sql_check, (user_id,))
            exists = cursor.fetchone()

            if exists:
                # User exists, update their points
                sql_update = "UPDATE users SET points = points + %s WHERE id = %s"
                cursor.execute(sql_update, (points_to_add, user_id))
            else:
                # User does not exist, insert new user
                sql_insert = "INSERT INTO users (id, username, points) VALUES (%s, %s, %s)"
                cursor.execute(sql_insert, (user_id, username or "Unknown", points_to_add))

        connection.commit()
    except pymysql.err.IntegrityError as e:
        print(f"Failed to update user points: {e}")
    finally:
        connection.close()


def get_user_points(user_id):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            sql = "SELECT points FROM users WHERE id = %s"
            cursor.execute(sql, (user_id, ))
            result = cursor.fetchone()
            return result['points'] if result else 0
    finally:
        connection.close()

vc_data_file = "vc_data.json"
if not os.path.exists(vc_data_file):
    with open(vc_data_file, 'w') as f:
        json.dump({}, f)

# Function to load VC data from the file
def load_vc_data():
    with open(vc_data_file, 'r') as f:
        return json.load(f)

# Function to save VC data to the file
def save_vc_data(data):
    with open(vc_data_file, 'w') as f:
        json.dump(data, f, indent=4)



@client.event
async def on_message(message):
    if message.author == client.user:
        return
    if message.content.startswith("-load"):
        await handle_load_command(message)
    elif message.content.startswith("-unload"):
        await handle_take_command(message)
    elif message.content.startswith("-mark"):
        await handle_setprice_command(message)
    elif message.content.startswith("-mr_vc"):
        await handle_manual_reset_vc(message)
    elif message.content.startswith("-mr_daily"):
        await handle_manual_reset_daily(message)
    elif message.content.startswith("-mr_daily"):
        await handle_manual_reset_daily(message)
    if message.guild and message.guild.id == allowed_server_id and message.channel.id == allowed_channel_id:
        if message.content.startswith("-help"):
            await handle_help_command(message)
        elif message.content.startswith("-ynk"):
            await handle_ynk_command(message)
        elif message.content.startswith("-top"):
            await handle_top_command(message)
        elif message.content.startswith("-points"):
            await handle_points_command(message)
        elif message.content.startswith("-profile"):
            user = message.author
            await show_user_info(message, user)
        elif message.content.startswith("-shop"):
            await handle_shop_command(message)
        elif message.content.startswith("-steal"):
            await handle_steal_command(message)
        elif message.content.startswith("-heist"):
            await handle_heist_command(message)
        elif message.content.startswith("-family"):
            await handle_family_command(message)
        elif message.content.startswith("-refamily"):
            await handle_removefamily_command(message)

        elif message.content.startswith("-setactive"):
            await handle_setfamilyactive_command(message)
        elif message.content.startswith("-daily"):
            await handle_daily_command(message)
        elif message.content.startswith("-loyal"):
            await handle_loyal_command(message)
        elif message.content.startswith("-buy"):
            await handle_buy_command(message)
        elif message.content.startswith("-risk"):
            await handle_risk_command(message)
        elif message.content.startswith("-quests"):
            await handle_quests_command(message)
        elif message.content.startswith("-reset"):
            await update_expired_status(message)
        elif message.content.startswith("-bonus"):
            await  handle_bonus_command(message)
    if message.guild and message.guild.id == allowed_server_id and message.channel.id == allowed_channel_id2:
        if message.content.startswith("-تلبيس"):
            await handle_dress_command(message)
        elif message.content.startswith("-picture"):
            await handle_picture_command(message)
    if message.guild and message.guild.id == allowed_server_id and message.mentions:
        await handle_auto_react(message)
def get_user_rank_and_points(user_id):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # Get the user's points
            sql_points = """
            SELECT points
            FROM users
            WHERE id = %s
            """
            cursor.execute(sql_points, (user_id,))
            result_points = cursor.fetchone()

            if not result_points:
                return None, None  # If no points data is found

            user_points = result_points['points']

            # Get the user's rank, escape the `rank` keyword with backticks
            sql_rank = """
            SELECT COUNT(*) + 1 AS `rank`
            FROM users
            WHERE points > (
                SELECT points FROM users WHERE id = %s
            )
            """
            cursor.execute(sql_rank, (user_id,))
            result_rank = cursor.fetchone()

            if result_rank:
                user_rank = result_rank['rank']
            else:
                user_rank = None

            return user_points, user_rank
    finally:
        connection.close()


async def show_user_info(message, user):
    user_data = get_user_data(user.id)
    user_points, user_rank = get_user_rank_and_points(user.id)
    guild = message.guild

    # Check if various statuses are active
    now = datetime.now()

    lawyer_active = user_data['lawyer'] == 1 and user_data['lawyer_expiry'] and user_data['lawyer_expiry'] > now
    shield_active = user_data['shield'] == 1 and user_data['shield_expiry'] and user_data['shield_expiry'] > now
    rage_mode_active = user_data['rage_mode'] == 1 and user_data['rage_mode_expiry'] and user_data['rage_mode_expiry'] > now
    emoji_active = user_data['emoji'] and user_data['emoji_expiry'] and user_data['emoji_expiry'] > now
    gif_perm_active = discord.utils.get(guild.roles, id=gif_perm_role_id) in user.roles
    family_active = user_data['family_active'] == 'Yes'

    # Create an embed to display user info
    embed = discord.Embed(
        title=f"User Information for {user.display_name}",
        color=discord.Color.blue()
    )
    embed.set_thumbnail(url=user.avatar.url)

    # Add user details to the embed
    embed.add_field(name="Points", value=f"{user_points or 0}", inline=True)
    embed.add_field(name="Rank", value=f"#{user_rank}" if user_rank else "Unranked", inline=True)

    # Add status information
    embed.add_field(name="Lawyer Active", value="✅ Yes" if lawyer_active else "❌ No", inline=True)
    embed.add_field(name="Shield Active", value="✅ Yes" if shield_active else "❌ No", inline=True)
    embed.add_field(name="Rage Mode Active", value="✅ Yes" if rage_mode_active else "❌ No", inline=True)
    embed.add_field(name="Custom Emoji Active", value=f"✅ Yes ({user_data['emoji']})" if emoji_active else "❌ No", inline=True)
    embed.add_field(name="GIF Permission", value="✅ Yes" if gif_perm_active else "❌ No", inline=True)

    # Add bank and bags info
    embed.add_field(name="In Bank", value=f"{user_data['in_bank']}", inline=True)
    embed.add_field(name="Bags", value=f"{user_data['bags']}", inline=True)

    embed.add_field(name="Family Active", value="✅ Yes" if family_active else "❌ No", inline=True)

    # Send the embed in the channel where the command was invoked
    await message.channel.send(embed=embed)

async def handle_deposit_command(message):
    user_id = str(message.author.id)
    try:
        # Parse the amount from the message content
        _, amount = message.content.split()  # Assuming the format is: -deposit <amount>
        amount = int(amount)

        # Call the deposit function
        result = deposit_money(user_id, amount)

        # Send the result back to the user
        await message.channel.send(result)

    except ValueError:
        await message.channel.send("يرجى تحديد المبلغ الصحيح لإيداعه. على سبيل المثال: -deposit 100")
    except Exception as e:
        await message.channel.send(f"حدث خطأ: {str(e)}")

async def handle_withdraw_command(message):
    user_id = str(message.author.id)
    try:
        # Parse the amount from the message content
        _, amount = message.content.split()  # Assuming the format is: -withdraw <amount>
        amount = int(amount)

        # Call the withdraw function
        result = withdraw_money(user_id, amount)

        # Send the result back to the user
        await message.channel.send(result)

    except ValueError:
        await message.channel.send("يرجى تحديد المبلغ الصحيح للسحب. على سبيل المثال: -withdraw 100")
    except Exception as e:
        await message.channel.send(f"حدث خطأ: {str(e)}")

def deposit_money(user_id, amount):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # Get the user's current balances and points
            sql = "SELECT in_bank, points FROM users WHERE id = %s"
            cursor.execute(sql, (user_id,))
            result = cursor.fetchone()

            if result:
                current_in_bank = result['in_bank']
                current_points = result['points']

                # Deduct 5% of the deposit amount
                deposit_amount = amount * 0.95

                # Check if the user has enough points to deposit
                if deposit_amount > current_points:
                    return f"لا يمكنك إيداع {amount}. لديك فقط {current_points} نقاط."

                # Update the balances
                new_in_bank = current_in_bank + deposit_amount
                new_points = current_points - amount
                update_user_data(user_id, in_bank=new_in_bank, points=new_points)

                return (f"تم إيداع {amount} في حساب البنك الخاص بك.\n"
                        f"رصيدك الحالي في البنك: {new_in_bank}\n"
                        f"رصيدك الحالي من النقاط: {new_points}")
            else:
                return "لم يتم العثور على حساب المستخدم."
    finally:
        connection.close()

def withdraw_money(user_id, amount):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # Get the user's current balances and points
            sql = "SELECT in_bank, points FROM users WHERE id = %s"
            cursor.execute(sql, (user_id,))
            result = cursor.fetchone()

            if result:
                current_in_bank = result['in_bank']
                current_points = result['points']

                # Check if the user has enough money in the bank to withdraw
                if amount > current_in_bank:
                    return f"لا يمكنك سحب {amount}. لديك فقط {current_in_bank} في البنك."

                # Update the balances
                new_in_bank = current_in_bank - amount
                new_points = current_points + amount
                update_user_data(user_id, in_bank=new_in_bank, points=new_points)

                return (f"تم سحب {amount} من حساب البنك الخاص بك.\n"
                        f"رصيدك الحالي في البنك: {new_in_bank}\n"
                        f"رصيدك الحالي من النقاط: {new_points}")
            else:
                return "لم يتم العثور على حساب المستخدم."
    finally:
        connection.close()

def update_user_data(user_id, **kwargs):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # Build the SQL query dynamically based on kwargs
            set_clause = ', '.join([f"{key} = %s" for key in kwargs.keys()])
            sql = f"UPDATE users SET {set_clause} WHERE id = %s"
            cursor.execute(sql, (*kwargs.values(), user_id))
            connection.commit()
    finally:
        connection.close()

async def handle_help_command(message):
    embed = discord.Embed(
        title="مساعدة أوامر البوت",
        description="نظام النقاط هو لعبة ممتعة في السيرفر تتيح لك شراء الأدوار والميزات داخل السيرفر، مع العديد من التحديثات القادمة قريبًا!",
        color=discord.Color.blue()
    )

    embed.add_field(
        name="-ynk",
        value=(
            "يتيح لك الأمر `-ynk` المشاركة في أنشطة مختلفة لكسب النقاط:\n"
            "- **-daily**: اربح بين 5 إلى 15 نقطة مرة واحدة يوميًا.\n"
            "- **-loyal**: اربح 10 نقاط إذا كنت تمتلك دورًا خاصًا. يُستخدم مرة واحدة يوميًا.\n"
            "- **-risk**: خذ مخاطرة! يمكنك الفوز بين 10 و 20 نقطة، ولكن قد تخسر بين 10 و 17 نقطة. يُستخدم مرة واحدة يوميًا.\n"
            "- **-quests**: أكمل مهام متنوعة لكسب نقاط إضافية.\n"
            "- **-bonus**: احصل على 10 نقاط إضافية إذا كنت نشطًا في فريق"
        ),
        inline=False
    )

    embed.add_field(
        name="-shop",
        value=(
            "يتيح لك الأمر `-shop` شراء عناصر متنوعة باستخدام نقاطك:\n"
            "- **GIFs**: اشترِ القدرة على إرسال صور GIF. كل عملية شراء تمنحك 7 أيام من القدرة على إرسال صور GIF. يمكنك تمديد المدة عن طريق الشراء عدة مرات.\n"
            "- **Custom Emoji Reaction**: اشترِ تفاعل رموز تعبيرية مخصصة تظهر تلقائيًا في رسائلك لمدة 7 أيام. يمكنك شراء وقت إضافي عن طريق الشراء عدة مرات."
        ),
        inline=False
    )

    embed.add_field(
        name="-hide",
        value="يتيح لك الأمر `-hide` تخزين نقاطك في البنك حتى لا تفقدها. استخدمه لحماية نقاطك.",
        inline=False
    )

    embed.add_field(
        name="-take",
        value="يتيح لك الأمر `-take` سحب النقاط من البنك لاستخدامها في الشراء أو التحديات.",
        inline=False
    )

    embed.set_footer(text="استخدم هذه الأوامر لكسب وإنفاق النقاط في السيرفر!")

    embed.set_image(url="https://cdn.discordapp.com/attachments/1277379592247574539/1278438677433028618/image.png?ex=66d0ce4c&is=66cf7ccc&hm=7aaf2bedcfc315b58812420bd7430009e97cb8e4ffff40ec6586f460d24e9d5b&")

    await message.channel.send(embed=embed)



async def handle_dress_command(message):
    user_id = str(message.author.id)
    current_points = get_user_points(user_id)


    try:
        hat_choice = await get_choice_with_buttons(message, hat_options + ['None'],
                                                   message.author)
        top_choice = await get_choice_with_buttons(message, top_options + ['None'],
                                                   message.author)
        bottom_choice = await get_choice_with_buttons(
            message, bottom_options + ['None'], message.author)
        dress_choice = await get_choice_with_buttons(message,
                                                     dress_options + ['None'],
                                                     message.author)
        shoes_choice = await get_choice_with_buttons(message, shoe_options + ['None'],
                                                     message.author)
        color_choice = await get_choice_with_buttons(message, color_options + ['None'],
                                                     message.author)

        # Count the number of "None" choices
        none_count = sum(
            [choice == 'None' for choice in [hat_choice,top_choice,shoes_choice,color_choice,bottom_choice, dress_choice]])

        # Check if there are 3 or more "None" choices
        if none_count >= 3:
            await message.channel.send(
                f"{message.author.mention} https://media.discordapp.net/attachments/1276917351811645521/1277681613928402958/Picsart_24-08-18_20-03-45-756.jpg?ex=66ce0d3a&is=66ccbbba&hm=2030e6b5f1314d73187e249b98da38615f911b7c30e54747cc32f9ca8b112862&=&format=webp&width=328&height=437"
            )
            return

        # Construct the prompt
        prompt = f"Create a detailed image of a white anime character. The character is wearing a {hat_choice}, {top_choice}, "
        if bottom_choice != 'None':
            prompt += f"{bottom_choice}, "
        if dress_choice != 'None':
            prompt += f"{dress_choice}, "
        prompt += f"{shoes_choice} in {color_choice} color. The character should stand confidently with an expressive face. The background could be a modern cityscape, a stylized anime landscape, or a contemporary room, enhancing the character's fashionable appearance."

        await message.channel.send(
            f"{message.author.mention}, generating your anime character...")

        image_file = await generate_image(prompt)

        file = discord.File(image_file, filename="character.png")
        await message.channel.send(
            f"Character created by {message.author.mention}:", file=file)

    except Exception as e:
        await message.channel.send(
            f"{message.author.mention}, an error occurred: {str(e)}")


async def get_choice_with_buttons(message, options, user):
    view = discord.ui.View()
    chosen_option = None

    for option in options:
        button = discord.ui.Button(label=option, custom_id=option)

        async def button_callback(interaction):
            nonlocal chosen_option
            if interaction.user != user:
                await interaction.response.send_message(
                    "This button is not for you!", ephemeral=True)
                return
            chosen_option = interaction.data['custom_id']
            await interaction.response.send_message(
                f"You chose: {chosen_option}", ephemeral=True)
            view.stop()

        button.callback = button_callback
        view.add_item(button)

    choice_message = await message.channel.send(
        f"{user.mention}, choose an option:", view=view)
    await view.wait()
    await choice_message.delete()

    return chosen_option


async def generate_job(prompt, seed=None):
    if seed is None:
        seed = random.randint(10000, 99999)

    url = "https://api.prodia.com/generate"
    params = {
        "new": "true",
        "prompt": f"{urllib.parse.quote(prompt)}",
        "model": "v1-5-pruned-emaonly.safetensors [d7049739]",
        "negative_prompt":
        "(nsfw:1.5), (ugly face:0.8), cross-eyed, sketches, bad anatomy, extra digit, mutation, nudity",
        "steps": "30",
        "cfg": "9.5",
        "seed": f"{seed}",
        "sampler": "Euler",
        "aspect_ratio": "square",
    }
    headers = {
        "authority": "api.prodia.com",
        "accept": "*/*",
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params,
                               headers=headers) as response:
            data = await response.json()
            return data["job"]


async def generate_image(prompt):
    job_id = await generate_job(prompt)
    url = f"https://api.prodia.com/job/{job_id}"
    headers = {
        "authority": "api.prodia.com",
        "accept": "*/*",
    }

    async with aiohttp.ClientSession() as session:
        while True:
            await asyncio.sleep(0.3)
            async with session.get(url, headers=headers) as response:
                json = await response.json()
                if json["status"] == "succeeded":
                    async with session.get(
                            f"https://images.prodia.xyz/{job_id}.png?download=1",
                            headers=headers,
                    ) as response:
                        content = await response.content.read()
                        img_file_obj = io.BytesIO(content)
                        return img_file_obj
async def handle_picture_command(message):
    # Check if the command is used in the specific channel
    if message.channel.id != 1267858595802779648:
        await message.channel.send("This command can only be used in the designated channel.")
        return

    user_id = str(message.author.id)
    current_points = get_user_points(user_id)

    # Ensure user has enough points
    if current_points < 5:
        await message.channel.send(f"{message.author.mention}, you need at least 5 points to generate an image.")
        return

    try:
        # Extract the prompt from the message content
        command_prefix = "-picture"
        user_prompt = message.content[len(command_prefix):].strip()

        if not user_prompt:
            await message.channel.send(f"{message.author.mention}, please provide a prompt after the command.")
            return

        await message.channel.send(f"{message.author.mention}, generating your image based on: `{user_prompt}`")

        # Generate the image with the provided prompt
        image_file = await generate_image(user_prompt)

        # Deduct 5 points from the user
        update_user_points(user_id, -5)

        # Send the generated image
        file = discord.File(image_file, filename="generated_image.png")
        await message.channel.send(f"Generated by {message.author.mention}:", file=file)

    except Exception as e:
        await message.channel.send(f"An error occurred: {str(e)}")

async def handle_ynk_command(message):
    user_id = str(message.author.id)
    daily_usage = load_daily_usage()

    if not isinstance(daily_usage, dict):
        daily_usage = {}

    if user_id not in daily_usage:
        daily_usage[user_id] = {
            "daily": False,
            "special": False,
            "risk": False,
            "quests": False  
        }
    else:
        if "quests" not in daily_usage[user_id]:
            daily_usage[user_id]["quests"] = False

    await get_or_create_user(user_id, message.author.name)
      
    role_id = 1278375524368125962
    role = message.guild.get_role(role_id)
    if role not in message.author.roles:
        await message.author.add_roles(role)
        await message.channel.send(f"{message.author.mention}, you have been given the role {role.name}.")

    embed = discord.Embed(
        title="مساعدة أوامر البوت",
        description="نظام النقاط هو لعبة ممتعة في السيرفر تتيح لك شراء الأدوار والميزات داخل السيرفر، مع العديد من التحديثات القادمة قريبًا!",
        color=discord.Color.blue()
    )


    embed.set_footer(text="استخدم هذه الأوامر لكسب وإنفاق النقاط في السيرفر!")

    embed.set_image(url="https://media.discordapp.net/attachments/1285016876056842391/1294100386772160574/image.png?ex=670b19e7&is=6709c867&hm=52dfee18c5e08dd31b1f8cef49bc5a2365c173657d604c1ef497e7233d52b3eb&=&format=webp&quality=lossless&width=427&height=662")

    await message.channel.send(embed=embed)


async def handle_bonus_command(message):
    user_id = str(message.author.id)
    
    # Load the daily usage data
    daily_usage = load_daily_usage()

    # Ensure the user exists in the daily_usage, otherwise initialize their data
    if user_id not in daily_usage:
        daily_usage[user_id] = {
            "daily": False,
            "special": False,
            "risk": False,
            "quests": False,
            "bonus": False  # Adding the 'bonus' key for daily tracking of bonus
        }
    
    # Check if the bonus has already been claimed today
    if daily_usage[user_id]["bonus"]:
        await message.channel.send(f"{message.author.mention}, you have already claimed your bonus today. Please try again tomorrow.")
        return

    # Check if the user is in a family and the family is active
    family_data = get_user_data(user_id)  # Assuming this function fetches family info from the DB
    if family_data["family"] is None or family_data["family_active"].lower() != "yes":
        await message.channel.send(f"{message.author.mention}, you are either not in a family or your family is not active.")
        return

    # Grant the bonus points and update daily usage
    points = 3  # Example bonus points
    update_user_points(user_id, points)  # Assume this function updates user points in the DB
    daily_usage[user_id]["bonus"] = True  # Mark the bonus as claimed for today
    save_daily_usage(daily_usage)  # Save the updated daily usage to file

    await message.channel.send(f"{message.author.mention}, you've received {points} bonus points for being in an active family!")

async def handle_load_command(message):
    if message.author.id != bot_owner_id and not any(
            role.id == 1267858269888839721 for role in message.author.roles):
        await message.channel.send(
            "You don't have permission to use this command.")
        return

    parts = message.content.split()
    if len(parts) != 3:
        await message.channel.send("Usage: -load @user amount")
        return

    try:
        target_user = message.mentions[0]
        amount = int(parts[2])
    except (IndexError, ValueError):
        await message.channel.send("Please mention a valid user and amount.")
        return

    user_id = str(target_user.id)
    get_or_create_user(user_id, target_user.name)
    update_user_points(user_id, amount)

    await message.channel.send(
        f"Successfully added {amount} points to {target_user.mention}.")

async def handle_daily_command(message):
    user_id = str(message.author.id)
    daily_usage = load_daily_usage()

    if not isinstance(daily_usage, dict):
        daily_usage = {}

    if user_id not in daily_usage:
        daily_usage[user_id] = {
            "daily": False,
            "special": False,
            "risk": False,
            "quests": False  
        }
    else:
        if "quests" not in daily_usage[user_id]:
            daily_usage[user_id]["quests"] = False

    get_or_create_user(user_id, message.author.name)
      
    role_id = 1278375524368125962
    role = message.guild.get_role(role_id)
    if role not in message.author.roles:
        await message.author.add_roles(role)
        await message.channel.send(f"{message.author.mention}, you have been given the role {role.name}.")
    # Check if the daily has already been claimed
    if daily_usage[user_id]["daily"]:
        await message.channel.send(f"{message.author.mention}, لقد استخدمت هذا الزر اليوم، عد غدًا.")
        return

    # Give daily points and update usage
    points = random.randint(1, 5)
    update_user_points(user_id, points)
    daily_usage[user_id]["daily"] = True
    save_daily_usage(daily_usage)

    await message.channel.send(f"{message.author.mention}, لقد حصلت على {points} نقاط من مكافأتك اليومية!")

async def handle_loyal_command(message):
    user_id = str(message.author.id)
    daily_usage = load_daily_usage()

    # Ensure the user exists in the daily_usage, otherwise initialize
    if user_id not in daily_usage:
        daily_usage[user_id] = {
            "daily": False,
            "special": False,
            "risk": False,
            "quests": False
        }
    
    # Check if the special has already been claimed
    if daily_usage[user_id]["special"]:
        await message.channel.send(f"{message.author.mention}, لقد استخدمت هذا الزر اليوم، عد غدًا.")
        return

    # Check if the user has the special role
    if special_role_id in [role.id for role in message.author.roles]:
        points = 3
        update_user_points(user_id, points)
        daily_usage[user_id]["special"] = True
        save_daily_usage(daily_usage)
        await message.channel.send(f"{message.author.mention}, لقد حصلت على {points} نقاط خاصة!")
    else:
        await message.channel.send(f"{message.author.mention}, ليس لديك الدور المطلوب لهذه المكافأة.")

async def handle_risk_command(message):
    user_id = str(message.author.id)
    daily_usage = load_daily_usage()

    # Ensure the user exists in the daily_usage, otherwise initialize
    if user_id not in daily_usage:
        daily_usage[user_id] = {
            "daily": False,
            "special": False,
            "risk": False,
            "quests": False,
        }

    # Check if the risk has already been claimed
    if daily_usage[user_id]["risk"]:
        await message.channel.send(f"{message.author.mention}, لقد استخدمت هذا الزر اليوم، عد غدًا.")
        return

    # Handle risk-based point gain/loss
    chance = random.random()
    if chance < 0.5:
        points = random.randint(1, 3)
        update_user_points(user_id, points)
        await message.channel.send(f"{message.author.mention}, لقد أخذت مخاطرة وربحت {points} نقاط!")
    else:
        current_points = get_user_points(user_id)
        points_lost = min(current_points, random.randint(1, 3))
        update_user_points(user_id, -points_lost)
        await message.channel.send(f"{message.author.mention}, لقد أخذت مخاطرة وخسرت {points_lost} نقاط!")

    daily_usage[user_id]["risk"] = True
    save_daily_usage(daily_usage)


async def handle_quests_command(message):
    embed = discord.Embed(
        title="المهام المتاحة",
        description="هنا المهام التي يمكنك إكمالها للحصول على نقاط إضافية."
    )
    embed.add_field(
        name="المهام",
        value=(
            "1. **كن نشطًا في المحادثات الصوتية** - اقضِ ساعة واحدة في المحادثة الصوتية. يمكنك القيام بهذه المهمة 3 مرات في اليوم. *(المكافأة 3 نقاط)*\n"
            "2. **كن نشطًا في المحادثات النصية** -اكثر شخص نشاطا في السيرفر اسبوعيا  *(المكافأة: 15 نقطة)*\n"
            "3. **ادعُ صديقًا** - ادخال اصدقاء للسيرفر ثم افتح تكت للحصول على النقاط *(المكافأة: 5 نقاط)*\n"
        ),
        inline=False
    )
    await message.channel.send(embed=embed)
async def handle_take_command(message):
    if message.author.id != bot_owner_id and not any(
            role.id == 1267858269888839721 for role in message.author.roles):
        await message.channel.send(
            "You don't have permission to use this command.")
        return

    parts = message.content.split()
    if len(parts) != 3:
        await message.channel.send("Usage: -take @user amount")
        return

    try:
        target_user = message.mentions[0]
        amount = int(parts[2])
    except (IndexError, ValueError):
        await message.channel.send("Please mention a valid user and amount.")
        return

    user_id = str(target_user.id)
    get_or_create_user(user_id, target_user.name)
    current_points = get_user_points(user_id)

    if amount > current_points:
        await message.channel.send(
            f"{target_user.mention} does not have enough points.")
        return

    update_user_points(user_id, -amount)
    await message.channel.send(
        f"Successfully removed {amount} points from {target_user.mention}.")
async def handle_family_command(message):
    if message.author.id != bot_owner_id and not any(
            role.id == 1267858269888839721 for role in message.author.roles):
        await message.channel.send(
            "You don't have permission to use this command.")
        return

    parts = message.content.split()
    
    # Ensure the command has exactly 3 parts: command, mention, and family role ID
    if len(parts) != 3:
        await message.channel.send("Usage: -family @user family_role_id")
        return

    try:
        target_user = message.mentions[0]  # Get the mentioned user object
        family_role_id = parts[2]  # Family role ID (as the third part)
    except (IndexError, ValueError):
        await message.channel.send("Please mention a valid user and family role ID.")
        return

    user_id = str(target_user.id)
    get_or_create_user(user_id, target_user.name)
    
    # Update the family role in the database
    update_user_family(user_id, family_role_id)
    
    await message.channel.send(
        f"Successfully added family role {family_role_id} to {target_user.mention}."
    )



def update_user_family(user_id, family_role):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            sql = "UPDATE users SET family = %s WHERE id = %s"
            cursor.execute(sql, (family_role, user_id))
            connection.commit()
    finally:
        connection.close()

async def handle_removefamily_command(message):
    if message.author.id != bot_owner_id and not any(
            role.id == 1267858269888839721 for role in message.author.roles):
        await message.channel.send(
            "You don't have permission to use this command.")
        return

    parts = message.content.split()

    # Ensure the command has exactly 2 parts: command and mention
    if len(parts) != 2:
        await message.channel.send("Usage: -removefamily @user")
        return

    try:
        target_user = message.mentions[0]  # Get the mentioned user object
    except IndexError:
        await message.channel.send("Please mention a valid user.")
        return

    user_id = str(target_user.id)
    
    # Remove the family role from the database
    update_user_family(user_id, None)
    
    await message.channel.send(
        f"Successfully removed family role from {target_user.mention}."
    )

async def handle_setfamilyactive_command(message):
    if message.author.id != bot_owner_id and not any(
            role.id == 1267858269888839721 for role in message.author.roles):
        await message.channel.send(
            "You don't have permission to use this command.")
        return

    parts = message.content.split()
    
    # Make sure the command has exactly 3 parts: command, user mention, and yes/no
    if len(parts) != 3:
        await message.channel.send("Usage: -setfamilyactive @user yes|no")
        return

    # Extract the mentioned user and the yes/no argument
    try:
        target_user = message.mentions[0]  # Mentioned user object
        family_active = parts[2].lower()  # yes or no (case insensitive)
        if family_active not in ['yes', 'no']:
            raise ValueError
    except (IndexError, ValueError):
        await message.channel.send("Please mention a valid user and set family active to 'yes' or 'no'.")
        return

    user_id = str(target_user.id)
    
    # Update family_active status in the database
    update_user_family_active(user_id, family_active)
    
    await message.channel.send(
        f"Successfully set family active to {family_active} for {target_user.mention}."
    )

def update_user_family_active(user_id, family_active):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            sql = "UPDATE users SET family_active = %s WHERE id = %s"
            cursor.execute(sql, (family_active, user_id))
            connection.commit()
    finally:
        connection.close()




async def handle_points_command(message):
    # Extract the content after the command
    args = message.content.split()

    if len(args) == 2:
        # If an argument is provided, check if it's a mention or ID
        identifier = args[1]

        if identifier.isdigit():
            # If it's a digit, assume it's a user ID
            user_id = identifier
            user = await message.guild.fetch_member(user_id)
        elif message.mentions:
            # If it's a mention, get the mentioned user
            user = message.mentions[0]
            user_id = str(user.id)
        else:
            user_id = None
            user = None
    else:
        # No argument provided, use the message author
        user_id = str(message.author.id)
        user = message.author

    if user_id:
        current_points = get_user_points(user_id)
        # Create an embed for displaying the points
        embed = discord.Embed(
            title="User Points",
            description=f"{user.mention} currently has {current_points} points <:ynk_points:1294654518067335229>.",
            color=discord.Color.blue()
        )
        # Add additional message as a field
        embed.add_field(
            name="Don't forget!",
            value="لا تنسى اخذ مكافئتك الاضافية من موقعنا: [YNK Website](https://ynk-rho.vercel.app/)",
            inline=False
        )
        await message.channel.send(embed=embed)
    else:
        await message.channel.send(
            f"{message.author.mention}, please provide a valid user mention or ID."
        )



async def update_expired_status(message):
    if message.author.id != bot_owner_id and not any(
            role.id == 1267858269888839721 for role in message.author.roles):
        await message.channel.send(
            "You don't have permission to use this command.")
        return
    
    connection = get_db_connection()
    now = datetime.now()

    try:
        with connection.cursor() as cursor:
            # Fetch all users that have non-null expiry dates for various features
            sql = """
            SELECT id, emoji_expiry, rage_mode_expiry, lawyer_expiry, shield_expiry
            FROM users
            WHERE 
                (emoji IS NOT NULL AND emoji_expiry IS NOT NULL)
                OR (rage_mode_expiry IS NOT NULL)
                OR (lawyer_expiry IS NOT NULL)
                OR (shield_expiry IS NOT NULL)
            """
            cursor.execute(sql)
            results = cursor.fetchall()

            # Prepare the update queries
            update_queries = []
            for row in results:
                user_id = row['id']
                
                # Check if the emoji has expired
                if row['emoji_expiry'] and isinstance(row['emoji_expiry'], datetime):
                    if row['emoji_expiry'] <= now:
                        update_queries.append(f"""
                        UPDATE users
                        SET emoji = NULL, emoji_expiry = NULL
                        WHERE id = {user_id}
                        """)
                
                # Check if the rage mode has expired
                if row['rage_mode_expiry'] and isinstance(row['rage_mode_expiry'], datetime):
                    if row['rage_mode_expiry'] <= now:
                        update_queries.append(f"""
                        UPDATE users
                        SET rage_mode = 0, rage_mode_expiry = NULL, rage_steals = 0, rage_vulnerabilities = 0
                        WHERE id = {user_id}
                        """)
                
                # Check if the lawyer has expired
                if row['lawyer_expiry'] and isinstance(row['lawyer_expiry'], datetime):
                    if row['lawyer_expiry'] <= now:
                        update_queries.append(f"""
                        UPDATE users
                        SET lawyer = 0, lawyer_expiry = NULL
                        WHERE id = {user_id}
                        """)

                # Check if the shield has expired
                if row['shield_expiry'] and isinstance(row['shield_expiry'], datetime):
                    if row['shield_expiry'] <= now:
                        update_queries.append(f"""
                        UPDATE users
                        SET shield = 0, shield_expiry = NULL
                        WHERE id = {user_id}
                        """)

            # Execute all update queries
            for query in update_queries:
                cursor.execute(query)

            # Commit the changes
            connection.commit()

            # Inform the bot owner or the person who used the command
            await message.channel.send(f"Expired statuses for emoji, rage mode, lawyers, and shields have been updated.")

    finally:
        connection.close()  # Ensure the connection is closed

cooldowns = {}
async def handle_steal_command(message):
    stealer_id = str(message.author.id)
    now = datetime.now()
    
    # Check for cooldown
    if stealer_id in cooldowns:
        last_attempt_time = cooldowns[stealer_id]
        if now < last_attempt_time + timedelta(seconds=15):
            remaining_time = (last_attempt_time + timedelta(seconds=15) - now).seconds
            await message.channel.send(f"يرجى الانتظار {remaining_time} ثانية قبل محاولة السرقة مرة أخرى.")
            return

    # Ensure exactly one user is mentioned
    if len(message.mentions) != 1:
        await message.channel.send("يرجى ذكر مستخدم واحد ليتم سرقته.")
        return
    
    victim = message.mentions[0]
    victim_id = str(victim.id)

    # Prevent self-stealing
    if stealer_id == victim_id:
        await message.channel.send("لا يمكنك سرقة نفسك!")
        return

    # Load data
    steal_attempts = load_steal_attempts()
    steal_victims = load_steal_victims()

    # Initialize data if not present
    if stealer_id not in steal_attempts:
        steal_attempts[stealer_id] = 0
    
    if victim_id not in steal_victims:
        steal_victims[victim_id] = 0

    stealer_data = get_user_data(stealer_id)
    victim_data = get_user_data(victim_id)

    # Shield check
    if stealer_data['shield'] > 0 and stealer_data['shield_expiry'] > now:
        await message.channel.send("لا يمكنك السرقة أثناء تفعيل الدرع.")
        return
    
    if victim_data['shield'] > 0 and victim_data['shield_expiry'] > now:
        await message.channel.send(f"{victim.mention} لديه درع نشط. لا يمكنك سرقته.")
        return

    # Rage mode check
    if stealer_data['rage_mode'] > 0 and stealer_data['rage_mode_expiry'] > now and stealer_data['rage_steals'] > 0:
        stealer_data['rage_steals'] -= 1
        update_user_data(stealer_id, rage_steals=stealer_data['rage_steals'])
    elif stealer_data['rage_mode'] > 0 and (stealer_data['rage_mode_expiry'] <= now or stealer_data['rage_steals'] == 0):
        await message.channel.send("لقد استنفدت جميع محاولات السرقة في وضع الغضب أو انتهت مدة الفعالية.")
        return
    else:
        # Check for daily steal limits
        if steal_attempts[stealer_id] >= 3:
            await message.channel.send("لقد استخدمت بالفعل محاولات السرقة الثلاث اليوم.")
            return
        
        # Check if the victim has already been stolen from today
        if steal_victims[victim_id] >= 1:
            await message.channel.send(f"تمت سرقة {victim.mention} بالفعل اليوم.")
            return
        
        # Increment attempt counters
        steal_attempts[stealer_id] += 1
        steal_victims[victim_id] += 1

    # Perform the steal attempt
    success = random.random() < 0.5  # 50% chance of success

    if success:
        stolen_points = random.randint(1, 4)
        victim_points = get_user_points(victim_id)
        stolen_points = min(stolen_points, victim_points)
        
 
        if stealer_data['bags'] > 0:
            stolen_points *= 2
            update_user_data(stealer_id, bags=stealer_data['bags'] - 1)
            await message.channel.send(f"تم استخدام حقيبة مضاعفة النقاط، النقاط المسروقة مضاعفة إلى {stolen_points}.")


        if stolen_points > 6:
            fine = 2
            update_user_points(stealer_id, -fine)  
            update_user_points(victim_id, stolen_points)  
            await message.channel.send(
                f"{message.author.mention} سرق {stolen_points} نقاط من {victim.mention}، لكن حصل على غرامة 10 نقاط وتمت إعادة النقاط!"
            )
        else:

            update_user_points(victim_id, -stolen_points)
            update_user_points(stealer_id, stolen_points)

            if victim_data['lawyer'] > 0 and victim_data['lawyer_expiry'] > now:
                update_user_points(victim_id, stolen_points)  
                victim_data['lawyer'] -= 1
                update_user_data(victim_id, lawyer=victim_data['lawyer'])
                await message.channel.send(
                    f"{message.author.mention} نجح في سرقة {stolen_points} نقاط من {victim.mention}، لكن المحامي أعاد النقاط المسروقة!"
                )
            else:
                await message.channel.send(
                    f"{message.author.mention} نجح في سرقة {stolen_points} نقاط من {victim.mention}!"
                )
    else:
        lost_points = 2
        current_points = get_user_points(stealer_id)
        lost_points = min(lost_points, current_points)
        update_user_points(stealer_id, -lost_points)

        if stealer_data['lawyer'] > 0 and stealer_data['lawyer_expiry'] > now:
            update_user_points(stealer_id, lost_points)  
            stealer_data['lawyer'] -= 1
            update_user_data(stealer_id, lawyer=stealer_data['lawyer'])
            await message.channel.send(
                f"{message.author.mention} فشل في السرقة وخسر {lost_points} نقاط، لكن المحامي استعاد النقاط المفقودة!"
            )
        else:
            await message.channel.send(
                f"{message.author.mention} فشل في السرقة وخسر {lost_points} نقاط!"
            )

    save_steal_attempts(steal_attempts)
    save_steal_victims(steal_victims)

    cooldowns[stealer_id] = now

async def handle_heist_command(message):
    stealer_id = str(message.author.id)
    now = datetime.now()

    # Check for cooldown
    if stealer_id in cooldowns:
        last_attempt_time = cooldowns[stealer_id]
        if now < last_attempt_time + timedelta(minutes=5):  # 5-minute cooldown
            remaining_time = (last_attempt_time + timedelta(minutes=5) - now).seconds
            await message.channel.send(f"⏳ يرجى الانتظار {remaining_time // 60} دقيقة و {remaining_time % 60} ثانية قبل محاولة السطو مرة أخرى.")
            return

    # Check if user has enough points
    stealer_points = get_user_points(stealer_id)
    if stealer_points < 50:
        await message.channel.send("💸 يجب أن تمتلك على الأقل 50 نقطة لتنفيذ عملية السطو.")
        return

    # Deduct 50 points for the heist
    update_user_points(stealer_id, -50)

    # Retrieve all users from the database and filter out ineligible targets
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT id, points, shield, shield_expiry FROM users")
            all_users = cursor.fetchall()
            targets = [
                {
                    "id": user['id'],
                    "points": user['points']
                }
                for user in all_users
                if user['id'] != stealer_id and user['points'] > 0 and 
                (user['shield'] == 0 or (user['shield_expiry'] and user['shield_expiry'] <= now))
            ]
    finally:
        connection.close()

    if not targets:
        await message.channel.send("🚫 لا يوجد أهداف متاحة للسرقة بسبب وجود دروع أو نقص النقاط.")
        return

    # Determine success or failure (40% success rate)
    success = random.random() < 0.4

    if success:
        total_stolen_points = random.randint(25, 100)
        stolen_points_per_target = []
        
        random.shuffle(targets)
        
        for target in targets:
            target_id = target['id']
            target_points = target['points']
            points_to_steal = min(random.randint(1, target_points), total_stolen_points)
            update_user_points(target_id, -points_to_steal)
            total_stolen_points -= points_to_steal
            stolen_points_per_target.append((target_id, points_to_steal))

            if total_stolen_points <= 0:
                break
        
        update_user_points(stealer_id, sum(points for _, points in stolen_points_per_target))
        target_names = ", ".join([f"<@{target_id}>" for target_id, _ in stolen_points_per_target])
        
        await message.channel.send(
            f"🏴‍☠️ {message.author.mention} نفذ عملية سطو ناجحة وسرق {sum(points for _, points in stolen_points_per_target)} نقاط من: {target_names}!"
        )
    else:
        # Failed heist - assign penalty role
        role = message.guild.get_role(1281737638063243274)
        await message.author.add_roles(role)
        await message.channel.send(
            f"🔒 {message.author.mention} فشل في عملية السطو وتم منحه الدور <@&{1281737638063243274}>!"
        )

    # Save cooldown time
    cooldowns[stealer_id] = now

async def handle_shop_command(message):
    embed = discord.Embed(
        title="المتجر",
        description="اختر عنصرًا للشراء باستخدام الأمر `-buy <رقم العنصر>`:",
        color=discord.Color.blue()
    )

    embed.set_image(url="https://media.discordapp.net/attachments/1285016876056842391/1294094675728269384/image.png?ex=670b1495&is=6709c315&hm=9d487ae7f3c6ce4c421f445695dc1895f2cd62ec2d9f221fe69f05d675db0237&=&format=webp&quality=lossless&width=412&height=662")
    await message.channel.send(embed=embed)

def start_vc(user_id):
    data = load_vc_data()

    if str(user_id) not in data:
        data[str(user_id)] = {
            "total_time": 0,
            "bonus_received": 0,
            "last_join": datetime.now().isoformat()
        }
    else:
        data[str(user_id)]["last_join"] = datetime.now().isoformat()

    save_vc_data(data)


def end_vc(user_id):
    data = load_vc_data()

    if str(user_id) in data and "last_join" in data[str(user_id)]:
        last_join = datetime.fromisoformat(data[str(user_id)]["last_join"])
        now = datetime.now()
        time_spent = (now - last_join).total_seconds() / 60  

        data[str(user_id)]["total_time"] += time_spent

        if data[str(user_id)]["total_time"] >= 60:
            if data[str(user_id)]["bonus_received"] < 3:

                update_user_points(user_id, 3)
                data[str(user_id)]["bonus_received"] += 1
            else:

                update_user_points(user_id, 1)

            data[str(user_id)]["total_time"] -= 60 

        save_vc_data(data)

@client.event
async def on_voice_state_update(member, before, after):
    if before.channel is None and after.channel is not None:
        start_vc(member.id)
    elif before.channel is not None and after.channel is None:
        end_vc(member.id)



@tasks.loop(hours=24)
async def cleanup_expired_emoji_reactions():
    connection = get_db_connection()
    now = datetime.now()

    try:
        with connection.cursor() as cursor:
            sql = """
            DELETE FROM users
            WHERE emoji_expiry IS NOT NULL AND emoji_expiry <= %s
            """
            cursor.execute(sql, (now,))
            connection.commit()
    finally:
        connection.close()

    print("Expired emoji reactions have been removed from the database.")



async def handle_auto_react(message):
    emoji_reactions =  load_emoji_reactions()

    for user in message.mentions:
        user_id = str(user.id)
        if user_id in emoji_reactions:
            emoji = emoji_reactions[user_id]
            try:
                await message.add_reaction(emoji)
            except Exception as e:
                print(f"Failed to add reaction {emoji} for user {user_id}: {e}")
                
async def reset_vc_data():
    with open(vc_data_file, 'w') as f:
         json.dump({}, f)
    print("VC data reset.")
def reset_daily_usage():

    with open('daily_usage.json', 'r') as file:
        daily_usage_data = json.load(file)['daily_usage']
    

    for record in daily_usage_data:
        record['daily'] = 0
        record['special'] = 0
        record['risk'] = 0
        record['quests'] = 0
        record['bonus'] = 0 


    with open('daily_usage.json', 'w') as file:
        json.dump({"daily_usage": daily_usage_data}, file, indent=4)

    print("Daily usage data has been reset.")
def get_all_users_data():
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            sql = """
            SELECT id, lawyer, lawyer_expiry, shield, shield_expiry, rage_mode, rage_mode_expiry, rage_steals, rage_vulnerabilities,
                   emoji, emoji_expiry, family, family_active
            FROM users
            """
            cursor.execute(sql)
            result = cursor.fetchall()
            if result:
                return [
                    {
                        "id": row['id'],
                        "lawyer": row['lawyer'],
                        "lawyer_expiry": row['lawyer_expiry'],
                        "shield": row['shield'],
                        "shield_expiry": row['shield_expiry'],
                        "rage_mode": row['rage_mode'],
                        "rage_mode_expiry": row['rage_mode_expiry'],
                        "rage_steals": row['rage_steals'],
                        "rage_vulnerabilities": row['rage_vulnerabilities'],
                        "emoji": row['emoji'],
                        "emoji_expiry": row['emoji_expiry'],
                        "family": row['family'],
                        "family_active": row.get('family_active', 'No')
                    }
                    for row in result
                ]
            else:
                return []
    finally:
        connection.close()

async def reset_rage_mode():
    now = datetime.now()
    max_rage_steals = 5
    max_rage_vulnerabilities = 5
    all_users = get_all_users_data()

    for user_data in all_users:
        if user_data['rage_mode'] > 0 and user_data['rage_mode_expiry'] > now:

            if user_data['family'] and user_data['family_active'] == 'Yes':
                user_data['rage_steals'] = max_rage_steals
                user_data['rage_vulnerabilities'] = max_rage_vulnerabilities
                update_user_data(
                    user_data['id'],
                    rage_steals=user_data['rage_steals'],
                    rage_vulnerabilities=user_data['rage_vulnerabilities']
                )

    print("Rage mode steals and vulnerabilities have been reset for active family members.")


@tasks.loop(seconds=1)
async def daily_reset():
    now = datetime.now()

    # Check if the time is exactly 20:00:00 (hour 20, minute 0, second 0)
    if now.hour == 20 and now.minute == 0 and now.second == 0:
        print('Performing daily reset...')

        notification_channel_id = 1278306906036899860  # Replace with your actual channel ID
        role_id = 1278375524368125962  # Replace with your actual role ID
        role_mention = f"<@&{role_id}>"

        reset_daily_usage()  
        await reset_vc_data() 
        await reset_rage_mode()  

        with open(steal_attempts_file, 'w') as f:
            json.dump({}, f)
        with open(steal_victims_file, 'w') as f:
            json.dump({}, f)
        print("Steal data reset.")

        notification_channel = client.get_channel(notification_channel_id) 
        if notification_channel:
            await notification_channel.send(
                f"{role_mention}, daily commands and quests have been reset! You can use them again."
            )

    await asyncio.sleep(1)  

DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
if not DISCORD_TOKEN:
    raise ValueError("No DISCORD_TOKEN environment variable set.")
keep_alive()
client.run(DISCORD_TOKEN)
