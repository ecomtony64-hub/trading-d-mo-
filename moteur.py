"""Moteur de la démo de trading (argent fictif).

Usage : python3 moteur.py ETAT.json [--mode strict|actif] [--veto SYMBOLE="raison"] [--news "texte"]
Mode strict : trade si les graphiques jour et 4 h sont d'accord. Mode actif : si 4 h et 1 h sont d'accord.
Lit les prix (Yahoo Finance) et le calendrier (Forex Factory), met à jour les
positions fictives, applique les règles de la méthode et réécrit ETAT.json.
"""
import json, sys, urllib.request, datetime as dt

UA = {"User-Agent": "Mozilla/5.0"}
MARCHES = {
    "EURUSD": {"nom": "Euro / Dollar", "yahoo": "EURUSD=X", "devises": ["EUR", "USD"], "decimales": 5},
    "OR": {"nom": "Or", "yahoo": "GC=F", "devises": ["USD"], "decimales": 1},
}
RISQUE = 0.01      # 1 % du capital par trade
RATIO = 2.0        # objectif = 2 fois le risque
FENETRE_MIN = 30   # pas de trade 30 min avant / après une annonce rouge
# Conditions réelles d'un courtier européen classique (compte « micro-lots »).
# spread : écart achat/vente payé à chaque trade ; glissement : sortie un peu moins bonne sur un stop ;
# nuit : frais par nuit et par unité ; pas : plus petite taille autorisée ; levier : garantie = valeur / levier.
FRAIS = {
    "EURUSD": {"spread": 0.00010, "glissement": 0.00005, "nuit": 0.00005, "pas": 1000, "levier": 30},
    "OR": {"spread": 0.35, "glissement": 0.20, "nuit": 0.40, "pas": 1, "levier": 20},
}
RISQUE_MAX = 0.05  # si la taille minimale fait risquer plus de 5 % du compte, le trade est refusé
MAX_PAR_MARCHE = 2   # trades ouverts en même temps sur un même marché
MAX_OUVERTS = 2      # trades ouverts en même temps sur un compte (Tony, 19/11)
MARGE_TRADE = 30.0   # garantie visée par trade, en € (Tony, 19/11)
RISQUE_MAX_TRADE = 0.15  # sécurité : refus si un trade risque plus de 15 % du compte
ECART_H = 4          # heures minimum entre deux ouvertures sur le même marché
RISQUE_TOTAL = 0.20  # risque total de tous les trades ouverts : 20 % du compte au plus
MAJEURES = ("FOMC", "Federal Funds Rate", "Non-Farm", "CPI")


def get_json(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
        return json.load(r)


def bougies(symbole, intervalle, periode):
    import os, time
    cache = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"prix-cache-{symbole}-{intervalle}-{periode}.json")
    # 20 comptes tournent à la suite : on garde les prix 10 minutes pour ne pas être bloqué par Yahoo
    if os.path.exists(cache) and time.time() - os.path.getmtime(cache) < 600:
        return json.load(open(cache))
    res = get_json(f"https://query1.finance.yahoo.com/v8/finance/chart/{symbole}?interval={intervalle}&range={periode}")["chart"]["result"][0]
    q = res["indicators"]["quote"][0]
    out = []
    for i, t in enumerate(res["timestamp"]):
        if None in (q["open"][i], q["high"][i], q["low"][i], q["close"][i]):
            continue
        out.append({"t": t, "o": q["open"][i], "h": q["high"][i], "l": q["low"][i], "c": q["close"][i]})
    json.dump(out, open(cache, "w"))
    return out


def en_h4(h1):
    groupes = {}
    for b in h1:
        cle = b["t"] - b["t"] % (4 * 3600)
        g = groupes.get(cle)
        if g is None:
            groupes[cle] = dict(b, t=cle)
        else:
            g["h"], g["l"], g["c"] = max(g["h"], b["h"]), min(g["l"], b["l"]), b["c"]
    return [groupes[k] for k in sorted(groupes)]


def sommets(b, k=2):
    hauts, bas = [], []
    for i in range(k, len(b) - k):
        fen = b[i - k:i + k + 1]
        if b[i]["h"] == max(x["h"] for x in fen):
            hauts.append(b[i]["h"])
        if b[i]["l"] == min(x["l"] for x in fen):
            bas.append(b[i]["l"])
    return hauts, bas


def tendance(b):
    hauts, bas = sommets(b)
    if len(hauts) < 2 or len(bas) < 2:
        return "RANGE", hauts, bas
    if hauts[-1] > hauts[-2] and bas[-1] > bas[-2]:
        return "HAUSSIER", hauts, bas
    if hauts[-1] < hauts[-2] and bas[-1] < bas[-2]:
        return "BAISSIER", hauts, bas
    return "RANGE", hauts, bas


def moyenne(b, n):
    return sum(x["c"] for x in b[-n:]) / n if len(b) >= n else None


def rsi(b, n=14):
    if len(b) < n + 1:
        return None
    gains = pertes = 0.0
    for i in range(len(b) - n, len(b)):
        v = b[i]["c"] - b[i - 1]["c"]
        gains += max(v, 0)
        pertes += max(-v, 0)
    return 100.0 if pertes == 0 else 100 - 100 / (1 + gains / pertes)


def atr(b, n=14):
    """Taille moyenne des n dernières bougies : sert à placer un stop à bonne distance."""
    if len(b) < n + 1:
        return None
    return sum(max(b[i]["h"] - b[i]["l"], abs(b[i]["h"] - b[i - 1]["c"]), abs(b[i]["l"] - b[i - 1]["c"]))
               for i in range(len(b) - n, len(b))) / n


def signal(mode, d, tj, t4, t1):
    if mode.startswith("c:"):
        import os as _o, time as _t; sys.path.insert(0, _o.path.join(_o.path.dirname(_o.path.abspath(__file__)), "cent")); import strategies as _cs
        return _cs.signal(mode[2:], d, _t.time())
    import os as _o; sys.path.insert(0, _o.path.join(_o.path.dirname(_o.path.abspath(__file__)), "nouvelles-methodes")); import methodes as _nm
    if mode in _nm.METHODES:
        return _nm.METHODES[mode][1](d)
    """Renvoie (sens ou None, raison du refus, type de stop) pour la méthode du compte."""
    H, B = "HAUSSIER", "BAISSIER"

    def accord(tendances, noms, stop):
        if all(t == H for t in tendances):
            return "ACHAT", "", stop
        if all(t == B for t in tendances):
            return "VENTE", "", stop
        if len(tendances) == 1:
            return None, f"Pas de tendance claire sur le graphique {noms}.", stop
        return None, f"Pas de tendance claire : les graphiques {noms} ne vont pas dans le même sens.", stop

    def moyennes(b, nom, stop):
        m20, m50, c = moyenne(b, 20), moyenne(b, 50), b[-1]["c"]
        if m20 and m50 and m20 > m50 and c > m20:
            return "ACHAT", "", stop
        if m20 and m50 and m20 < m50 and c < m20:
            return "VENTE", "", stop
        return None, f"Les moyennes du graphique {nom} ne donnent pas de direction nette.", stop

    def cassure(b, nom, stop):
        avant = b[-21:-1]
        if len(avant) == 20 and b[-1]["c"] > max(x["h"] for x in avant):
            return "ACHAT", "", stop
        if len(avant) == 20 and b[-1]["c"] < min(x["l"] for x in avant):
            return "VENTE", "", stop
        return None, f"Le prix n'a pas cassé son plus haut ni son plus bas des 20 dernières bougies ({nom}).", stop

    def extreme(b, nom, stop):
        r = rsi(b)
        if r is not None and r < 30:
            return "ACHAT", "", stop
        if r is not None and r > 70:
            return "VENTE", "", stop
        return None, f"Le prix n'est ni très bas ni très haut sur le graphique {nom} (indicateur RSI entre 30 et 70).", stop

    if mode == "strict":
        return accord([tj, t4], "jour et 4 h", "sommet_h4")
    if mode == "actif":
        return accord([t4, t1], "4 h et 1 h", "sommet_h4")
    if mode == "triple":
        return accord([tj, t4, t1], "jour, 4 h et 1 h", "sommet_h4")
    if mode == "rapide":
        return accord([t1], "d'1 h", "sommet_h1")
    if mode == "h4":
        return accord([t4], "de 4 h", "sommet_h4")
    if mode == "jour":
        return accord([tj], "journalier", "sommet_h4")
    if mode == "h4_atr":
        return accord([t4], "de 4 h", "atr_h4")
    if mode == "h1_atr":
        return accord([t1], "d'1 h", "atr_h1")
    if mode == "mm_h1":
        return moyennes(d["h1"], "d'1 h", "atr_h1")
    if mode == "mm_h4":
        return moyennes(d["h4"], "de 4 h", "atr_h4")
    if mode == "mm_j":
        return moyennes(d["j"], "journalier", "atr_h4")
    if mode == "cassure_h1":
        return cassure(d["h1"], "1 h", "atr_h1")
    if mode == "cassure_h4":
        return cassure(d["h4"], "4 h", "atr_h4")
    if mode == "cassure_j":
        return cassure(d["j"], "jour", "atr_h4")
    if mode == "rsi_h1":
        return extreme(d["h1"], "d'1 h", "atr_h1")
    if mode == "rsi_h4":
        return extreme(d["h4"], "de 4 h", "atr_h4")
    if mode == "repli":
        r = rsi(d["h1"])
        if t4 == H and r is not None and r < 40:
            return "ACHAT", "", "sommet_h4"
        if t4 == B and r is not None and r > 60:
            return "VENTE", "", "sommet_h4"
        return None, "Pas de petit retour en arrière dans une tendance de 4 h.", "sommet_h4"
    if mode == "elan":
        h1 = d["h1"]
        v = (h1[-1]["c"] / h1[-25]["c"] - 1) * 100 if len(h1) > 25 else 0
        if v > 0.3 and t4 != B:
            return "ACHAT", "", "atr_h1"
        if v < -0.3 and t4 != H:
            return "VENTE", "", "atr_h1"
        return None, "Le prix n'a pas assez bougé depuis 24 h (moins de 0,3 %).", "atr_h1"
    if mode == "mm200":
        m200, c = moyenne(d["h1"], 200), d["h1"][-1]["c"]
        if t1 == H and m200 and c > m200:
            return "ACHAT", "", "sommet_h1"
        if t1 == B and m200 and c < m200:
            return "VENTE", "", "sommet_h1"
        return None, "La tendance d'1 h et la moyenne longue (200 heures) ne sont pas d'accord.", "sommet_h1"
    if mode == "large":
        m50, c = moyenne(d["j"], 50), d["j"][-1]["c"]
        s, pq, st = cassure(d["h4"], "4 h", "atr_h4")
        if s == "ACHAT" and m50 and c > m50:
            return s, "", st
        if s == "VENTE" and m50 and c < m50:
            return s, "", st
        return None, pq if not s else "La cassure de 4 h va contre la grande tendance (moyenne de 50 jours).", st
    return None, f"Méthode inconnue : {mode}.", "sommet_h4"


def calcul_stop(type_stop, sens, entree, d, h4_hauts, h4_bas, h1_hauts, h1_bas):
    if type_stop.startswith("cent_"):
        import strategies as _cs
        return _cs.stop(type_stop, sens, entree, d)
    if type_stop in ("couloir", "bougie"):
        import methodes as _nm
        return _nm.stop(type_stop, sens, entree, d)
    if type_stop.startswith("atr"):
        a = atr(d["h1"] if type_stop == "atr_h1" else d["h4"])
        if not a:
            return None
        return entree - 1.5 * a if sens == "ACHAT" else entree + 1.5 * a   # stop à 1,5 fois la taille moyenne d'une bougie
    hauts, bas = (h1_hauts, h1_bas) if type_stop == "sommet_h1" else (h4_hauts, h4_bas)
    if not hauts or not bas:
        return None
    return bas[-1] if sens == "ACHAT" else hauts[-1]


def calendrier(maintenant):
    import os, time
    cache = os.path.join(os.path.dirname(os.path.abspath(__file__)), "calendrier-cache.json")
    try:  # le site limite les appels : on garde une copie pendant 1 h
        if os.path.exists(cache) and time.time() - os.path.getmtime(cache) < 3600:
            evts = json.load(open(cache))
        else:
            evts = get_json("https://nfs.faireconomy.media/ff_calendar_thisweek.json")
            json.dump(evts, open(cache, "w"))
    except Exception as e:
        if not os.path.exists(cache):
            return None, f"calendrier indisponible ({e})"
        evts = json.load(open(cache))
    rouges = []
    for e in evts:
        if e.get("impact") != "High":
            continue
        try:
            quand = dt.datetime.fromisoformat(e["date"]).astimezone(dt.timezone.utc)
        except Exception:
            continue
        rouges.append({"titre": e["title"], "devise": e["country"], "quand": quand})
    return rouges, None


def fermer(pos, prix, motif, quand, eurusd, frais_usd=0.0):
    sens = 1 if pos["sens"] == "ACHAT" else -1
    gain_usd = pos["unites"] * (prix - pos["entree"]) * sens - frais_usd
    pos.update(sortie=prix, motif=motif, ferme_le=quand, frais_nuit=round(frais_usd / eurusd, 2),
               resultat=round(gain_usd / eurusd, 2))
    return pos["resultat"]


def main():
    chemin = sys.argv[1]
    vetos, news, mode, ratio = {}, "", "strict", RATIO
    risque, risque_max, fort = RISQUE, RISQUE_MAX, False
    args = sys.argv[2:]
    for i, a in enumerate(args):
        if a == "--veto":
            s, r = args[i + 1].split("=", 1)
            vetos[s.upper()] = r
        if a == "--news":
            news = args[i + 1]
        if a == "--mode":
            mode = args[i + 1]
        if a == "--ratio":
            ratio = float(args[i + 1])
        if a == "--risque":   # compte « risque fort » : vise ce % du compte par trade, plafond 25 % au-dessus
            risque = float(args[i + 1]) / 100
            risque_max, fort = risque * 1.25, True
    try:
        etat = json.load(open(chemin))
    except FileNotFoundError:
        etat = {"capital_depart": 100.0, "capital": 100.0, "positions": [], "historique": [], "analyses": [], "courbe": []}

    maintenant = dt.datetime.now(dt.timezone.utc)
    iso = maintenant.isoformat(timespec="minutes")
    rouges, err_cal = calendrier(maintenant)
    donnees = {}
    for code, m in MARCHES.items():
        donnees[code] = {"j": bougies(m["yahoo"], "1d", "1y"), "h1": bougies(m["yahoo"], "60m", "60d")}
        donnees[code]["h4"] = en_h4(donnees[code]["h1"])
    eurusd = donnees["EURUSD"]["h1"][-1]["c"]

    # 1. Suivre les positions ouvertes : stop ou objectif touché ?
    for pos in [p for p in etat["positions"]]:
        for b in donnees[pos["marche"]]["h1"]:
            if b["t"] <= pos["t_entree"]:
                continue
            achat = pos["sens"] == "ACHAT"
            f = FRAIS[pos["marche"]]
            reel = pos.get("reel")
            sp = f["spread"] if reel else 0.0   # une vente se referme au prix d'achat (prix + spread)
            bas, haut, ouv = (b["l"], b["h"], b["o"]) if achat else (b["l"] + sp, b["h"] + sp, b["o"] + sp)
            stop = bas <= pos["stop"] if achat else haut >= pos["stop"]
            cible = haut >= pos["objectif"] if achat else bas <= pos["objectif"]
            if stop or cible:
                quand = dt.datetime.fromtimestamp(b["t"], dt.timezone.utc).isoformat(timespec="minutes")
                if stop:  # les deux dans la même bougie : on compte le stop
                    prix = pos["stop"]
                    if reel:  # trou de cotation : sortie au prix d'ouverture s'il est pire, plus le glissement
                        prix = min(prix, ouv) - f["glissement"] if achat else max(prix, ouv) + f["glissement"]
                else:
                    prix = pos["objectif"]
                nuits = int((b["t"] - pos["t_entree"]) // 86400) if reel else 0
                frais = pos["unites"] * f["nuit"] * nuits
                etat["capital"] = round(etat["capital"] + fermer(pos, prix, "Stop touché" if stop else "Objectif atteint", quand, eurusd, frais), 2)
                etat["positions"].remove(pos)
                etat["historique"].append(pos)
                break

    # 2. Analyse de chaque marché
    for code, m in MARCHES.items():
        d = donnees[code]
        tj, _, _ = tendance(d["j"])
        t4, h4_hauts, h4_bas = tendance(d["h4"])
        t1, h1_hauts, h1_bas = tendance(d["h1"])
        prix = d["h1"][-1]["c"]
        raisons = []
        sens = None
        sens, pourquoi, type_stop = signal(mode, d, tj, t4, t1)
        if not sens:
            raisons.append(pourquoi)
        alerte = None
        if rouges is None:
            raisons.append("Calendrier économique indisponible.")
        else:
            for e in rouges:
                if e["devise"] not in m["devises"]:
                    continue
                ecart = (e["quand"] - maintenant).total_seconds() / 60
                if abs(ecart) <= FENETRE_MIN:
                    raisons.append(f"Annonce importante trop proche : {e['titre']} ({e['devise']}).")
                if 0 <= ecart <= 36 * 60 and any(k in e["titre"] for k in MAJEURES) and e["devise"] == "USD":
                    alerte = f"{e['titre']} le {e['quand'].strftime('%d/%m à %H:%M')} UTC"
        if code in vetos:
            raisons.append(vetos[code])
        # Plusieurs trades en même temps (Tony, 18/11) : au plus MAX_PAR_MARCHE par marché,
        # au moins ECART_H heures entre deux ouvertures sur le même marché, et risque total ouvert limité.
        sur_marche = [p for p in etat["positions"] if p["marche"] == code]
        if len(etat["positions"]) >= MAX_OUVERTS:
            raisons.append(f"Déjà {MAX_OUVERTS} trades ouverts sur ce compte.")
        elif len(sur_marche) >= MAX_PAR_MARCHE:
            raisons.append(f"Déjà {MAX_PAR_MARCHE} trades ouverts sur ce marché.")
        elif sur_marche and d["h1"][-1]["t"] - max(p["t_entree"] for p in sur_marche) < ECART_H * 3600:
            raisons.append(f"Un trade a été ouvert sur ce marché il y a moins de {ECART_H} h.")
        if etat["capital"] <= 0:
            raisons.append("Compte vide : il a perdu ses 100 €. Il sera supprimé (avec l'accord de Tony).")
        if fort and etat["capital"] < 0.5 * etat.get("capital_depart", 100.0):
            raisons.append("Compte en pause : il a perdu la moitié de sa mise de départ.")
        plan = None
        if sens and not raisons:
            f = FRAIS[code]
            entree = prix + f["spread"] if sens == "ACHAT" else prix   # un achat se paie au prix d'achat (prix + spread)
            stop = calcul_stop(type_stop, sens, entree, d, h4_hauts, h4_bas, h1_hauts, h1_bas)
            dist = abs(entree - stop) if stop else 0
            if not stop or dist <= 0 or (sens == "ACHAT" and stop >= entree) or (sens == "VENTE" and stop <= entree):
                raisons.append("Impossible de placer un stop logique.")
            elif dist / prix > 0.03:
                raisons.append("Stop trop loin du prix (plus de 3 %).")
            else:
                objectif = entree + ratio * dist if sens == "ACHAT" else entree - ratio * dist
                # Taille (Tony, 19/11) : environ MARGE_TRADE € de garantie par trade, levier légal européen (30 EUR/USD, 20 or).
                ideal = MARGE_TRADE * eurusd * f["levier"] / prix
                unites = max(f["pas"], int(round(ideal / f["pas"])) * f["pas"])   # arrondi à la taille du courtier
                marge_prise = sum(p.get("marge", 0) for p in etat["positions"])
                risque_eur = round(unites * dist / eurusd, 2)
                marge = round(unites * prix / f["levier"] / eurusd, 2)
                risque_ouvert = sum(p.get("risque", 0) for p in etat["positions"])
                if risque_eur > etat["capital"] * RISQUE_MAX_TRADE:
                    raisons.append(f"Stop trop loin : ce trade risquerait {risque_eur} € (plus de {round(RISQUE_MAX_TRADE * 100)} % du compte).")
                elif risque_ouvert + risque_eur > etat["capital"] * RISQUE_TOTAL:
                    raisons.append(f"Trop de risque déjà en jeu : {round(risque_ouvert, 2)} € sur les trades ouverts (maximum {round(RISQUE_TOTAL * 100)} % du compte au total).")
                elif marge + marge_prise > etat["capital"]:
                    raisons.append(f"Compte trop petit : le courtier demanderait {marge} € de garantie pour cette position.")
                else:
                    r = m["decimales"]
                    plan = {"marche": code, "nom": m["nom"], "sens": sens, "entree": round(entree, r), "stop": round(stop, r),
                            "objectif": round(objectif, r), "unites": unites, "risque": risque_eur, "marge": marge, "reel": True,
                            "ouvert_le": iso, "t_entree": d["h1"][-1]["t"]}
                    etat["positions"].append(plan)
        verdict = "TRADE" if plan else "PAS DE TRADE"
        etat["analyses"].append({"quand": iso, "marche": code, "nom": m["nom"], "prix": round(prix, m["decimales"]),
                                 "jour": tj, "h4": t4, "h1": t1, "verdict": verdict,
                                 "sens": plan["sens"] if plan else None, "raisons": raisons, "alerte": alerte})

    # 3. Valeur du compte (positions ouvertes comprises) et historique
    latent = 0.0
    for p in etat["positions"]:
        s = 1 if p["sens"] == "ACHAT" else -1
        c = donnees[p["marche"]]["h1"][-1]["c"]
        if s == -1 and p.get("reel"):
            c += FRAIS[p["marche"]]["spread"]
        latent += p["unites"] * (c - p["entree"]) * s / eurusd
    etat["valeur"] = round(etat["capital"] + latent, 2)
    etat["courbe"].append({"quand": iso, "valeur": etat["valeur"]})
    etat["analyses"] = etat["analyses"][-60:]
    if news:  # sans --news (contrôle léger), on garde le dernier résumé
        etat["news"] = news
    etat.setdefault("news", "")
    etat["methode"] = mode
    etat["ratio"] = ratio
    etat["risque_vise"] = round(risque * 100, 1)
    etat["conditions"] = "réelles"
    etat["mis_a_jour"] = iso
    etat["erreur_calendrier"] = err_cal
    json.dump(etat, open(chemin, "w"), ensure_ascii=False, indent=1)
    for a in etat["analyses"][-len(MARCHES):]:
        print(a["nom"], a["prix"], a["jour"], a["h4"], a["h1"], "->", a["verdict"], a["sens"] or "", "|", " ".join(a["raisons"]))
    print("Valeur du compte :", etat["valeur"], "€")


if __name__ == "__main__":
    main()
