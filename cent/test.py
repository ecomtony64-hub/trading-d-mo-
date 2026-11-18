"""Teste les 100 stratégies sur ~2 ans d'EUR/USD (1 h) avec frais. Usage : python3 test.py DOSSIER_CACHES"""
import json, os, sys, bisect
ici = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, ici)
import strategies as S
dem = sys.argv[1]
h1 = json.load(open(os.path.join(dem, "prix-cache-EURUSD=X-60m-730d.json")))
jr = json.load(open(os.path.join(dem, "prix-cache-EURUSD=X-1d-2y.json")))
def en_h4(b):
    g = {}
    for x in b:
        k = x["t"] - x["t"] % 14400
        if k not in g: g[k] = dict(x, t=k)
        else: y = g[k]; y["h"], y["l"], y["c"] = max(y["h"], x["h"]), min(y["l"], x["l"]), x["c"]
    return [g[k] for k in sorted(g)]
TF = {"h1": h1, "h4": en_h4(h1), "j": [x for x in jr if x["t"] >= h1[0]["t"] - 86400 * 250]}
t1 = [x["t"] for x in h1]; COUT = 0.00015; coupe = h1[int(len(h1) * 0.7)]["t"]; RATIO = 2.0
res = {}
for cle, (nom, regle, tf, f, p) in S.STRATS.items():
    b = TF[tf]; sig = f(b, *p); a = S.atr(b); r = {"entr": [], "verif": []}; libre = 0
    for i, s in enumerate(sig):
        if not s or a[i] is None: continue
        fin = b[i]["t"] + S.DUREE[tf]
        if fin < libre or fin < h1[0]["t"] + 86400 * 20: continue
        j = bisect.bisect_left(t1, fin)
        if j >= len(h1) - 1: break
        e = h1[j]["o"]; dist = 1.5 * a[i]
        if dist < 0.0003 or dist > 0.03: continue
        st, ob = (e - dist, e + RATIO * dist) if s > 0 else (e + dist, e - RATIO * dist); out = None
        while j < len(h1) and out is None:
            x = h1[j]
            if (s > 0 and x["l"] <= st) or (s < 0 and x["h"] >= st): out = -1.0
            elif (s > 0 and x["h"] >= ob) or (s < 0 and x["l"] <= ob): out = RATIO
            j += 1
        if out is None: break
        r["entr" if fin < coupe else "verif"].append(out - COUT / dist); libre = h1[j - 1]["t"]
    res[cle] = r
L = []
for cle, r in res.items():
    tout = r["entr"] + r["verif"]; g = sum(1 for x in tout if x > 0)
    L.append({"cle": cle, "nom": S.STRATS[cle][0], "trades": len(tout), "gagnes_pct": round(g / max(len(tout), 1) * 100),
              "R_ancien": round(sum(r["entr"]), 1), "R_recent": round(sum(r["verif"]), 1)})
L.sort(key=lambda x: -(min(x["R_ancien"], x["R_recent"] * 7 / 3) + x["R_ancien"] + x["R_recent"]))
json.dump(L, open(os.path.join(ici, "resultats.json"), "w"), indent=1, ensure_ascii=False)
for x in L: print(f'{x["cle"]:16} {x["trades"]:4} {x["gagnes_pct"]:3}% {x["R_ancien"]:7} {x["R_recent"]:7}')
