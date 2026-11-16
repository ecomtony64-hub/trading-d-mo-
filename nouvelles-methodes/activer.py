"""À lancer UNE fois, mercredi 18/11 après 6 h (Paris) : branche les nouvelles méthodes sur la démo.
Usage : python3 activer.py [dossier_demo]   (par défaut : le dossier demo/ parent)
1. Sauvegarde moteur.py et comptes.json dans demo/avant-nouvelles-methodes/
2. Ajoute 2 lignes dans moteur.py pour qu'il sache lire methodes.py
3. Ajoute les comptes de NOUVEAUX_COMPTES à comptes.json (100 € chacun, départ à zéro)
Sans danger si relancé : ne fait rien de plus la 2e fois.
"""
import json, os, shutil, sys
ici = os.path.dirname(os.path.abspath(__file__))
demo = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(ici)
NOUVEAUX_COMPTES = {   # clé : (mode, objectif, nom, règle)
    "macd-h4": ("macd_h4", 3, "MACD 4 h", "Croisement de l'élan (MACD) sur 4 h dans le sens de la moyenne de 50 jours, objectif 3 fois le risque"),
    "compression": ("compression", 3, "Sortie de calme 4 h", "Après une période très calme sur 4 h, on suit la sortie des bandes, objectif 3 fois le risque"),
    "londres": ("ouverture_londres", 3, "Ouverture de Londres", "Cassure du couloir de la nuit à l'ouverture de Londres, objectif 3 fois le risque"),
    "interieure": ("bougie_interieure", 3, "Journée intérieure", "Sortie d'une journée restée à l'intérieur de la précédente, objectif 3 fois le risque"),
    "avalement": ("avalement", 2, "Bougie de retournement 4 h", "Bougie qui avale la précédente sur un plus haut ou plus bas de 4 h, objectif 2 fois le risque"),
    "elastique": ("elastique", 2, "Élastique jour", "Contre-pied quand le prix est très loin de sa moyenne de 20 jours, objectif 2 fois le risque"),
}
mot, cpt = os.path.join(demo, "moteur.py"), os.path.join(demo, "comptes.json")
sauve = os.path.join(demo, "avant-nouvelles-methodes"); os.makedirs(sauve, exist_ok=True)
for f in (mot, cpt):
    if not os.path.exists(os.path.join(sauve, os.path.basename(f))): shutil.copy(f, sauve)
src = open(mot).read()
if "nouvelles-methodes" not in src:
    src = src.replace("def signal(mode, d, tj, t4, t1):\n",
        "def signal(mode, d, tj, t4, t1):\n"
        "    import os as _o; sys.path.insert(0, _o.path.join(_o.path.dirname(_o.path.abspath(__file__)), \"nouvelles-methodes\")); import methodes as _nm\n"
        "    if mode in _nm.METHODES:\n        return _nm.METHODES[mode][1](d)\n", 1)
    src = src.replace("def calcul_stop(type_stop, sens, entree, d, h4_hauts, h4_bas, h1_hauts, h1_bas):\n",
        "def calcul_stop(type_stop, sens, entree, d, h4_hauts, h4_bas, h1_hauts, h1_bas):\n"
        "    if type_stop in (\"couloir\", \"bougie\"):\n        import methodes as _nm\n        return _nm.stop(type_stop, sens, entree, d)\n", 1)
    assert src.count("_nm.") == 3, "moteur.py a changé : branchement à faire à la main"
    open(mot, "w").write(src)
c = json.load(open(cpt))
for k, (mode, ratio, nom, regle) in NOUVEAUX_COMPTES.items():
    c.setdefault(k, {"fichier": f"etat-{k}.json", "nom": nom, "regle": regle, "args": ["--mode", mode, "--ratio", str(ratio)]})
json.dump(c, open(cpt, "w"), indent=1, ensure_ascii=False)
print(f"OK : {len(c)} comptes dans comptes.json. Sauvegarde dans {sauve}")
