"""À lancer UNE fois, seulement après le oui de Tony : ajoute les 74 nouveaux comptes (100 au total).
Usage : python3 cent/activer.py [dossier_demo]   (par défaut : le dossier parent)
Sauvegarde d'abord moteur.py et comptes.json dans avant-cent/. Sans danger si relancé.
"""
import json, os, shutil, sys
ici = os.path.dirname(os.path.abspath(__file__))
demo = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(ici)
sys.path.insert(0, ici); import strategies as S
mot, cpt = os.path.join(demo, "moteur.py"), os.path.join(demo, "comptes.json")
sauve = os.path.join(demo, "avant-cent"); os.makedirs(sauve, exist_ok=True)
for f in (mot, cpt):
    if not os.path.exists(os.path.join(sauve, os.path.basename(f))): shutil.copy(f, sauve)
src = open(mot).read()
if "strategies as _cs" not in src:
    src = src.replace("def signal(mode, d, tj, t4, t1):\n",
        "def signal(mode, d, tj, t4, t1):\n"
        "    if mode.startswith(\"c:\"):\n        import os as _o, time as _t; sys.path.insert(0, _o.path.join(_o.path.dirname(_o.path.abspath(__file__)), \"cent\")); import strategies as _cs\n"
        "        return _cs.signal(mode[2:], d, _t.time())\n", 1)
    src = src.replace("def calcul_stop(type_stop, sens, entree, d, h4_hauts, h4_bas, h1_hauts, h1_bas):\n",
        "def calcul_stop(type_stop, sens, entree, d, h4_hauts, h4_bas, h1_hauts, h1_bas):\n"
        "    if type_stop.startswith(\"cent_\"):\n        import strategies as _cs\n        return _cs.stop(type_stop, sens, entree, d)\n", 1)
    assert src.count("_cs.") == 2, "moteur.py a changé : branchement à faire à la main"
    open(mot, "w").write(src)
c = json.load(open(cpt))
choisis = [x["cle"] for x in json.load(open(os.path.join(ici, "resultats.json")))][:100 - len(c)] if len(c) < 100 else []
for k in choisis:
    nom, regle, tf, f, p = S.STRATS[k]
    c.setdefault("c-" + k, {"fichier": f"etat-c-{k}.json", "nom": nom, "regle": regle, "args": ["--mode", "c:" + k]})
json.dump(c, open(cpt, "w"), indent=1, ensure_ascii=False)
print(f"OK : {len(c)} comptes. Sauvegarde dans {sauve}")
