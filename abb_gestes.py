"""
Pilotage d'un bras ABB (RoboDK) par gestes de la main - MediaPipe + OpenCV.

Installation :  pip install opencv-python mediapipe robodk numpy
Prérequis    :  RoboDK ouvert avec une station contenant un robot ABB
                (ex. "ABB IRB 120-3/0.6"). Adaptez ROBOT_NAME si besoin.

Gestes (une seule main, paume vers la caméra) :
    1 doigt (index)        -> monter      (Z+)
    2 doigts               -> descendre   (Z-)
    3 doigts               -> droite      (Y-)
    4 doigts               -> gauche      (Y+)
    Poing                  -> fermer la pince
    Main ouverte (5)       -> ouvrir la pince  (+ arrêt des mouvements)
    Pouce seul             -> retour position Home
    Touche 'q'             -> quitter
"""
import threading
import time
from collections import deque

import cv2
import mediapipe as mp
import numpy as np
from robodk import robolink

# ----------------------------- CONFIGURATION -----------------------------
ROBOT_NAME = "ABB IRB 120-3/0.6"   # nom exact dans l'arbre de la station RoboDK
STEP_MM = 20                       # pas de déplacement par commande (mm)
SPEED_MM_S = 150                   # vitesse linéaire max (mm/s)
STABLE_FRAMES = 6                  # nb d'images identiques avant validation
COMMAND_PERIOD = 0.4               # délai mini entre deux commandes (s)
GRIPPER_DO = None                  # sortie digitale de la pince (None = ignoré)
RANGE_MM = 150                     # amplitude autorisée autour de la pose de départ

# Limites de l'espace de travail (mm, dans le repère de base du robot)
LIMITS = {"x": (150, 450), "y": (-300, 300), "z": (80, 450)}

# ------------------------------ GESTES -----------------------------------
mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils


def dist(a, b):
    return np.hypot(a.x - b.x, a.y - b.y)


def fingers_state(lm):
    """Retourne [pouce, index, majeur, annulaire, auriculaire] (1 = étendu).
    Critère indépendant de l'orientation : la pointe est plus loin du
    poignet que l'articulation PIP."""
    wrist = lm[0]
    state = []
    # Pouce : pointe plus loin de la base de l'auriculaire que l'IP
    state.append(int(dist(lm[4], lm[17]) > dist(lm[3], lm[17]) * 1.1))
    for tip, pip in [(8, 6), (12, 10), (16, 14), (20, 18)]:
        state.append(int(dist(lm[tip], wrist) > dist(lm[pip], wrist) * 1.05))
    return state


def classify(lm):
    t, i, m, r, p = fingers_state(lm)
    n = i + m + r + p
    if n == 0 and t == 0:
        return "POING"
    if n == 0 and t == 1:
        return "POUCE"
    if n == 4 and t == 1:
        return "OUVERTE"
    if n == 1 and i == 1:
        return "UN"
    if n == 2 and i == 1 and m == 1:
        return "DEUX"
    if n == 3 and i == 1 and m == 1 and r == 1:
        return "TROIS"
    if n == 4 and t == 0:
        return "QUATRE"
    return None


# --------------------------- CONTRÔLE ROBOT ------------------------------
class RobotController:
    def __init__(self):
        self.rdk = robolink.Robolink()
        self.robot = self.rdk.Item(ROBOT_NAME, robolink.ITEM_TYPE_ROBOT)
        if not self.robot.Valid():
            raise RuntimeError(f"Robot '{ROBOT_NAME}' introuvable dans RoboDK")
        self.robot.setSpeed(SPEED_MM_S)
        self.home_joints = self.robot.Joints()
        x0, y0, z0 = self.robot.Pose().Pos()
        self.limits = {"x": (x0 - RANGE_MM, x0 + RANGE_MM),
                       "y": (y0 - RANGE_MM, y0 + RANGE_MM),
                       "z": (z0 - RANGE_MM, z0 + RANGE_MM)}
        print(f"Pose de départ : X={x0:.0f} Y={y0:.0f} Z={z0:.0f} mm")
        print("Limites :", self.limits)
        self.cmd = None
        self.lock = threading.Lock()
        self.running = True
        self.last_gripper = None
        threading.Thread(target=self._worker, daemon=True).start()

    def send(self, command):
        with self.lock:
            self.cmd = command

    def _pop(self):
        with self.lock:
            c, self.cmd = self.cmd, None
        return c

    def _worker(self):
        """Exécute les commandes dans un thread pour ne pas bloquer la vidéo."""
        deltas = {"UN": (0, 0, STEP_MM), "DEUX": (0, 0, -STEP_MM),
                  "TROIS": (0, -STEP_MM, 0), "QUATRE": (0, STEP_MM, 0)}
        while self.running:
            c = self._pop()
            if c is None:
                time.sleep(0.02)
                continue
            try:
                if c in deltas:
                    self._move_rel(deltas[c])
                elif c == "POUCE":
                    self.robot.MoveJ(self.home_joints)
                elif c == "POING":
                    self._gripper(1)
                elif c == "OUVERTE":
                    self._gripper(0)
            except Exception as e:  # ne jamais planter le thread
                print("Erreur robot :", e)

    def _move_rel(self, d):
        pose = self.robot.Pose()
        x, y, z = pose.Pos()
        nx, ny, nz = x + d[0], y + d[1], z + d[2]
        L = self.limits
        if not (L["x"][0] <= nx <= L["x"][1]
                and L["y"][0] <= ny <= L["y"][1]
                and L["z"][0] <= nz <= L["z"][1]):
            print("Hors limites : mouvement refusé")
            return
        pose.setPos([nx, ny, nz])
        if len(self.robot.SolveIK(pose).list()) == 0:
            print("Pose inatteignable (IK) : mouvement refusé")
            return
        self.robot.MoveL(pose)

    def _gripper(self, value):
        if GRIPPER_DO and value != self.last_gripper:
            self.robot.setDO(GRIPPER_DO, value)
            self.last_gripper = value
            print("Pince :", "fermée" if value else "ouverte")

    def stop(self):
        self.running = False


# ------------------------------ PRINCIPAL --------------------------------
def main():
    ctrl = RobotController()
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    history = deque(maxlen=STABLE_FRAMES)
    last_sent = 0.0
    hands = mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.7,
                           min_tracking_confidence=0.6)

    while cap.isOpened():
        ok, frame = cap.read()
        if not ok:
            break
        frame = cv2.flip(frame, 1)
        res = hands.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))

        gesture = None
        if res.multi_hand_landmarks:
            hl = res.multi_hand_landmarks[0]
            mp_draw.draw_landmarks(frame, hl, mp_hands.HAND_CONNECTIONS)
            gesture = classify(hl.landmark)
        history.append(gesture)

        # Validation : geste identique sur STABLE_FRAMES images consécutives
        stable = (len(history) == STABLE_FRAMES and gesture is not None
                  and all(g == gesture for g in history))
        if stable and time.time() - last_sent > COMMAND_PERIOD:
            ctrl.send(gesture)
            last_sent = time.time()

        cv2.putText(frame, f"Geste: {gesture} {'[OK]' if stable else ''}",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        cv2.imshow("Pilotage ABB par gestes", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    ctrl.stop()
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
