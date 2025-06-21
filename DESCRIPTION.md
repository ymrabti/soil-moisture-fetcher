## 🛰️ **Projet de Suivi Automatisé de l'Humidité des Sols**

### 🎯 Objectif

Mettre en place un système **automatisé et cartographique** qui :

* Mesure l’humidité du sol dans une **zone d’intérêt (ZOI)**.
* Stocke les données jour après jour dans une base de données.
* Génère des **cartes** et envoie des **notifications** (email + webhook) en cas de nouvelles données.
* S’intègre dans une infrastructure **Dockerisée**, réutilisable et facile à maintenir.

---

### 📌 Pourquoi mesurer l’humidité des sols ?

* Pour détecter les zones sèches ou irriguées.
* Pour **suivre l'impact des pluies ou des arrosages**.
* Pour une **gestion plus efficace des ressources agricoles et environnementales**.

---

## 🔍 **Sources de données satellitaires utilisées**

| Critère                     | Sentinel-1 (COPERNICUS/S1\_GRD)               | SMAP (NASA/SMAP/SPL4SMGP/007)                      |
| --------------------------- | --------------------------------------------- | -------------------------------------------------- |
| **Agence spatiale**         | ESA (Agence Spatiale Européenne)              | NASA (États-Unis)                                  |
| **Capteur**                 | Radar à synthèse d’ouverture (SAR)            | Radiomètre + Modèle terrestre                      |
| **Type d'humidité mesurée** | Signal radar sensible à l'humidité de surface | Humidité **quantifiée** : surface, racines, profil |
| **Résolution spatiale**     | Haute (\~10 m)                                | Moyenne (\~9 km)                                   |
| **Fréquence temporelle**    | Très fréquente (tous les 6 à 12 jours)        | Toutes les 3 heures (produit L4)                   |
| **Précision des valeurs**   | Relative (niveau de réflectance en dB)        | Absolue (valeurs de teneur en eau volumique)       |
| **Usage recommandé**        | Cartographie fine, surveillance locale        | Analyse régionale ou globale                       |
| **Couverture nuageuse**     | Fonctionne même par temps nuageux (radar)     | Oui                                                |
| **Disponibilité sur GEE**   | Oui                                           | Oui                                                |

---

### 🗺️ Fonctionnement global du système

1. **Connexion à Earth Engine** (plateforme de Google pour données satellites).
2. **Sélection d'une zone d'étude** (ZOI) à l’aide d’un polygone.
3. **Téléchargement automatique des données** Sentinel-1 ou SMAP.
4. **Extraction des moyennes d'humidité** sur la ZOI.
5. **Enregistrement des valeurs dans une base PostgreSQL** (Docker).
6. **Export cartographique** des images (GeoTIFF ou cartes JPEG).
7. **Notification email & webhook** quand des données nouvelles sont disponibles.

---

### 🎨 Résultat visuel

* Cartes en **niveau de gris** ou **couleur** représentant l’humidité.
* Légendes ajoutées automatiquement.
* Données datées et archivées.

---

### 🛠️ Infrastructure technique (résumé)

* 📦 **Docker** pour tout automatiser (tâche journalière, API, base de données).
* 🐘 **PostgreSQL** pour stocker les résultats.
* ✉️ **Email + Webhook** pour notifier les utilisateurs ou applications.
* 🧠 **Script Python** orchestrant tout.

---

### 🧾 Exemple d’une donnée stockée

```json
{
  "date": "2025-06-15",
  "vv_dB": -15.78,
  "description": "5 – Sol humide : Irrigation récente ou après pluie"
}
```

---

### 👨‍💼 À qui s’adresse ce projet ?

* **Collectivités locales** (gestion espaces verts, arrosage urbain)
* **Agriculteurs / Coopératives**
* **Chercheurs** en environnement
* **Services SIG** souhaitant intégrer la donnée sol dans leur workflow

---
