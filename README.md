# random-message-picker
Creation of a bot picking random messages for Discord 🕹️

# Requirements
discord.py>=2.3.0
python-dotenv

# 🎮 Availables commandes

| Commande | Description |
|----------|-------------|
| `!startgame` | Start a gaming session |
| `!classement` | Standings for the current session |
| `!classement-global` | Standings all-time |
| `!messtats` | Personal points all-time |
| `!stopgame` | End the session |
| `!aide` | Displays the available commands |

# ⚙️ .env file
The bot need an .env file to work properly. So an example is available as `.env-example` among the files.

⚠️ Reminder : if you ever fork this project, never push your `.env` !

## Configuration of the .env file
### Token
You need to generate a token from Discord Developer Portal to link the bot to your server.

### Exclusions of channels/category
If you ever rename an exclude channel or a category in your Discord's server, simply update it in your `.env` under NOMS_CHANNELS_EXCLUS or NOMS_CATEGORIES_EXCLUSES. Depends of what you renamed.

Same for role and ROLE_MINIMUM present in the `.env`.

# 🧩 Other specifications
## 🖼️ Filter ‘plain text’ messages
The `_message_est_valide()` function blocks all of that:
- Attachments (images, uploaded files)
- Embeds (link previews, YouTube, etc.)
- HTTP links in the text
- Discord animated emojis (GIFs)

## 👑 Minimum role filter
The `_a_role_suffisant()` function checks the Discord role hierarchy. So if ‘minimum_role’ is in position 3, all members with a role in positions 3, 4, 5… are eligible.

As writed before, you just have to change the value of ROLE_MINIMUM in your `.env` if the name changes.


# ⚠️ One last thing to check
The bot must have access to member information in order to read their roles. In the Developer Portal, make sure you enable the Server Members Intent in the Bot tab.