"""Rassemble l'état des comptes dans donnees.json et donnees.js (lu par la page de suivi sur claude.ai)."""
import json, os, datetime as dt
ici = os.path.dirname(os.path.abspath(__file__))
comptes = json.load(open(os.path.join(ici, "comptes.json")))
out = {}
for doc, c in comptes.items():
    f = os.path.join(ici, c["fichier"])
    if not os.path.exists(f):
        continue
    e = json.load(open(f))
    d = {k: e.get(k) for k in ("capital", "capital_depart", "valeur", "methode", "ratio", "conditions", "mis_a_jour",
                               "erreur_calendrier", "news", "positions")}
    d.update(nom=c["nom"], regle=c["regle"], historique=e.get("historique", [])[-10:], courbe=e.get("courbe", [])[-12:],
             analyses=e.get("analyses", [])[-2:])
    if doc != "courant":
        d["news"] = ""
    out[doc] = d
# Prix pour la Salle de trading : les 80 dernières bougies d'1 h téléchargées par le moteur (t en millisecondes).
prix = {}
for code, sym in (("EURUSD", "EURUSD=X"), ("OR", "GC=F")):
    f = os.path.join(ici, f"prix-cache-{sym}-60m-60d.json")
    if os.path.exists(f):
        b = json.load(open(f))[-80:]
        prix[code] = {"maj": dt.datetime.fromtimestamp(os.path.getmtime(f), dt.timezone.utc).isoformat(timespec="minutes"),
                      "bougies": [{"t": x["t"] * 1000, "o": x["o"], "h": x["h"], "l": x["l"], "c": x["c"]} for x in b]}
paquet = {"genere": dt.datetime.now(dt.timezone.utc).isoformat(timespec="minutes"), "etat": out, "prix": prix}
json.dump(paquet, open(os.path.join(ici, "donnees.json"), "w"), ensure_ascii=False, separators=(",", ":"))
open(os.path.join(ici, "donnees.js"), "w").write("window.DEMO_DONNEES=" + json.dumps(paquet, ensure_ascii=False, separators=(",", ":")) + ";\n")
print(len(out), "comptes publiés")
