"""Canal Tchap de la remontée d'alerte.

    python .github/tchap.py envoyer "<texte>"
    python .github/tchap.py verifier

Tchap n'offre pas de webhook entrant : la voie documentée par l'équipe Tchap
est un compte utilisateur dédié au robot (adresse « bot-… » autorisée), qui
poste par l'API client de Matrix avec un jeton d'accès réutilisé — jamais une
connexion à chaque appel, qui multiplierait les sessions.
https://aide.tchap.beta.gouv.fr/fr/article/documentation-technique-bot-et-integrations-tchap-1z3dfx/

Configuration, toutes trois requises, sinon le canal est simplement ignoré :

- TCHAP_HOMESERVER (variable)   ex. https://matrix.agent.social.tchap.gouv.fr
- TCHAP_ROOM_ID    (variable)   ex. !abcdef:agent.social.tchap.gouv.fr
- TCHAP_ACCESS_TOKEN (secret)   jeton du compte robot

Le message part en clair. Le robot ne détient pas les clés de chiffrement du
salon ; le contenu, une panne d'un outil dont le dépôt est public, n'a rien
de confidentiel.

`verifier` ne poste rien : il contrôle que le jeton est encore valide et que
le robot est bien membre du salon. Un compte Tchap expire faute de
renouvellement périodique par courriel ; sans ce contrôle quotidien, le canal
tomberait en silence et on ne le découvrirait qu'à la panne suivante.
"""

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

DELAI = 30


def _configuration():
    serveur = os.environ.get("TCHAP_HOMESERVER", "").rstrip("/")
    salon = os.environ.get("TCHAP_ROOM_ID", "")
    jeton = os.environ.get("TCHAP_ACCESS_TOKEN", "")
    if not (serveur and salon and jeton):
        return None
    return serveur, salon, jeton


def _appel(methode, url, jeton, corps=None):
    donnees = json.dumps(corps).encode() if corps is not None else None
    requete = urllib.request.Request(url, data=donnees, method=methode, headers={
        "Authorization": f"Bearer {jeton}",
        "Content-Type": "application/json",
    })
    try:
        with urllib.request.urlopen(requete, timeout=DELAI) as reponse:
            return json.load(reponse)
    except urllib.error.HTTPError as erreur:
        detail = erreur.read().decode(errors="replace")[:300]
        raise SystemExit(f"Tchap a refusé ({erreur.code}) : {detail}") from None


def envoyer(texte):
    serveur, salon, jeton = _configuration()
    transaction = f"supervision-{os.environ.get('GITHUB_RUN_ID', '0')}-{time.time_ns()}"
    url = (f"{serveur}/_matrix/client/v3/rooms/{urllib.parse.quote(salon, safe='')}"
           f"/send/m.room.message/{transaction}")
    reponse = _appel("PUT", url, jeton, {"msgtype": "m.text", "body": texte})
    print(f"Message Tchap envoyé ({reponse.get('event_id')}).")


def verifier():
    serveur, salon, jeton = _configuration()
    # L'identifiant du robot n'est jamais écrit : les journaux d'un dépôt public
    # sont lisibles par tous, et sur Tchap il contient l'adresse e-mail du compte.
    _appel("GET", f"{serveur}/_matrix/client/v3/account/whoami", jeton)
    salons = _appel("GET", f"{serveur}/_matrix/client/v3/joined_rooms", jeton)["joined_rooms"]
    if salon not in salons:
        raise SystemExit("Le compte robot n'est pas membre du salon d'alerte.")
    print("Canal Tchap opérationnel : le compte robot est membre du salon.")


def main(arguments):
    if _configuration() is None:
        print("Canal Tchap non configuré (TCHAP_HOMESERVER, TCHAP_ROOM_ID, "
              "TCHAP_ACCESS_TOKEN) — ignoré.")
        return
    if arguments[:1] == ["envoyer"] and len(arguments) == 2:
        envoyer(arguments[1])
    elif arguments == ["verifier"]:
        verifier()
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
