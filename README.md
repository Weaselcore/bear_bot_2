# bear_bot_2

This is a personal code for a private Discord bot. However, anyone is welcome to contribute to the codebase.

This bot is written in Python and utilises the discord.py library and SqlAlchemy library to create
a database agnostic backend. All the features of the bot are written and separated into cog files under the cog directory.

---

## *Lobby Cog*
Allows members on the server to create lobbies as channels to rally others for a gaming session.
  - There is an embed that becomes populated with a list of slots and members that have joined.
  - Uses Discord's views and buttons for a convenient GUI.
    - Join
    - Ready
    - Leave 
    - Lock
    - Change Leader
    - Edit Description
    - Disband
    - Promote

  - Each lobby channel comes with its own thread for lobby history and separate chat.
  - A queue for longer play sessions where members queue up to fill up slots when current members leave the lobby.

  ### Commands
  - Initialise lobby with:
    - ```/lobby create [game] [size] (description)```
  - The information used by the lobby command is validated using the game info added to the game table, games can be added by members using the command below.
    - ```/lobby gameadd [game_name] @[role] [max_size] (game_url)``` - Adds game info for the lobby
  - Game entries can be removed by:
    - ```/lobby gameremove [game]```
  - To list all games on the server:
    - ```/lobby listgames```

  - Comes with lobby owner commands:
    - ```/lobby userjoin @[member]``` - Adds member in the server to the lobby
    - ```/lobby userkick @[member]``` - Removes member from the lobby
    - ```/lobby userready @[member]``` - Toggles member ready state

    ---
    
- ## TODO:
  - An admin command that cleans up lobby by id
  - A scheduler that cleans up lobbies past a configured time
  - A feature to set a time for a lobby deadline before the owner leaves/plays
  - Utilise the lock function to work with deadlines/cleanup (anything to do with the scheduler)
  - A reminder to leave lobby when member leaves voice chat
  - Server set configurations saved in database, i.e. lobby limit, timeout, promotion cooldown

---

## *Soundboard Cog*
Allows members on the server to create soundbites which can be played in a voice channel.

### Commands
  - Comes with commands to add soundbites.
    - ```/soundboard upload [file]``` - Uploads a sound for the soundboard, limited by server upload limit.
    - ```/soundboard streamable [streamable_url]``` - Downloads a streamable video and strips the audio based on the timestamp given.

  - Command to delete soundbite.
    - ```/soundboard delete [name]``` - Delete soundbite based on autocompleted name.

  - Soundboard persists on bot restart but if something wrong occurs, it can be reinitialised using:
    - ```/soundboard createsoundboardchannel```

  - You can invoke audio player states with these commands:
    - ```/soundboard play [name]```
    and
    - ```/soundboard stop```

    ---

- ## TODO:
  - Use a database to store soundbite information/integration
  - Stats on soundbite usage
  - Better organisation of soundbites
  - Have most used/recent soundbites on top
  - A builtin soundbite editor

---

# Installation for Development

1. Clone from this repository
2. Set up venv: ```python -m venv .```
3. Install pipenv as a global library: ```pip install pipenv```
4. ```pipenv install```
5. Create .env in root:

- TOKEN=
- PG_USER=
- PG_PASSWORD=
- PG_HOST=
- PG_PORT=
- PG_DATABASE=

6. Run a Postgresql instance on your development machine.
7. Create database called whatever you added to **PG_DATABASE** in your .env, with psql tool or a db editor tool.
8. Run using:
```python bot.py```
