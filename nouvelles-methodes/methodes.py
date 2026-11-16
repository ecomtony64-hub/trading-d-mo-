"""10 nouvelles méthodes démo (préparées le 14/11, à activer le mercredi 18/11).

Chaque fonction reçoit d = {"j": bougies jour, "h4": bougies 4 h, "h1": bougies 1 h} (bougies terminées)
et renvoie (sens "ACHAT"/"VENTE" ou None, raison du refus, type de stop), comme signal() dans moteur.py.
Toutes visent 2 fois le risque. Aucune ne reprend les 20 méthodes déjà actives.
"""
import datetime as dt

def _mm(b, n):
    return sum(x["c"] for x in b[-n:]) / n if len(b) >= n else None

def _ecart(b, n):
    m = _mm(b, n)
    return (sum((x["c"] - m) ** 2 for x in b[-n:]) / n) ** 0.5 if m else None

def _ema(vals, n):
    k, e = 2 / (n + 1), vals[0]
    out = []
    for v in vals:
        e = v * k + e * (1 - k); out.append(e)
    return out

def _atr(b, n=14):
    if len(b) < n + 1: return None
    return sum(max(b[i]["h"] - b[i]["l"], abs(b[i]["h"] - b[i-1]["c"]), abs(b[i]["l"] - b[i-1]["c"])) for i in range(len(b) - n, len(b))) / n

def _heure(b):
    return dt.datetime.fromtimestamp(b["t"] + 3600, dt.timezone.utc)   # heure de FIN de la bougie, UTC

def _jour_bougies(h1, debut, fin):
    """Bougies d'1 h du jour en cours dont le début est entre debut et fin (heures UTC)."""
    j = _heure(h1[-1]).date()
    return [x for x in h1[-30:] if dt.datetime.fromtimestamp(x["t"], dt.timezone.utc).date() == j
            and debut <= dt.datetime.fromtimestamp(x["t"], dt.timezone.utc).hour < fin]

NON = lambda raison, stop: (None, raison, stop)

def bandes_rebond(d):
    """Contre-pied : le prix sort des bandes de Bollinger 1 h puis rentre dedans."""
    b = d["h1"]; m, e = _mm(b, 20), _ecart(b, 20)
    if not m: return NON("Pas assez de bougies.", "atr_h1")
    m0, e0 = _mm(b[:-1], 20), _ecart(b[:-1], 20)
    if b[-2]["c"] < m0 - 2 * e0 and b[-1]["c"] > m - 2 * e: return "ACHAT", "", "atr_h1"
    if b[-2]["c"] > m0 + 2 * e0 and b[-1]["c"] < m + 2 * e: return "VENTE", "", "atr_h1"
    return NON("Le prix n'est pas revenu dans ses bandes de 1 h après en être sorti.", "atr_h1")

def compression(d):
    """Après une période très calme (bandes 4 h les plus serrées depuis 1 mois), on suit la sortie."""
    b = d["h4"]
    if len(b) < 160: return NON("Pas assez de bougies.", "atr_h4")
    larg = [_ecart(b[:i], 20) for i in range(len(b) - 120, len(b) + 1)]
    m, e = _mm(b, 20), _ecart(b, 20)
    calme = min(larg[-6:-1]) <= min(larg[:-1]) * 1.05
    if calme and b[-1]["c"] > m + 2 * e: return "ACHAT", "", "atr_h4"
    if calme and b[-1]["c"] < m - 2 * e: return "VENTE", "", "atr_h4"
    return NON("Pas de sortie après une période calme sur 4 h.", "atr_h4")

def ouverture_londres(d):
    """Cassure du petit couloir de la nuit (0 h-7 h UTC) pendant la matinée de Londres (7 h-11 h UTC)."""
    b = d["h1"]; h = _heure(b[-1]).hour
    nuit = _jour_bougies(b, 0, 7)
    if not (8 <= h <= 11) or len(nuit) < 5: return NON("Ce n'est pas la matinée de Londres.", "couloir")
    haut, bas = max(x["h"] for x in nuit), min(x["l"] for x in nuit)
    if b[-1]["c"] > haut and b[-2]["c"] <= haut: return "ACHAT", "", "couloir"
    if b[-1]["c"] < bas and b[-2]["c"] >= bas: return "VENTE", "", "couloir"
    return NON("Le prix reste dans le couloir de la nuit.", "couloir")

def ouverture_newyork(d):
    """Cassure du couloir de la matinée européenne (7 h-12 h UTC) à l'ouverture de New York (13 h-16 h UTC)."""
    b = d["h1"]; h = _heure(b[-1]).hour
    matin = _jour_bougies(b, 7, 12)
    if not (14 <= h <= 16) or len(matin) < 4: return NON("Ce n'est pas l'ouverture de New York.", "atr_h1")
    haut, bas = max(x["h"] for x in matin), min(x["l"] for x in matin)
    if b[-1]["c"] > haut and b[-2]["c"] <= haut: return "ACHAT", "", "atr_h1"
    if b[-1]["c"] < bas and b[-2]["c"] >= bas: return "VENTE", "", "atr_h1"
    return NON("Le prix reste dans le couloir du matin.", "atr_h1")

def veille(d):
    """Cassure du plus haut ou du plus bas de la veille (graphique journalier), entre 7 h et 17 h UTC."""
    b, j = d["h1"], d["j"]; h = _heure(b[-1]).hour
    if not (7 <= h <= 17) or len(j) < 2: return NON("Hors des heures actives.", "atr_h1")
    hier = j[-1] if dt.datetime.fromtimestamp(j[-1]["t"], dt.timezone.utc).date() < _heure(b[-1]).date() else j[-2]
    if b[-1]["c"] > hier["h"] and b[-2]["c"] <= hier["h"]: return "ACHAT", "", "atr_h1"
    if b[-1]["c"] < hier["l"] and b[-2]["c"] >= hier["l"]: return "VENTE", "", "atr_h1"
    return NON("Le prix n'a pas dépassé le plus haut ni le plus bas d'hier.", "atr_h1")

def macd_h4(d):
    """Croisement du MACD sur 4 h (élan qui change de sens), dans le sens de la moyenne 50 jours."""
    b = d["h4"]
    if len(b) < 60: return NON("Pas assez de bougies.", "atr_h4")
    c = [x["c"] for x in b[-150:]]
    macd = [a - z for a, z in zip(_ema(c, 12), _ema(c, 26))]; sig = _ema(macd, 9)
    m50 = _mm(d["j"], 50)
    if macd[-2] <= sig[-2] and macd[-1] > sig[-1] and m50 and c[-1] > m50: return "ACHAT", "", "atr_h4"
    if macd[-2] >= sig[-2] and macd[-1] < sig[-1] and m50 and c[-1] < m50: return "VENTE", "", "atr_h4"
    return NON("Pas de croisement MACD 4 h dans le sens de la grande tendance.", "atr_h4")

def avalement(d):
    """Bougie 4 h « avalante » (elle englobe la précédente) au plus haut/bas des 20 dernières bougies."""
    b = d["h4"]
    if len(b) < 22: return NON("Pas assez de bougies.", "bougie")
    p, x = b[-2], b[-1]
    bas20, haut20 = min(y["l"] for y in b[-21:]), max(y["h"] for y in b[-21:])
    if p["c"] < p["o"] and x["c"] > x["o"] and x["c"] > p["o"] and x["o"] <= p["c"] and min(p["l"], x["l"]) <= bas20:
        return "ACHAT", "", "bougie"
    if p["c"] > p["o"] and x["c"] < x["o"] and x["c"] < p["o"] and x["o"] >= p["c"] and max(p["h"], x["h"]) >= haut20:
        return "VENTE", "", "bougie"
    return NON("Pas de bougie de retournement sur un extrême de 4 h.", "bougie")

def bougie_interieure(d):
    """La bougie d'hier est contenue dans celle d'avant-hier : on suit la sortie de cette zone (1 h)."""
    j, b = d["j"], d["h1"]
    if len(j) < 3: return NON("Pas assez de bougies.", "atr_h1")
    a, i = j[-3], j[-2]
    if not (i["h"] < a["h"] and i["l"] > a["l"]): return NON("Hier n'était pas une journée « intérieure ».", "atr_h1")
    if b[-1]["c"] > i["h"] and b[-2]["c"] <= i["h"]: return "ACHAT", "", "atr_h1"
    if b[-1]["c"] < i["l"] and b[-2]["c"] >= i["l"]: return "VENTE", "", "atr_h1"
    return NON("Le prix n'est pas sorti de la journée intérieure.", "atr_h1")

def elastique(d):
    """Contre-pied journalier : le prix s'est éloigné de plus de 2,5 « bougies moyennes » de sa moyenne 20 jours."""
    j = d["j"]; m, a = _mm(j, 20), _atr(j)
    if not (m and a): return NON("Pas assez de bougies.", "atr_h4")
    c = d["h1"][-1]["c"]
    if c < m - 2.5 * a: return "ACHAT", "", "atr_h4"
    if c > m + 2.5 * a: return "VENTE", "", "atr_h4"
    return NON("Le prix n'est pas trop éloigné de sa moyenne de 20 jours.", "atr_h4")

def stoch_tendance(d):
    """Stochastique 1 h qui remonte de la zone basse (ou redescend de la zone haute) dans le sens de la moyenne 20 jours."""
    b = d["h1"]
    if len(b) < 20: return NON("Pas assez de bougies.", "atr_h1")
    def k(bb):
        hh, ll = max(x["h"] for x in bb[-14:]), min(x["l"] for x in bb[-14:])
        return 50 if hh == ll else (bb[-1]["c"] - ll) / (hh - ll) * 100
    k0, k1 = k(b[:-1]), k(b); m = _mm(d["j"], 20)
    if m and b[-1]["c"] > m and k0 < 20 <= k1: return "ACHAT", "", "atr_h1"
    if m and b[-1]["c"] < m and k0 > 80 >= k1: return "VENTE", "", "atr_h1"
    return NON("Pas de signal du stochastique 1 h dans le sens de la tendance.", "atr_h1")

METHODES = {
    "bandes_rebond": ("Rebond des bandes 1 h", bandes_rebond),
    "compression": ("Sortie de calme 4 h", compression),
    "ouverture_londres": ("Ouverture de Londres", ouverture_londres),
    "ouverture_newyork": ("Ouverture de New York", ouverture_newyork),
    "veille": ("Plus haut / bas d'hier", veille),
    "macd_h4": ("MACD 4 h", macd_h4),
    "avalement": ("Bougie de retournement 4 h", avalement),
    "bougie_interieure": ("Journée intérieure", bougie_interieure),
    "elastique": ("Élastique jour", elastique),
    "stoch_tendance": ("Stochastique 1 h", stoch_tendance),
}

def stop(type_stop, sens, entree, d):
    """Prix du stop. couloir = autre bord du couloir de la nuit ; bougie = derrière les 2 dernières bougies 4 h."""
    if type_stop == "couloir":
        nuit = _jour_bougies(d["h1"], 0, 7)
        s = min(x["l"] for x in nuit) if sens == "ACHAT" else max(x["h"] for x in nuit)
    elif type_stop == "bougie":
        b = d["h4"][-2:]
        s = min(x["l"] for x in b) if sens == "ACHAT" else max(x["h"] for x in b)
    else:
        a = _atr(d["h1"] if type_stop == "atr_h1" else d["h4"])
        s = entree - 1.5 * a if sens == "ACHAT" else entree + 1.5 * a
    return s
