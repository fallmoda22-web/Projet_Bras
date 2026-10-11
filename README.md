# Projet_Bras
Pilotage d'un bras robotique ABB IRB 120 par gestes de la main : vision par ordinateur (MediaPipe + OpenCV) et simulation RoboDK en Python.
# 🤖 Pilotage d'un bras robotique ABB par gestes de la main

![Python](https://img.shields.io/badge/Python-3.10%20|%203.11-blue?logo=python&logoColor=white)
![MediaPipe](https://img.shields.io/badge/MediaPipe-0.10.14-orange)
![OpenCV](https://img.shields.io/badge/OpenCV-vision-green?logo=opencv&logoColor=white)
![RoboDK](https://img.shields.io/badge/RoboDK-simulation-red)
![License](https://img.shields.io/badge/license-MIT-lightgrey)

Contrôle d'un bras **ABB IRB 120**, simulé dans **RoboDK**, à partir des gestes de la main
captés par une simple webcam. MediaPipe Hands extrait 21 points de repère de la main,
interprétés par des règles géométriques pour reconnaître sept gestes (déplacements, pince, retour Home).

<!-- Ajoutez ici un GIF de démonstration :
![Démo](docs/demo.gif)
-->

## Sommaire

- [Fonctionnalités](#fonctionnalités)
- [Architecture](#architecture)
- [Structure du projet](#structure-du-projet)
- [Prérequis](#prérequis)
- [Installation](#installation)
- [Mise en place de RoboDK](#mise-en-place-de-robodk)
- [Utilisation](#utilisation)
- [Gestes reconnus](#gestes-reconnus)
- [Paramètres](#paramètres)
- [Dépannage](#dépannage)
- [Pistes d'amélioration](#pistes-damélioration)
- [Sécurité](#sécurité)
- [Licence](#licence)

## Fonctionnalités

- Détection de la main en temps réel (MediaPipe Hands, 21 landmarks)
- 7 gestes discrets : déplacements Z/Y, pince, retour Home
- Validation d'un geste sur plusieurs images consécutives (anti-bruit)
- Commandes robot dans un thread séparé : la vidéo reste fluide
- Sécurité : limites d'espace de travail calculées automatiquement et vérification de cinématique inverse (`SolveIK`)

## Architecture

```
Webcam ─► OpenCV ─► MediaPipe Hands ─► Reconnaissance de gestes
                                              │
                                   Validation (N images stables)
                                              │
                                    File de commandes (thread)
                                              │
                                   API Python RoboDK ─► Robot simulé
```

## Structure du projet

```
projet_bras/
├── src/
│   └── abb_gestes.py        # programme principal
├── scripts/                 # tests manuels
│   ├── test_camera.py       # webcam + MediaPipe
│      # pose de départ du robot
│   ├── lire_pose.py         # connexion RoboDK
│   └── test_mouvement.py    # mouvement de test
├── docs/                    # gestes, dépannage
├── station/                 # station RoboDK (.rdk)
├── requirements.txt
├── LICENSE
└── README.md
```

## Prérequis

- Windows, macOS ou Linux, avec une webcam
- Python 3.10 ou 3.11
- [RoboDK](https://robodk.com/download) (la version d'essai suffit pour la simulation)
- VS Code (recommandé)

## Installation

```bash
git clone https://github.com/<votre-compte>/projet_bras.git
cd projet_bras
python -m venv venv
venv\Scripts\activate          # Linux/Mac : source venv/bin/activate
pip install -r requirements.txt
```

> **PowerShell bloque l'activation ?**
> `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned`
> ou utilisez l'invite de commandes (CMD) avec `venv\Scripts\activate.bat`.

## Mise en place de RoboDK

1. Ouvrir RoboDK, puis la bibliothèque en ligne : **ABB > IRB 120-3/0.6 > Télécharger**.
2. Enregistrer la station dans `station/station_abb.rdk`.
3. Laisser RoboDK ouvert, en mode simulation.
4. Placer le robot en pose de travail :
   ```bash
   python scripts/pose_travail.py
   ```
   Les axes sont mis à θ = [0, 0, 0, 0, 90, 0] pour éviter la singularité de poignet.

## Utilisation

**1. Vérifications progressives**

```bash
python scripts/test_camera.py       # le squelette de la main s'affiche (q pour quitter)
python scripts/lire_pose.py         # Python communique avec RoboDK
python scripts/test_mouvement.py    # le robot monte de 2 cm
```

**2. Lancer le pilotage par gestes**

```bash
python src/abb_gestes.py
```

Placez la main à 40-60 cm de la caméra, paume vers l'objectif. Quand l'écran affiche
`[OK]`, le geste est validé et envoyé au robot. Appuyez sur **q** pour quitter.

## Gestes reconnus

| Geste | Action |
|---|---|
| 1 doigt (index) | Monter (Z+) |
| 2 doigts | Descendre (Z−) |
| 3 doigts | Droite (Y−) |
| 4 doigts | Gauche (Y+) |
| Poing | Fermer la pince |
| Main ouverte | Ouvrir la pince |
| Pouce seul | Retour Home |

## Paramètres

Modifiables en tête de `src/abb_gestes.py` :

| Paramètre | Rôle | Défaut |
|---|---|---|
| `ROBOT_NAME` | Nom du robot dans RoboDK | `ABB IRB 120-3/0.6` |
| `STEP_MM` | Pas par commande (mm) | 20 |
| `SPEED_MM_S` | Vitesse linéaire (mm/s) | 150 |
| `STABLE_FRAMES` | Images identiques pour valider un geste | 6 |
| `COMMAND_PERIOD` | Délai minimum entre deux commandes (s) | 0.4 |
| `RANGE_MM` | Amplitude autorisée autour de la pose de départ (mm) | 150 |
| `GRIPPER_DO` | Sortie digitale de la pince (`None` = désactivée) | `None` |

## Dépannage

| Problème | Solution |
|---|---|
| `mediapipe has no attribute 'solutions'` | `pip install mediapipe==0.10.14` |
| `FieldDescriptor ... 'label'` | `pip install "protobuf>=4.25.3,<5"` |
| Le bouton ▶ utilise le mauvais Python | Lancer depuis le terminal avec `(venv)` actif |
| `Robot introuvable` | Corriger `ROBOT_NAME` (nom exact dans l'arbre RoboDK) |
| `Pose inatteignable (IK)` | Relancer `scripts/pose_travail.py` ou réduire `STEP_MM` |
| Caméra noire | Essayer `VideoCapture(1)`, fermer Zoom/Teams |

Liste complète : [docs/depannage.md](docs/depannage.md)

## Pistes d'amélioration

- [ ] Axes X (avant/arrière) et rotation de l'outil
- [ ] Geste d'arrêt d'urgence
- [ ] Classifieur entraîné (MLP, LSTM) sur les landmarks
- [ ] Pick-and-place avec pince RoboDK
- [ ] Mesures : latence bout-en-bout, taux de reconnaissance, précision
- [ ] Contrôle continu par suivi de la position de la main
- [ ] Passage au robot réel après validation en simulation

## Sécurité

Validez toujours en simulation avant d'utiliser un robot réel. Réduisez la vitesse,
prévoyez un arrêt d'urgence matériel et gardez l'espace de travail dégagé.

## Licence

Distribué sous licence MIT. Voir [LICENSE](LICENSE).

## Auteur

Projet réalisé par **Moda Fall**, linkedin: www.linkedin.com/in/moda-fall-95a874344
