"""Lance le moteur sur tous les comptes démo, puis prépare l'envoi à la page de suivi.

Usage : python3 tout.py [--leger] [--versions "courant=7,actif=4,..."] [--veto SYMBOLE="raison"] [--news "texte"]

--leger    : contrôle horaire sans veille d'actualités (ne pas passer --news : le dernier résumé est gardé).
--versions : versions actuelles des documents de la page (lues avec ArtifactData list). Elles sont mises
             dans if_version ; un compte absent de la liste est traité comme un nouveau document (set).

Affiche une ligne par compte, puis après la ligne WRITES le tableau JSON à passer tel quel à
ArtifactData batch (paramètre writes). En mode léger, un compte sans changement n'envoie que sa valeur.
"""
import json, os, subprocess, sys
ici = os.path.dirname(os.path.abspath(__file__))
comptes = json.load(open(os.path.join(ici, "comptes.json")))
args = sys.argv[1:]
leger = "--leger" in args
versions = {}
if "--versions" in args:
    i = args.index("--versions")
    for morceau in args[i + 1].split(","):
        if "=" in morceau:
            k, v = morceau.split("=")
            versions[k.strip()] = int(v)
    del args[i:i + 2]
args = [a for a in args if a != "--leger"]
# Les vetos de la dernière veille complète restent valables 4 h pour les contrôles légers.
import time
fv = os.path.join(ici, "vetos.json")
if leger:
    if os.path.exists(fv) and time.time() - os.path.getmtime(fv) < 4 * 3600:
        for v in json.load(open(fv)):
            args += ["--veto", v]
else:
    json.dump([args[i + 1] for i, a in enumerate(args) if a == "--veto"], open(fv, "w"), ensure_ascii=False)
writes, changes = [], []
for doc, c in comptes.items():
    f = os.path.join(ici, c["fichier"])
    avant = json.load(open(f)) if os.path.exists(f) else {"positions": [], "historique": []}
    r = subprocess.run([sys.executable, os.path.join(ici, "moteur.py"), f] + c["args"] + args, capture_output=True, text=True)
    if r.returncode:
        print(f"ERREUR {doc}: {r.stderr[-500:]}"); continue
    e = json.load(open(f))
    e["nom"], e["regle"] = c["nom"], c["regle"]
    json.dump(e, open(f, "w"), ensure_ascii=False, indent=1)
    ouverts = len(e["positions"]) - len(avant["positions"]) + len(e["historique"]) - len(avant["historique"])
    fermes = len(e["historique"]) - len(avant["historique"])
    change = ouverts != 0 or fermes != 0
    print(f"=== {doc} | {c['nom']} | valeur {e['valeur']} € | positions {len(e['positions'])} | trades fermés {len(e['historique'])} | CHANGEMENT: {'OUI' if change else 'non'}")
    if change:
        derniers = [f"{h['nom']} {h['sens']} : {h['motif']}, {h['resultat']} €" for h in e["historique"][len(avant["historique"]):]]
        nouveaux = [f"{p['nom']} {p['sens']} ouvert à {p['entree']}" for p in e["positions"] if p not in avant["positions"]]
        changes.append(f"{c['nom']} : " + " ; ".join(derniers + nouveaux))
    complet = {k: e.get(k) for k in ("capital", "capital_depart", "valeur", "methode", "ratio", "conditions", "nom", "regle",
                                     "mis_a_jour", "erreur_calendrier", "news", "positions")}
    complet.update(historique=e["historique"][-10:], courbe=e["courbe"][-12:], analyses=e["analyses"][-2:])
    if doc != "courant":   # la page lit le résumé d'actualités sur un seul document : on ne le répète pas 20 fois
        complet["news"] = ""
    if doc in versions and not change:   # rien de neuf : inutile de renvoyer ce qui ne bouge pas
        for k in ("capital_depart", "methode", "ratio", "conditions", "nom", "regle", "positions", "historique"):
            complet.pop(k, None)
    if doc not in versions:
        writes.append({"op": "set", "collection": "etat", "doc_id": doc, "data": complet})
    elif leger and not change:
        writes.append({"op": "update", "collection": "etat", "doc_id": doc, "if_version": versions[doc],
                       "data": {"valeur": e["valeur"], "capital": e["capital"], "mis_a_jour": e["mis_a_jour"]}})
    else:
        writes.append({"op": "update", "collection": "etat", "doc_id": doc, "if_version": versions[doc], "data": complet})
print("CHANGEMENTS:", " | ".join(changes) if changes else "aucun")
print("WRITES")
print(json.dumps(writes, ensure_ascii=False, separators=(",", ":")))
