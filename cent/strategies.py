"""100 agents démo (préparés le 18/11) : variantes de méthodes classiques sur EUR/USD.

Chaque stratégie calcule une série de signaux sur des bougies TERMINÉES (+1 achat, -1 vente, 0 rien) ;
le même code sert au test sur 2 ans et au fonctionnement en direct (on lit seulement la dernière valeur).
Stop = 1,5 fois la taille moyenne d'une bougie (ATR 14) du même graphique ; objectif 2 fois le risque.
"""
import math

DUREE = {"h1": 3600, "h4": 14400, "j": 86400}
TFNOM = {"h1": "1 h", "h4": "4 h", "j": "jour"}

def mm(c, n):
    out, s = [None] * len(c), 0.0
    for i, v in enumerate(c):
        s += v
        if i >= n: s -= c[i - n]
        if i >= n - 1: out[i] = s / n
    return out

def ema(c, n):
    k, e, out = 2 / (n + 1), None, []
    for v in c:
        e = v if e is None else v * k + e * (1 - k); out.append(e)
    return out

def ecart(c, n):
    m, out = mm(c, n), [None] * len(c)
    for i in range(n - 1, len(c)):
        w = c[i - n + 1:i + 1]; out[i] = (sum((x - m[i]) ** 2 for x in w) / n) ** 0.5
    return out

def atr(b, n=14):
    tr = [b[0]["h"] - b[0]["l"]] + [max(b[i]["h"] - b[i]["l"], abs(b[i]["h"] - b[i-1]["c"]), abs(b[i]["l"] - b[i-1]["c"])) for i in range(1, len(b))]
    return mm(tr, n)

def rsi(c, n):
    out, g, p = [None] * len(c), 0.0, 0.0
    for i in range(1, len(c)):
        d = c[i] - c[i-1]; up, dn = max(d, 0), max(-d, 0)
        if i <= n: g += up / n; p += dn / n
        else: g = (g * (n - 1) + up) / n; p = (p * (n - 1) + dn) / n
        if i >= n: out[i] = 100 if p == 0 else 100 - 100 / (1 + g / p)
    return out

def stoch(b, n):
    out = [None] * len(b)
    for i in range(n - 1, len(b)):
        h = max(x["h"] for x in b[i-n+1:i+1]); l = min(x["l"] for x in b[i-n+1:i+1])
        out[i] = 50 if h == l else (b[i]["c"] - l) / (h - l) * 100
    return out

def croise(a, b, i):
    """+1 si a passe au-dessus de b sur la bougie i, -1 si en dessous."""
    if i < 1 or None in (a[i], b[i], a[i-1], b[i-1]): return 0
    if a[i-1] <= b[i-1] and a[i] > b[i]: return 1
    if a[i-1] >= b[i-1] and a[i] < b[i]: return -1
    return 0

def niveau(x, i, bas, haut, contre):
    """Sortie de zone : contre-pied (remonte au-dessus de bas = achat) ou suivi (dépasse haut = achat)."""
    if i < 1 or x[i] is None or x[i-1] is None: return 0
    if contre:
        if x[i-1] < bas <= x[i]: return 1
        if x[i-1] > haut >= x[i]: return -1
    else:
        if x[i-1] <= haut < x[i]: return 1
        if x[i-1] >= bas > x[i]: return -1
    return 0

# --- familles : chaque fonction renvoie la liste des signaux pour les bougies b ---
def f_mm(b, r, l):
    c = [x["c"] for x in b]; a, z = mm(c, r), mm(c, l); return [croise(a, z, i) for i in range(len(b))]
def f_ema(b, r, l):
    c = [x["c"] for x in b]; a, z = ema(c, r), ema(c, l); return [croise(a, z, i) for i in range(len(b))]
def f_rsi(b, n, bas, contre):
    x = rsi([y["c"] for y in b], n); return [niveau(x, i, bas, 100 - bas, contre) for i in range(len(b))]
def f_rsi50(b, n):
    c = [y["c"] for y in b]; x, t = rsi(c, n), mm(c, 200)
    out = []
    for i in range(len(b)):
        s = niveau(x, i, 50, 50, False) if t[i] else 0
        out.append(s if (s == 1 and c[i] > t[i]) or (s == -1 and c[i] < t[i]) else 0)
    return out
def f_donchian(b, n, filtre=False):
    c = [y["c"] for y in b]; t = mm(c, 200) if filtre else None; out = [0] * len(b)
    for i in range(n, len(b)):
        h = max(y["h"] for y in b[i-n:i]); l = min(y["l"] for y in b[i-n:i])
        s = 1 if c[i] > h and c[i-1] <= h else -1 if c[i] < l and c[i-1] >= l else 0
        if filtre and (t[i] is None or (s == 1 and c[i] < t[i]) or (s == -1 and c[i] > t[i])): s = 0
        out[i] = s
    return out
def f_boll(b, k, contre):
    c = [y["c"] for y in b]; m, e = mm(c, 20), ecart(c, 20); out = [0] * len(b)
    for i in range(20, len(b)):
        hi, lo, hp, lp = m[i] + k * e[i], m[i] - k * e[i], m[i-1] + k * e[i-1], m[i-1] - k * e[i-1]
        if contre: out[i] = 1 if c[i-1] < lp and c[i] >= lo else -1 if c[i-1] > hp and c[i] <= hi else 0
        else: out[i] = 1 if c[i-1] <= hp and c[i] > hi else -1 if c[i-1] >= lp and c[i] < lo else 0
    return out
def f_macd(b, r, l, s):
    c = [y["c"] for y in b]; m = [x - y for x, y in zip(ema(c, r), ema(c, l))]; sg = ema(m, s)
    return [croise(m, sg, i) for i in range(len(b))]
def f_stoch(b, contre):
    k = stoch(b, 14); d = mm([x if x is not None else 50 for x in k], 3)
    return [niveau(d, i, 20, 80, contre) for i in range(len(b))]
def f_keltner(b, k):
    c = [y["c"] for y in b]; m, a = ema(c, 20), atr(b); out = [0] * len(b)
    for i in range(21, len(b)):
        if a[i] is None or a[i-1] is None: continue
        hi, lo, hp, lp = m[i] + k * a[i], m[i] - k * a[i], m[i-1] + k * a[i-1], m[i-1] - k * a[i-1]
        out[i] = 1 if c[i-1] <= hp and c[i] > hi else -1 if c[i-1] >= lp and c[i] < lo else 0
    return out
def f_roc(b, n):
    c = [y["c"] for y in b]; roc = [None] * n + [c[i] / c[i-n] - 1 for i in range(n, len(c))]
    return [niveau(roc, i, 0, 0, False) for i in range(len(b))]
def f_pinbar(b):
    out = [0] * len(b)
    for i in range(20, len(b)):
        x = b[i]; corps = abs(x["c"] - x["o"]); tot = x["h"] - x["l"] or 1e-9
        bas_m, haut_m = min(x["o"], x["c"]) - x["l"], x["h"] - max(x["o"], x["c"])
        if corps < tot * 0.3 and bas_m > tot * 0.6 and x["l"] <= min(y["l"] for y in b[i-20:i]): out[i] = 1
        elif corps < tot * 0.3 and haut_m > tot * 0.6 and x["h"] >= max(y["h"] for y in b[i-20:i]): out[i] = -1
    return out
def f_trois(b, contre):
    out = [0] * len(b)
    for i in range(3, len(b)):
        sens = [1 if b[j]["c"] > b[j]["o"] else -1 for j in range(i-2, i+1)]
        if len(set(sens)) == 1 and (b[i-3]["c"] > b[i-3]["o"]) != (sens[0] == 1):
            out[i] = -sens[0] if contre else sens[0]
    return out
def f_repli(b):
    c = [y["c"] for y in b]; m20, m100 = ema(c, 20), mm(c, 100); out = [0] * len(b)
    for i in range(101, len(b)):
        if c[i] > m100[i] and b[i]["l"] <= m20[i] < c[i] and c[i-1] > m20[i-1]: out[i] = 1
        elif c[i] < m100[i] and b[i]["h"] >= m20[i] > c[i] and c[i-1] < m20[i-1]: out[i] = -1
    return out
def f_cci(b, contre):
    tp = [(y["h"] + y["l"] + y["c"]) / 3 for y in b]; m = mm(tp, 20); cci = [None] * len(b)
    for i in range(19, len(b)):
        md = sum(abs(x - m[i]) for x in tp[i-19:i+1]) / 20; cci[i] = 0 if md == 0 else (tp[i] - m[i]) / (0.015 * md)
    return [niveau(cci, i, -100, 100, contre) for i in range(len(b))]
def f_williams(b):
    k = stoch(b, 14); return [niveau(k, i, 20, 80, True) for i in range(len(b))]
def f_adx(b):
    n = 14; out = [0] * len(b); pdm, mdm, tr = [0.0], [0.0], [b[0]["h"] - b[0]["l"]]
    for i in range(1, len(b)):
        up, dn = b[i]["h"] - b[i-1]["h"], b[i-1]["l"] - b[i]["l"]
        pdm.append(up if up > dn and up > 0 else 0); mdm.append(dn if dn > up and dn > 0 else 0)
        tr.append(max(b[i]["h"] - b[i]["l"], abs(b[i]["h"] - b[i-1]["c"]), abs(b[i]["l"] - b[i-1]["c"])))
    a, p, m = ema(tr, n), ema(pdm, n), ema(mdm, n)
    pdi = [100 * x / y if y else 0 for x, y in zip(p, a)]; mdi = [100 * x / y if y else 0 for x, y in zip(m, a)]
    dx = [100 * abs(x - y) / (x + y) if x + y else 0 for x, y in zip(pdi, mdi)]; adx = ema(dx, n)
    for i in range(30, len(b)):
        s = croise(pdi, mdi, i)
        if s and adx[i] > 25: out[i] = s
    return out
def f_interieure(b):
    out = [0] * len(b)
    for i in range(2, len(b)):
        m, x = b[i-2], b[i-1]
        if x["h"] < m["h"] and x["l"] > m["l"]:
            out[i] = 1 if b[i]["c"] > m["h"] else -1 if b[i]["c"] < m["l"] else 0
    return out
def f_heikin(b):
    out, ho, hc = [0] * len(b), b[0]["o"], b[0]["c"]; prev = 0
    for i, x in enumerate(b):
        nc = (x["o"] + x["h"] + x["l"] + x["c"]) / 4; ho = (ho + hc) / 2; hc = nc
        col = 1 if hc > ho else -1
        if i > 2 and prev and col != prev: out[i] = col
        prev = col
    return out
def f_supertrend(b, k):
    a = atr(b, 10); out = [0] * len(b); sens, haut, bas = 0, None, None
    for i in range(11, len(b)):
        mid = (b[i]["h"] + b[i]["l"]) / 2; hu, bl = mid + k * a[i], mid - k * a[i]
        haut = hu if haut is None or hu < haut or b[i-1]["c"] > haut else haut
        bas = bl if bas is None or bl > bas or b[i-1]["c"] < bas else bas
        nouveau = 1 if b[i]["c"] > haut else -1 if b[i]["c"] < bas else sens
        if sens and nouveau != sens: out[i] = nouveau
        sens = nouveau
    return out
def f_aroon(b, n=25):
    out = [0] * len(b); up, dn = [None] * len(b), [None] * len(b)
    for i in range(n, len(b)):
        w = b[i-n:i+1]; hi = max(range(n + 1), key=lambda j: w[j]["h"]); lo = min(range(n + 1), key=lambda j: w[j]["l"])
        up[i], dn[i] = hi / n * 100, lo / n * 100
    return [croise(up, dn, i) for i in range(len(b))]

# --- les 100 agents : clé -> (nom, règle, graphique, fonction, paramètres) ---
STRATS = {}
def ajoute(cle, nom, regle, tf, f, *p):
    STRATS[cle] = (f"{nom} {TFNOM[tf]}", regle.replace("{tf}", TFNOM[tf]) + ", objectif 2 fois le risque", tf, f, p)
for tf in ("h1", "h4"):
    for r, l in ((5, 20), (10, 30), (20, 50), (10, 50), (20, 100)):
        ajoute(f"mm{r}-{l}-{tf}", f"Moyennes {r}/{l}", f"La moyenne de {r} bougies croise celle de {l} sur le graphique {{tf}}", tf, f_mm, r, l)
for tf in ("h1", "h4", "j"):
    for r, l in ((9, 21), (12, 26), (21, 55)):
        ajoute(f"ema{r}-{l}-{tf}", f"Moyennes rapides {r}/{l}", f"Croisement des moyennes rapides {r} et {l} sur {{tf}}", tf, f_ema, r, l)
for tf in ("h1", "h4"):
    for n in (7, 14):
        for bas in (25, 30, 35):
            ajoute(f"rsi{n}-{bas}-{tf}", f"RSI {n} ({bas}/{100-bas})", f"Contre-pied : le RSI {n} ressort de sa zone {bas}/{100-bas} sur {{tf}}", tf, f_rsi, n, bas, True)
    for n in (14, 21):
        ajoute(f"rsi50-{n}-{tf}", f"RSI {n} passe 50", f"Le RSI {n} passe 50 dans le sens de la moyenne 200 sur {{tf}}", tf, f_rsi50, n)
for tf in ("h1", "h4", "j"):
    for n in (10, 20, 55):
        ajoute(f"donch{n}-{tf}", f"Cassure {n} bougies", f"Le prix casse le plus haut ou le plus bas des {n} dernières bougies sur {{tf}}", tf, f_donchian, n)
for tf in ("h1", "h4"):
    ajoute(f"donch20f-{tf}", "Cassure 20 + moyenne 200", "Cassure des 20 dernières bougies dans le sens de la moyenne 200 sur {tf}", tf, f_donchian, 20, True)
    for k in (2.0, 2.5):
        ajoute(f"boll{int(k*10)}r-{tf}", f"Rebond bandes {k:g}", f"Contre-pied : le prix rentre dans les bandes de Bollinger ({k:g}) sur {{tf}}", tf, f_boll, k, True)
for tf in ("h1", "h4", "j"):
    ajoute(f"bollc-{tf}", "Sortie des bandes", "Suivi : le prix sort des bandes de Bollinger sur {tf}", tf, f_boll, 2.0, False)
    for r, l, s in ((12, 26, 9), (5, 35, 5)):
        ajoute(f"macd{r}-{l}-{tf}", f"MACD {r}/{l}/{s}", f"Croisement du MACD {r}/{l}/{s} sur {{tf}}", tf, f_macd, r, l, s)
    for n in (10, 20):
        ajoute(f"roc{n}-{tf}", f"Élan {n} bougies", f"Le prix repasse au-dessus ou en dessous de son niveau d'il y a {n} bougies sur {{tf}}", tf, f_roc, n)
    ajoute(f"heikin-{tf}", "Changement de couleur lissé", "Les bougies lissées (Heikin-Ashi) changent de couleur sur {tf}", tf, f_heikin)
    for k in (2, 3):
        ajoute(f"super{k}-{tf}", f"Stop suiveur {k}x", f"Le prix traverse une ligne suiveuse à {k} fois la taille moyenne des bougies sur {{tf}}", tf, f_supertrend, k)
for tf in ("h1", "h4"):
    ajoute(f"stochc-{tf}", "Stochastique contre-pied", "Contre-pied : la stochastique ressort de 20/80 sur {tf}", tf, f_stoch, True)
    ajoute(f"stochs-{tf}", "Stochastique suivi", "Suivi : la stochastique dépasse 80 ou passe sous 20 sur {tf}", tf, f_stoch, False)
    for k in (1.5, 2.0):
        ajoute(f"kelt{int(k*10)}-{tf}", f"Canal de Keltner {k:g}", f"Le prix sort du canal de Keltner ({k:g} fois la taille moyenne) sur {{tf}}", tf, f_keltner, k)
    ajoute(f"trois-{tf}", "3 bougies, on suit", "Après 3 bougies de même couleur, on suit le mouvement sur {tf}", tf, f_trois, False)
    ajoute(f"troisc-{tf}", "3 bougies, contre-pied", "Après 3 bougies de même couleur, on parie sur le retour sur {tf}", tf, f_trois, True)
    ajoute(f"repli20-{tf}", "Retour sur la moyenne 20", "Dans la tendance (moyenne 100), le prix touche la moyenne 20 et repart sur {tf}", tf, f_repli)
    ajoute(f"ccic-{tf}", "CCI contre-pied", "Contre-pied : le CCI ressort de -100/+100 sur {tf}", tf, f_cci, True)
    ajoute(f"ccis-{tf}", "CCI suivi", "Suivi : le CCI dépasse +100 ou passe sous -100 sur {tf}", tf, f_cci, False)
    ajoute(f"williams-{tf}", "Williams %R", "Contre-pied : le Williams %R ressort de sa zone extrême sur {tf}", tf, f_williams)
    ajoute(f"adx-{tf}", "ADX + croisement DI", "Les lignes DI se croisent avec une tendance forte (ADX > 25) sur {tf}", tf, f_adx)
for tf in ("h4", "j"):
    ajoute(f"pinbar-{tf}", "Bougie à longue mèche", "Bougie à longue mèche sur un extrême des 20 dernières sur {tf}", tf, f_pinbar)
ajoute("interieure-h4", "Sortie de bougie intérieure", "Le prix sort d'une bougie restée dans la précédente sur {tf}", "h4", f_interieure)
ajoute("aroon-h4", "Aroon", "Les lignes Aroon haut/bas se croisent sur {tf}", "h4", f_aroon)

def bougies_tf(d, tf):
    return d["j"] if tf == "j" else d["h4"] if tf == "h4" else d["h1"]

def signal(cle, d, maintenant_ts=None, fenetre=7200):
    """En direct : regarde la dernière bougie TERMINÉE du graphique. Signal valable 2 h après sa clôture."""
    nom, regle, tf, f, p = STRATS[cle]
    b = bougies_tf(d, tf)
    if maintenant_ts is not None:   # on enlève la bougie pas encore terminée
        b = [x for x in b if x["t"] + DUREE[tf] <= maintenant_ts]
    if len(b) < 60:
        return None, "Pas assez d'historique.", None
    s = f(b[-300:], *p)[-1]
    if maintenant_ts is not None and maintenant_ts - (b[-1]["t"] + DUREE[tf]) > fenetre:
        s = 0
    if not s:
        return None, f"Pas de signal : {regle.split(',')[0][0].lower() + regle.split(',')[0][1:]} (attendu).", None
    return ("ACHAT" if s > 0 else "VENTE"), "", "cent_" + tf

def stop(type_stop, sens, entree, d):
    tf = type_stop[5:]; b = bougies_tf(d, tf)
    a = atr(b[-60:])[-1]
    if not a: return None
    return entree - 1.5 * a if sens == "ACHAT" else entree + 1.5 * a
