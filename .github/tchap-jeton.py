"""Obtenir le jeton du compte robot Tchap et le poser dans le dépôt.

    python3 .github/tchap-jeton.py

À lancer soi-même, dans un terminal, une fois (et à nouveau si la vigie ouvre
un ticket `panne-tchap` pour jeton invalide). Le mot de passe est saisi sans
écho, n'est envoyé qu'au serveur Tchap, et le jeton va directement dans le
secret GitHub `TCHAP_ACCESS_TOKEN` sans jamais s'afficher.

Pourquoi une connexion et pas le jeton affiché dans Tchap web : les serveurs
Tchap délèguent l'authentification à un service OIDC (MAS). Le jeton que
montre le client web y est de courte durée et se renouvelle en coulisse ; collé
dans un secret, il cesserait de fonctionner en quelques minutes. Une connexion
par mot de passe sans jeton de rafraîchissement ouvre une session dédiée dont
le jeton ne s'éteint pas de lui-même. Ne pas déconnecter la session
« supervision-bal-mss » depuis Tchap : le jeton serait révoqué.

Pose aussi la variable `TCHAP_HOMESERVER` : le serveur du robot dépend du
domaine de son adresse (`@sante.gouv.fr` → agent.social, …), pas du salon.

Requiert `gh` authentifié sur le dépôt.
"""

import getpass
import json
import os
import ssl
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

DEPOT = "chaibax/monitoring-publication-bal-mss"
ANNUAIRE = "https://matrix.agent.dinum.tchap.gouv.fr/_matrix/identity/api/v1/info"


def _contexte_tls():
    """Le Python de python.org sur macOS est livré sans magasin de certificats,
    et le fichier /etc/ssl/cert.pem de macOS est trop ancien pour connaître la
    racine HARICA des serveurs Tchap. Sur macOS, on charge donc les racines du
    trousseau système, celles qu'utilise le navigateur ; ailleurs, le magasin
    du système suffit."""
    contexte = ssl.create_default_context(cafile=os.environ.get("SSL_CERT_FILE"))
    if sys.platform == "darwin":
        racines = subprocess.run(
            ["security", "find-certificate", "-a", "-p",
             "/System/Library/Keychains/SystemRootCertificates.keychain"],
            capture_output=True, text=True, check=True,
        ).stdout
        contexte.load_verify_locations(cadata=racines)
    return contexte


def _json(url, corps=None):
    requete = urllib.request.Request(
        url, data=json.dumps(corps).encode() if corps else None,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(requete, timeout=30, context=_contexte_tls()) as reponse:
            return json.load(reponse)
    except urllib.error.HTTPError as erreur:
        sys.exit(f"Refus de Tchap ({erreur.code}) : {erreur.read().decode(errors='replace')[:300]}")
    except urllib.error.URLError as erreur:
        sys.exit(f"Tchap injoignable : {erreur.reason}")


def main():
    sys.stderr.write("Adresse e-mail du compte robot Tchap : ")
    sys.stderr.flush()
    adresse = sys.stdin.readline().strip()
    hs = _json(f"{ANNUAIRE}?{urllib.parse.urlencode({'medium': 'email', 'address': adresse})}").get("hs")
    if not hs:
        sys.exit(f"Aucun serveur Tchap pour {adresse}.")
    serveur = f"https://matrix.{hs}"
    print(f"Serveur du robot : {serveur}", file=sys.stderr)

    mot_de_passe = getpass.getpass("Mot de passe du compte robot : ")
    session = _json(f"{serveur}/_matrix/client/v3/login", {
        "type": "m.login.password",
        "identifier": {"type": "m.id.thirdparty", "medium": "email", "address": adresse},
        "password": mot_de_passe,
        "initial_device_display_name": "supervision-bal-mss (GitHub Actions)",
    })
    del mot_de_passe

    subprocess.run(["gh", "secret", "set", "TCHAP_ACCESS_TOKEN", "--repo", DEPOT],
                   input=session["access_token"].encode(), check=True)
    subprocess.run(["gh", "variable", "set", "TCHAP_HOMESERVER", "--repo", DEPOT,
                    "--body", serveur], check=True)
    print(f"Fait : {session['user_id']} connecté, secret et serveur posés dans {DEPOT}.",
          file=sys.stderr)


if __name__ == "__main__":
    main()
