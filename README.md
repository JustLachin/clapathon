# Clapathon

A motion control application that allows you to control your computer through hand gestures detected by camera.

## Features

- 👏 Take screenshots with clap gesture
- 👆 Control system volume with index fingers
- 📸 Toggle camera on/off
- 🎚️ Manual volume control slider
- 📁 Automatic screenshot folder creation

## Requirements

The following packages need to be installed to run the application:

```bash
pip install -r requirements.txt
```

## Usage

1. Start the application:
```bash
python main.py
```

2. Click "Start Camera" button to activate the camera.

3. Control with hand gestures:
   - Clap gesture: Takes a screenshot
   - Two index fingers: Control volume by moving up/down

4. Screenshots are saved in the `screenshots` folder.

## Notes

- Camera is initially off, needs to be started manually
- Clap detection sensitivity and cooldown can be adjusted in the code
- System audio device access is required for volume control 