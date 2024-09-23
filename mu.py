import requests
import hashlib
import re
from urllib3._collections import HTTPHeaderDict
import uuid
import json
import random
import mafia_roles
import town_roles
import independent_roles
import roles
from bs4 import BeautifulSoup

def load_json_file(json_file):
    with open(json_file, 'r') as f:
        return json.load(f)


#with open('turboers.json', 'r') as file:
#    name_image_pairs = json.load(file)
#with open('powerroles.json', 'r') as file:
#    pr_name_image_pairs = json.load(file)
#with open('wolves.json', 'r') as file:
#    wolf_name_image_pairs = json.load(file)

data = None

def generate_game_thread_uuid():
    random_uuid = str(uuid.uuid4())[:16]
    return f"Automated turbo game thread: {random_uuid}"
    
def login(username, password):
    session = requests.Session()
    login_url = "https://www.mafiauniverse.com/forums/login.php"  # Replace with the actual login URL

    # Encode the password as MD5 hash
    md5_password = hashlib.md5(password.encode('utf-8')).hexdigest()

    # Form data for login
    payload = {
        "do": "login",
        "vb_login_username": username,
        "vb_login_md5password": md5_password,
        "vb_login_md5password_utf": md5_password,
        "s": "",
        "securitytoken": "guest",
		"vb_login_password": "",
		"vb_login_password_hint": "Password",
		"cookieuser": "1"
    }

    # Send POST request to login
    response = session.post(login_url, data=payload)

    # Check if login was successful (verify response status code, content, or other criteria)
    if response.status_code == 200:
        print("Login successful.")

    else:
        print("Login failed.")
    
    return session

def extract_security_token(response_text):
    # Extract the security token from JavaScript code using regex
    pattern = r'var\s+SECURITYTOKEN\s+=\s+"([^"]+)";'
    match = re.search(pattern, response_text)
    if match:
        security_token = match.group(1)
        return security_token
    return None

def extract_game_id(response_text):
    soup = BeautifulSoup(response_text, 'html.parser')
    game_id = soup.find('li', {'class': 'game-thread'}).get('data-gameid')

    return game_id

def open_game_thread(session, thread_id):
    url = f"https://www.mafiauniverse.com/forums/threads/{thread_id}"
    response = session.get(url)
    security_token = extract_security_token(response.text)
    game_id = extract_game_id(response.text)

    return game_id, security_token 

def ita_window(session, game_id, security_token):
    url = "https://www.mafiauniverse.com/forums/modbot/ita-window.php"

    payload = {
        "do": "open",
        "game_id": game_id,
        "timeout": "60",
        "securitytoken": security_token
        }
    itas = session.post(url, data=payload)
    return itas.text

def sub_player(session, game_id, player, player_in, security_token):
    url = "https://www.mafiauniverse.com/forums/modbot/subs.php"

    payload = {
        "do": "immediate-sub",
        "game_id": game_id,
        "player": player,
        "player_in": player_in,
        "reason": "Automatic turbot replacement",
        "securitytoken": security_token
        }
    subs = session.post(url, data=payload)
    return subs.text
    
def new_thread_token(session):
    protected_url = "https://www.mafiauniverse.com/forums/newthread.php"
    #
    payload = {
        "do": "newthread",
        "f": "6"
        }
        
    response = session.get(protected_url, data=payload)
    
    security_token = extract_security_token(response.text)
    if security_token:
        print("Security token extracted and stored.")
        return security_token
    else:
        print("Failed to extract security token.")

def list_dicts_in_module(module):
    dict_names = [name for name in dir(module) if isinstance(getattr(module, name), dict)]
    return dict_names

def post_thread(session, game_title, security_token, setup, test):

    flavor = load_json_file('flavor.json')
    flavors = flavor['flavors']

    protected_url = "https://www.mafiauniverse.com/forums/newthread.php"

    if setup == "closedrandomXer":
        town_role_names = [name for name in dir(town_roles) if not name.startswith('__')]
        mafia_role_names = [name for name in dir(mafia_roles)  if not name.startswith('__')]
        independent_role_names = [name for name in dir(independent_roles) if not name.startswith('__')]

        town_descriptions = []
        mafia_descriptions = []
        independent_descriptions = []

        def extract_descriptions(role_categories):
            descriptions = []
            for category in role_categories:
                if isinstance(category, dict):
                    for role in category.values():
                        descriptions.append(role.get('description', 'Unknown role, tell @benneh to fix this!'))
            return descriptions    
        """
        for name in town_role_names:
            role = getattr(town_roles, name)
            town_descriptions.append(role.get('description', 'Unknown role, tell @benneh to fix this!'))
        for name in mafia_role_names:
            role = getattr(mafia_roles, name)
            mafia_descriptions.append(role.get('description', 'Unknown role, tell @benneh to fix this!'))
        for name in independent_role_names:
            role = getattr(independent_roles, name)
            independent_descriptions.append(role.get('description', 'Unknown role, tell @benneh to fix this!'))
        """
        town_role_categories = [town_roles.killing_roles, town_roles.utility_roles]
        town_descriptions.extend(extract_descriptions(town_role_categories))

        # Extract descriptions for mafia roles
        mafia_role_categories = [mafia_roles.killing_roles, mafia_roles.utility_roles]
        mafia_descriptions.extend(extract_descriptions(mafia_role_categories))

        for name in independent_role_names:
            role = getattr(independent_roles, name)
            independent_descriptions.append(role.get('description', 'Unknown role, tell @benneh to fix this!'))


        town_flavor = "<br>[*]".join(town_descriptions)
        mafia_flavor = "<br>[*]".join(mafia_descriptions)
        independent_flavor = "<br>[*]".join(independent_descriptions)

        town_flavor = "[*]" + town_flavor
        mafia_flavor = "[*]" + mafia_flavor
        independent_flavor = "[*]" + independent_flavor

        if setup == "closedrandomXer":
            game_flavor = f'''[CENTER][TITLE][B]This is a closed and random Xer[/B][/TITLE][/CENTER]
<br><br>[B][SIZE=4]Roles have been randomly selected from a pool of roles Turby has access to that is ever growing.[/SIZE][/B]
<br><br>[BOX=Setup possibilities]
<br><br>[LIST]
<br>[*]This cannot rand as mountainous (unless the setup only has 1 wolf). 
<br>[*]The [B][COLOR=#ff0000]wolf team[/B][/COLOR] will always be 25% of the total players, rounded down. (e.g. 12 players = 3 wolves, 15 players = 3 wolves, 16 players = 4 wolves)
<br>[*]The amount of PRs for each team will be: (# of wolves / 2) [b]or[/b] ((# of wolves / 2) + 1), e.g. 4 wolves = 2 PRs minimum, possibly 3
<br>[*]Both teams will have the same amount of PRs in closedrandomXers.
<br>[*]There is a [COLOR=#800080][B]1.5% chance for the last vanilla villager to rand as an [/B][/COLOR][B][COLOR=#800080]independent role[/COLOR][/B] instead.[COLOR=#800080][B] Independent roles no longer take up town PR slots.[/b][/color]
<br>[*]In [b]2 POWER ROLE SETUPS[/b], there will be a MAXIMUM of 1 Killing role per team, but killing roles are NO LONGER GUARANTEED in these setups. 2 util roles for both teams are now possible or 2 util for one team, and 1 util 1 killing for the other. The only thing that is not possible is a team having 2 killing roles. 
<br>[*]If there is 1 POWER ROLE or 3 or MORE POWER ROLES, any combination of KILLING/UTILITY can rand for both teams.
<br>[*]There is no weight assigned to any power roles--any variation of these setups is possible and balance is not guaranteed. 
<br>[*]There is an [b]10%[/b] chance for any wolf to rand a bulletproof vest in addition to the rest of it's role.
<br>[*]There is a [b]20%[/b] total chance for neighbors to rand into the setup. They can be any pairing of VT/PR/Wolves.
<br>[/LIST]
<br>[/BOX]
<br><br>[BOX=Cop Checks may not be trustworthy!]
<br>[LIST]
<br>[*][COLOR=#8b4513][B]Millers and Godfathers[/B][/COLOR] can be randed into this setup. Millers are unaware and show as vanilla villagers in their role PMs.
<br>[*]Each [B][COLOR=#008000]VT [/COLOR][/B]has a standalone [B]2.5%[/B] chance to rand as a miller instead. 
<br>[*][b]EVERY[/b] [B][COLOR=#ff0000]wolf [/COLOR][/B]has a standalone [B]5%[/B] chance to rand as a godfather in addition to the rest of it's role. 
<br>[*]The existence of a flipped [B][COLOR=#8b4513]Miller or Godfather[/COLOR][/B]  does NOT confirm or deny the existence of any [B]cops [/B]in the setup. 
<br>[*][COLOR=#8b4513][B]Millers [/B][/COLOR]do not count as a '[COLOR=#008000][B]PR[/B][/COLOR]' slot for the town - they only replace [B][COLOR=#008000]VTs[/COLOR][/B]. 
<br>[/LIST]
<br>[/BOX]
<br><br>[BOX=Possible Village Roles][LIST=1]
{town_flavor}[/LIST][/BOX]
<br><br>[BOX=Possible Independent Roles][LIST=1]
{independent_flavor}[/LIST][/BOX]
<br><br>[BOX=Possible Wolf Roles][LIST=1]
{mafia_flavor}[/LIST][/BOX]
<br><br>[BOX=Suffix Legend][LIST=1]
[*][B]d(x)[/B] - Day (x) use of the PR
[*][B]de[/B] - Disabled in Endgame
[*][B]c [/B]- Compulsive
[*][B]m [/B]- Macho
[*][B]st [/B]- Self-Targetable
[*][B]gf [/B]- Godfather[/LIST][/BOX]'''

        #game_flavor = f"[CENTER][TITLE][B]This is a closed and random 10er[/B][/TITLE][/CENTER]<br><br>[B][SIZE=4]Roles have been randomly selected from a pool of roles Turby has access to that is ever growing.[/SIZE][/B]<br><br>[BOX=Setup possibilities][LIST][*]This cannot rand as mountainous.<br>[*]The village rands between 1 and 2 PRs. There is a [b]1% chance[/b] that each village PR rands as an independent role instead. If the village rands 1 PR, the wolves rand between 0 and 1 PRs. If the village rands 2 PRs, the wolves rand between 1 and 2 PRs. There is no weight assigned to any power roles--any variation of these setups is possible and balance is not guaranteed.<br><br>Millers can be randed into this setup. Each VT has a standalone 5% chance to rand as a miller instead. This does [b]NOT[/b] confirm or deny the existance of cops. Millers do not count as a 'PR' slot for the town. Godfathers may exist for mafia, but only as PR roles and the ones that are are noted in the role list below. <br><br>There are at most 2 PRs for the village and at most 2 for the wolves. <br><br>These are the roles possible for the village: <br><br>{town_flavor}<br><br>These are the roles possible for 3rd-party/independent:<br><br>{independent_flavor}<br><br>These are the roles possible for wolves:<br><br>{mafia_flavor}<br><br><br>[COLOR=\"#FF0000\"][U][B]Suffix Legend:[/B][/U][/COLOR]<br>[B]d(x)[/B] - Day (x) use of the PR<br>[B]de[/B] - Disabled in Endgame<br>[B]c [/B]- Compulsive<br>[B]m [/B]- Macho<br>[B]st [/B]- Self-Targetable<br>[B]gf [/B]- Godfather"
    else:
        game_flavor = random.choice(flavors)

    if test == False:
        forum = "6"
    else:
        forum = "48"
        
    payload = {
        "do": "postthread",
        "f": forum,
        "s": "",
        "prefixid": "GameThread",
        "subject": f"{game_title} - [{setup} game]",
        "message": game_flavor,
        "message_backup": game_flavor,
        "sbutton": "Submit New Thread",
        "securitytoken": security_token,
        "wysiwyg": "1",
        "iconid": "0",        
        }
        
    response = session.post(protected_url, data=payload)
    
    if response.status_code == 200:
        print("Thread attempt successful.")
        thread_id = extract_thread_id(response.text)
        return thread_id
        
    else:
        print("Thread creation failed.")

def extract_thread_id(response_text):
    start_index = response_text.find('type="hidden" name="t" value="')
    if start_index != -1:
        start_index += len('name="t" type="hidden" value="')
        end_index = response_text.find('"', start_index)
        if end_index != -1:
            thread_id = response_text[start_index:end_index]
            return thread_id
    return None
    
def new_game_token(session, thread_id):
    protected_url = "https://www.mafiauniverse.com/forums/modbot/manage-game/"
    
    payload = {
        "do": "newgame",
        "thread_id": thread_id
        }
        
    response = session.get(protected_url, data=payload)
    
    security_token = extract_security_token(response.text)
    if security_token:
        print("Security token extracted and stored.")
        return security_token
    else:
        print("Failed to extract security token.")
        
def start_game(session, security_token, game_title, thread_id, player_aliases, game_setup, day_length, night_length, host_name, anon_enabled, player_limit):
    global data

    if game_setup == "closedrandomXer":
        setup_title = "closedrandomXer"
        final_game_setup = game_setup
        data = HTTPHeaderDict({'s': '', 'securitytoken': security_token, 'submit': '1', 'do': 'newgame', 'automated': '0', 'automation_setting': '2', 'game_name': f"{game_title} - [{setup_title} game]", 'thread_id': thread_id, 'speed_type': '1', 'game_type': 'Closed', 'period': 'day', 'phase': '1', 'phase_end': '', 'started': '1', 'start_date': '', 'votecount_interval': '0', 'votecount_units': 'minutes', 'speed_preset': 'custom', 'day_units': 'hours', 'night_units': 'hours', 'itas_enabled': '0', 'default_ita_hit': '15', 'default_ita_count': '1', 'ita_immune_policy': '0', 'alias_pool': 'Greek_Alphabet', 'daily_post_limit': '0', 'postlimit_cutoff': '0', 'postlimit_cutoff_units': 'hours', 'character_limit': '0', 'proxy_voting': '0', 'tied_lynch': '1', 'self_voting': '0', 'no_lynch': '1', 'announce_lylo': '1', 'votes_locked': '1', 'votes_locked_manual': '0', 'auto_majority': '2', 'maj_delay': '0', 'show_flips': '0', 'suppress_rolepms': '0', 'suppress_phasestart': '0', 'day_action_cutoff': '1', 'mafia_kill_enabled': '1', 'mafia_kill_type': 'kill', 'detailed_flips': '0', 'backup_inheritance': '0', 'mafia_win_con': '1', 'mafia_kill_assigned': '1', 'mafia_day_chat': '1', 'characters_enabled': '2', 'role_quantity': '1'})
        
    else:
        final_game_setup = game_setup
        setup_title = final_game_setup
        data = HTTPHeaderDict({'s': '', 'securitytoken': security_token, 'submit': '1', 'do': 'newgame', 'automated': '0', 'automation_setting': '2', 'game_name': f"{game_title} - [{setup_title} game]", 'thread_id': thread_id, 'speed_type': '1', 'game_type': 'Open', 'period': 'day', 'phase': '1', 'phase_end': '', 'started': '1', 'start_date': '', 'votecount_interval': '0', 'votecount_units': 'minutes', 'speed_preset': 'custom', 'day_units': 'hours', 'night_units': 'hours', 'itas_enabled': '0', 'default_ita_hit': '15', 'default_ita_count': '1', 'ita_immune_policy': '0', 'alias_pool': 'Greek_Alphabet', 'daily_post_limit': '0', 'postlimit_cutoff': '0', 'postlimit_cutoff_units': 'hours', 'character_limit': '0', 'proxy_voting': '0', 'tied_lynch': '1', 'self_voting': '0', 'no_lynch': '1', 'announce_lylo': '1', 'votes_locked': '1', 'votes_locked_manual': '0', 'auto_majority': '2', 'maj_delay': '0', 'show_flips': '0', 'suppress_rolepms': '0', 'suppress_phasestart': '0', 'day_action_cutoff': '1', 'mafia_kill_enabled': '1', 'mafia_kill_type': 'kill', 'detailed_flips': '0', 'backup_inheritance': '0', 'mafia_win_con': '1', 'mafia_kill_assigned': '1', 'mafia_day_chat': '1', 'characters_enabled': '2', 'role_quantity': '1'})


    data.add('day_length', day_length)
    data.add('night_length', night_length)
    num_hosts = len(host_name)
    data.add('num_hosts', num_hosts)
    
    if anon_enabled == True:
        data.add('aliased', '1')
        data.add('alias_pool', 'Marvel')
    elif anon_enabled == False:
        data.add('aliased', '0')
    

    if final_game_setup == "joat10":
        add_joat_roles(game_title)
        data.add("preset", "custom")
        data.add('num_players', '10')
        data.add('roles_dropdown', '39')
    if final_game_setup == "bomb10":
        add_bomb_roles(game_title)
        data.add("preset", "custom")
        data.add('num_players', '10')
    if final_game_setup == "vig10":
        add_vig_roles(game_title)
        data.add("preset", "vig-10") 
        data.add('num_players', '10')
    if final_game_setup == "bml10":
        add_bml_roles(game_title)
        data.add("preset", "custom")
        data.add('num_players', '10')
    if final_game_setup == "closedrandomXer":
        add_closedrandomXer_roles(game_title, player_limit)
        data.add("preset", "custom")
        data.add('num_players', player_limit)
    if final_game_setup == "ita10":
        add_ita10_roles(game_title)
        data.add("preset", "custom")
        data.add("num_players", "10")
        data.add("itas_enabled", "1")
        data.add("default_ita_hit", "25")
        data.add("default_ita_count", "1")
        data.add("ita_immune_policy", "0")
    if final_game_setup == "ita13":
        add_ita13_roles(game_title)
        data.add("preset", "custom")
        data.add("num_players", "13")
        data.add("itas_enabled", "1")
        data.add("default_ita_hit", "25")
        data.add("default_ita_count", "1")
        data.add("ita_immune_policy", "0")
    if final_game_setup == "cop9":
        add_cop9_roles(game_title)
        data.add("preset", "cop-9")
        data.add('num_players', '9')
        data.add('n0_peeks', '1')
    if final_game_setup == "cop13":
        add_cop13_roles(game_title)
        data.add("preset", "cop-13")
        data.add('num_players', '13')
        data.add('n0_peeks', '1')
    if final_game_setup == "doublejoat13":
        add_doublejoat13_roles(game_title)
        data.add("preset", "custom")
        data.add('num_players', '13')

    add_players(player_aliases, host_name)
    
    protected_url = "https://www.mafiauniverse.com/forums/modbot/manage-game/"
    response = session.post(protected_url, data=data)
    if response.status_code == 200:
        print("Game rand submitted successfully")
        soup = BeautifulSoup(response.text, 'html.parser')
        
        errors_div = soup.find('div', class_='errors')
        if errors_div:
            blockhead_text = errors_div.find('h2', class_='blockhead').get_text(strip=True)
            
            if blockhead_text == "Success!":
                success_message = errors_div.find('div', class_='blockrow').find('p').get_text(strip=True)
                print(success_message)
                return success_message
            
            elif blockhead_text == "Errors":
                error_message = errors_div.find('div', class_='blockrow').find('p').get_text(strip=True)
                print(error_message)
                return error_message
                
            else:
                print("Unexpected blockhead text received:", blockhead_text)
                return ("Unexpected blockhead text received:", blockhead_text)
        else:
            print("No 'errors' div found in the response.")            
            return ("No 'errors' div found in the response.")

    else:
        print("Game rand fucked up")


def load_flavor_jsons():
    name_image_pairs = load_json_file('turboers.json')
    pr_name_image_pairs = load_json_file('powerroles.json')
    wolf_name_image_pairs = load_json_file('wolves.json')
    return name_image_pairs, pr_name_image_pairs, wolf_name_image_pairs

def add_closedrandomXer_roles(game_title, player_limit=13):
    global data
    
    name_image_pairs, pr_name_image_pairs, wolf_name_image_pairs = load_flavor_jsons()

    wolf_count = (player_limit * 25) // 100
    village_count = player_limit - wolf_count

    pr_base_count = wolf_count // 2

    village_pr_count = random.randint(pr_base_count, pr_base_count + 1)
    wolf_pr_count = village_pr_count

    if village_pr_count == 2:
        village_killing_role_count = random.randint(0,1)
        wolf_killing_role_count = random.randint(0,1)
        village_utility_role_count = village_pr_count - village_killing_role_count
        wolf_utility_role_count = wolf_pr_count - wolf_killing_role_count
    else:
        village_killing_role_count = random.randint(0, village_pr_count)
        village_utility_role_count = village_pr_count - village_killing_role_count
        wolf_killing_role_count = random.randint(0, wolf_pr_count)
        wolf_utility_role_count = wolf_pr_count - wolf_killing_role_count
    
    village_vt_count = village_count - village_pr_count
    wolf_goon_count = wolf_count - wolf_pr_count


    villagers = random.sample(name_image_pairs, village_vt_count)
    village_prs = random.sample(pr_name_image_pairs, village_pr_count)
    independent_prs = random.sample(pr_name_image_pairs, village_pr_count)
    wolves = random.sample(wolf_name_image_pairs, wolf_count)

    village_killing_roles = [value for key, value in town_roles.killing_roles.items()]
    village_utility_roles = [value for key, value in town_roles.utility_roles.items()]
 
    wolf_killing_roles = [value for key, value in mafia_roles.killing_roles.items()]
    wolf_utility_roles = [value for key, value in mafia_roles.utility_roles.items()]

    thirdparty_roles = [value for key, value in vars(independent_roles).items() if isinstance(value, dict) and '__name__' not in value.keys()]

    selected_village_killing_roles = random.sample(village_killing_roles, village_killing_role_count)
    selected_village_utility_roles = random.sample(village_utility_roles, village_utility_role_count)
    selected_wolf_killing_roles = random.sample(wolf_killing_roles, wolf_killing_role_count)
    selected_wolf_utility_roles = random.sample(wolf_utility_roles, wolf_utility_role_count)

    selected_village_roles = selected_village_killing_roles + selected_village_utility_roles
    selected_wolf_roles = selected_wolf_killing_roles + selected_wolf_utility_roles
    selected_independent_roles = random.sample(thirdparty_roles, 1)
    
    neighbor_rand = random.random()

    vvneighbors, vprvneighbors, vtwneighbors, vprwneighbors, wwneighbors = False, False, False, False, False

    if 0.0 <= neighbor_rand < 0.05:
        vvneighbors = True
    elif 0.05 <= neighbor_rand < 0.1:
        vprvneighbors = True
    elif 0.1 <= neighbor_rand < 0.15:
        vtwneighbors = True
    elif 0.15 <= neighbor_rand < .2:
        vprwneighbors = True

    for i in range(0, village_vt_count):

        if i == village_vt_count - 1:
            independent_rand = random.random()
            if independent_rand <=.015:
                current_ind = selected_independent_roles[i].copy()
                current_ind['character_name'] = villagers[i]['character_name']
                current_ind['character_image'] = villagers[i]['character_image']
                ind_json = json.dumps(current_ind)
                data.add("roles[]", ind_json)
            else:
                current_vt = roles.vt.copy()
                current_vt['character_name'] = villagers[i]['character_name']
                current_vt['character_image'] = villagers[i]['character_image']
                vt_json = json.dumps(current_vt)
                data.add("roles[]", vt_json)
                data.add("role_pms[]", f"[CENTER][TITLE]Role PM for {game_title}[/TITLE][/CENTER]\n\nYou are [B][COLOR=#339933]Vanilla Villager[/COLOR][/B]. You win when all threats to the Village have been eliminated.{{HIDE_FROM_FLIP}}\n\n{{ROLE_PM_FOOTER_LINKS}}{{/HIDE_FROM_FLIP}}")
        else:
            if vvneighbors and i in [0, 1]:
                current_vt = roles.vt.copy()
                current_vt['character_name'] = villagers[i]['character_name']
                current_vt['character_image'] = villagers[i]['character_image']
                current_vt['neighbor'] = "a"
                vt_json = json.dumps(current_vt)
                data.add("roles[]", vt_json)
            elif (vtwneighbors and i in [0]) or (vprvneighbors and i in [0]):
                current_vt = roles.vt.copy()
                current_vt['character_name'] = villagers[i]['character_name']
                current_vt['character_image'] = villagers[i]['character_image']
                current_vt['neighbor'] = "a"
                vt_json = json.dumps(current_vt)
                data.add("roles[]", vt_json)
            else:
                current_vt = roles.vt.copy()
                current_vt['character_name'] = villagers[i]['character_name']
                current_vt['character_image'] = villagers[i]['character_image']
                vt_json = json.dumps(current_vt)
                data.add("roles[]", vt_json)

    for i in range(0, village_pr_count):
        current_pr = selected_village_roles[i].copy()
        current_pr['character_name'] = village_prs[i]['character_name']
        current_pr['character_image'] = village_prs[i]['character_image']
        if vprvneighbors and i in [0]:
            current_pr['neighbor'] = "a"
        elif vprwneighbors and i in [0]:
            current_pr['neighbor'] = "a"
        pr_json = json.dumps(current_pr)
        data.add("roles[]", pr_json)
        
    for i in range(0, wolf_pr_count):
        wolf = wolves.pop(0)
        bpv_rand = random.random()
        gf_rand = random.random()

        current_wolf = selected_wolf_roles[i].copy()
        if bpv_rand <=.1:
            current_wolf['bpv_status'] = "1"
        if gf_rand <=.05:
            current_wolf['godfather'] = "1"
        if vtwneighbors and i in [0]:
            current_wolf['neighbor'] = "a"
        elif vprwneighbors and i in [0]:
            current_wolf['neighbor'] = "a"
        current_wolf['character_name'] = wolf['character_name']
        current_wolf['character_image'] = wolf['character_image']
        wolf_json = json.dumps(current_wolf)
        data.add("roles[]", wolf_json)

    for i in range(0, wolf_goon_count):
        wolf = wolves.pop(0)
        bpv_rand = random.random()
        gf_rand = random.random()

        current_wolf = roles.goon.copy()
        if bpv_rand <=.1:
            current_wolf['bpv_status'] = "1"
        if gf_rand <=.05:
            current_wolf['godfather'] = "1"

        current_wolf['character_name'] = wolf['character_name']
        current_wolf['character_image'] = wolf['character_image']
        wolf_json = json.dumps(current_wolf)
        data.add("roles[]", wolf_json)

def add_ita10_roles(game_title):
    global data
    
    name_image_pairs, pr_name_image_pairs, wolf_name_image_pairs = load_flavor_jsons()

    villagers = random.sample(name_image_pairs, 8)
    wolves = random.sample(wolf_name_image_pairs, 2)

    for i in range(0,8):
        current_vanchilla = roles.vt.copy()
        current_vanchilla['character_name'] = villagers[i]["character_name"]
        current_vanchilla['character_image'] = villagers[i]["character_image"]
        vt_json = json.dumps(current_vanchilla)
        data.add("roles[]", vt_json)

    for i in range(0,2):
        current_wolves = roles.goon.copy()
        current_wolves['character_name'] = wolves[i]['character_name']
        current_wolves['character_image'] = wolves[i]['character_image']
        wolf_json = json.dumps(current_wolves)
        data.add("roles[]", wolf_json)

def add_ita13_roles(game_title):
    global data
    
    name_image_pairs, pr_name_image_pairs, wolf_name_image_pairs = load_flavor_jsons()

    villagers = random.sample(name_image_pairs, 9)
    wolves = random.sample(wolf_name_image_pairs, 4)

    for i in range(0,9):
        current_vanchilla = roles.vt.copy()
        current_vanchilla['character_name'] = villagers[i]["character_name"]
        current_vanchilla['character_image'] = villagers[i]["character_image"]
        vt_json = json.dumps(current_vanchilla)
        data.add("roles[]", vt_json)
   
    for i in range(0,4):
        current_wolves = roles.goon.copy()
        current_wolves['character_name'] = wolves[i]['character_name']
        current_wolves['character_image'] = wolves[i]['character_image']
        wolf_json = json.dumps(current_wolves)
        data.add("roles[]", wolf_json)


def add_joat_roles(game_title):
    global data
    
    name_image_pairs, pr_name_image_pairs, wolf_name_image_pairs = load_flavor_jsons()

    villagers = random.sample(name_image_pairs, 7)
    joat = random.sample(pr_name_image_pairs, 1)
    wolves = random.sample(wolf_name_image_pairs, 2)

    for i in range(0,7):
        current_vanchilla = roles.vt.copy()
        current_vanchilla['character_name'] = villagers[i]["character_name"]
        current_vanchilla['character_image'] = villagers[i]["character_image"]
        vt_json = json.dumps(current_vanchilla)
        data.add("roles[]", vt_json)
 
    current_joat = town_roles.utility_roles['joat_peekvigdoc'].copy()
    current_joat['character_name'] = joat[0]["character_name"]
    current_joat['character_image'] = joat[0]["character_image"]
    joat_json = json.dumps(current_joat)
    data.add("roles[]", joat_json)
 
    for i in range(0,2):
        current_wolves = roles.goon.copy()
        current_wolves['character_name'] = wolves[i]['character_name']
        current_wolves['character_image'] = wolves[i]['character_image']
        wolf_json = json.dumps(current_wolves)
        data.add("roles[]", wolf_json)

def add_bomb_roles(game_title):
    global data
    
    name_image_pairs, pr_name_image_pairs, wolf_name_image_pairs = load_flavor_jsons()

    villagers = random.sample(name_image_pairs, 6)
    powerroles_bomb = random.sample(pr_name_image_pairs, 2)
    wolves = random.sample(wolf_name_image_pairs, 2)

    for i in range(0,6):
        current_vanchilla = roles.vt.copy()
        current_vanchilla['character_name'] = villagers[i]["character_name"]
        current_vanchilla['character_image'] = villagers[i]["character_image"]
        vt_json = json.dumps(current_vanchilla)
        data.add("roles[]", vt_json)
  
    for i in range (0,2):
        if i < 1:
            current_ic = town_roles.utility_roles['ic_d2plus'].copy()
            current_ic['character_name'] = powerroles_bomb[i]["character_name"]
            current_ic['character_image'] = powerroles_bomb[i]["character_image"]
            ic_json = json.dumps(current_ic)
            data.add("roles[]", ic_json)
        else: 
            current_inven = town_roles.killing_roles['inv_1xsuibomb'].copy()
            current_inven['character_name'] = powerroles_bomb[i]["character_name"]
            current_inven['character_image'] = powerroles_bomb[i]["character_image"]
            inven_json = json.dumps(current_inven)
            data.add("roles[]", inven_json)
            
    for i in range(0,2):
        if i < 1:
            current_wolves = mafia_roles.killing_roles['prk_1x'].copy()
            current_wolves['character_name'] = wolves[i]['character_name']
            current_wolves['character_image'] = wolves[i]['character_image']
            wolf_json = json.dumps(current_wolves)
            data.add("roles[]", wolf_json)
        else:
            current_wolves = mafia_roles.utility_roles['rb_1x'].copy()
            current_wolves['character_name'] = wolves[i]['character_name']
            current_wolves['character_image'] = wolves[i]['character_image']
            wolf_json = json.dumps(current_wolves)
            data.add("roles[]", wolf_json)
 

def add_bml_roles(game_title):
    global data
    
    name_image_pairs, pr_name_image_pairs, wolf_name_image_pairs = load_flavor_jsons()

    villagers = random.sample(name_image_pairs, 7)
    powerroles_bml = random.sample(pr_name_image_pairs, 1)
    wolves = random.sample(wolf_name_image_pairs, 2)

    for i in range(0,7):
        current_vanchilla = roles.vt.copy()
        current_vanchilla['character_name'] = villagers[i]["character_name"]
        current_vanchilla['character_image'] = villagers[i]["character_image"]
        vt_json = json.dumps(current_vanchilla)
        data.add("roles[]", vt_json)
   

    current_inven = town_roles.killing_roles['inv_2xdayvig'].copy()
    current_inven['character_name'] = powerroles_bml[0]["character_name"]
    current_inven['character_image'] = powerroles_bml[0]["character_image"]
    inven_json = json.dumps(current_inven)
    data.add("roles[]", inven_json)
    
    for i in range(0,2):
        if i < 1:
            current_wolves = roles.goon.copy()
            current_wolves['character_name'] = wolves[i]['character_name']
            current_wolves['character_image'] = wolves[i]['character_image']
            wolf_json = json.dumps(current_wolves)
            data.add("roles[]", wolf_json)
        else:
            current_wolves = mafia_roles.utility_roles['rb_2x'].copy()
            current_wolves['character_name'] = wolves[i]['character_name']
            current_wolves['character_image'] = wolves[i]['character_image']
            wolf_json = json.dumps(current_wolves)
            data.add("roles[]", wolf_json)
       



def add_doublejoat13_roles(game_title):

    global data
    name_image_pairs, pr_name_image_pairs, wolf_name_image_pairs = load_flavor_jsons()

    villagers = random.sample(name_image_pairs, 9)
    joat = random.sample(pr_name_image_pairs, 1)
    wolves = random.sample(wolf_name_image_pairs, 3)    

    for i in range(0,9):
        current_vanchilla = roles.vt.copy()
        current_vanchilla['character_name'] = villagers[i]["character_name"]
        current_vanchilla['character_image'] = villagers[i]["character_image"]
        vt_json = json.dumps(current_vanchilla)
        data.add("roles[]", vt_json)
      
    current_joat = town_roles.utility_roles['joat_peekvigdoc'].copy()
    current_joat['character_name'] = joat[0]["character_name"]
    current_joat['character_image'] = joat[0]["character_image"]
    joat_json = json.dumps(current_joat)
    data.add("roles[]", joat_json)
    
    for i in range(0,3):
        if i < 2:
            current_wolves = roles.goon.copy()
            current_wolves['character_name'] = wolves[i]['character_name']
            current_wolves['character_image'] = wolves[i]['character_image']
            wolf_json = json.dumps(current_wolves)
            data.add("roles[]", wolf_json)
        
        else:
            current_wolves = mafia_roles.utility_roles['joat_rb_rd_track'].copy()
            current_wolves['character_name'] = wolves[i]['character_name']
            current_wolves['character_image'] = wolves[i]['character_image']
            wolf_json = json.dumps(current_wolves)
            data.add("roles[]", wolf_json)
  
def add_vig_roles(game_title):	
    global data

    name_image_pairs, pr_name_image_pairs, wolf_name_image_pairs = load_flavor_jsons()
    villagers = random.sample(name_image_pairs, 7)
    vig = random.sample(pr_name_image_pairs, 1)
    wolves = random.sample(wolf_name_image_pairs, 2)

    for i in range(0,7):
        current_vanchilla = roles.vt.copy()
        current_vanchilla['character_name'] = villagers[i]["character_name"]
        current_vanchilla['character_image'] = villagers[i]["character_image"]
        vt_json = json.dumps(current_vanchilla)
        data.add("roles[]", vt_json)
    
    current_vig = town_roles.killing_roles['vig_2x'].copy()
    current_vig['character_name'] = vig[0]['character_name']
    current_vig['character_image'] = vig[0]['character_image']
    vig_json = json.dumps(current_vig)
    data.add("roles[]", vig_json)
    
    for i in range(0,2):
        current_wolves = roles.goon.copy()
        current_wolves['character_name'] = wolves[i]['character_name']
        current_wolves['character_image'] = wolves[i]['character_image']
        wolf_json = json.dumps(current_wolves)
        data.add("roles[]", wolf_json)
 

def post(session, thread_id, security_token, message):
	url = f"https://www.mafiauniverse.com/forums/newreply.php?do=postreply&t={thread_id}"
	payload = {
		"do": "postreply",
		"t": thread_id,
		"p": "who cares",
		"sbutton": "Post Quick Reply",
		"wysiwyg": "0",
		"message": message,
		"message_backup": message,
		"fromquickreply": "1",
		"securitytoken": security_token
		}
	post = session.post(url, data=payload)
	return post.text

def add_cop9_roles(game_title):	
    global data

    name_image_pairs, pr_name_image_pairs, wolf_name_image_pairs = load_flavor_jsons()
    villagers = random.sample(name_image_pairs, 6)
    cop = random.sample(pr_name_image_pairs, 1)
    wolves = random.sample(wolf_name_image_pairs, 2)

    for i in range(0,6):
        current_vanchilla = roles.vt.copy()
        current_vanchilla['character_name'] = villagers[i]["character_name"]
        current_vanchilla['character_image'] = villagers[i]["character_image"]
        vt_json = json.dumps(current_vanchilla)
        data.add("roles[]", vt_json)
   
    current_cop = town_roles.utility_roles['cop'].copy()
    current_cop['character_name'] = cop[0]["character_name"]
    current_cop['character_image'] = cop[0]["character_image"]
    cop_json = json.dumps(current_cop)
    data.add("roles[]", cop_json)
     
    for i in range(0,2):
        current_wolves = roles.goon.copy()
        current_wolves['character_name'] = wolves[i]['character_name']
        current_wolves['character_image'] = wolves[i]['character_image']
        wolf_json = json.dumps(current_wolves)
        data.add("roles[]", wolf_json)
 

def add_cop13_roles(game_title):
	
    global data

    name_image_pairs, pr_name_image_pairs, wolf_name_image_pairs = load_flavor_jsons()
    villagers = random.sample(name_image_pairs, 9)
    cop = random.sample(pr_name_image_pairs, 1)
    wolves = random.sample(wolf_name_image_pairs, 3)

    for i in range(0,9):
        current_vanchilla = roles.vt.copy()
        current_vanchilla['character_name'] = villagers[i]["character_name"]
        current_vanchilla['character_image'] = villagers[i]["character_image"]
        vt_json = json.dumps(current_vanchilla)
        data.add("roles[]", vt_json)
  
    current_cop = town_roles.utility_roles['cop'].copy()
    current_cop['character_name'] = cop[0]["character_name"]
    current_cop['character_image'] = cop[0]["character_image"]
    cop_json = json.dumps(current_cop)
    data.add("roles[]", cop_json)
     
    for i in range(0,3):
        current_wolves = roles.goon.copy()
        current_wolves['character_name'] = wolves[i]['character_name']
        current_wolves['character_image'] = wolves[i]['character_image']
        wolf_json = json.dumps(current_wolves)
        data.add("roles[]", wolf_json)
 
def add_players(player_aliases, host_name):
    global data
    
    for host in host_name:
        data.add("host_name[]", host)
    
    for player_id in player_aliases:
        data.add("player_name[]", player_id)
        data.add("player_alias[]", "")
