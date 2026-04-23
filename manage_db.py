#!/usr/bin/env python3
"""
Script pour gérer la base de données classement.db
Permet de voir, modifier, supprimer les données sans logiciel tiers
"""

import sqlite3
import sys

DB_FILE = "classement.db"

def get_guildes_disponibles():
    """Retourne la liste des Guild IDs disponibles"""
    con = sqlite3.connect(DB_FILE)
    cur = con.cursor()
    cur.execute("SELECT DISTINCT guild_id FROM scores")
    guildes = [row[0] for row in cur.fetchall()]
    con.close()
    return guildes

def chercher_utilisateur_par_nom(guild_id, username):
    """Cherche un utilisateur par son nom dans une guilde et retourne son user_id"""
    con = sqlite3.connect(DB_FILE)
    cur = con.cursor()
    cur.execute("SELECT user_id, username, points, victoires FROM scores WHERE guild_id = ? AND LOWER(username) = LOWER(?)", 
                (guild_id, username))
    resultat = cur.fetchone()
    con.close()
    return resultat

def afficher_utilisateurs_guilde(guild_id):
    """Affiche les utilisateurs d'une guilde spécifique"""
    con = sqlite3.connect(DB_FILE)
    cur = con.cursor()
    cur.execute("SELECT user_id, username, points, victoires FROM scores WHERE guild_id = ? ORDER BY points DESC", (guild_id,))
    resultats = cur.fetchall()
    con.close()
    return resultats

def afficher_donnees(guild_id=None):
    """Affiche tous les scores ou ceux d'une guilde spécifique"""
    con = sqlite3.connect(DB_FILE)
    cur = con.cursor()
    
    if guild_id:
        cur.execute("SELECT user_id, username, points, victoires FROM scores WHERE guild_id = ? ORDER BY points DESC", (guild_id,))
        headers = ["User ID", "Username", "Points", "Victoires"]
    else:
        cur.execute("SELECT guild_id, user_id, username, points, victoires FROM scores ORDER BY guild_id, points DESC")
        headers = ["Guild ID", "User ID", "Username", "Points", "Victoires"]
    
    resultats = cur.fetchall()
    con.close()
    
    if not resultats:
        print("❌ Aucune donnée trouvée")
        return
    
    # Affichage manuel sans dépendance
    print("\n" + "─" * 100)
    print(" | ".join(f"{h:<20}" for h in headers))
    print("─" * 100)
    for row in resultats:
        print(" | ".join(f"{str(val):<20}" for val in row))
    print("─" * 100 + "\n")

def modifier_points(guild_id, user_id, nouveaux_points):
    """Modifie le nombre de points d'un utilisateur"""
    con = sqlite3.connect(DB_FILE)
    cur = con.cursor()
    
    cur.execute("UPDATE scores SET points = ? WHERE guild_id = ? AND user_id = ?", 
                (nouveaux_points, guild_id, user_id))
    
    if cur.rowcount == 0:
        print(f"❌ Utilisateur {user_id} non trouvé dans la guilde {guild_id}")
    else:
        print(f"✅ Points mis à jour : {user_id} → {nouveaux_points} points")
    
    con.commit()
    con.close()

def modifier_victoires(guild_id, user_id, nouvelles_victoires):
    """Modifie le nombre de victoires d'un utilisateur"""
    con = sqlite3.connect(DB_FILE)
    cur = con.cursor()
    
    cur.execute("UPDATE scores SET victoires = ? WHERE guild_id = ? AND user_id = ?", 
                (nouvelles_victoires, guild_id, user_id))
    
    if cur.rowcount == 0:
        print(f"❌ Utilisateur {user_id} non trouvé dans la guilde {guild_id}")
    else:
        print(f"✅ Victoires mises à jour : {user_id} → {nouvelles_victoires} victoires")
    
    con.commit()
    con.close()

def supprimer_utilisateur(guild_id, user_id, username=None):
    """Supprime un utilisateur de la BDD"""
    con = sqlite3.connect(DB_FILE)
    cur = con.cursor()
    
    # Si username n'est pas fourni, le récupérer
    if not username:
        cur.execute("SELECT username FROM scores WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))
        resultat = cur.fetchone()
        if not resultat:
            print(f"❌ Utilisateur {user_id} non trouvé")
            con.close()
            return
        username = resultat[0]
    
    confirmation = input(f"Êtes-vous sûr de vouloir supprimer '{username}' (user_id: {user_id}) ? (oui/non) : ").lower()
    
    if confirmation == "oui":
        cur.execute("DELETE FROM scores WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))
        con.commit()
        print(f"✅ '{username}' a été supprimé")
    else:
        print("❌ Suppression annulée")
    
    con.close()

def reinitialiser_bdd():
    """Réinitialise complètement la BDD"""
    confirmation = input("⚠️  Êtes-vous VRAIMENT sûr de vouloir tout supprimer ? (oui/non) : ").lower()
    
    if confirmation == "oui":
        confirmation2 = input("C'est la dernière chance ! Confirmer ? (oui/non) : ").lower()
        
        if confirmation2 == "oui":
            con = sqlite3.connect(DB_FILE)
            cur = con.cursor()
            cur.execute("DELETE FROM scores")
            con.commit()
            con.close()
            print("✅ Base de données réinitialisée (vide)")
        else:
            print("❌ Opération annulée")
    else:
        print("❌ Opération annulée")

def menu():
    """Affiche le menu interactif"""
    while True:
        print("\n" + "="*50)
        print("📊 GESTIONNAIRE DE BASE DE DONNÉES")
        print("="*50)
        print("1️⃣  Voir tous les scores")
        print("2️⃣  Voir les scores d'une guilde")
        print("3️⃣  Modifier les points d'un utilisateur")
        print("4️⃣  Modifier les victoires d'un utilisateur")
        print("5️⃣  Supprimer un utilisateur")
        print("6️⃣  Réinitialiser la BDD")
        print("7️⃣  Quitter")
        print("="*50)
        
        choix = input("Choisir une option (1-7) : ").strip()
        
        if choix == "1":
            afficher_donnees()
        
        elif choix == "2":
            guildes = get_guildes_disponibles()
            if not guildes:
                print("❌ Aucune guilde trouvée dans la BDD")
                continue
            print("\n📌 Guildes disponibles :")
            for i, g in enumerate(guildes, 1):
                print(f"  {i}. {g}")
            try:
                entree_guilde = input("\nChoisir une guilde (numéro ou ID) : ").strip()
                
                # Essayer d'interprétter comme numéro d'abord
                try:
                    choix_guilde = int(entree_guilde) - 1
                    if 0 <= choix_guilde < len(guildes):
                        guild_id = guildes[choix_guilde]
                    else:
                        print("❌ Numéro invalide")
                        continue
                except ValueError:
                    # Sinon, chercher par ID
                    if int(entree_guilde) in guildes:
                        guild_id = int(entree_guilde)
                    else:
                        print("❌ Guild ID non trouvé")
                        continue
                
                utilisateurs = afficher_utilisateurs_guilde(guild_id)
                if utilisateurs:
                    print(f"\n📊 Scores de la guilde {guild_id}:")
                    print("─" * 70)
                    print(f"{'User ID':<20} | {'Username':<20} | {'Points':<10} | {'Victoires':<10}")
                    print("─" * 70)
                    for uid, uname, pts, vic in utilisateurs:
                        print(f"{str(uid):<20} | {uname:<20} | {str(pts):<10} | {str(vic):<10}")
                    print("─" * 70)
            except ValueError:
                print("❌ Entrée invalide")
        
        elif choix == "3":
            guildes = get_guildes_disponibles()
            if not guildes:
                print("❌ Aucune guilde trouvée")
                continue
            print("\n📌 Guildes disponibles :")
            for i, g in enumerate(guildes, 1):
                print(f"  {i}. {g}")
            try:
                entree_guilde = input("Choisir une guilde (numéro ou ID) : ").strip()
                
                # Essayer d'interprétter comme numéro d'abord
                try:
                    choix_guilde = int(entree_guilde) - 1
                    if 0 <= choix_guilde < len(guildes):
                        guild_id = guildes[choix_guilde]
                    else:
                        print("❌ Numéro invalide")
                        continue
                except ValueError:
                    # Sinon, chercher par ID
                    if int(entree_guilde) in guildes:
                        guild_id = int(entree_guilde)
                    else:
                        print("❌ Guild ID non trouvé")
                        continue
                
                username = input("Nom d'utilisateur : ").strip()
                resultat = chercher_utilisateur_par_nom(guild_id, username)
                if resultat:
                    user_id, uname, pts_actuels, _ = resultat
                    print(f"✅ Utilisateur trouvé : {uname} (ID: {user_id})")
                    print(f"   Points actuels : {pts_actuels}")
                    try:
                        nouveaux_points = int(input("Nouveaux points : "))
                        modifier_points(guild_id, user_id, nouveaux_points)
                    except ValueError:
                        print("❌ Points invalides")
                else:
                    print(f"❌ Utilisateur '{username}' non trouvé dans cette guilde")
            except ValueError:
                print("❌ Entrée invalide")
        
        elif choix == "4":
            guildes = get_guildes_disponibles()
            if not guildes:
                print("❌ Aucune guilde trouvée")
                continue
            print("\n📌 Guildes disponibles :")
            for i, g in enumerate(guildes, 1):
                print(f"  {i}. {g}")
            try:
                entree_guilde = input("Choisir une guilde (numéro ou ID) : ").strip()
                
                # Essayer d'interprétter comme numéro d'abord
                try:
                    choix_guilde = int(entree_guilde) - 1
                    if 0 <= choix_guilde < len(guildes):
                        guild_id = guildes[choix_guilde]
                    else:
                        print("❌ Numéro invalide")
                        continue
                except ValueError:
                    # Sinon, chercher par ID
                    if int(entree_guilde) in guildes:
                        guild_id = int(entree_guilde)
                    else:
                        print("❌ Guild ID non trouvé")
                        continue
                
                username = input("Nom d'utilisateur : ").strip()
                resultat = chercher_utilisateur_par_nom(guild_id, username)
                if resultat:
                    user_id, uname, _, vic_actuelles = resultat
                    print(f"✅ Utilisateur trouvé : {uname} (ID: {user_id})")
                    print(f"   Victoires actuelles : {vic_actuelles}")
                    try:
                        nouvelles_victoires = int(input("Nouvelles victoires : "))
                        modifier_victoires(guild_id, user_id, nouvelles_victoires)
                    except ValueError:
                        print("❌ Victoires invalides")
                else:
                    print(f"❌ Utilisateur '{username}' non trouvé dans cette guilde")
            except ValueError:
                print("❌ Entrée invalide")
        
        elif choix == "5":
            guildes = get_guildes_disponibles()
            if not guildes:
                print("❌ Aucune guilde trouvée")
                continue
            print("\n📌 Guildes disponibles :")
            for i, g in enumerate(guildes, 1):
                print(f"  {i}. {g}")
            try:
                entree_guilde = input("Choisir une guilde (numéro ou ID) : ").strip()
                
                # Essayer d'interprétter comme numéro d'abord
                try:
                    choix_guilde = int(entree_guilde) - 1
                    if 0 <= choix_guilde < len(guildes):
                        guild_id = guildes[choix_guilde]
                    else:
                        print("❌ Numéro invalide")
                        continue
                except ValueError:
                    # Sinon, chercher par ID
                    if int(entree_guilde) in guildes:
                        guild_id = int(entree_guilde)
                    else:
                        print("❌ Guild ID non trouvé")
                        continue
                
                username = input("Nom d'utilisateur : ").strip()
                resultat = chercher_utilisateur_par_nom(guild_id, username)
                if resultat:
                    user_id, uname, _, _ = resultat
                    supprimer_utilisateur(guild_id, user_id, uname)
                else:
                    print(f"❌ Utilisateur '{username}' non trouvé")
            except ValueError:
                print("❌ Entrée invalide")
        
        elif choix == "6":
            reinitialiser_bdd()
        
        elif choix == "7":
            print("👋 Au revoir !")
            break
        
        else:
            print("❌ Option invalide")

if __name__ == "__main__":
    menu()
