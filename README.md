# HGR — Gesture-Controlled Door Lock

A real-time, contactless door lock. A camera watches your hand, a YOLOv11 model recognizes the gesture, and an Arduino locks, unlocks or raises an alarm, with no touch, key or card needed.

| mAP50 | Precision | Recall | Inference |
| :---: | :---: | :---: | :---: |
| **98.7%** | **96.0%** | **96.3%** | **2.6 ms / frame** |

## How it works

```
 Webcam ──▶ YOLOv11n ──▶ Smoothing filter ──▶ PySerial ──▶ Arduino Uno ──▶ Servo lock
 (OpenCV)   (5 gestures)  (7-frame vote)     (9600 baud)  (state machine)  LEDs + buzzer
```

1. **Detect:** every webcam frame goes through a custom-trained YOLOv11n model.
2. **Stabilize:** a gesture counts only when it wins at least 4 of the last 7 frames with confidence of 0.60 or more. The same command is not re-sent within 1.5 s.
3. **Act:** the command is sent over USB serial to the Arduino, which moves the servo and updates the LEDs and buzzer.

## Gestures

| Gesture | Command | What the lock does | LED |
| --- | --- | --- | --- |
| 👍 Like | `UNLOCK` | Servo to 90°, door unlocked | Green |
| ✊ Fist | `LOCK` | Servo to 0°, door locked | Red |
| ✋ Palm | `WAIT` | Return to standby | Yellow |
| 👎 Dislike | `ALARM` | Buzzer sounds, red LED blinks | Red (blinking) |
| 🤚 Palm (reverse) | `CANCEL` | Stops the alarm, back to standby | Blue |

While the alarm is on, the Arduino accepts **only** `CANCEL`, so a stray gesture cannot unlock the door during an alarm.

## Model

| | |
| --- | --- |
| Architecture | YOLOv11n: 2.58 M parameters, 6.3 GFLOPs |
| Dataset | HaGRID-based hand gesture dataset (Roboflow), 18 classes, 540 validation images |
| Training | 20 epochs on Google Colab (Tesla T4), about 26 minutes |
| Results | mAP50 98.7%, precision 96.0%, recall 96.3% |
| Speed | 2.6 ms inference per frame (input size 320) |

**Why YOLOv11?** I first tried a two-stage pipeline (YOLOv8 to find the hand, then ResNet-50 to classify it). It took about 51 s per training epoch and needed two models at run time. A single-stage YOLOv11n detects and classifies in one pass, fast enough for real time on a laptop.

| Training curves | Confusion matrix |
| --- | --- |
| ![Training results](results%20(1).png) | ![Confusion matrix](confusion_matrix%20(2).png) |

## Hardware

| Part | Arduino pin |
| --- | --- |
| SG90 servo (0° locked, 90° unlocked) | D6 |
| Passive buzzer | D7 |
| Yellow LED: waiting | D8 |
| Green LED: unlocked | D9 |
| Red LED: locked / alarm | D10 |
| Blue LED: cancelled | D11 |

The firmware is a four-state machine (`WAITING`, `UNLOCKED`, `LOCKED`, `ALARM_ON`). It uses `millis()` timing instead of `delay()`, so it never blocks and keeps reading serial commands while the alarm LED blinks.

## Project structure

```
HGR/
├── main2.py                       # Python app: camera, YOLO, smoothing, serial
├── best(2).pt                     # trained YOLOv11n weights
├── results (1).png                # training curves
├── confusion_matrix (2).png
└── PlatformIO/Projects/thefinalbest/
    ├── platformio.ini             # Arduino Uno, Servo library
    ├── src/main.cpp               # state machine firmware
    └── diagram.json, Wokwi.toml   # circuit for the Wokwi simulator
```

## Run it

**1. Arduino.** Open `PlatformIO/Projects/thefinalbest` in VS Code with the PlatformIO extension, set `upload_port` in `platformio.ini`, and upload. No board? Run the circuit in the Wokwi simulator with `diagram.json`.

**2. Python app**

```bash
pip install ultralytics opencv-python pyserial
python main2.py
```

Set `SERIAL_PORT` at the top of `main2.py` (for example `COM11` on Windows or `/dev/ttyUSB0` on Linux). If no Arduino is connected, the app runs in **simulation mode** and prints the commands it would send. Press `Q` to quit.

## Academic context

- Design project for **BM328 Tasarım Çalışması II**, Computer Engineering, Bilecik Şeyh Edebali University, supervised by **Dr. Vedat Marttin**. The project was completed and defended.
- Abstract *"Hand Gesture Recognition-Based Door Lock System with YOLOv11"* (R. Elhussain, V. Marttin) submitted for oral presentation at the 700th Year Şeyh Edebali Scientific Research Symposium, 2026.

## Built with

Python · Ultralytics YOLOv11 · OpenCV · PySerial · Arduino (C++) · PlatformIO · Wokwi · Google Colab

---

**Rawan Elhussain** · [github.com/rawan237](https://github.com/rawan237)
