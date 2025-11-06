# Instructions de déploiement - Corrections Tarifs Logistiques

## Modifications effectuées

### 1. Fichiers modifiés
- `api/views.py` : Ajout de permissions AllowAny pour les endpoints de lecture des tarifs logistiques
- `api/management/commands/seed_data.py` : Ajout de l'initialisation automatique des tarifs logistiques et taux de change

### 2. Endpoints modifiés
- **GET** `/api/logistics-rates/all_rates/` : Maintenant accessible sans authentification
- **GET** `/api/exchange-rates/current/` : Maintenant accessible sans authentification
- **PATCH** `/api/logistics-rates/{id}/` : Nécessite toujours l'authentification (pour la sécurité)
- **POST** `/api/exchange-rates/` : Nécessite toujours l'authentification (pour la sécurité)

## Déploiement sur le serveur de production

### Étape 1 : Se connecter au serveur
```bash
ssh user@api.kotoafrica.com
# Ou utilisez votre méthode habituelle de connexion SSH
```

### Étape 2 : Naviguer vers le dossier du projet
```bash
cd /path/to/koto_africa_backend
# Remplacez par le chemin réel de votre projet
```

### Étape 3 : Sauvegarder les fichiers actuels (recommandé)
```bash
cp api/views.py api/views.py.backup
cp api/management/commands/seed_data.py api/management/commands/seed_data.py.backup
```

### Étape 4 : Pull les dernières modifications
```bash
git pull origin main
# Ou la branche appropriée (cedric, master, etc.)
```

### Étape 5 : Vérifier les modifications
```bash
git diff HEAD~1 api/views.py
```

Vous devriez voir les modifications suivantes dans `api/views.py` :
- Ligne 1106-1107 : `if self.action in ['list', 'retrieve', 'all_rates']:` et `permission_classes = [AllowAny]`
- Ligne 1112 : `@action(detail=False, methods=['get'], permission_classes=[AllowAny])`
- Ligne 1141-1142 : `if self.action in ['list', 'retrieve', 'current']:` et `permission_classes = [AllowAny]`
- Ligne 1147 : `@action(detail=False, methods=['get'], permission_classes=[AllowAny])`

### Étape 6 : Exécuter les migrations (si nécessaire)
```bash
python manage.py migrate
```

### Étape 7 : Initialiser les tarifs logistiques (si première fois)
```bash
python manage.py seed_data
```

### Étape 8 : Redémarrer le serveur
Selon votre configuration, utilisez une des commandes suivantes :

**Pour Gunicorn avec systemd :**
```bash
sudo systemctl restart gunicorn
# ou
sudo systemctl restart koto_africa
```

**Pour Gunicorn avec supervisor :**
```bash
sudo supervisorctl restart koto_africa
```

**Pour uWSGI :**
```bash
sudo systemctl restart uwsgi
```

**Si vous utilisez un script de démarrage personnalisé :**
```bash
./restart_server.sh
```

### Étape 9 : Vérifier que le serveur fonctionne
```bash
# Test 1 : Vérifier que l'API répond
curl https://api.kotoafrica.com/api/logistics-rates/all_rates/

# Test 2 : Vérifier le format JSON
curl https://api.kotoafrica.com/api/logistics-rates/all_rates/ | python -m json.tool
```

**Résultat attendu :**
```json
{
  "rates": [
    {
      "id": 1,
      "shipping_method": "air_rapide",
      "shipping_method_display": "Aérien Rapide",
      "rate_per_kg": "17000.00",
      "rate_per_m3": null,
      "min_days": 10,
      "max_days": 17,
      "is_active": true,
      ...
    },
    ...
  ],
  "usd_to_fcfa": 661.28
}
```

### Étape 10 : Tester depuis le frontend
1. Ouvrir l'interface admin : http://localhost:5174/admin
2. Se connecter avec vos identifiants admin
3. Cliquer sur l'onglet "Logistique"
4. Vérifier que les tarifs se chargent correctement

## Dépannage

### Erreur 401 Unauthorized persistante
Si vous obtenez toujours une erreur 401, vérifiez :
1. Que le fichier `api/views.py` a bien été modifié sur le serveur
2. Que le serveur Django a bien été redémarré
3. Que le cache nginx n'est pas activé pour ces endpoints

**Solution :** Vider le cache nginx
```bash
sudo systemctl reload nginx
```

### Erreur 404 Not Found
L'endpoint n'existe pas. Vérifiez :
1. Que `api/urls.py` contient bien `router.register(r'logistics-rates', LogisticsRateViewSet)`
2. Que les migrations sont à jour

### Les modifications ne sont pas visibles
1. Vérifier que vous êtes sur la bonne branche : `git branch`
2. Forcer le rechargement : `git reset --hard origin/main`
3. Redémarrer le serveur avec force : `sudo systemctl restart gunicorn --force`

### Base de données vide (pas de tarifs)
Exécuter la commande seed_data :
```bash
python manage.py seed_data
```

## Contact
En cas de problème, contactez l'équipe de développement ou consultez les logs :
```bash
# Logs Gunicorn
sudo journalctl -u gunicorn -f

# Logs nginx
sudo tail -f /var/log/nginx/error.log
sudo tail -f /var/log/nginx/access.log

# Logs Django (si configuré)
tail -f /path/to/django.log
```
