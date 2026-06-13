#include <Servo.h>
#include <Arduino.h>

Servo doorServo;

// ── Pin definitions ──────────────────────────
const int TRIG_PIN   = 2;
const int ECHO_PIN   = 3;
const int SERVO_PIN  = 6;
const int BUZZER     = 7;
const int YELLOW_LED = 8;
const int GREEN_LED  = 9;
const int RED_LED    = 10;
const int BLUE_LED   = 11;
// ─────────────────────────────────────────────

enum State { WAITING, UNLOCKED, LOCKED, ALARM_ON };
State currentState = WAITING;

unsigned long blinkMillis = 0;
bool blinkState = false;

void allLedsOff();
void goWaiting();

long getDistance() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);
  long duration = pulseIn(ECHO_PIN, HIGH, 30000);
  return duration * 0.034 / 2;
}

void allLedsOff() {
  digitalWrite(YELLOW_LED, LOW);
  digitalWrite(GREEN_LED,  LOW);
  digitalWrite(RED_LED,    LOW);
  digitalWrite(BLUE_LED,   LOW);
}

void goWaiting() {
  currentState = WAITING;
  allLedsOff();
  noTone(BUZZER);
  doorServo.write(90);
  digitalWrite(YELLOW_LED, HIGH);
  Serial.println("STATE: WAITING — Yellow ON");
}

void goUnlocked() {
  currentState = UNLOCKED;
  allLedsOff();
  noTone(BUZZER);
  doorServo.write(90);
  digitalWrite(GREEN_LED, HIGH);
  Serial.println("STATE: UNLOCKED — Green ON");
}

void goLocked() {
  currentState = LOCKED;
  allLedsOff();
  noTone(BUZZER);
  doorServo.write(0);
  digitalWrite(RED_LED, HIGH);
  Serial.println("STATE: LOCKED — Red ON");
}

void goAlarm() {
  currentState = ALARM_ON;
  allLedsOff();
  tone(BUZZER, 1000);
  Serial.println("STATE: ALARM — Buzzer ON, Red blinking");
}

void goCancel() {
  noTone(BUZZER);
  allLedsOff();
  digitalWrite(BLUE_LED, HIGH);  // ← زودي السطر ده
  delay(1000);                    // يفضل أزرق ثانية
  goWaiting();
  Serial.println("STATE: CANCELLED — back to WAITING");
}

void setup() {
  Serial.begin(9600);
  doorServo.attach(SERVO_PIN);

  pinMode(TRIG_PIN,   OUTPUT);
  pinMode(ECHO_PIN,   INPUT);
  pinMode(YELLOW_LED, OUTPUT);
  pinMode(GREEN_LED,  OUTPUT);
  pinMode(RED_LED,    OUTPUT);
  pinMode(BLUE_LED,   OUTPUT);
  pinMode(BUZZER,     OUTPUT);

  goWaiting();
  Serial.println("System ready.");
}

void loop() {
  long dist = getDistance();
  if (dist > 0 && dist < 50) {
    if (currentState == WAITING) {
      Serial.println("Person detected!");
    }
  }

  if (Serial.available() > 0) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();
    cmd.toUpperCase();
    Serial.print("Received: ");
    Serial.println(cmd);

    if      (cmd == "UNLOCK") goUnlocked();
    else if (cmd == "LOCK")   goLocked();
    else if (cmd == "WAIT")   goWaiting();
    else if (cmd == "ALARM")  goAlarm();
    else if (cmd == "CANCEL") goCancel();
    else Serial.println("Unknown command");
  }

  if (currentState == ALARM_ON) {
    unsigned long now = millis();
    if (now - blinkMillis >= 300) {
      blinkMillis = now;
      blinkState  = !blinkState;
      digitalWrite(RED_LED, blinkState ? HIGH : LOW);
    }
  }
}