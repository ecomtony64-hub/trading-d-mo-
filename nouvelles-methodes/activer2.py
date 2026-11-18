"""Vague 2 : ajoute 3 comptes à comptes.json (méthodes déjà dans methodes.py). Usage : python3 activer2.py [dossier]"""
import json, os, sys
demo = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NOUVEAUX = {
    "lundi-trou": ("lundi_trou", 3, "Trou du lundi", "Le lundi à l'ouverture, si le prix a sauté loin de la clôture du vendredi, on parie qu'il revient, objectif 3 fois le risque"),
    "vendredi": ("vendredi", 3, "Vendredi contre-pied", "Le vendredi après-midi, si la semaine a beaucoup bougé, on parie sur un petit retour, objectif 3 fois le risque"),
}
p = os.path.join(demo, "comptes.json"); c = json.load(open(p))
for k, (mode, ratio, nom, regle) in NOUVEAUX.items():
    c.setdefault(k, {"fichier": f"etat-{k}.json", "nom": nom, "regle": regle, "args": ["--mode", mode, "--ratio", str(ratio)]})
json.dump(c, open(p, "w"), indent=1, ensure_ascii=False)
print(f"OK : {len(c)} comptes")
