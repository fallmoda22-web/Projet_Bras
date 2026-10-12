# Hand-Gesture Control of a Robotic Arm (MediaPipe + RoboDK + Arduino UNO Q)

![Python](https://img.shields.io/badge/Python-3.10%20|%203.11-blue?logo=python&logoColor=white)
![MediaPipe](https://img.shields.io/badge/MediaPipe-0.10.14-orange)
![OpenCV](https://img.shields.io/badge/OpenCV-vision-green?logo=opencv&logoColor=white)
![RoboDK](https://img.shields.io/badge/RoboDK-simulation-red)
![Arduino](https://img.shields.io/badge/Arduino-UNO%20Q-00979D?logo=arduino&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-lightgrey)

Real-time control of a robotic arm with hand gestures captured by an ordinary webcam.
MediaPipe Hands extracts 21 hand landmarks, a rule-based classifier turns them into
gestures, and the resulting commands drive either:

1. a simulated **ABB IRB 120** in **RoboDK** (Cartesian control), or
2. a real **6-servo arm** (gripper included) through an **Arduino UNO Q** over Wi-Fi.

> 🇫🇷 A French version of this README is available in [README.md](README.md).

<!-- Add a demo GIF here:
![Demo](docs/demo.gif)
-->

## Project status

| Component | Status |
|---|---|
| Hand detection and gesture recognition | Implemented |
| ABB IRB 120 control in RoboDK (simulation) | Implemented |
| Wi-Fi pipeline to the Arduino UNO Q (PC, board Python, sketch) | Implemented; control logic checked with software tests |
| Validation on the physical arm | **Not yet done** (calibration procedure provided) |

Update this table as each part is validated on your setup.

## Contents

- [Features](#features)
- [Architecture](#architecture)
- [Repository structure](#repository-structure)
- [Requirements](#requirements)
- [Installation](#installation)
- [Mode A: RoboDK simulation](#mode-a-robodk-simulation)
- [Mode B: real arm with Arduino UNO Q](#mode-b-real-arm-with-arduino-uno-q)
- [Gestures](#gestures)
- [Safety design](#safety-design)
- [Configuration](#configuration)
- [Limitations](#limitations)
- [Roadmap](#roadmap)
- [Evaluation](#evaluation)
- [Troubleshooting](#troubleshooting)
- [License](#license)
- [Author](#author)

## Features

- Real-time hand tracking (MediaPipe Hands, 21 landmarks) on a standard webcam
- Rule-based finger-state classification, independent of hand orientation
- **Temporal validation**: a gesture is accepted only after several identical consecutive frames, which filters out noise
- Two control back-ends sharing the same vision front-end: RoboDK and Arduino UNO Q
- Non-blocking robot control (command thread / network messages), so the video stays smooth
- Safety mechanisms in both back-ends (see [Safety design](#safety-design))
- Calibration tool for the real arm

## Architecture

**Mode A: simulation**

```
Webcam -> OpenCV -> MediaPipe -> gesture classifier -> validation
       -> command thread -> RoboDK Python API -> ABB IRB 120 (simulated)
```

**Mode B: real arm**

```
PC:  Webcam -> MediaPipe -> gesture + mode -> action message (UDP, 20 Hz)
                                    |  Wi-Fi
Arduino UNO Q:  Python (Linux side) -> Arduino Bridge -> sketch (MCU)
                -> I2C -> PCA9685 -> 6 servos (gripper included)
```

The UNO Q has two processors: a Linux side running Python (network, control logic) and a
microcontroller side running the Arduino sketch (servo driver). They communicate through
the Arduino Bridge RPC.

## Repository structure

```
projet_bras/
├── src/
│   ├── abb_gestes.py        # Mode A: gesture control of the ABB arm in RoboDK
│   ├── pc_gestes_wifi.py    # Mode B: PC side (vision + UDP sender)
│   └── calibration.py       # Mode B: servo calibration tool (keyboard, no camera)
├── uno_q/
│   ├── python/main.py       # Mode B: board side, Linux (UDP receiver, control logic)
│   └── sketch/sketch.ino    # Mode B: board side, microcontroller (PCA9685 driver)
├── scripts/                 # Manual tests (camera, RoboDK connection, test move)
├── docs/                    # Guides (in French): gestures, troubleshooting, full UNO Q guide
├── station/                 # RoboDK station (.rdk)
├── requirements.txt
└── LICENSE
```

## Requirements

- Python 3.10 or 3.11 and a webcam
- **Mode A:** [RoboDK](https://robodk.com/download) (the trial version is enough for simulation)
- **Mode B:** Arduino UNO Q with Arduino App Lab, a 6-servo arm, a PCA9685 servo driver, and a
  dedicated 5-6 V servo power supply rated for several amps, plus a 470-1000 µF capacitor

## Installation

```bash
git clone https://github.com/<your-username>/projet_bras.git
cd projet_bras
python -m venv venv
venv\Scripts\activate          # Linux/Mac: source venv/bin/activate
python -m pip install --upgrade pip
```

Mode A (simulation):

```bash
pip install -r requirements.txt
```

Mode B only (no RoboDK needed):

```bash
pip install opencv-python mediapipe==0.10.14 "protobuf>=4.25.3,<5" "numpy<2"
```

> MediaPipe is pinned to 0.10.14 because recent releases removed the `mp.solutions` API used here.
> On Windows PowerShell, if the environment will not activate:
> `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned`

## Mode A: RoboDK simulation

1. In RoboDK, download **ABB IRB 120-3/0.6** from the online library and save the station in `station/`.
2. Keep RoboDK open, in simulation mode.
3. Put the arm in a working pose (avoids the wrist singularity):
   ```bash
   python scripts/pose_travail.py
   ```
   This sets the joints to [0, 0, 0, 0, 90, 0].
4. Check the pipeline step by step:
   ```bash
   python scripts/test_camera.py       # hand skeleton shown on screen
   python scripts/lire_pose.py         # Python can talk to RoboDK
   python scripts/test_mouvement.py    # the arm moves up by 2 cm
   ```
5. Run the gesture control:
   ```bash
   python src/abb_gestes.py
   ```

The workspace limits are computed automatically around the starting pose
(`RANGE_MM`, 150 mm by default). Each move is checked with `SolveIK` before it is sent.

## Mode B: real arm with Arduino UNO Q

> ⚠️ This mode drives real hardware. Follow the commissioning procedure in
> [docs/GUIDE_COMPLET_BRAS_UNO_Q.md](docs/GUIDE_COMPLET_BRAS_UNO_Q.md) (written in French):
> wiring, power supply, calibration, and safety. Keep a power switch on the servo supply
> within reach at all times.

Summary:

1. Wire the PCA9685 to the UNO Q (I2C, common ground) and power the servos from their own supply.
2. In Arduino App Lab, create an application and paste `uno_q/python/main.py` (Python part)
   and `uno_q/sketch/sketch.ino` (sketch part). Set a private `TOKEN`.
3. Note the board's IP address (`hostname -I`) and set `UNO_Q_IP` and the same `TOKEN` in
   `src/pc_gestes_wifi.py` and `src/calibration.py`.
4. Calibrate each servo and its limits:
   ```bash
   python src/calibration.py       # commands: "<channel> <angle>", "home", "stop", "q"
   ```
5. Run the gesture control:
   ```bash
   python src/pc_gestes_wifi.py    # q = quit, e = software emergency stop
   ```

Servo channels on the PCA9685: 0 base, 1 shoulder, 2 elbow, 3 wrist pitch, 4 wrist roll, 5 gripper.

## Gestures

One hand, palm facing the camera, 40-60 cm away.

### Mode A (ABB in RoboDK)

| Gesture | Action |
|---|---|
| 1 finger (index) | Move up (Z+) |
| 2 fingers | Move down (Z-) |
| 3 fingers | Move right (Y-) |
| 4 fingers | Move left (Y+) |
| Fist / open hand | Close / open gripper |
| Thumb only | Return to the starting pose |
| `q` | Quit |

### Mode B (real arm): three control modes

With seven basic gestures and six axes, the **shaka** gesture (thumb and pinky extended,
other fingers folded) cycles through three modes. The active mode is shown on screen.

| Gesture | Mode 1 | Mode 2 | Mode 3 |
|---|---|---|---|
| 1 finger | Base + | Elbow + | Wrist roll + |
| 2 fingers | Base - | Elbow - | Wrist roll - |
| 3 fingers | Shoulder + | Wrist pitch + | |
| 4 fingers | Shoulder - | Wrist pitch - | |

In every mode: **fist** closes the gripper, **open hand** opens it, **thumb only** returns
to the home pose (the gripper is excluded so a held object is not dropped).

While a gesture is held, the axis moves at a limited speed; when released, the arm stops.

## Safety design

| Mechanism | Mode A | Mode B |
|---|---|---|
| Temporal validation of gestures | yes | yes |
| Workspace / angle limits | automatic Cartesian box around the start pose | per-servo angle limits on both the board's Python and the sketch |
| Reachability check | `SolveIK` before each move | not applicable |
| Speed limiting | `SPEED_MM_S`, fixed step | `SPEED_DPS`, slower gripper |
| Connection loss | commands stop | **watchdog**: stop after 0.5 s without a message |
| Authentication | not applicable | shared **token**; messages without it are ignored |
| Start-up | not applicable | servos initialised one at a time |
| Emergency stop | `q` | `e` key / `stop` command (software) + **physical power switch** |

The token is a basic protection, not encryption. Do not expose the UDP port to the Internet;
use a VPN (e.g. WireGuard, Tailscale) for remote operation.

## Configuration

| Parameter | File | Role | Default |
|---|---|---|---|
| `ROBOT_NAME` | `src/abb_gestes.py` | Robot name in the RoboDK station | `ABB IRB 120-3/0.6` |
| `STEP_MM`, `SPEED_MM_S`, `RANGE_MM` | `src/abb_gestes.py` | Step, speed, workspace range (mm) | 20, 150, 150 |
| `STABLE_FRAMES` | both PC scripts | Identical frames needed to accept a gesture | 6 (A), 4 (B) |
| `UNO_Q_IP`, `UDP_PORT`, `TOKEN` | PC scripts, `main.py` | Network settings | to set |
| `SPEED_DPS`, `SPEED_OVERRIDE` | `uno_q/python/main.py` | Axis speed (deg/s) | 40, gripper 25 |
| `WATCHDOG_S` | `uno_q/python/main.py` | Stop delay without messages (s) | 0.5 |
| `SERVOS` | `uno_q/python/main.py` | (min, max, home) per channel | to calibrate |
| `ANGLE_MIN/MAX`, `US_MIN/US_MAX`, `I2C_BUS` | `uno_q/sketch/sketch.ino` | Limits, pulse range, I2C bus | to calibrate |

## Limitations

- Hand tracking depends on lighting and background; accuracy is lower with the hand at an angle.
- The gesture classifier is rule-based and handles a small, fixed vocabulary.
- Control is **discrete and per-axis** (no Cartesian target on the real arm, no inverse kinematics).
- The gripper has **no force or current feedback**; the closing limit must be calibrated per object.
- The Wi-Fi link adds latency; there is no video feedback from the robot side.
- Mode B has not yet been validated on the physical arm.

## Roadmap

- [ ] Validate and calibrate Mode B on the physical arm
- [ ] Continuous control: map hand position to joint angles
- [ ] Inverse kinematics for Cartesian control of the real arm
- [ ] Learned gesture classifier (MLP / LSTM on landmark sequences)
- [ ] Gripper current sensing (INA219) to detect grasp automatically
- [ ] Hardware emergency cut-off using the PCA9685 output-enable pin
- [ ] Camera on the robot side and secure remote operation over a VPN

## Evaluation

To be completed once the system is validated:

| Metric | How to measure | Result |
|---|---|---|
| End-to-end latency (gesture to motion) | Timestamped messages / video frame count | - |
| Gesture recognition rate | Confusion matrix over N repetitions per gesture | - |
| False-trigger rate | Count unintended commands per minute with a hand in view | - |
| Pick-and-place success | Successful grasp-and-place trials / attempts | - |

## Troubleshooting

| Problem | Solution |
|---|---|
| `mediapipe has no attribute 'solutions'` | `pip install mediapipe==0.10.14` |
| `protobuf` error (`label`, `GetPrototype`) | `pip install "protobuf>=4.25.3,<5"` |
| Wrong Python used by the Run button | Run from the terminal with `(venv)` active |
| Black camera image | Try `VideoCapture(1)`; close Zoom/Teams; allow camera access in Windows |
| `Robot not found` (Mode A) | Fix `ROBOT_NAME` to match the RoboDK tree |
| `Pose unreachable (IK)` (Mode A) | Re-run `scripts/pose_travail.py`; reduce `STEP_MM` |
| Nothing moves (Mode B) | Check IP, token, same network, app running, servo power on |

More details: [docs/depannage.md](docs/depannage.md) and the full UNO Q guide (both in French).

## License

Released under the MIT License. See [LICENSE](LICENSE).

## Author

**<Moda Fall>**, Bachelor's student in Robotics, <UNCHK>.
[LinkedIn](<www.linkedin.com/in/moda-fall-95a874344>)  · <fallmoda22@gmail.com>
