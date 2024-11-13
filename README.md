# PiFace-Tello

**PiFace-Tello** is a Python script that uses Raspberry Pi and the PiFace Control and Display module to control a DJI Tello EDU or Robomaster TT drone and capture images through the drone’s camera. This project enables easy control of basic drone functions via PiFace CAD buttons.

## Features

- Takeoff and landing control via PiFace CAD buttons
- Capture and save images from the drone camera with a single button press
- Check battery level and display low-battery warnings

## Requirements

To use this project, you’ll need the following:

- **DJI Tello EDU or Robomaster TT** drone
- **Raspberry Pi** (compatible with PiFace CAD; either built-in Wi-Fi or with a USB Wi-Fi adapter)
- **PiFace Control and Display (CAD)** module
- **Python3** and related libraries:
  - Python3
  - `opencv-python` (OpenCV)
  - `pifacecad`
  - `numpy`

### OpenCV Installation

Please ensure OpenCV is installed on your Raspberry Pi. Installing OpenCV on Raspberry Pi can be tricky, so consult the latest resources or guides for a successful installation method that fits your setup. 

## Installation

1. **Clone this repository**:

   ```bash
   git clone https://github.com/ychoi-kr/piface-tello.git
   cd piface-tello
   ```

2. **Make the script executable**:

   ```bash
   chmod +x run.py
   ```

## Usage

1. **Run the script**:

   ```bash
   python3 run.py
   ```

   - The script will automatically scan for available Tello drones and connect to the drone’s Wi-Fi network.
   - Make sure the drone is powered on and within range of the Raspberry Pi.

2. **Controls**:
   - **Button 4**: Press and hold for 2 seconds to take off or land
   - **Button 5**: Capture a single image from the drone’s camera and save it
   - **Other buttons**: Basic directional controls for the drone (e.g., move forward, backward, left, right)

3. **Image Storage**: Captured images are saved in the format `capture_YYYYMMDD_HHMMSS.jpg` in the project directory.

## Notes

- **Battery Warning**: The system will display a "LOW BATTERY" warning if the battery level falls below a set threshold.
- **Network Connectivity**: The script will automatically connect to the drone’s Wi-Fi network. If connection issues arise, ensure the drone is powered on and within range.
