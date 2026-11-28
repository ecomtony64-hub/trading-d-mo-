"""Bots or du classement en 4 points (Tony, 28/11) : mêmes règles que le test sur 2 ans (trading-agent/bots-or/).

Signal sur la dernière bougie d'1 h TERMINÉE, valable 1 h après sa clôture.
Stop = k fois l'agitation (ATR 14 sur 1 h) à la bougie du signal ; l'objectif est réglé par --ratio dans comptes.json.
Clé du mode : famille:stop[:achat], ex. « b:londres:5 », « b:cassure48:6 », « b:londres:8:achat ».
Familles : londres (cassure de la nuit 0-7 h UTC, bougies de 8 h et 9 h UTC), cassure24, cassure48 (plus haut / plus bas de n heures).
"achat" = le bot ne prend que les achats.
"""
NOMS = {"londres": "cassure de la nuit asiatique à l'ouverture de Londres",
        "cassure48": "cassure du plus haut ou du plus bas des 48 dernières heures",
        "cassure24": "cassure du plus haut ou du plus bas des 24 dernières heures"}


def atr(b, n=14):
    tr = [max(b[i]["h"] - b[i]["l"], abs(b[i]["h"] - b[i - 1]["c"]), abs(b[i]["l"] - b[i - 1]["c"])) for i in range(len(b) - n, len(b))]
    return sum(tr) / n


def _terminees(d, maintenant_ts):
    return [x for x in d["h1"] if x["t"] + 3600 <= maintenant_ts]


def _sens(cle, b):
    i = len(b) - 1
    if cle.startswith("cassure"):
        n = int(cle[7:])
        if b[i]["c"] > max(x["h"] for x in b[i - n:i]): return 1
        if b[i]["c"] < min(x["l"] for x in b[i - n:i]): return -1
        return 0
    # londres
    h = (b[i]["t"] // 3600) % 24
    if h not in (8, 9): return 0   # comme le test : la bougie de 7 h est encore dans la nuit (0-7 h)
    jour = b[i]["t"] // 86400
    nuit = [x for x in b if x["t"] // 86400 == jour and (x["t"] // 3600) % 24 < 7]
    if not nuit or (nuit[0]["t"] // 3600) % 24 != 0: return 0
    hi, lo = max(x["h"] for x in nuit), min(x["l"] for x in nuit)
    if b[i]["c"] > hi and b[i - 1]["c"] <= hi: return 1
    if b[i]["c"] < lo and b[i - 1]["c"] >= lo: return -1
    return 0


def signal(mode, d, maintenant_ts, fenetre=3600):
    morceaux = mode.split(":"); cle, k = morceaux[0], morceaux[1]
    achat_seul = len(morceaux) > 2 and morceaux[2] == "achat"
    b = _terminees(d, maintenant_ts)
    if len(b) < 60:
        return None, "Pas assez d'historique.", None
    if maintenant_ts - (b[-1]["t"] + 3600) > fenetre:
        return None, "Dernière bougie trop ancienne (marché fermé ?).", None
    s = _sens(cle, b)
    if achat_seul and s < 0:
        s = 0
    if not s:
        return None, f"Pas de signal : {NOMS[cle]} (attendu).", None
    return ("ACHAT" if s > 0 else "VENTE"), "", f"botor_{cle}_{k}_{b[-1]['t']}"


def stop(type_stop, sens, entree, d):
    _, cle, k, t = type_stop.split("_")
    b = [x for x in d["h1"] if x["t"] <= int(t)]
    if len(b) < 20: return None
    dist = float(k) * atr(b)
    return entree - dist if sens == "ACHAT" else entree + dist
