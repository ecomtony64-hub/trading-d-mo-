# Règles des comptes démo (décidées par Tony)

- Chaque méthode gère son propre porte-monnaie de 100 € (aucun argent partagé entre comptes). 100 comptes depuis le 18/11.
- Taille des trades (19/11) : environ 30 € de garantie par trade, avec le levier légal européen (30 sur EUR/USD, 20 sur l'or).
  Sur EUR/USD ça fait 1 000 unités (la plus petite taille du courtier, 33 € de garantie) : un trade risque en général 2 à 6 € et vise le double.
  L'or reste trop cher pour 100 € (1 once = plus de 100 € de garantie).
- 15 trades ouverts au plus en même temps par compte (20/11, avant 2). En pratique la garantie limite à environ 3 trades en même temps avec 100 € (33 € par trade), 4 h minimum entre deux ouvertures sur le même marché,
  risque total ouvert ≤ 20 % du compte, refus si un trade risque plus de 15 % du compte.
- 5 comptes « risque max » (19/11) : mêmes méthodes que les 5 meilleurs du moment (Tendance 4 h + 1 h, Tendance 4 h, Repli dans la tendance, Moyennes 1 h, Tendance 4 h stop serré), 100 € chacun, taille fixe de 2 000 unités d'EUR/USD (90 % de 100 € en garantie), 1 trade à la fois, sans aucun blocage de risque ni de garantie : ils continuent même sous 0 € (Tony, 19/11), le solde réel est affiché. Ils ne « meurent » pas (Tony, 19/11) : ils restent affichés et tradent tant que leur argent le permet.
- Un compte qui perd ses 100 € est supprimé (18/11). Rien n'est supprimé sans l'accord de Tony : la liste est donnée au bilan du vendredi 18h15 (Paris).
- Les comptes « risque fort » se mettent en pause à 50 € (moitié de la mise).
- Règle des 150 € en fin de semaine : annulée par Tony le 18/11.

## Comptes or (Tony, 24/11)

- 100 comptes qui ne tradent que l'or : 25 méthodes x 4 niveaux de risque. Chacun a ses propres 100 € fictifs (rien de partagé).
- 4 trades ouverts au plus en même temps par compte, 1 h minimum entre deux ouvertures.
- Taille : par pas de 0,01 once (il faut un courtier qui accepte les micro-lots d'or), levier 20, calculée pour risquer :
  - « prudent » (or-p-...) : 1 % du compte par trade ;
  - « normal » (or-...) : 2 % du compte par trade ;
  - « risque fort » (or-f-...) : 5 % du compte par trade, pause sous 50 € ;
  - « risque max » (or-max-...) : 10 € par trade (10 % des 100 € de départ), sans blocage de risque ni de garantie, continue même sous 0 € (comme les comptes risque max EUR/USD). Un vrai courtier refuserait certains de ces trades faute de garantie.
- Prudent/normal/fort : refus si le risque total ouvert dépasse 20 % du compte, si un trade risque plus de 15 % du compte, ou si la garantie manque.
- Méthodes : les 15 meilleures des 100 méthodes sur 2 ans d'or (test du 24/11, frais compris ; l'or a beaucoup monté sur cette période, donc les méthodes qui suivent la tendance en profitent) + 10 méthodes maison de l'EUR/USD pour comparer. Liste et réglages dans or/activer.py.
- Les comptes EUR/USD ne changent pas.

## Tri et autres marchés (Tony, 26/11)

- Tony a gardé seulement les comptes à 120 € ou plus (19 comptes, presque tous sur l'or). Les 188 autres sont rangés dans supprimes-26-11/ (rien n'est perdu).
- Les 5 meilleures méthodes sont copiées sur 31 autres marchés : Élan 24 h, Tendance 4 h stop serré, Cassure 20 bougies 1 h, Cassure 20 + moyenne 200 1 h, Moyennes 1 h.
  Marchés : 14 paires de devises (GBP/USD, USD/JPY, AUD/USD, NZD/USD, USD/CAD, USD/CHF, EUR/GBP, EUR/JPY, EUR/CHF, EUR/AUD, GBP/JPY, AUD/JPY, GBP/AUD, CHF/JPY),
  8 indices (S&P 500, Nasdaq 100, Dow Jones, DAX, CAC 40, Euro Stoxx 50, FTSE 100, Nikkei), 5 matières premières (argent, pétrole WTI et Brent, gaz, cuivre), 4 cryptos (Bitcoin, Ethereum, Solana, XRP).
- Chaque copie : 100 € fictifs à elle, un seul marché, environ 30 € de garantie par trade avec le levier légal européen (30 grandes paires, 20 autres paires et indices, 10 matières premières, 2 crypto), pause sous 50 €, mêmes limites que les comptes EUR/USD (stop ≤ 15 % du compte, risque total ≤ 20 %, 4 h entre deux ouvertures).
- Les gains et pertes sont convertis en euros. Frais réalistes (écart, glissement, nuits) réglés dans AUTRES de moteur.py.

## Conditions proches du réel (26/11)
- Prix relus toutes les 4-5 min ; stops et objectifs suivis sur des bougies de 5 minutes, à partir de l'heure exacte d'ouverture.
- Entrée au marché : spread payé + petit glissement contre nous.
- Spread multiplié par 3 entre 21 h et 23 h UTC (heure creuse), sauf crypto.
- Stop : si le prix saute par-dessus, sortie au prix réel du saut, plus un glissement.
- Frais de nuit : à chaque passage à 22 h UTC ; triple le mercredi (forex, or, matières premières), le vendredi (indices) ; crypto tous les jours. Ils sont déduits aussi de la valeur des trades encore ouverts.
- Limites : prix Yahoo gratuits (l'or et le pétrole peuvent avoir ~10 min de retard), pas de vrai carnet d'ordres. 100 % réel = seulement chez un vrai courtier (compte démo).

## Bots or du classement (Tony, 28/11 soir)
- 3 comptes « podium » (classement en 4 points) : or-bot-londres (stop 5 / objectif 1), or-bot-cassure48 (6 / 2), or-bot-cassure24 (1 / 4).
  Risque 2 % du compte par trade, par pas de 0,01 once, 1 trade à la fois, 2 h entre deux ouvertures, stop jusqu'à 6 % du prix.
- 3 comptes « 100 € par mois » (nouvelle règle de Tony : les 100 € sont le budget d'un mois, on accepte de les risquer) :
  or-tout-londres-achat (8 / 0,75, achats seulement), or-tout-londres (5 / 1), or-tout-cassure48 (6 / 2).
  Taille = la plus grosse que la garantie permet (levier 20) : tout le compte en jeu. 100 € remis au début de chaque mois
  (dès qu'aucun trade n'est ouvert) ; le résultat de chaque mois est gardé dans « bilans_mois ».
- Code : bots-or/bots.py (mêmes règles que le test sur 2 ans). Stop et objectif en « agitation » = taille moyenne d'une bougie d'1 h.
