"""Ajoute les 100 comptes démo sur l'or (Tony, 24/11) : 25 méthodes x 4 niveaux de risque.

Chaque compte : 100 € fictifs à lui, ne trade que l'or, 4 trades ouverts au plus, 1 h entre deux ouvertures.
Les 15 méthodes « c:... » sont les meilleures des 100 méthodes sur 2 ans d'or (test du 24/11, frais compris) ;
les 10 autres reprennent les méthodes maison de l'EUR/USD pour comparer.
Usage : python3 or/activer.py   (sans danger si relancé : ne touche pas aux comptes existants)
"""
import json, os
ici = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
fc = os.path.join(ici, "comptes.json")
comptes = json.load(open(fc))
METHODES = ["c:donch10-h1", "c:donch55-h1", "c:donch20f-h1", "c:ccis-h1", "c:donch20-h1", "c:trois-h1", "c:mm20-50-h1",
            "c:donch20f-h4", "c:adx-h1", "c:macd5-35-h4", "c:macd12-26-h1", "c:kelt20-h4", "c:roc20-h1", "c:super3-h4",
            "c:ema9-21-h4", "actif", "repli", "h4", "h4_atr", "mm_h1", "cassure_h4", "large", "elan", "macd_h4", "compression"]
NIVEAUX = [  # (préfixe, nom, risque par trade en %, options en plus, texte)
    ("or-p-", "prudent", 1, [], "risque 1 % du compte par trade"),
    ("or-", "normal", 2, [], "risque 2 % du compte par trade"),
    ("or-f-", "risque fort", 5, ["--pause50"], "risque 5 % du compte par trade, pause sous 50 €"),
    ("or-max-", "risque max", 10, ["--max"], "risque 10 € par trade (10 % des 100 € de départ), sans aucun blocage : continue même sous 0 €"),
]
# nom et règle de chaque méthode, repris des comptes EUR/USD
infos = {}
for c in comptes.values():
    a = c["args"]
    if "--mode" in a and "--max" not in a:
        infos.setdefault(a[a.index("--mode") + 1], (c["nom"], c["regle"]))
import sys
sys.path.insert(0, os.path.join(ici, "cent"))
import strategies
for k, v in strategies.STRATS.items():
    infos["c:" + k] = (v[0], v[1])
ajout = 0
for m in METHODES:
    nom, regle = infos[m]
    for pre, niv, pct, opts, txt in NIVEAUX:
        cle = pre + m.replace("c:", "").replace("_", "-")
        if cle in comptes:
            continue
        comptes[cle] = {"fichier": f"etat-{cle}.json", "nom": f"Or · {nom} ({niv})",
                        "regle": f"Or seulement. {regle} ; {txt} ; 4 trades ouverts au plus",
                        "args": ["--mode", m, "--marche", "OR", "--risque-trade", str(pct), "--max-ouverts", "4", "--ecart", "1"] + opts}
        ajout += 1
json.dump(comptes, open(fc, "w"), ensure_ascii=False, indent=1)
print(ajout, "comptes or ajoutés ;", len(comptes), "comptes en tout")
