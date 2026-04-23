import discord
from discord import app_commands
from discord.ext import commands
import sqlite3
import random
import asyncio
import re
import os
from dotenv import load_dotenv

# Charger les variables d'environnement depuis .env
load_dotenv()

# ─────────────────────────────────────────
#  CONFIG  →  modifie ces valeurs
# ─────────────────────────────────────────
TOKEN = os.getenv('TOKEN')
TIMER_SECONDES = 60

MIN_CHARS = 20
MAX_CHARS = 300
POINTS_VICTOIRE = 1

# Noms exacts des channels à exclure (insensible à la casse)
NOMS_CHANNELS_EXCLUS = [
    "lp-tracker",
    "☎️-gartic-phone",
    "🎥stream",
    "🎵dj-fred",
    "🏠images-minecraft",
]

# Noms exacts des catégories à exclure (insensible à la casse)
NOMS_CATEGORIES_EXCLUSES = [
    "📈Mudae",
]

# Rôle minimum requis pour que les messages soient sélectionnés
# Le bot sélectionne les membres ayant CE rôle OU un rôle "supérieur" dans la hiérarchie
ROLE_MINIMUM = "Prokobz"
# ─────────────────────────────────────────

# Regex pour détecter les liens, mentions, commandes
RE_LIEN = re.compile(r"https?://\S+|discord\.gg/\S+", re.IGNORECASE)
RE_TENOR_GIPHY = re.compile(r"tenor\.com|giphy\.com", re.IGNORECASE)

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

class Bot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # Synchronise les slash commands avec Discord au démarrage
        await self.tree.sync()
        print("✅ Slash commands synchronisées !")

bot = Bot()

# ── Base de données ───────────────────────
def init_db():
    con = sqlite3.connect("classement.db")
    cur = con.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS scores (
            guild_id    INTEGER,
            user_id     INTEGER,
            username    TEXT,
            points      INTEGER DEFAULT 0,
            victoires   INTEGER DEFAULT 0,
            PRIMARY KEY (guild_id, user_id)
        )
    """)
    con.commit()
    con.close()

def ajouter_point(guild_id, user_id, username):
    con = sqlite3.connect("classement.db")
    cur = con.cursor()
    cur.execute("""
        INSERT INTO scores (guild_id, user_id, username, points, victoires)
        VALUES (?, ?, ?, 1, 1)
        ON CONFLICT(guild_id, user_id) DO UPDATE SET
            points    = points + 1,
            victoires = victoires + 1,
            username  = excluded.username
    """, (guild_id, user_id, username))
    con.commit()
    con.close()

def get_classement(guild_id, limit=10):
    con = sqlite3.connect("classement.db")
    cur = con.cursor()
    cur.execute("""
        SELECT username, points, victoires
        FROM scores
        WHERE guild_id = ?
        ORDER BY points DESC
        LIMIT ?
    """, (guild_id, limit))
    rows = cur.fetchall()
    con.close()
    return rows

# ── État des parties en cours ─────────────
parties_en_cours = {}  # guild_id → dict

# ── Événements ───────────────────────────
@bot.event
async def on_ready():
    init_db()
    print(f"✅ Bot connecté en tant que {bot.user} !")
    await bot.change_presence(activity=discord.Game("/startgame pour jouer 🎮"))

# ── Slash Commands ────────────────────────

@bot.tree.command(name="startgame", description="Lance une partie — devine qui a écrit le message mystère !")
async def startgame(interaction: discord.Interaction):
    guild_id = interaction.guild_id

    if guild_id in parties_en_cours:
        await interaction.response.send_message(
            "⚠️ Hé oh !Une partie est déjà en cours ! Attendez qu'elle se termine.", ephemeral=True
        )
        return

    await interaction.response.send_message("🕵️‍♀️ Je cherche un message mystère...")

    message_cible = await _piocher_message(interaction)
    if not message_cible:
        await interaction.edit_original_response(content="❌ Impossible de trouver un message valide !")
        return

    auteur  = message_cible.author
    contenu = message_cible.content

    parties_en_cours[guild_id] = {
        "auteur_id":  auteur.id,
        "auteur_nom": auteur.display_name,
        "message_id": message_cible.id,
        "channel_id": interaction.channel_id,
        "task":       None,
        "reponses":   {},  # user_id → nombre de réponses
    }

    embed = discord.Embed(
        title="🥸 Qui a écrit ce message ?",
        description=f"```{contenu}```",
        color=discord.Color.blurple()
    )
    embed.set_footer(text=f"⏳ Vous avez {TIMER_SECONDES} secondes — écrivez le pseudo dans le chat !")
    await interaction.edit_original_response(content=None, embed=embed)

    task = asyncio.create_task(_timer_fin(interaction.channel_id, guild_id))
    parties_en_cours[guild_id]["task"] = task


@bot.tree.command(name="classement", description="Affiche le top 10 des joueurs du serveur")
async def classement(interaction: discord.Interaction):
    rows = get_classement(interaction.guild_id)
    if not rows:
        await interaction.response.send_message(
            "📊 Aucun score pour le moment. Lance une partie avec `/startgame` !", ephemeral=True
        )
        return

    medailles = ["🥇", "🥈", "🥉"]
    lignes = []
    for i, (username, points, victoires) in enumerate(rows):
        medaille = medailles[i] if i < 3 else f"`{i+1}.`"
        lignes.append(
            f"{medaille} **{username}** — {points} pt{'s' if points > 1 else ''}  "
            f"*(x{victoires} victoire{'s' if victoires > 1 else ''})*"
        )

    embed = discord.Embed(
        title="🏆  Classement général",
        description="\n".join(lignes),
        color=discord.Color.gold()
    )
    embed.set_footer(text=f"Serveur : {interaction.guild.name}")
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="monstats", description="Affiche tes propres statistiques")
async def monstats(interaction: discord.Interaction):
    con = sqlite3.connect("classement.db")
    row = con.execute(
        "SELECT username, points, victoires FROM scores WHERE guild_id=? AND user_id=?",
        (interaction.guild_id, interaction.user.id)
    ).fetchone()
    rang = None
    if row:
        rang_row = con.execute("""
            SELECT COUNT(*) + 1 FROM scores
            WHERE guild_id = ? AND points > ?
        """, (interaction.guild_id, row[1])).fetchone()
        rang = rang_row[0] if rang_row else "?"
    con.close()

    if not row:
        await interaction.response.send_message(
            "📊 Tu n'as pas encore de score ! Lance une partie avec `/startgame`.", ephemeral=True
        )
        return

    username, points, victoires = row
    embed = discord.Embed(
        title=f"📊  Stats de {interaction.user.display_name}",
        color=discord.Color.blurple()
    )
    embed.add_field(name="🏅 Points",     value=str(points),    inline=True)
    embed.add_field(name="🎯 Victoires",  value=str(victoires), inline=True)
    embed.add_field(name="🏆 Classement", value=f"#{rang}",     inline=True)
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="stopgame", description="Arrête la partie en cours et révèle la réponse")
async def stopgame(interaction: discord.Interaction):
    guild_id = interaction.guild_id
    if guild_id not in parties_en_cours:
        await interaction.response.send_message("🤔 Aucune partie n'est en cours.", ephemeral=True)
        return
    await interaction.response.send_message("🛑 Partie arrêtée par un admin.", ephemeral=True)
    channel = bot.get_channel(parties_en_cours[guild_id]["channel_id"])
    if channel is None:
        channel = await bot.fetch_channel(parties_en_cours[guild_id]["channel_id"])
    await _terminer_partie(channel, guild_id, reveler=True, force_stop=True)


@bot.tree.command(name="aide", description="Affiche toutes les commandes disponibles")
async def aide(interaction: discord.Interaction):
    embed = discord.Embed(title="📖  Aide — Qui a dit ça ?", color=discord.Color.green())
    embed.add_field(name="/startgame",  value="Lance une nouvelle partie",           inline=False)
    embed.add_field(name="/classement", value="Affiche le top 10 du serveur",        inline=False)
    embed.add_field(name="/monstats",   value="Tes points, victoires et classement", inline=False)
    embed.add_field(name="/stopgame",   value="(Admin) Arrête la partie en cours",   inline=False)
    embed.set_footer(text=f"Timer : {TIMER_SECONDES}s  •  Rôle minimum : {ROLE_MINIMUM}")
    await interaction.response.send_message(embed=embed, ephemeral=True)


# ── Détection des réponses dans le chat ───
@bot.event
async def on_message(message):
    if message.author.bot or not message.guild:
        await bot.process_commands(message)
        return

    guild_id = message.guild.id
    if guild_id not in parties_en_cours:
        await bot.process_commands(message)
        return

    partie = parties_en_cours[guild_id]

    if message.channel.id != partie["channel_id"]:
        await bot.process_commands(message)
        return

    # Vérifier si l'utilisateur a déjà répondu 2 fois
    user_id = message.author.id
    if partie["reponses"].get(user_id, 0) >= 2:
        await message.channel.send(f"🙈 {message.author.mention} a dépassé son quota de réponses (2) pour cette manche ! 👮‍♀️🫵")
        await bot.process_commands(message)
        return

    nom_auteur = partie["auteur_nom"].lower().strip()
    reponse    = message.content.lower().strip()

    if reponse == nom_auteur or reponse in nom_auteur or nom_auteur in reponse:
        if partie["task"]:
            partie["task"].cancel()

        ajouter_point(guild_id, message.author.id, message.author.display_name)

        embed = discord.Embed(
            title="💃 Bonne réponse !",
            description=(
                f"🎉 **{message.author.display_name}** a trouvé.e !\n"
                f"Le message avait été écrit par **{partie['auteur_nom']}**.\n"
                f"+{POINTS_VICTOIRE} point{'s' if POINTS_VICTOIRE > 1 else ''} au classement ! 😎"
            ),
            color=discord.Color.green()
        )
        await message.channel.send(embed=embed)
        del parties_en_cours[guild_id]

    else:
        # Incrémenter le compteur de réponses pour cet utilisateur
        partie["reponses"][user_id] = partie["reponses"].get(user_id, 0) + 1

    await bot.process_commands(message)


# ── Helpers internes ───────────────────────
def _a_role_suffisant(member: discord.Member, guild: discord.Guild) -> bool:
    role_min = discord.utils.get(guild.roles, name=ROLE_MINIMUM)
    if role_min is None:
        return False
    return any(r.position >= role_min.position for r in member.roles)

def _message_est_valide(msg: discord.Message) -> bool:
    if msg.attachments:
        return False
    if msg.embeds:
        return False
    if RE_LIEN.search(msg.content):
        return False
    if re.search(r"<a?:\w+:\d+>", msg.content):
        return False
    return True

async def _piocher_message(interaction: discord.Interaction):
    candidats = []
    noms_channels_exclus   = {n.lower() for n in NOMS_CHANNELS_EXCLUS}
    noms_categories_exclus = {n.lower() for n in NOMS_CATEGORIES_EXCLUSES}

    for channel in interaction.guild.text_channels:
        if channel.name.lower() in noms_channels_exclus:
            continue
        if channel.category and channel.category.name.lower() in noms_categories_exclus:
            continue
        perms = channel.permissions_for(interaction.guild.me)
        if not perms.read_message_history:
            continue
        try:
            async for msg in channel.history(limit=200):
                if (
                    not msg.author.bot
                    and MIN_CHARS <= len(msg.content) <= MAX_CHARS
                    and _message_est_valide(msg)
                    and _a_role_suffisant(msg.author, interaction.guild)
                ):
                    candidats.append(msg)
        except (discord.Forbidden, discord.HTTPException):
            continue

    if not candidats:
        return None
    return random.choice(candidats)

async def _timer_fin(channel_id, guild_id):
    await asyncio.sleep(TIMER_SECONDES)
    if guild_id in parties_en_cours:
        channel = bot.get_channel(channel_id)
        if channel is None:
            try:
                channel = await bot.fetch_channel(channel_id)
            except Exception:
                del parties_en_cours[guild_id]
                return
        await _terminer_partie(channel, guild_id, reveler=True)

async def _terminer_partie(channel, guild_id, reveler=False, force_stop=False):
    if guild_id not in parties_en_cours:
        return
    partie = parties_en_cours[guild_id]

    if reveler:
        if force_stop:
            desc  = f"🛑 Partie arrêtée.\nL'auteur était **{partie['auteur_nom']}** ! ☝️🤓"
            color = discord.Color.orange()
        else:
            desc  = f"⏰ Temps écoulé ! Personne n'a trouvé...\n Actually l'auteur était **{partie['auteur_nom']}** ! ☝️🤓"
            color = discord.Color.red()

        embed = discord.Embed(title="❌ Personne n'a deviné, bande de nullos. 🤢", description=desc, color=color)
        await channel.send(embed=embed)

    del parties_en_cours[guild_id]

# ── Lancement ─────────────────────────────
bot.run(TOKEN)