# Vehículo WRO 2026 Future Engineers (Guía para Principiantes)

**Idioma:** [English](README.md) | Español

¡Bienvenidos! 👋  
Este repositorio está diseñado para estudiantes (incluyendo equipos de
ingeniería mecánica) que pueden tener **poca experiencia programando**.

Si puedes seguir una lista de pasos, puedes ejecutar este proyecto.

---

## Qué hace este proyecto (en palabras simples)

- Usa una **cámara de Raspberry Pi** para detectar colores (rojo, verde, magenta).
- Envía comandos por USB serial a un **Arduino Uno**.
- Arduino controla:
  - servo de dirección (comandos `S...`)
  - aceleración/ESC (comandos `T...`)

---

## Mapa visual (de clonar a ejecutar)

### 1) Flujo completo

![Flujo de inicio rápido](docs/diagrams/01_quick_start_workflow.png)

### 2) Resumen de conexiones

![Resumen de conexiones](docs/diagrams/02_connection_overview.png)

---

## Antes de empezar (checklist de hardware + software)

### Hardware

- Raspberry Pi (con Raspberry Pi OS)
- Arduino Uno
- Cable USB (Pi ↔ Arduino)
- Módulo de cámara o cámara USB
- Servo de dirección
- ESC + motor
- Batería / fuente de poder

### Software

- Git instalado
- Python 3 instalado
- Arduino IDE instalado

---

## Instrucciones paso a paso

## Paso 1 — Clonar este repositorio

En la terminal de Raspberry Pi:

```bash
git clone https://github.com/sjhallo07/wro2026-fe-vehicle.git
cd wro2026-fe-vehicle
```

---

## Paso 2 — Instalar dependencias de Python

### Raspberry Pi / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Windows (pruebas en mesa opcionales)

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

---

## Paso 3 — Subir firmware a Arduino

1. Abre Arduino IDE.
2. Abre el archivo: `src/arduino/motor_control.ino`
3. Selecciona la placa: **Arduino Uno**
4. Selecciona el puerto correcto (ejemplo: `COM3` en Windows).
5. Haz clic en **Upload**.

Cuando esté conectado, Arduino debería enviar `ARDUINO_READY` por serial.

---

## Paso 4 — Conectar Raspberry Pi y Arduino

Conexiones mínimas necesarias:

- Raspberry Pi a Arduino por **USB** (comunicación serial).
- Cámara conectada a Raspberry Pi.
- Señal del servo al pin **10** de Arduino.
- Señal del ESC al pin **9** de Arduino.
- Usar alimentación correcta y **GND común**.

⚠️ Seguridad primero: prueba con las ruedas levantadas antes de conducir.

---

## Paso 5 — Probar comunicación serial (importante)

Ejecuta esto en Raspberry Pi:

```bash
python3 src/examples/rpi_arduino_serial_test.py --port /dev/ttyACM0
```

Ejemplo en Windows:

```bash
python src/examples/rpi_arduino_serial_test.py --port COM3
```

Si todo está bien, verás respuestas como:

- `STEER:90`
- `THROTTLE:1500`

---

## Paso 6 — Calibrar colores de la cámara

Ejecuta:

```bash
python3 src/utils/calibration.py
```

Cómo usarlo:

- Mueve los trackbars hasta que la máscara detecte bien el color objetivo.
- Presiona **S** para guardar.
- Presiona **Q** para salir.

Haz esto cada vez que cambie la iluminación.

---

## Paso 7 — Ejecutar el programa principal del vehículo

```bash
python3 src/main.py
```

Qué esperar:

- Se abre la ventana de la cámara.
- Aparecen las detecciones de color.
- Las acciones se convierten a comandos de Arduino:
  - `FORWARD` → `S90`, `T1600`
  - `LEFT` → `S60`, `T1550`
  - `RIGHT` → `S120`, `T1550`
  - `STOP` → `T1500`, `S90`

---

## Solución rápida de problemas (fallas comunes)

### 1) `Could not connect to Arduino`

- Revisa el cable USB.
- Revisa el puerto (`/dev/ttyACM0` o `COMx`).
- Cierra el monitor serial de Arduino IDE (puede bloquear el puerto).

### 2) Cámara no detectada

- Verifica el cable de la cámara.
- Prueba otro índice de cámara en el código, si es necesario.

### 3) Detección de color incorrecta

- Repite calibración (`src/utils/calibration.py`).
- Mejora la consistencia de iluminación.

### 4) Servo/motor no se mueve

- Revisa cableado de alimentación.
- Confirma que los pines en Arduino coinciden con el sketch (`10` y `9`).
- Confirma que ESC/servo compartan GND con Arduino.

### 5) Errores de importación de Python (`cv2`, `serial`, `numpy`)

- Activa primero `.venv`.
- Vuelve a ejecutar `pip install -r requirements.txt`.

---

## Estructura del repositorio

```text
wro2026-fe-vehicle/
├── README.md
├── README.es.md
├── requirements.txt
├── src/
│   ├── main.py
│   ├── arduino/
│   │   └── motor_control.ino
│   ├── examples/
│   │   └── rpi_arduino_serial_test.py
│   └── utils/
│       └── calibration.py
├── cad/
├── wiring/
└── docs/
    └── diagrams/
        ├── 01_quick_start_workflow.png
        └── 02_connection_overview.png
```

---

## Para profesores/mentores

Este README fue escrito de forma explícita y procedural para que estudiantes
sin base fuerte en programación puedan seguirlo. Puedes usar cada paso como
checkpoint de laboratorio.
