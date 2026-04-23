# random-message-picker
Creation of a bot picking random messages for Discord 🕹️

# Requirements
discord.py>=2.3.0

# 🎮 Commandes disponibles
Commande         Description
!startgame       Lance une partie
!classement      Top 10 du serveur
!stopsame(Admin) Stoppe la partie
!aide            Affiche l'aide

# Exclusions channels/catégories — p
Les noms dans les listes NOMS_CHANNELS_EXCLUS et NOMS_CATEGORIES_EXCLUSES. 
Si tu renommes un channel un jour, tu n'as qu'à mettre à jour ici.

# 🖼️ Filtre messages "purs texte" — la fonction _message_est_valide() bloque tout ça :

Pièces jointes (images, fichiers uploadés)
Embeds (aperçus de liens, YouTube, etc.)
Liens HTTP dans le texte
Emojis animés Discord (gifs)

# 👑 Filtre rôle minimum — 
_a_role_suffisant() vérifie la hiérarchie des rôles Discord. Donc si "Prokobz" est en position 3, tous les membres avec un rôle en position 3, 4, 5… sont éligibles. Tu changes juste ROLE_MINIMUM = "Prokobz" si le nom évolue.

⚠️ Une chose à vérifier : le bot doit avoir accès aux infos des membres pour lire leurs rôles. Dans le Developer Portal, active bien le Server Members Intent dans l'onglet Bot.