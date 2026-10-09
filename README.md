# Shielded Nakas — tableau de marché

Tableau de bord statique, en français, pour la collection Bitcoin Ordinals **Shielded Nakas** (ord-dropz). La page montre les bougies de prix (1h / 4h / 1j), la médiane des ventes, le floor, le volume, le nombre de ventes et le RSI(14).

**Site :** https://3ajfr.github.io/shielded-nakas-dashboard/

Heures en Europe/Paris. Les prix sont en BTC, avec l’équivalent USD. Filtres : Tous, Legendary+Epic, sub100, sub1k. Échelle linéaire ou log. La page se recharge toute seule toutes les 5 minutes.

## Mise à jour automatique

Le workflow [`.github/workflows/pages.yml`](.github/workflows/pages.yml) reconstruit la page et la publie sur GitHub Pages :

- toutes les 10 minutes (`cron`)
- à chaque push sur `main`
- à la demande (`workflow_dispatch`)

Aucun serveur, aucune clé d’API, aucun secret. Les endpoints sont publics et en lecture seule.

À chaque exécution, le floor live est ajouté à [`data/floor_history.csv`](data/floor_history.csv), puis ce fichier est commité dans le dépôt pour que l’historique réel s’accumule. Avant le premier point enregistré, la courbe en pointillés est une **approximation** : la vente la plus basse de chaque heure, en excluant les ventes sous 5 000 sats. Ce n’est pas un floor de listings.

## Réglage à faire une fois

GitHub Pages n’est pas activé sur ce dépôt, et le `GITHUB_TOKEN` du workflow ne peut pas le créer (`enablement: true` exige un jeton d’administration, que ce dépôt ne stocke pas).

**Settings → Pages → Build and deployment → Source → GitHub Actions**

Ensuite, le workflow sur `main` publie le site. Aucun secret à ajouter. Les permissions dont le workflow a besoin (`contents: write`, `pages: write`, `id-token: write`) sont déjà déclarées dans le fichier : il n’est pas nécessaire de passer « Workflow permissions » en lecture-écriture dans Settings → Actions.

Si le dépôt reste sans activité pendant 60 jours, GitHub coupe les planifications. Un push ou un lancement manuel les réactive.

## Build local

Python 3.11 ou plus récent. Bibliothèque standard seulement (`zoneinfo` a besoin des fuseaux du système ; Ubuntu les fournit via `tzdata`).

```bash
python3 build_dashboard.py
```

Cela régénère `site/index.html` (non versionné) et ajoute une ligne à `data/floor_history.csv`. Ouvrir `site/index.html` dans un navigateur. Plotly est chargé depuis le CDN.

## Sources

- Collection, inscriptions (traits, rareté) et ventes : `https://backend-secondary-market-production.up.railway.app/api/secondary`
- Listings live : `https://shielded-mint-server-production.up.railway.app/api/shielded/listings`
- BTC/USD : mempool.space, repli CoinGecko

Les listings absents du flux live, ou en cours d’annulation, sont exclus du floor.

Pas un conseil financier.
