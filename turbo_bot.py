import discord
from discord.ext import commands, tasks
import json
import asyncio
import mu
import os
import argparse
import random
import requests
import csv
from bs4 import BeautifulSoup
import pandas as pd
import re

intents = discord.Intents.default()
intents.typing = False
intents.presences = False
intents.message_content = True
intents.messages = True
intents.reactions = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix='!', case_insensitive=True, intents=intents, help_command=None)

player_limit = 10
players = {}
waiting_list = {}
recruit_list = {}
spec_list = {}
recruit_timer = 0
aliases = {}
dvc_roles = {}
message_ids = {}
game_host_name = ["Turby"]
mods = [178647349369765888]
current_game = None
current_setup = "joat10"
current_timer = "14-3"
valid_setups = ["joat10", "vig10", "bomb10", "bml10", "ita10", "ita13", "cop9", "cop13", "doublejoat13", "random10er", "closedrandomXer"] #future setups
valid_timers = ["12-12", "36-12", "48-24"] # 12/12, 36/12, 48/24
day_length = 12
night_length = 12
allowed_channels = [1287607575377875098]  # 1287607575377875098 signups, 
all_channels = [1287607575377875098] #signups
react_channels = [1287607575377875098, 1287597070865141830] #signups and spec chat links
banned_users = [1173036536166621286]
future_banned = [190312702692818946]
dvc_channel = 1287597070865141830  # ongoing game links
dvc_server = 1264753929678487563   # DVC Server id
anon_enabled = False
baitping = False

status_id = None
status_channel = None
is_rand_running = False
SNG_ping_message = None
    
def load_flavor_json(file):
    try:
        with open(file, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_flavor_json(file, existing_flavor):
    with open(file, 'w') as f:
        json.dump(existing_flavor, f, indent=4)

def save_aliases():
    with open('aliases.json', 'w') as f:
        json.dump(aliases, f, indent=4)

def load_aliases():
    try:
        with open("aliases.json", "r") as f:
            loaded_aliases = json.load(f)
            aliases.update({int(id): alias for id, alias in loaded_aliases.items()})
    except FileNotFoundError:
        pass

def save_dvc_roles():
    with open('dvc_roles.json', 'w') as f:
        json.dump(dvc_roles, f, indent=4)

def load_dvc_roles():
    try:
        with open("dvc_roles.json", "r") as f:
            loaded_dvc_roles = json.load(f)
            dvc_roles.update({int(id): alias for id, alias in loaded_dvc_roles.items()})
    except FileNotFoundError:
        pass

def save_player_list(player_list, waiting_list, current_setup, game_host_name, player_limit):
    with open('player_list_data.json', 'w') as f:
        json.dump({"player_list": player_list, "waiting_list": waiting_list, "current_setup": current_setup, "game_host_name": game_host_name, "player_limit": player_limit}, f, indent=4)
       
def load_player_list():
    global player_list, waiting_list, current_setup, game_host_name, player_limit
    try:
        with open('player_list_data.json', 'r') as f:
            data = json.load(f)
        player_list = data.get('player_list')
        waiting_list = data.get('waiting_list')
        current_setup = data.get('current_setup')
        game_host_name = data.get('game_host_name')
        player_limit = data.get('player_limit')
        return player_list, waiting_list, current_setup, game_host_name, player_limit
    except FileNotFoundError:
        return {}, {}, "joat 10", ["Turby"], 10
    except json.JSONDecodeError:
        return {}, {}, "joat 10", ["Turby"], 10
        
def find_key_by_value(dictionary, value):
    for key, val in dictionary.items():
        if val == value:
            return key
    return None

@bot.event
async def on_ready():
    global players, waiting_list, current_setup, game_host_name, player_limit, recruit_list, spec_list
    print(f"We have logged in as {bot.user}", flush=True)
    load_aliases()
    load_dvc_roles()
    players, waiting_list, current_setup, game_host_name, player_limit = load_player_list()
    if players is None:
        players = {}
    if waiting_list is None:
        waiting_list = {}
    if current_setup is None:
        current_setup = "joat10" 
    if game_host_name is None:
        game_host_name = ["Turby"] 
    if player_limit is None:
        player_limit = 10  
    update_players.start()  # Start background task

async def create_dvc(thread_id):
    guild = bot.get_guild(dvc_server)
    # DVC Archive cat_id
    # category_id = 1114340515006136411
    category_id = 1287550351435632714
    role = await guild.create_role(name=f"DVC: {thread_id}", permissions=discord.Permissions.none())
    dvc_roles[int(thread_id)] = role.id
    save_dvc_roles()
    await guild.me.add_roles(role)
    category = guild.get_channel(category_id)
    channel = await guild.create_text_channel(
        name = f"DVC {thread_id}",
        overwrites={
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            role: discord.PermissionOverwrite(read_messages=True)
        },
        category = category,
        position = 0

    )
    return role, channel.id, guild

async def create_wolf_chat(thread_id):
    guild = bot.get_guild(dvc_server)

    category_id = 1287550351435632714

    category = guild.get_channel(category_id)
    channel = await guild.create_text_channel(
        name = f"WC {thread_id}",
        overwrites={
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            #role: discord.PermissionOverwrite(read_messages=True)
        },
        category = category,
        position = 0

    )

    #return role, channel.id, guild
    return channel.id, guild

async def edit_dvc(channel, guild):

    global dvc_archive

    category = bot.get_channel(dvc_archive)
    # backup_category = bot.get_channel(backup_archive)
    channel_count = len(category.channels)

    if channel:
        #Set an overwrite for the default role so players can read messages in the channel after update
        permissions = channel.overwrites_for(guild.default_role)
        permissions.read_messages = True

        #Check to make sure we aren't at the channel cap for our primary category. If not, move channel to that category.
        #Otherwise we move to the backup category and create a help message to remind me to update this thing.
        if channel_count < 50:
            await channel.edit(category=category, position=1)
            await channel.edit(category=category, position=0)

        else:
            match = re.search(r'\d+$', category.name)
            if match:
                # Increment the numeric part and create the new category
                old_number = int(match.group())
                new_number = old_number + 1
                new_category_name = f'dvc archive {new_number}'
                new_category = await guild.create_category(name=new_category_name)
                await new_category.edit(position=2)
                await channel.edit(category=new_category, position=1)
                await channel.edit(category=new_category, position=0)
                dvc_archive = new_category.id
            
        await channel.set_permissions(guild.default_role, overwrite=permissions)
        await channel.send("This channel is now open to everyone")

async def delete_dvc_role(channel, role):
    guild = bot.get_guild(dvc_server)

    if role:
        try:
            await role.delete()
            await channel.send("DVC Role deleted for post-game clean up.")
        except:
            await channel.send("Failed to delete dvc role")

async def post_game_reply(thread_id, message):
    username = os.environ.get('MUUN')
    password = os.environ.get('MUPW')
    session = mu.login(username,password)
    game_id, security_token = mu.open_game_thread(session, thread_id)
    mu.post(session, thread_id, security_token, message)

async def start_itas(current_game):
    username = os.environ.get('MUUN')
    password = os.environ.get('MUPW')
    ita_session = mu.login(username, password)
    ita_game_id, ita_security_token = mu.open_game_thread(ita_session, current_game)
    mu.ita_window(ita_session, ita_game_id, ita_security_token)

async def get_wolf_info(game_title, setup_title):
    username = os.environ.get('MUUN')
    password = os.environ.get('MUPW')
    session = mu.login(username, password)
    mafia_players = []

    pms = session.get("https://www.mafiauniverse.com/forums/private.php")
    pm_html_list = BeautifulSoup(pms.text, 'html.parser')
    pm_list_parsed = pm_html_list.find_all('li', class_='blockrow pmbit')

    link = None
    for pm in pm_list_parsed:
        unread_span = pm.find('span', class_='unread')
        if unread_span:
            title = unread_span.find('a', class_='title')
            if title.text == f"{game_title} - [{setup_title} game] Host Information":
                link = title['href']

    base_url = "https://www.mafiauniverse.com/forums/"

    if link:
        link_content_html = session.get(base_url + link)
        link_content_parsed = BeautifulSoup(link_content_html.text, 'html.parser')
        mafia_section = link_content_parsed.find('font', string='Mafia Players (Roles)').find_next('br').find_all_next('b')

        for player in mafia_section:
            username = player.find('span', style="color: #ff2244;")
            if username:
                mafia_players.append(username.text)
    return mafia_players
            
    

class ThreadmarkProcessor:
    def __init__(self):
        self.processed_threadmarks = []

    async def process_threadmarks(self, thread_id, player_aliases, role, guild, channel_id, game_setup, current_game):

        while True:		
            url = f"https://www.mafiauniverse.com/forums/threadmarks/{thread_id}"
            response = requests.get(url)
            html = response.text
            soup = BeautifulSoup(html, "html.parser")
            event_div = soup.find("div", class_="bbc_threadmarks view-threadmarks")
            channel = bot.get_channel(channel_id)
            pl_list = [item.lower() for item in player_aliases]
            for i, row in enumerate(reversed(event_div.find_all("div", class_="threadmark-row"))):
                event = row.find("div", class_="threadmark-event").text
                
                if event in self.processed_threadmarks:
                    continue
                            
                await channel.send(event)
                            
                if "Elimination:" in event and " was " in event:
                    results = event.split("Elimination: ")[1].strip()
                    username = results.split(" was ")[0].strip().lower()
                    flavor = results.split(" was ")[1].strip().lower()
                    if username in aliases.values():
                        try:
                            mention_id = find_key_by_value(aliases, username)
                            member = guild.get_member(mention_id)
                            await member.add_roles(role)
                            # await channel.set_permissions(member, read_messages=True, send_messages=True)
                            await channel.send(f"<@{mention_id}> has been added to DVC.")
                        except:
                            await channel.send(f"{username} could not be added to DVC. They are not in the server or something else failed.")
                    else:
                        await channel.send(f"{username} could not be added to DVC. I don't have an alias for them!")                    
                    if "neil the eel" in flavor:
                        await post_game_reply(thread_id, "have you seen this fish\n[img]https://i.imgur.com/u9QjIqc.png[/img]\n now you have")



        
                elif "Results: No one died" in event or "Event" in event or "Game Information" in event:
                    pass

                elif ("Day 2 Start" in event) and (game_setup == 'ita10' or game_setup == 'ita13'):
                    await start_itas(current_game)
                
                #elif "In-Thread Attack: " in event:
                #    results = event.split()

                elif "Suicide Bomb (1):" in event:
                    results = event.split("Suicide Bomb (1):")[1].strip()
                    players = results.split(", ")
                    
                    for player in players:
                        username = None
                        if " was " in player:
                            username = player.split(" was ")[0].strip().lower()
                            flavor = results.split(" was ")[1].strip().lower()
                            if username in aliases.values():
                                try:
                                    mention_id = find_key_by_value(aliases, username)
                                    member = guild.get_member(mention_id)
                                    await member.add_roles(role)
                                    await channel.send(f"<@{mention_id}> has been added to DVC.")
                                except:
                                    await channel.send(f"{username} could not be added to DVC. They are not in the server or something else failed.")
                            if "neil the eel" in flavor:
                                await post_game_reply(thread_id, "have you seen this fish\n[img]https://i.imgur.com/u9QjIqc.png[/img]\n now you have")
                        else:
                            if username:
                                await channel.send(f"{username} could not be added to DVC. I don't have an alias for them!")
                    
                elif "Results:" in event:
                    results = event.split("Results:")[1].strip()
                    players = results.split(", ")
                    
                    for player in players:
                        if " was " in player:
                            username = player.split(" was ")[0].strip().lower()
                            flavor = results.split(" was ")[1].strip().lower()
                            if username in aliases.values():
                                try:
                                    mention_id = find_key_by_value(aliases, username)
                                    member = guild.get_member(mention_id)
                                    await member.add_roles(role)
                                    await channel.send(f"<@{mention_id}> has been added to DVC.")
                                except:
                                    await channel.send(f"{username} could not be added to DVC. They are not in the server or something else failed.")

                            else:
                                await channel.send(f"{username} could not be added to DVC. I don't have an alias for them!")
                            if "neil the eel" in flavor:
                                await post_game_reply(thread_id, "have you seen this fish\n[img]https://i.imgur.com/u9QjIqc.png[/img]\n now you have")

                elif "Elimination: Sleep" in event:
                    await channel.send("Players voted sleep. ZzZZZZzzzZzzz.")
                    await channel.send("https://media1.tenor.com/m/VdIKn05yIh8AAAAd/cat-sleep.gif")
                    await post_game_reply(thread_id, "eepy\n\n[img]https://media1.tenor.com/m/VdIKn05yIh8AAAAd/cat-sleep.gif[/img]\n\neepy")
        
                elif "Game Over:" in event:
                    await channel.send("Game concluded -- attempting channel housekeeping/clean up")
                    # Not used anymore
                    # process_threadmarks.stop()
                    self.processed_threadmarks.clear()
                    return
                self.processed_threadmarks.append(event)

            await asyncio.sleep(600)

processor = ThreadmarkProcessor()

@bot.command()
async def sub(ctx, player=None):
    global current_game, aliases

    if ctx.channel.id not in allowed_channels:
        return
    if ctx.author.id in banned_users:
        await ctx.send("You have been banned for misusing bigping and are not allowed to adjust SNGs.")
        return 
    if player == None:
        await ctx.send("Use !sub [Player_to_replace] to sub into the game. You will need an alias set in order to sub.")
        return
    if current_game == None:
        await ctx.send("No current game running or known thread_id to use. Ping @benneh his shits broken if there is a game running")
        return
    if ctx.author.id not in aliases:
        await ctx.send("Please set your MU username by using !alias MU_Username before inning!")
        return

    player_in = aliases[ctx.author.id]

    username = os.environ.get('MUUN')
    password = os.environ.get('MUPW')
    
    #Login and get Initial Token
    session = mu.login(username, password)
    game_id, security_token = mu.open_game_thread(session, current_game)
    
    sub = mu.sub_player(session, game_id, player, player_in, security_token)
    if '"success":true' in sub:
        await ctx.send(f"{player} has been successfully replaced by {player_in}. <@{ctx.author.id}> please report to the game thread: https://www.mafiauniverse.com/forums/threads/{current_game}")
    else:
        await ctx.send("Replacement didn't work, please do so manually or fix syntax")


@bot.command()
async def stats(ctx, game_setup=None):

    if ctx.channel.id not in allowed_channels:  
        return
    
    if ctx.author.id in banned_users:
        await ctx.send("You have been banned for misusing bigping and are not allowed to adjust SNGs.")
        return   

    df = pd.read_csv('game_database.csv')

    overall_mafia_wins = 0
    overall_town_wins = 0
    overall_independent_wins = 0
    overall_draws = 0

    setup_wins = {}
    setup_total_games = {}

    for index, row in df.iterrows():
        if row['Winning Alignment'] == 'Mafia':
            winning_team = 'wolves'
        elif row['Winning Alignment'] == 'Evil Independent':
            winning_team = 'independent'
        elif row['Winning Alignment'] == 'Town':
            winning_team = 'villagers'
        else:
            winning_team = 'Draw'

        if winning_team == 'wolves':
            overall_mafia_wins += 1
        elif winning_team == 'independent':
            overall_independent_wins += 1
        elif winning_team == 'villagers':
            overall_town_wins += 1
        elif winning_team == 'Draw':
            overall_draws += 1

        setup = row['Setup']
        setup_wins[setup] = setup_wins.get(setup, {'mafia': 0, 'town': 0, 'evil_independent': 0, 'draw': 0})
        setup_total_games[setup] = setup_total_games.get(setup, 0) + 1

        if winning_team == 'wolves':
            setup_wins[setup]['mafia'] += 1
        elif winning_team == 'villagers':
            setup_wins[setup]['town'] += 1
        elif winning_team == 'independent':
            setup_wins[setup]['evil_independent'] += 1        
        elif winning_team == 'Draw':
            setup_wins[setup]['draw'] += 1

    # Calculate overall win percentages
    total_games = len(df)
    overall_mafia_win_percentage = (overall_mafia_wins / (total_games- overall_draws)) * 100
    overall_town_win_percentage = (overall_town_wins / (total_games- overall_draws)) * 100
    overall_ind_win_percentage = (overall_independent_wins / (total_games - overall_draws)) * 100
    overall_draw_percentage = (overall_draws / total_games) * 100

    # Display overall stats

    if game_setup is None:
        setup_embed = discord.Embed(title="Setup Stats", color=0x3381ff)
        setup_embed.add_field(name=f'Overall Stats', value=f"Total Games since September 2023: {total_games}", inline=False)
        setup_embed.add_field(name="Town Win Percentage", value=f'{overall_town_win_percentage:.2f}%', inline=True)
        setup_embed.add_field(name='Mafia Win Percentage', value=f'{overall_mafia_win_percentage:.2f}%', inline=True)
        setup_embed.add_field(name="Stats by Turby!", value=f"Use !stats [setup] to get individual setup stats!", inline=False)
        setup_embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/1149013467790053420/1246701427380850751/images.png?ex=665d58ae&is=665c072e&hm=b84fa3677984afac2e13d4636c5c527fdeefb22d561b5c234472cd36d8c6fdc2&")
        await ctx.send(embed=setup_embed)
    else:
        if game_setup not in setup_total_games:
            await ctx.send("Setup not found in the database.")
            return

        count = setup_total_games[game_setup]
        await display_setup_stats(ctx, game_setup, count, setup_wins)

async def display_setup_stats(ctx, setup, count, setup_wins):

    mafia_wins = setup_wins[setup]['mafia']
    town_wins = setup_wins[setup]['town']
    independent_wins = setup_wins[setup]['evil_independent']
    draws = setup_wins[setup]['draw']

    mafia_win_percentage = (mafia_wins / (count - draws)) * 100
    town_win_percentage = (town_wins / (count - draws)) * 100
    independent_win_percentage = (independent_wins / (count - draws)) * 100
    draw_percentage = (draws / count) * 100

    setup_embed = discord.Embed(title=f"{setup} Stats", color=0x3381ff)
    setup_embed.add_field(name="Total Games", value=count, inline=False)
    setup_embed.add_field(name="Mafia Win Percentage", value=f"{mafia_win_percentage:.2f}%", inline=True)
    setup_embed.add_field(name="Town Win Percentage", value=f"{town_win_percentage:.2f}%", inline=True)

    if independent_wins:
        setup_embed.add_field(name="Evil Independent Win Percentage", value=f"{independent_win_percentage:.2f}%", inline=True)
    setup_embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/1149013467790053420/1246701427380850751/images.png?ex=665d58ae&is=665c072e&hm=b84fa3677984afac2e13d4636c5c527fdeefb22d561b5c234472cd36d8c6fdc2&")

    await ctx.send(embed=setup_embed)

@bot.command()
async def anongame(ctx, anon=None):
    if ctx.channel.id not in allowed_channels:  
        return
    
    if ctx.author.id in banned_users:
        await ctx.send("You have been banned for misusing bigping and are not allowed to adjust SNGs.")
        return
    
    global anon_enabled

    if anon is None:
        await ctx.send(f"The current game is set as Anon: {anon_enabled}, use !anongame on or !anongame off to turn anon games on and off.")
    
    elif anon.lower() == "on":
        anon_enabled = True
        await ctx.send(f"The current game is set to anonymous/aliased.")
    elif anon.lower() == "off":
        anon_enabled = False
        await ctx.send(f"The current game is set to normal accounts.")
    else:
        await ctx.send(f"The current game is set as Anon: {anon_enabled}, use !anongame on or !anongame off to turn anon games on and off.")       


@bot.command()
async def game(ctx, setup_name=None, Xer_Players: int = None):
    if ctx.channel.id not in allowed_channels:  
        return
    if ctx.author.id in future_banned:
        await ctx.send("Your future ban of August 1st, 2027 is not yet in effect, so you may use Turby until then.")
    if ctx.author.id in banned_users:
        await ctx.send("You have been banned for misusing bigping and are not allowed to adjust SNGs.")
        return

    global current_setup, player_limit, players, waiting_list

    if setup_name is None:
        await ctx.send(f"The current game setup is '{current_setup}'. To change the setup, use !game <setup_name>. Valid setup names are: {', '.join(valid_setups)}.")
    elif setup_name in valid_setups:
        if setup_name == "cop9":
            new_player_limit = 9
        elif setup_name == "vig10":
            new_player_limit = 10
        elif setup_name == "joat10":
            new_player_limit = 10
        elif setup_name == "neilgame":
            new_player_limit = 3
        elif setup_name == "ita10":
            new_player_limit = 10
        elif setup_name == "ita13":
            new_player_limit = 13
        elif setup_name == "bml10":
            new_player_limit = 10
        elif setup_name == "bomb10":
            new_player_limit = 10
        elif setup_name == "random10er":
            new_player_limit = 10
        elif setup_name == "closedrandomXer" and Xer_Players is not None:
            new_player_limit = Xer_Players
            if new_player_limit < 7:
                await ctx.send(f"Cannot change setup to '{setup_name} - {new_player_limit}'. Minimum number of players for closedrandomXers is 7")
                return
            if new_player_limit < len(players):
                await ctx.send(f"Cannot change setup to '{setup_name} - {new_player_limit}'. The current number of players ({len(players)}) exceeds the player limit for this setup ({new_player_limit}).")
                return
            await ctx.send(f"Player limit has been increased to {Xer_Players}!")

        elif setup_name == "closedrandomXer":
            await ctx.send("Please include the number of players after !game closedrandomXer [#] and try again")
        elif setup_name == "cop13":
            new_player_limit = 13
        elif setup_name == "doublejoat13":
            new_player_limit = 13
        elif setup_name == "rolemadness13":
            new_player_limit = 13
        elif setup_name == "alexa25":
            new_player_limit = 25
        elif setup_name == "f3practice":
            new_player_limit = 3
        else:
            await ctx.send(f"'{setup_name}' is not a valid setup name. Please choose from: {', '.join(valid_setups)}.")
            return
        
        if new_player_limit < len(players):
            await ctx.send(f"Cannot change setup to '{setup_name}'. The current number of players ({len(players)}) exceeds the player limit for this setup ({new_player_limit}).")
            return
        
        while new_player_limit > len(players) and len(waiting_list) > 0:
            next_in_line = waiting_list.popitem()
            players[next_in_line[0]] = next_in_line[1]
            
        current_setup = setup_name
        player_limit = new_player_limit

        await ctx.send(f"The game setup has been changed to '{current_setup}'")

    else:
        await ctx.send(f"'{setup_name}' is not a valid setup name. Please choose from: {', '.join(valid_setups)}.")

    await update_status()        

@bot.command()
async def phases(ctx, timer_name=None):
    if ctx.channel.id not in allowed_channels:  
        return
    
    if ctx.author.id in banned_users:
        await ctx.send("You have been banned for misusing bigping and are not allowed to adjust SNGs.")
        return

    global current_timer, day_length, night_length

    if timer_name is None:
        await ctx.send(f"The current phases are '{current_timer}'. To change the phases, use !phases <setup_name>. Valid setup names are: {', '.join(valid_timers)}.")
    elif timer_name in valid_timers:
        if timer_name == "12-12":
            new_day_length = 12
            new_night_length = 12
        elif timer_name == "36-12":
            new_day_length = 36
            new_night_length = 12
        elif timer_name == "48-24":
            new_day_length = 48
            new_night_length = 24

        else:
            await ctx.send(f"'{timer_name}' is not a valid phase. Please choose from: {', '.join(valid_timers)}.")
            return
        
            
        day_length = new_day_length
        night_length = new_night_length
        current_timer = timer_name

        await ctx.send(f"The day/night phases have been changed to '{current_timer}'")
    else:
        await ctx.send(f"'{timer_name}' is not a valid setup name. Please choose from: {', '.join(valid_timers)}.")
    await update_status()     



@bot.command()
async def flavors(ctx):
    if ctx.channel.id not in allowed_channels:  # Restrict to certain channels
        return
    
    vt_flavor = load_flavor_json('turboers.json')
    pr_flavor = load_flavor_json('powerroles.json')
    wolf_flavor = load_flavor_json('wolves.json')



    async def send_message(flavor, role, ctx):
        charnames = []
        message = f"```\n{role}\n\n"
        for i, item in enumerate(flavor):
            
            message += f"{i + 1}. {item['character_name']}\n"
        
        message += "```"

        await ctx.author.send(message)
    
    await send_message(vt_flavor, "Vanilla Towns", ctx)
    await send_message(pr_flavor, "Power Roles", ctx)
    await send_message(wolf_flavor, "Wolves", ctx)
    


@bot.command()
async def flavor(ctx, charname=None, charimage=None):
    if ctx.channel.id not in allowed_channels:  # Restrict to certain channels
        return
    
    if ctx.author.id in banned_users:
        await ctx.send("You have been banned for misusing bigping and are not allowed to in SNGs.")
        return    
    existing_flavor = load_flavor_json('turboers.json')
    added_flavor = {'character_name': charname, 'character_image': charimage}

    if ctx.author.id not in mods:
        if charname != None:
            if charimage != None:
                await ctx.send(f"You don't have privs to add flavor. Doing flavor lookup for {charname} instead.")
            for i in existing_flavor:
                if i['character_name'].lower() == charname.lower():
                    await ctx.send(f"Flavor found for {i['character_name']}: {i['character_image']}")
                    return
            await ctx.send(f"No flavor found for {charname}. Try again noob")
        return
    
    if charname != None:
        if charimage != None:
            for i, item in enumerate(existing_flavor):
                if item['character_name'].lower() == charname.lower():
                    existing_flavor[i]['character_image'] = charimage
                    await ctx.send("flavor updated successfully thxxxbai")
                    save_flavor_json('turboers.json', existing_flavor)
                    return
            existing_flavor.append(added_flavor)
            await ctx.send("flavor add successful thxxxbai")
        else:
            for i in existing_flavor:
                if i['character_name'].lower() == charname.lower():
                    await ctx.send(f"Flavor found for {i['character_name']}: {i['character_image']}")
                    return
            await ctx.send(f"No flavor found for {charname}. Try again noob")

    else:
        await ctx.send("No character name selected, try again using quotes")
        return
    
    save_flavor_json('turboers.json', existing_flavor)

@bot.command()
async def wolf_flavor(ctx, charname=None, charimage=None):
    if ctx.channel.id not in allowed_channels:  # Restrict to certain channels
        return
    
    if ctx.author.id in banned_users:
        await ctx.send("You have been banned for misusing bigping and are not allowed to in SNGs.")
        return    

    existing_flavor = load_flavor_json('wolves.json')
    added_flavor = {'character_name': charname, 'character_image': charimage}

    if ctx.author.id not in mods:
        if charname != None:
            if charimage != None:
                await ctx.send(f"You don't have privs to add flavor. Doing flavor lookup for {charname} instead.")
            for i in existing_flavor:
                if i['character_name'].lower() == charname.lower():
                    await ctx.send(f"Flavor found for {i['character_name']}: {i['character_image']}")
                    return
            await ctx.send(f"No flavor found for {charname}. Try again noob")
        return
    

    if charname != None:
        if charimage != None:
            for i, item in enumerate(existing_flavor):
                if item['character_name'].lower() == charname.lower():
                    existing_flavor[i]['character_image'] = charimage
                    await ctx.send("flavor updated successfully thxxxbai")
                    save_flavor_json('wolves.json', existing_flavor)
                    return
            existing_flavor.append(added_flavor)
            await ctx.send("flavor add successful thxxxbai")
        else:
            for i in existing_flavor:
                if i['character_name'].lower() == charname.lower():
                    await ctx.send(f"Flavor found for {i['character_name']}: {i['character_image']}")
                    return
            await ctx.send(f"No flavor found for {charname}. Try again noob")

    else:
        await ctx.send("No character name selected, try again using quotes")
        return
    
    save_flavor_json('wolves.json', existing_flavor)

@bot.command()
async def pr_flavor(ctx, charname=None, charimage=None):
    if ctx.channel.id not in allowed_channels:  # Restrict to certain channels
        return
    
    if ctx.author.id in banned_users:
        await ctx.send("You have been banned for misusing bigping and are not allowed to in SNGs.")
        return    
    existing_flavor = load_flavor_json('powerroles.json')
    added_flavor = {'character_name': charname, 'character_image': charimage}
    if ctx.author.id not in mods:
        if charname != None:
            if charimage != None:
                await ctx.send(f"You don't have privs to add flavor. Doing flavor lookup for {charname} instead.")
            for i in existing_flavor:
                if i['character_name'].lower() == charname.lower():
                    await ctx.send(f"Flavor found for {i['character_name']}: {i['character_image']}")
                    return
            await ctx.send(f"No flavor found for {charname}. Try again noob")
        return
    

    if charname != None:
        if charimage != None:
            for i, item in enumerate(existing_flavor):
                if item['character_name'].lower() == charname.lower():
                    existing_flavor[i]['character_image'] = charimage
                    await ctx.send("flavor updated successfully thxxxbai")
                    save_flavor_json('powerroles.json', existing_flavor)
                    return
            existing_flavor.append(added_flavor)
            await ctx.send("flavor add successful thxxxbai")
        else:
            for i in existing_flavor:
                if i['character_name'].lower() == charname.lower():
                    await ctx.send(f"Flavor found for {i['character_name']}: {i['character_image']}")
                    return
            await ctx.send(f"No flavor found for {charname}. Try again noob")

    else:
        await ctx.send("No character name selected, try again using quotes")
        return
    
    save_flavor_json('powerroles.json', existing_flavor)

@bot.command(name="in")
async def in_(ctx, time: int = 10080):
    if ctx.channel.id not in allowed_channels:  # Restrict to certain channels
        return
    
    if ctx.author.id in banned_users:
        await ctx.send("You have been banned for misusing bigping and are not allowed to in SNGs.")
        return
    if ctx.author.id in future_banned:
        await ctx.send("Your future ban of August 1st, 2027 is not yet in effect, so you may use Turby until then.")

    if ctx.author.id not in aliases:
        await ctx.send("Please set your MU username by using !alias MU_Username before inning!")
        return

    alias = aliases[ctx.author.id]
    global game_host_name, player_limit, players, waiting_list

        
    if alias in game_host_name:
        if len(game_host_name) == 1:
            game_host_name = ["Turby"]
            if len(players) < player_limit:
                players[alias] = time
                await ctx.send(f"{alias} has been removed as host and added to the list for the next {time} minutes. Your current host is Turby :3")
            else:
                waiting_list[alias] = time
                await ctx.send(f"{alias} has been removed as host and added to the waiting list for the next {time} minutes. Your current host is Turby :3")
            await update_status()
            return
            
        elif len(game_host_name) > 1:
            game_host_name.remove(alias)
            if len(players) < player_limit:
                players[alias] = time
                await ctx.send(f"{alias} has been removed as host and added to the list for the next {time} minutes.")
            else:
                waiting_list[alias] = time
                await ctx.send(f"The list is full. {alias} has been removed as host and added to the waiting list instead.")
            await update_status()    
            return
            
    if alias in players or alias in waiting_list:
        if alias in players:
            players[alias] = time            
        else:
            waiting_list[alias] = time            
        #await ctx.send(f"{alias}'s in has been renewed for the next {time} minutes.")
        await ctx.message.add_reaction('👍')
    else:
        if len(players) < player_limit:
            players[alias] = time            
            #await ctx.send(f"{alias} has been added to the list for the next {time} minutes.")
            await ctx.message.add_reaction('👍')
        else:
            waiting_list[alias] = time
            #await ctx.send(f"The list is full. {alias} has been added to the waiting list.")
            await ctx.message.add_reaction('👍')
    await update_status()            

@bot.command()
async def out(ctx):
    if ctx.channel.id not in allowed_channels:  # Restrict to certain channels
        return
    if ctx.author.id in banned_users:
        await ctx.send("You have been banned for misusing bigping and are not allowed to adjust SNGs.")
        return
    if ctx.author.id in future_banned:
        await ctx.send("Your future ban of August 1st, 2027 is not yet in effect, so you may use Turby until then.")
    global game_host_name, player_limit, players, waiting_list 
    
    if ctx.author.id not in aliases:
        await ctx.send("You are not on the list and you haven't set an alias. Stop trolling me.")
        await ctx.message.add_reaction('👎')
        return
    alias = aliases[ctx.author.id]
    
    if alias in (hostname.lower() for hostname in game_host_name):
        if len(game_host_name) == 1:
            game_host_name = ["Turby"]
            await ctx.send(f"{alias} has been removed as host. Turby :3 has been set back to the default host.")
            await update_status()
            return
        else:
            game_host_name.remove(alias)
            host_list = [f"{host}" for host in game_host_name]
            hosts = ' '.join(host_list)
            await ctx.send(f"{alias} has been removed as host. Your current host(s): {hosts}")
            await update_status()
            return
        
    if alias in players:
        del players[alias]
        #await ctx.send(f"{alias} has been removed from the list.")
        await ctx.message.add_reaction('👎')
    elif alias in waiting_list:
        del waiting_list[alias]
        #await ctx.send(f"{alias} has been removed from the waiting list.")
        await ctx.message.add_reaction('👎')
    else:
        await ctx.send(f"{alias} is not on the list.")
        await ctx.message.add_reaction('👎')
    # Add a player from waiting list to main list if it's not full
    if len(players) < player_limit and waiting_list:
        next_alias, next_time = waiting_list.popitem()
        players[next_alias] = next_time
        await ctx.message.add_reaction('👎')
        await ctx.send(f"{next_alias} has been moved from the waiting list to the main list.")
    await update_status()
    
@bot.command()
async def alias(ctx, *, alias):
    if ctx.channel.id not in allowed_channels:  # Restrict to certain channels
        return
    
    if ctx.author.id in banned_users:
        await ctx.send("You have been banned for misusing bigping and are not allowed to change your alias.")
        return

    alias = alias.lower()
    if alias in aliases.values() or alias in players:
        await ctx.send(f"The alias {alias} is already taken or being used in a current sign-up. If someone has taken your alias, fight them.")
    else:
        old_alias = aliases.get(ctx.author.id)
        aliases[ctx.author.id] = alias
        save_aliases()
        await ctx.send(f"Alias for {ctx.author} has been set to {alias}.")

        # Update alias in players and waiting_list
        for player_list in [players, waiting_list]:
            for player in list(player_list.keys()):  # Create a copy of keys to avoid RuntimeError
                if player == old_alias:
                    player_list[alias] = player_list.pop(old_alias)                   
    await update_status()
        
@bot.command()
async def add(ctx, *, alias):
    if ctx.channel.id not in allowed_channels:  # Restrict to certain channels
        return
    
    if ctx.author.id in banned_users:
        await ctx.send("You have been banned for misusing bigping and are not allowed to in SNGs.")
        return
    alias = alias.lower()
    global game_host_name, player_limit, players, waiting_list
    
    if alias in game_host_name:
        if len(game_host_name) == 1:
            game_host_name = ["Turby"]
            if len(players) < player_limit:
                players[alias] = 10080
                await ctx.send(f"{alias} has been removed as host and added to the list for the next 60 minutes. Your current host is Turby :3.")
            else:
                waiting_list[alias] = 10080
                await ctx.send(f"{alias} has been removed as host and added to the waiting list for the next 60 minutes. Your current host is Turby :3.")
            await update_status()
            return
            
        elif len(players) < player_limit:
            players[alias] = 10080
            game_host_name.remove(alias)
            host_list = [f"{host}" for host in game_host_name]
            hosts = ' '.join(host_list)
            await ctx.send(f"{alias} has been removed as host and added to the list for the next 60 minutes. Your current host(s): {hosts}")
            await update_status()
            return
        else:
            waiting_list[alias] = 10080 
            await ctx.send(f"The list is full. {alias} has been removed as host and added to the waiting list instead.")
            await update_status()
            return
            
    if alias in players or alias in waiting_list:
        if alias in players:
            players[alias] = 10080  # Default time
        else:
            waiting_list[alias] = 10080  # Default time
        await ctx.message.add_reaction('👍')    
        #await ctx.send(f"{alias}'s in has been renewed for 60 minutes.")
    else:
        if len(players) < player_limit:
            players[alias] = 10080  # Default time
            #await ctx.send(f"{alias} has been added to the list with for 60 minutes.")
        else:
            waiting_list[alias] = 10080  # Default time
            #await ctx.send(f"The list is full. {alias} has been added to the waiting list.")
        await ctx.message.add_reaction('👍')
    await update_status()    

@bot.command()
async def remove(ctx, *, alias):
    if ctx.channel.id not in allowed_channels:  # Restrict to certain channels
        return
    
    if ctx.author.id in banned_users:
        await ctx.send("You have been banned for misusing bigping and are not allowed to in SNGs.")
        return
    alias = alias.lower()
    global game_host_name, player_limit, players, waiting_list
    
    if alias in (hostname.lower() for hostname in game_host_name):
        if len(game_host_name) == 1:
            game_host_name = ["Turby"]
            await ctx.send(f"{alias} has been removed as host. Turby :3 has been set back to the default host.")
            await update_status()
            return
        else:
            game_host_name.remove(alias)
            host_list = [f"{host}" for host in game_host_name]
            hosts = ' '.join(host_list)
            await ctx.send(f"{alias} has been removed as host. Your current host(s): {hosts}")
            await update_status()
            return
        
    if alias in players:
        del players[alias]
        await ctx.message.add_reaction('👎')
        #await ctx.send(f"{alias} has been removed from the list.")
    elif alias in waiting_list:
        del waiting_list[alias]
        await ctx.message.add_reaction('👎')
        #await ctx.send(f"{alias} has been removed from the waiting list.")
    else:
        await ctx.send(f"{alias} is not on the list.")
        await ctx.message.add_reaction('👎')
    # Add a player from waiting list to main list if it's not full
    if len(players) < player_limit and waiting_list:
        next_alias, next_time = waiting_list.popitem()
        players[next_alias] = next_time
        
        await ctx.send(f"{next_alias} has been moved from the waiting list to the main list.")
    await update_status()

@bot.command()
async def status(ctx, *args):
    if ctx.guild is not None and ctx.channel.id not in allowed_channels:  # Restrict to certain channels
        return
    if ctx.author.id in future_banned:
        await ctx.send("Your future ban of August 1st, 2027 is not yet in effect, so you may use Turby until then.") 
    global game_host_name, status_id, status_channel, baitping

    baitping = False

    embed = discord.Embed(title="**2023 Award Winner for Best Mechanic!\nSNG Bot v2.1 (with subs!) by benneh\nHelp keep Turby running by supporting its GoFundMe: https://gofund.me/64aaddfd", color=0x3381ff)
    embed.add_field(name="**Game Setup**", value=current_setup, inline=True)    
    host_list = [f"{host}\n" for host in game_host_name]
    hosts = ''.join(host_list)
    embed.add_field(name="**Host**", value=hosts, inline=True)
    embed.add_field(name="**Phases**", value=str(day_length) + "h Days, " + str(night_length) + "h Nights", inline=True)
    embed.add_field(name="", value="", inline=True)
    embed.add_field(name="", value="", inline=True)
    embed.add_field(name="", value="", inline=True)

    embed.add_field(name="", value="", inline=True)
    embed.add_field(name="", value="", inline=True)
    embed.add_field(name="", value="", inline=True)

    status_flavor = load_flavor_json('icons.json')    

    if players:
        player_message = ""
        time_message = ""
        for i, (alias, remaining_time) in enumerate(players.items(), 1):
            player_msg = alias
            for item in status_flavor:
                if alias == item['alias']:
                    player_msg = f"{alias} {item['icon']}"
            player_message += f"{player_msg}\n"
            time_message += f"{remaining_time} minutes\n"
            
        spots_left = player_limit - len(players)
        if spots_left > 1:
            player_message += f"+{spots_left} !!\n"
        elif spots_left == 1:
            player_message += "+1 HERO NEEDED\n"
        else:
            player_message += "Game is full. Switch to a larger setup using `!game [setup]` or rand the game using `!rand -title \"Title of game thread\"`\n"        
        time_message +=  "!in or react ✅ to join!\n"  
        embed.set_field_at(3, name="**Players:**", value=player_message, inline=True)
        #embed.set_field_at(5, name="**Time Remaining:**", value=time_message, inline=True)
        embed.set_field_at(4, name="", value="", inline=True)
    if waiting_list:
        waiting_list_message = ""
        time_message = ""
        for i, (alias, remaining_time) in enumerate(waiting_list.items(), 1):
            waiting_list_message += f"{alias}\n"
            time_message += f"{remaining_time} minutes\n"
            
        embed.set_field_at(6, name="**Waiting List:**", value=waiting_list_message, inline=True)
        #embed.set_field_at(7, name="**Time Remaining:**", value=time_message, inline=True)

    if not players and not waiting_list:
        embed.add_field(name="No players are currently signed up.", value="", inline=False)
    
    embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/1149013467790053420/1195471648850186401/image.png")

    status_embed = await ctx.send(embed=embed)
    await status_embed.add_reaction('✅')
    status_id = status_embed.id
    status_channel = ctx.channel

async def update_status():

    global status_id, baitping
    
    if status_id is None or status_channel is None:
        return
    
    status_message = await status_channel.fetch_message(status_id)
    embed = status_message.embeds[0]
    
    spots_left = player_limit - len(players)
    host_list = [f"{host}\n" for host in game_host_name]
    hosts = ''.join(host_list)
    """embed.set_field_at(0, name="**Game Setup**", value=current_setup, inline=True)
    embed.set_field_at(1, name="**Host**", value=hosts, inline=True)
    embed.set_field_at(2, name="", value="", inline=True)
    embed.set_field_at(3, name="No players are currently signed up.", value="", inline=True)
    embed.set_field_at(4, name="", value="", inline=True)
    embed.set_field_at(5, name="", value="", inline=True)
    embed.set_field_at(6, name="", value="", inline=True)
    embed.set_field_at(7, name="", value="", inline=True)"""

    embed.set_field_at(0, name="**Game Setup**", value=current_setup, inline=True)
    host_list = [f"{host}\n" for host in game_host_name]
    hosts = ''.join(host_list)
    embed.set_field_at(1, name="**Host**", value=hosts, inline=True)
    embed.set_field_at(2, name="**Phases**", value=str(day_length) + "h Days, " + str(night_length) + "h Nights", inline=True)

    

    status_flavor = load_flavor_json('icons.json')    

    if players:
        player_message = ""
        #time_message = ""
        for i, (alias, remaining_time) in enumerate(players.items(), 1):
            player_msg = alias
            for item in status_flavor:
                if alias == item['alias']:
                    player_msg = f"{alias} {item['icon']}"
            player_message += f"{player_msg}\n"
            #time_message += f"{remaining_time} minutes\n"
        #if baitping:
            #time_message += "10 minutes\n"
            
        spots_left = player_limit - len(players)
        if spots_left > 1:
            if baitping:
                player_message += "alexa.\n"
                player_message += f"+{spots_left - 1} !!\n"
            else:
                player_message += f"+{spots_left} !!\n"
        elif spots_left == 1:
            if baitping:
                player_message += "alexa.\n"
                player_message += f"+{spots_left - 1} !!\n"
            else:
                player_message += f"+{spots_left} !!\n"
        else:
            if baitping:
                player_message += "alexa.\n"
                player_message += f"+{spots_left - 1} !!\n"
            else:
                player_message += "Game is full. Switch to a larger setup using `!game [setup]` or rand the game using `!rand -title \"Title of game thread\"`\n"        
        #time_message +=  "!in or react ✅ to join!\n"
        
        embed.set_field_at(3, name="**Players:**", value=player_message, inline=True)
        #embed.set_field_at(5, name="**Time Remaining:**", value=time_message, inline=True)
    
    if waiting_list:
        waiting_list_message = ""
        time_message = ""
        for i, (alias, remaining_time) in enumerate(waiting_list.items(), 1):
            waiting_list_message += f"{alias}\n"
            time_message += f"{remaining_time} minutes\n"            

        embed.set_field_at(6, name="**Waiting List:**", value=waiting_list_message, inline=True)
        #embed.set_field_at(7, name="**Time Remaining:**", value=time_message, inline=True)
        
    if not players and not waiting_list:
        embed.set_field_at(3, name="No players are currently signed up.", value="", inline=False)
        embed.set_field_at(4, name="", value="", inline=True)
        embed.set_field_at(6, name="", value="", inline=True)
        embed.set_field_at(7, name="", value="", inline=True)
    
    if not waiting_list:
        embed.set_field_at(6, name="", value="", inline=True)
        embed.set_field_at(7, name="", value="", inline=True)
        
    
    await status_message.edit(embed=embed)
    
@bot.command()
async def delete_archive(ctx, category_name):
    if ctx.author.id not in mods:
        return
    
    guild = bot.get_guild(dvc_server)

    try:
        category = discord.utils.get(guild.categories, name=category_name)

        if category:
            for channel in category.channels:
                await channel.delete()
            await ctx.send(f"DVC Archive cleanup complete for {category_name}")
        else:
            await ctx.send(f"Category {category_name} not found on SNG DVC server. Try again.")
    except:
        await ctx.send("Somethin' fucked up, check logs")

@bot.command()
async def process_archive(ctx, category_name):
    if ctx.author.id not in mods:
        return
    
    guild = bot.get_guild(dvc_server)
    pattern = re.compile(r'(\d+)$')
    category = discord.utils.get(guild.categories, name=category_name)
    try:
        if category:
            print(category.channels)

            for channel in category.channels:
                print(channel.name, flush=True)
                chan_name = channel.name
                print(chan_name, flush=True)
                match = pattern.search(chan_name)
                print(match.group(1))

                thread_id_only = str(match.group(1))

        else:
            await ctx.send(f"Category {category_name} not found on SNG DVC server. Try again.")
    except Exception as error:
        print(f"Error: {error}", flush=True)
        await ctx.send("Somethin' fucked up, check logs")
    await ctx.send(f"Processed archive: {category_name}")


@bot.command()
async def host(ctx, *, host_name=None):
    if ctx.channel.id not in allowed_channels:  # Restrict to certain channels
        return
    if ctx.author.id in banned_users:
        await ctx.send("You have been banned and are not allowed to host SNGs.")
        return
    if ctx.author.id not in mods:
        await ctx.send("Hosting is limited to a select set of users who will not ruin the DVC experience for others and also for those who have subscribed to the Sit N Go-y Advanced package, $5.99 a month. DM Benneh for billing options.")
        return
    global game_host_name
    
    if host_name == "Turby":
        game_host_name = ["Turby"]
        await update_status()
        await ctx.send("Host setting has been set to default for Turby :3 and cleared all other hosts.")
        return

    if host_name is not None and host_name.lower() in game_host_name:
        await ctx.send(f"That account is already a host. Stop trying to break me. nya~")
        return   
        
    if host_name is None:
        if ctx.author.id in aliases:
            host_name = aliases[ctx.author.id]
            if host_name in players or host_name in waiting_list:
                await ctx.send(f"{host_name} is already on the SNG list or waiting list.\n Please choose a different name for the host.")
                return
            if host_name in game_host_name:
                await ctx.send(f"That account is already a host. Stop trying to break me. nya~")
                return  
            else:
                game_host_name.append(host_name)
                host_list = [f"{host}" for host in game_host_name]
                hosts = ', '.join(host_list)
                await ctx.send(f"Hosts for the next SNG are set as {hosts}")
                await update_status()
                return
        else:
            await ctx.send("You have not set an alias. Please use `!alias [MU Username]` before trying to use !host or !in commands.")
            return
    host_name = host_name.lower()            
    if host_name in players or host_name in waiting_list:
        await ctx.send(f"{host_name} is already on the SNG list or waiting list.\n Please choose a different name for the host.")
        return
    

    game_host_name.append(host_name)
    host_list = [f"{host}" for host in game_host_name]
    hosts = ', '.join(host_list)
    await ctx.send(f"Hosts for the next SNG are set as {hosts}")
    await update_status() 
    return
    
@tasks.loop(minutes=1)
async def update_players():
    global player_limit, recruit_timer
    
    try:
        if recruit_timer > 0:
             recruit_timer -= 1
        for alias in list(players.keys()):
            players[alias] -= 1
            if players[alias] <= 0:
                await bot.get_channel(223260125786406912).send(f"{alias} has run out of time and has been removed from the list.")
                del players[alias]

            # Add a player from waiting list to main list if it's not full
                if len(players) < player_limit and waiting_list:
                    next_alias, next_time = waiting_list.popitem()
                    players[next_alias] = next_time
                    await bot.get_channel(223260125786406912).send(f"{next_alias} has been moved from the waiting list to the main list.")
        save_player_list(players, waiting_list, current_setup, game_host_name, player_limit)
        await update_status()
    except:
        print("Error updating players with update_player function", flush=True)
   

@bot.command()
async def live_dvc(ctx, thread_id):
    if ctx.channel.id not in allowed_channels:  # Restrict to certain channels
        return

    global player_limit, game_host_name, current_setup, is_rand_running, current_game, spec_list, anon_enabled
    player_aliases = []
    final_game_setup = "custom"
	
    role, channel_id, guild = await create_dvc(thread_id)
    channel = bot.get_channel(channel_id)
	
    game_url = f"https://www.mafiauniverse.com/forums/threads/{thread_id}"
    await channel.send(f"MU Link for the current game: \n\n{game_url}")
    await new_game_spec_message(bot, thread_id, "Custom/Live DVC")
    current_game = thread_id 
    await processor.process_threadmarks(thread_id, player_aliases, role, guild, channel_id, final_game_setup, current_game)

    await edit_dvc(channel, guild)
    await delete_dvc_role(channel, role)
    current_game = None
    
    
@bot.command()
async def rand(ctx, *args):
    if ctx.channel.id not in allowed_channels:  # Restrict to certain channels
        return
    global player_limit, game_host_name, current_setup, is_rand_running, current_game, spec_list, anon_enabled, baitping

    allowed_randers = []
    player_aliases = list(players.keys())[:player_limit]

    for player in player_aliases:
        for key, value in aliases.items():
            if player == value:
                allowed_randers.append(int(key))
    for host in game_host_name:
        for key, value in aliases.items():
            if host == value:
                allowed_randers.append(int(key))    

    if ctx.author.id in banned_users:
        await ctx.send("You have been banned for misusing bigping and are not allowed to rand SNGs.")
        return   
    
    if ctx.author.id not in allowed_randers:
        await ctx.send("Only hosts and players on the list are allowed to execute this function.")
        return 
    
    if len(players) < player_limit and baitping:
        await ctx.send(f"You got baited by alexa, not enough players to start a game. Need {player_limit} players.")

    if len(players) < player_limit:
        await ctx.send(f"Not enough players to start a game. Need {player_limit} players.")
        return
        
    if is_rand_running:
        await ctx.send("The !rand command is currently being processed. Please wait.")
        return
    
    # args = shlex.split(' '.join(args))
    parser = argparse.ArgumentParser()
    parser.add_argument('-title', default=None)
    parser.add_argument('-thread_id', default=None)
    parser.add_argument('-wolves', default=None)
    parser.add_argument('-villager', default=None)
    try:
        args_parsed = parser.parse_args(args)
    except SystemExit:
        await ctx.send(f"Invalid arguments. Please check your command syntax. Do not use `-`, `--`, or `:` in your titles and try again.")
        return
    except Exception as e:
        await ctx.send(f"An unexpected error occurred. Please try again.\n{str(e)}")
        return

    is_rand_running = True

    mentions = " ".join([f"<@{id}>" for id in allowed_randers])
    cancel = await ctx.send(f"{mentions} \n\nThe game will rand in 15 seconds unless canceled by reacting with '❌'")
    await cancel.add_reaction('❌')

    def check(reaction, user):
        return str(reaction.emoji) == '❌' and user.id in allowed_randers and reaction.message.id == cancel.id

    try:
        reaction, user = await bot.wait_for('reaction_add', timeout=15, check=check)

        if str(reaction.emoji) == '❌':
            await ctx.send(f"Rand canceled")
            is_rand_running = False
            return
    except asyncio.TimeoutError:
        await ctx.send("Randing, stfu")
        
        try:
        
            username = os.environ.get('MUUN')
            password = os.environ.get('MUPW')
            
            #Login and get Initial Token
            session = mu.login(username, password)
            security_token = mu.new_thread_token(session)
            
            game_title = args_parsed.title
            thread_id = args_parsed.thread_id
            wolves = args_parsed.wolves
            fake_villager = args_parsed.villager

            if wolves is not None:
                await ctx.send(f"{wolves} have been set as the wolf team, proceeding with rand.")
            if fake_villager is not None:
                await ctx.send(f"{fake_villager} has been set as the town IC for this game, proceeding with rand.")

            if current_setup == "random10er":
                potential_setups = ["joat10", "vig10", "bomb10"]
                final_game_setup = random.choice(potential_setups)
                setup_title = final_game_setup
            else:
                final_game_setup = current_setup
                setup_title = final_game_setup

            if not game_title:
                game_title = mu.generate_game_thread_uuid()
                
            if not thread_id:
                print(f"Attempting to post new thread with {game_title}", flush=True)
                thread_id = mu.post_thread(session, game_title, security_token, setup_title,test=False)
            host_list = [f"{host}" for host in game_host_name]
            hosts = ', '.join(host_list)
            await ctx.send(f"Attempting to rand `{game_title}`, a {current_setup} game hosted by `{hosts}` using thread ID: `{thread_id}`. Please standby.")
            print(f"Attempting to rand `{game_title}`, a {current_setup} game hosted by `{hosts}` using thread ID: `{thread_id}`. Please standby.", flush=True)
            security_token = mu.new_game_token(session, thread_id)

            response_message = mu.start_game(session, security_token, game_title, thread_id, player_aliases, final_game_setup, day_length, night_length, game_host_name, anon_enabled,player_limit)
            
            if "was created successfully." in response_message:
                # Use aliases to get the Discord IDs
                print("Success. Gathering player list for mentions", flush=True)
                mention_list = []
                
                for player in player_aliases:
                    for key, value in aliases.items():
                        if player == value:
                            mention_list.append(int(key))
                            
                player_mentions = " ".join([f"<@{id}>" for id in mention_list])
                game_url = f"https://www.mafiauniverse.com/forums/threads/{thread_id}"  # Replace BASE_URL with the actual base URL
                await ctx.send(f"{player_mentions}\nranded STFU\n{game_url}\nType !dvc to join the SNG DVC/Graveyard. You will be auto-in'd to the graveyard channel upon your death if you are in that server!")
                
                ###################################################
                ####################### new code for wolf chat adds
                wolf_team = await get_wolf_info(game_title, setup_title)
                wc_channel_id, wc_guild = await create_wolf_chat(thread_id)
                wc_channel = bot.get_channel(wc_channel_id)

                wc_msg = "Wolf chat: "
                for wolf in wolf_team:
                    if wolf.lower() in aliases.values():
                        try:
                            mention_id = find_key_by_value(aliases, wolf.lower())
                            wolf_id = wc_guild.get_member(mention_id)
                            # await wolf_id.add_roles(wc_role)
                            await wc_channel.set_permissions(wolf_id, read_messages=True, send_messages=True)
                            wc_msg += f"<@{mention_id}> "
                        except:
                            print(f"Can't add {wolf} to wc", flush=True)
                await wc_channel.send(wc_msg)
                #####################################################
                #####################################################
                role, channel_id, guild = await create_dvc(thread_id)
                print(f"DVC thread created. Clearing variables", flush=True)
                channel = bot.get_channel(channel_id)

                host_msg = "Hosts for the current game: "
                for host in game_host_name:
                    if host in aliases.values():
                        try:
                            mention_id = find_key_by_value(aliases, host)
                            member = guild.get_member(mention_id)
                            await member.add_roles(role)
                            host_msg += f"<@{mention_id}> "
                            #await channel.send(f"<@{mention_id}> is hosting, welcome to dvc")
                        except:
                            print(f"Can't add {host} to dvc", flush=True)
                            #await channel.send(f"failed to add {host} to dvc.")
                await channel.send(host_msg)

                spec_msg = "Specs for the current game: "
                for spec in spec_list:
                    print(spec, flush=True)
                    if int(spec) in mention_list:
                        print(f"{spec} not in list, continuing to next", flush=True)
                        continue
                    else:
                        try:
                            spec_int = int(spec)
                            print(f"Trying to add {spec_int} to dvc",flush=True)

                            spec_member = guild.get_member(spec_int)
                            await spec_member.add_roles(role)
                            spec_msg += f"<@{spec}> "
                            #await channel.send(f"<@{spec}> is spectating, welcome to dvc")
                        except Exception as error:
                            print(f"Error: {error}", flush=True)
                await channel.send(spec_msg)
                
                await channel.send(f"MU Link for the current game: \n\n{game_url}")

                await new_game_spec_message(bot, thread_id, game_title)
                postgame_players = players
                game_host_name = ["Turby"]
                players.clear()
                players.update(waiting_list)
                waiting_list.clear()  
                anon_enabled = False 
                print("Old player/waiting lists cleared and updated and host set back to default. Starting threadmark processor next.", flush=True)			
                is_rand_running = False
                current_game = thread_id
                await processor.process_threadmarks(thread_id, player_aliases, role, guild, channel_id, final_game_setup, current_game)
                print(f"Threadmark processor finished. rand function finished.", flush=True)
                await edit_dvc(channel, guild)
                await edit_dvc(wc_channel, wc_guild)
                await delete_dvc_role(channel, role)
                # await delete_dvc_role(wc_channel, wc_role)
                current_game = None
                
                summary_url = f"https://www.mafiauniverse.com/forums/modbot-beta/get-game-summary.php?threadid={thread_id}"
                summary_response = requests.get(summary_url)
                summary_json = summary_response.json()

                summary_csv = 'game_database.csv'
                summary_headers = ['SNG Title', 'Setup', 'Thread ID', 'Game ID', 'Winning Alignment', 'Villagers', 'Wolves']
                town = summary_json['players']['town']
                mafia = summary_json['players']['mafia']

                town_list = []
                mafia_list = []

                for player in town:
                    town_list.append(player['username'])
                    
                for player in mafia:
                    mafia_list.append(player['username'])
                
                title = summary_json['title']
                start_index = title.find(" - [")
                if start_index != -1:
                    start_index += len(" - [")
                    end_index = title.find(" game]", start_index)

                    if end_index != -1:
                        extracted_setup = title[start_index:end_index]
                    else:
                        print("No setup found", flush=True)
                else:
                    print("No setup found", flush=True)

                with open(summary_csv, 'a', newline='') as csvfile:
                    csv_writer = csv.DictWriter(csvfile, fieldnames=summary_headers)

                    if csvfile.tell() == 0:
                        csv_writer.writeheader()
                    
                    csv_writer.writerow({
                        "SNG Title": summary_json['title'],
                        "Setup": extracted_setup,
                        "Thread ID": summary_json['threadid'],
                        "Game ID": summary_json['id'],
                        "Winning Alignment": summary_json['winning_alignment'],
                        "Villagers": town_list,
                        "Wolves": mafia_list,                          
                    })


            elif "Error" in response_message:
                print(f"Game failed to rand, reason: {response_message}", flush=True)
                await ctx.send(f"Game failed to rand, reason: {response_message}\nPlease fix the error and re-attempt the rand with thread_id: {thread_id} by typing '!rand -thread_id \"{thread_id}\" so a new game thread is not created.")    
        
        finally:
            is_rand_running = False

@bot.command()
async def clear(ctx, *args):
    if ctx.channel.id not in allowed_channels:  # Restrict to certain channels
        return
    if ctx.author.id in banned_users:
        await ctx.send("You have been banned for misusing bigping and are not allowed to clear SNGs.")
        return        
    global players, waiting_list, game_host_name, current_setup, player_limit    
    
    parser = argparse.ArgumentParser()
    parser.add_argument('-confirm', action='store_true') 
    
    try:
        args_parsed = parser.parse_args(args)
    except SystemExit:
        await ctx.send("Invalid arguments. Type `!clear -confirm` to clear the queue otherwise f off")
        return
    
    if args_parsed.confirm:        
        players = {}
        waiting_list = {}
        player_limit = 10
        game_host_name = ["Turby"]
        current_setup = "joat10"        
        await ctx.send("Player and waiting list has been cleared. Game is JOAT10 and host is Turby :3")
    else:
        await ctx.send("To clear, run !clear -confirm")
        
@bot.command(name='help')
async def help(ctx):
    if ctx.channel.id not in allowed_channels:  # Restrict to certain channels
        return
    embed = discord.Embed(title="Bot Commands", description="Here are the commands you can use:", color=0x1e00ff)
    embed.add_field(name="!in", value="Joins the player list. You must first set an alias using `!alias` before joining. Optionally specify duration with a number, e.g. `!in 60` to join for 60 minutes.", inline=False)
    embed.add_field(name="!out", value="Leaves the player list.", inline=False)
    embed.add_field(name="!add", value="Add a player to the player list. Must specify player's username, e.g. `!add MU_Username`. You cannot control the duration with this command.", inline=False)
    embed.add_field(name="!remove", value="Removes a player from the player list. Must specify player's username, e.g. `!remove MU_Username`.", inline=False)
    embed.add_field(name="!rand", value="Randomly selects a game setup from a pre-defined list. Additional arguments may be used to specify thread title or id, e.g. `!rand -title \"Game Title\" -thread_id \"123456\"`.", inline=False)
    embed.add_field(name="!alias", value="Sets the user's Mafia Universe username for use in other commands, e.g. `!alias MU_Username`.", inline=False)
    embed.add_field(name="!clear", value="Resets the current game to defaults. Must be confirmed with `!clear -confirm`.", inline=False)
    embed.add_field(name="!list", value="Displays the current list of the game, including player list, waiting list, host, and setup.", inline=False)
    embed.add_field(name="!host", value="Sets the host of the game. By default, it will use your defined alias. You can specify a different host's username, e.g. `!host MU_Username`.", inline=False)
    embed.add_field(name="!game", value="Sets the game setup. Must specify setup name from available options: cop9, cop13, joat10, vig10, bomb10, bml10, doublejoat13, random10er or closedrandomXer [PlayerLimit]. The random10er setup randomizes between a vig, bomb, and joat game. E.g. `!game cop9`.", inline=False)
    await ctx.send(embed=embed)

async def new_game_spec_message(bot, thread_id, title):
    global message_ids

    channel = bot.get_channel(dvc_channel)
    
    message_text = f"Game thread: {title}, thread_id: {thread_id} has just randed! React with 👀 to spectate. Make sure you are not in the game or that you have died before adding yourself. Bot will attempt to auto add those who are signed up with their alias."
    message = await channel.send(message_text)
    await message.add_reaction('👀')

    message_ids[thread_id] = message.id

    return

@bot.event
async def on_message(message):
    global SNG_ping_message
    if message.channel.id == dvc_channel:
        await bot.process_commands(message)
        return

    if isinstance(message.channel, discord.DMChannel):
        if message.author.id in mods:
            target_channel = bot.get_channel(1287607575377875098)
            await target_channel.send(f"{message.content}")   

    if message.author == bot.user or message.channel.id not in allowed_channels:
        return
    await bot.process_commands(message)


@bot.event 
async def on_reaction_add(reaction, user):
    if user == bot.user or reaction.message.channel.id not in react_channels:
        return
    global game_host_name, player_limit, players, waiting_list, SNG_ping_message   
    if reaction.message.id == SNG_ping_message:
        if reaction.emoji == '✅':
            if user.id in banned_users:
                await reaction.message.channel.send("You have been banned for misusing bigping and are not allowed to in SNGs.")
                return
            if user.id not in aliases:
                await reaction.message.channel.send("Please set your MU username by using !alias MU_Username before inning!")
                return

            alias = aliases[user.id]

            if alias in game_host_name:
                if len(game_host_name) == 1:
                    game_host_name = ["Turby"]    
                    if len(players) < player_limit:
                        players[alias] = 60
                        await reaction.message.channel.send(f"{alias} has been removed as host and added to the list for the next 60 minutes.")
                    else:
                        waiting_list[alias] = 60
                        await reaction.message.channel.send(f"The list is full. {alias} has been removed as host and added to the waiting list instead.")
                elif len(game_host_name) > 1:
                    game_host_name.remove(alias)
                    if len(players) < player_limit:
                        players[alias] = 60
                        await reaction.message.channel.send(f"{alias} has been removed as host and added to the list for the next 60 minutes.")
                    else:
                        waiting_list[alias] = 60
                        await reaction.message.channel.send(f"The list is full. {alias} has been removed as host and added to the waiting list instead.")
                await update_status()    
                return
                
            if alias in players or alias in waiting_list:
                if alias in players:
                    players[alias] = 60
                    
                else:
                    waiting_list[alias] = 60
                    
                await reaction.message.channel.send(f"{alias}'s in has been renewed for the next 60 minutes.")
                #await ctx.message.add_reaction('👍')
            else:
                if len(players) < player_limit:
                    players[alias] = 60            
                    await reaction.message.channel.send(f'{alias} joined the game!')
                    #await ctx.message.add_reaction('👍')
                else:
                    waiting_list[alias] = 60
                    #await ctx.send(f"The list is full. {alias} has been added to the waiting list.")
                    #await ctx.message.add_reaction('👍')           
                    await reaction.message.channel.send(f'{alias} joined the waiting list!')
            await update_status()

    if reaction.message.id == status_id:
        if reaction.emoji == '✅':
            if user.id in banned_users:
                await reaction.message.channel.send("You have been banned for misusing bigping and are not allowed to in SNGs.")
                return
            if user.id not in aliases:
                await reaction.message.channel.send("Please set your MU username by using !alias MU_Username before inning!")
                return

            alias = aliases[user.id]

            if alias in game_host_name:
                if len(game_host_name) == 1:
                    game_host_name = ["Turby"]    
                    if len(players) < player_limit:
                        players[alias] = 60
                        await reaction.message.channel.send(f"{alias} has been removed as host and added to the list for the next 60 minutes.")
                    else:
                        waiting_list[alias] = 60
                        await reaction.message.channel.send(f"The list is full. {alias} has been removed as host and added to the waiting list instead.")
                elif len(game_host_name) > 1:
                    game_host_name.remove(alias)
                    if len(players) < player_limit:
                        players[alias] = 60
                        await reaction.message.channel.send(f"{alias} has been removed as host and added to the list for the next 60 minutes.")
                    else:
                        waiting_list[alias] = 60
                        await reaction.message.channel.send(f"The list is full. {alias} has been removed as host and added to the waiting list instead.")
                await update_status()    
                return
                
            if alias in players or alias in waiting_list:
                if alias in players:
                    players[alias] = 60
                    
                else:
                    waiting_list[alias] = 60
                    
                await reaction.message.channel.send(f"{alias}'s in has been renewed for the next 60 minutes.")
                #await ctx.message.add_reaction('👍')
            else:
                if len(players) < player_limit:
                    players[alias] = 60            
                    await reaction.message.channel.send(f'{alias} joined the game!')
                    #await ctx.message.add_reaction('👍')
                else:
                    waiting_list[alias] = 60
                    #await ctx.send(f"The list is full. {alias} has been added to the waiting list.")
                    #await ctx.message.add_reaction('👍')           
                    await reaction.message.channel.send(f'{alias} joined the waiting list!')
            await update_status()

    if reaction.message.id in message_ids.values():
        role_thread_id = find_key_by_value(message_ids, reaction.message.id)
        role_id = dvc_roles[int(role_thread_id)]
        guild = bot.get_guild(dvc_server)
        role = guild.get_role(role_id)
        member = guild.get_member(user.id)
        await member.add_roles(role)
        channel = bot.get_channel(dvc_channel)
        await channel.send(f"Added <@{user.id}> to #dvc-{str(role_thread_id)}")

@bot.command()
async def clear_dvc(ctx):
    if ctx.channel.id not in allowed_channels:  # Restrict to certain channels
        return
    try:
        await clear_active_games()
        await clear_dvc_roles()
    except:
        print("failed to run clear_dvc", flush=True)

async def clear_active_games():
    games_to_delete = []
    guild = bot.get_guild(dvc_server)

    active_games_category = bot.get_channel(1117176858304336012)
    games_to_delete = active_games_category.channels
    archive = bot.get_channel(dvc_archive)

    for game in games_to_delete:
        try:
            permissions = game.overwrites_for(guild.default_role)
            permissions.read_messages = True
            await game.edit(category=archive)
            await game.set_permissions(guild.default_role, overwrite=permissions)
            await game.send("This channel should now be open to everyone.")
        except:
            print("Failed in games_to_delete", flush=True)


async def clear_dvc_roles():
    roles_to_delete = []

    guild = bot.get_guild(dvc_server)
    for role in guild.roles:
        if "DVC:" in role.name:
            roles_to_delete.append(role)
    
    for role in roles_to_delete:
        try:
            await role.delete()
            print(f"Deleted role {role.name}")
        except:
            print(f"Couldnt delete role {role.name}")
       
TOKEN = os.environ.get('TOKEN')
# Run the bot
bot.run(TOKEN)

