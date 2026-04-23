import discord
from discord.ext import commands
import sqlite3
import random
import asyncio
import re
from datetime import datetime
import os
from dotenv import load_dotenv

# Charger les variables d'environnement depuis .env
load_dotenv()

# ─────────────────────────────────────────
#  CONFIG  →  modifie ces valeurs
# ─────────────────────────────────────────
TOKEN = os.getenv('TOKEN')
PREFIX = "!"
TIMER_SECONDES = 60          # temps pour deviner
MIN_CHARS = 20               # longueur minimale d'un message pioché
MAX_CHARS = 300              # longueur maximale
POINTS_VICTOIRE = 1          # points gagnés si bonne réponse

# Noms exacts des channels à exclure (insensible à la casse)
NOMS_CHANNELS_EXCLUS = [
    "lp-tracker",
    "☎️-gartic-phone",
    "🎥stream",
    "🏠images-minecraft",
]

# Noms exacts des catégories à exclure (insensible à la casse)
NOMS_CATEGORIES_EXCLUSES = [
    "Mudae",
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

bot = commands.Bot(command_prefix=PREFIX, intents=intents)

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
parties_en_cours = {}   # guild_id → { auteur, message_id, task }

# ── Événements ───────────────────────────
@bot.event
async def on_ready():
    init_db()
    print(f"✅ Bot connecté en tant que {bot.user} !")
    await bot.change_presence(activity=discord.Game("!startgame pour jouer 🎮"))

# ── Commandes ────────────────────────────

@bot.command(name="startgame", aliases=["sg", "start"])
async def startgame(ctx):
    """Lance une partie : pioche un message aléatoire à deviner."""
    guild_id = ctx.guild.id

    if guild_id in parties_en_cours:
        await ctx.send("⚠️ Une partie est déjà en cours ! Attendez qu'elle se termine.")
        return

    await ctx.send("🔍 Je cherche un message mystère...")

    # Récupère un message aléatoire valide
    message_cible = await _piocher_message(ctx)
    if not message_cible:
        await ctx.send("❌ Impossible de trouver un message valide. Essaie dans un autre channel !")
        return

    auteur = message_cible.author
    contenu = message_cible.content

    # Démarre la partie
    parties_en_cours[guild_id] = {
        "auteur_id":   auteur.id,
        "auteur_nom":  auteur.display_name,
        "message_id":  message_cible.id,
        "channel_id":  ctx.channel.id,
        "task":        None,
    }

    embed = discord.Embed(
        title="🎭  Qui a écrit ce message ?",
        description=f"```{contenu}```",
        color=discord.Color.blurple()
    )
    embed.set_footer(text=f"⏳ Vous avez {TIMER_SECONDES} secondes — écrivez le pseudo dans le chat !")
    await ctx.send(embed=embed)

    # Lance le timer
    task = asyncio.create_task(_timer_fin(ctx, guild_id))
    parties_en_cours[guild_id]["task"] = task


@bot.command(name="classement", aliases=["top", "scores", "leaderboard"])
async def classement(ctx):
    """Affiche le classement du serveur."""
    rows = get_classement(ctx.guild.id)
    if not rows:
        await ctx.send("📊 Aucun score pour le moment. Lance une partie avec `!startgame` !")
        return

    medailles = ["🥇", "🥈", "🥉"]
    lignes = []
    for i, (username, points, victoires) in enumerate(rows):
        medaille = medailles[i] if i < 3 else f"`{i+1}.`"
        lignes.append(f"{medaille} **{username}** — {points} pt{'s' if points > 1 else ''}  *(x{victoires} victoire{'s' if victoires > 1 else ''})*")

    embed = discord.Embed(
        title="🏆  Classement général",
        description="\n".join(lignes),
        color=discord.Color.gold()
    )
    embed.set_footer(text=f"Serveur : {ctx.guild.name}")
    await ctx.send(embed=embed)


@bot.command(name="stopsame", aliases=["stop"])
@commands.has_permissions(manage_messages=True)
async def stopgame(ctx):
    """(Admin) Arrête la partie en cours."""
    guild_id = ctx.guild.id
    if guild_id not in parties_en_cours:
        await ctx.send("Aucune partie en cours.")
        return
    await _terminer_partie(ctx.channel, guild_id, reveler=True, force_stop=True)


@bot.command(name="aide", aliases=["help_jeu"])
async def aide(ctx):
    """Affiche l'aide du bot."""
    embed = discord.Embed(title="📖  Aide — Qui a dit ça ?", color=discord.Color.green())
    embed.add_field(name="`!startgame`",  value="Lance une nouvelle partie",       inline=False)
    embed.add_field(name="`!classement`", value="Affiche le top 10 du serveur",    inline=False)
    embed.add_field(name="`!stopsame`",   value="(Admin) Arrête la partie en cours", inline=False)
    embed.set_footer(text=f"Préfixe : {PREFIX}  •  Timer : {TIMER_SECONDES}s")
    await ctx.send(embed=embed)


# ── Détection des réponses ─────────────────
@bot.event
async def on_message(message):
    if message.author.bot:
        await bot.process_commands(message)
        return

    guild_id = message.guild.id if message.guild else None
    if guild_id and guild_id in parties_en_cours:
        partie = parties_en_cours[guild_id]

        # Vérifie que le message est dans le bon channel
        if message.channel.id != partie["channel_id"]:
            await bot.process_commands(message)
            return

        # Ignore les commandes
        if message.content.startswith(PREFIX):
            await bot.process_commands(message)
            return

        # Compare la réponse (insensible à la casse)
        nom_auteur = partie["auteur_nom"].lower().strip()
        reponse    = message.content.lower().strip()

        if reponse == nom_auteur or reponse in nom_auteur or nom_auteur in reponse:
            # Bonne réponse !
            if partie["task"]:
                partie["task"].cancel()

            ajouter_point(guild_id, message.author.id, message.author.display_name)

            embed = discord.Embed(
                title="✅  Bonne réponse !",
                description=(
                    f"🎉 **{message.author.display_name}** a trouvé !\n"
                    f"Le message avait été écrit par **{partie['auteur_nom']}**.\n"
                    f"+{POINTS_VICTOIRE} point{'s' if POINTS_VICTOIRE > 1 else ''} au classement !"
                ),
                color=discord.Color.green()
            )
            await message.channel.send(embed=embed)
            del parties_en_cours[guild_id]

    await bot.process_commands(message)


# ── Helpers internes ───────────────────────
def _a_role_suffisant(member: discord.Member, guild: discord.Guild) -> bool:
    """Retourne True si le membre possède le rôle minimum requis ou un rôle de position supérieure."""
    role_min = discord.utils.get(guild.roles, name=ROLE_MINIMUM)
    if role_min is None:
        return False  # rôle introuvable → on refuse plutôt que d'accepter tout le monde
    # On accepte le rôle exact ET tout rôle avec une position hiérarchique >= au rôle minimum
    return any(r.position >= role_min.position for r in member.roles)

def _message_est_valide(msg: discord.Message) -> bool:
    """Vérifie qu'un message ne contient que du texte brut (pas de lien, gif, image, embed)."""
    # Pièces jointes (images, fichiers, gifs uploadés)
    if msg.attachments:
        return False
    # Embeds (liens riches, aperçus YouTube, Tenor/Giphy, etc.)
    if msg.embeds:
        return False
    # Liens dans le texte
    if RE_LIEN.search(msg.content):
        return False
    # Emojis personnalisés Discord (<:nom:id> ou <a:nom:id> pour les animés/gifs)
    if re.search(r"<a?:\w+:\d+>", msg.content):
        return False
    return True

async def _piocher_message(ctx):
    """Parcourt les channels du serveur et retourne un message aléatoire valide."""
    candidats = []

    noms_channels_exclus  = {n.lower() for n in NOMS_CHANNELS_EXCLUS}
    noms_categories_exclus = {n.lower() for n in NOMS_CATEGORIES_EXCLUSES}

    for channel in ctx.guild.text_channels:
        # Exclure par nom de channel
        if channel.name.lower() in noms_channels_exclus:
            continue
        # Exclure par nom de catégorie
        if channel.category and channel.category.name.lower() in noms_categories_exclus:
            continue
        # Vérifie les permissions du bot
        perms = channel.permissions_for(ctx.guild.me)
        if not perms.read_message_history:
            continue
        try:
            async for msg in channel.history(limit=200):
                if (
                    not msg.author.bot
                    and MIN_CHARS <= len(msg.content) <= MAX_CHARS
                    and not msg.content.startswith(PREFIX)
                    and _message_est_valide(msg)
                    and _a_role_suffisant(msg.author, ctx.guild)
                ):
                    candidats.append(msg)
        except (discord.Forbidden, discord.HTTPException):
            continue

    if not candidats:
        return None
    return random.choice(candidats)


async def _timer_fin(ctx, guild_id):
    """Appelé quand le timer expire sans bonne réponse."""
    await asyncio.sleep(TIMER_SECONDES)
    if guild_id in parties_en_cours:
        channel = bot.get_channel(parties_en_cours[guild_id]["channel_id"])
        await _terminer_partie(channel, guild_id, reveler=True)


async def _terminer_partie(channel, guild_id, reveler=False, force_stop=False):
    """Termine la partie et révèle éventuellement l'auteur."""
    if guild_id not in parties_en_cours:
        return
    partie = parties_en_cours[guild_id]

    if reveler:
        if force_stop:
            desc = f"🛑 Partie arrêtée par un admin.\nC'était **{partie['auteur_nom']}** !"
            color = discord.Color.orange()
        else:
            desc = f"⏰ Temps écoulé ! Personne n'a trouvé...\nC'était **{partie['auteur_nom']}** !"
            color = discord.Color.red()

        embed = discord.Embed(title="❌  Personne n'a deviné", description=desc, color=color)
        await channel.send(embed=embed)

    del parties_en_cours[guild_id]


# ── Lancement ─────────────────────────────
bot.run(TOKEN)