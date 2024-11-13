import pifacecad
import time
import subprocess
import socket
import threading
import cv2

# Constants
BATTERY_CHECK_INTERVAL = 10  # seconds
LOW_BATTERY_THRESHOLD = 20   # Battery percentage threshold for low battery warning

# PiFace CAD initialization
cad = pifacecad.PiFaceCAD()
cad.lcd.backlight_on()

# Button number mapping
BUTTON_TAKEOFF_LANDING = 4
BUTTON_CAPTURE = 5  # 버튼 5에 카메라 기능 할당
BUTTON_FORWARD = 0
BUTTON_BACKWARD = 1
BUTTON_LEFT = 2
BUTTON_RIGHT = 3
BUTTON_NAV_LEFT = 6
BUTTON_NAV_RIGHT = 7

# Global variables
tello = None
is_flying = False

class Tello:
    def __init__(self):
        self.local_ip = ''
        self.local_cmd_port = 9000  # Changed from 8889 to avoid conflicts

        self.tello_ip = '192.168.10.1'
        self.tello_port = 8889
        self.tello_address = (self.tello_ip, self.tello_port)
        
        # Command socket
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            self.socket.bind((self.local_ip, self.local_cmd_port))
        except OSError as e:
            print(f"Error binding command socket on port {self.local_cmd_port}: {e}")
            self.socket.close()
            raise e
        
        self.response = None
        self.MAX_TIME_OUT = 15.0

        # Thread for receiving responses
        self.receive_thread = threading.Thread(target=self._receive_thread)
        self.receive_thread.daemon = True
        self.receive_thread.start()

    def send_command(self, command):
        """
        Sends a command to the Tello drone and waits for a response.
        Returns True if a response is received and is 'ok' or a number, False otherwise.
        """
        self.response = None
        self.socket.sendto(command.encode('utf-8'), self.tello_address)
        print(f"Sending command: {command}")
        start_time = time.time()
        while self.response is None:
            if time.time() - start_time > self.MAX_TIME_OUT:
                print("Timeout exceeded")
                return False
            time.sleep(0.1)
        response_text = self.response.decode('utf-8').strip()
        print(f"Received response: {response_text}")
        if response_text == 'ok' or response_text.isdigit():
            return True
        else:
            print(f"Command '{command}' failed with response: {response_text}")
            return False

    def _receive_thread(self):
        while True:
            try:
                self.response, _ = self.socket.recvfrom(1024)
            except Exception as e:
                print(f"Error receiving response: {e}")

    def get_response(self):
        if self.response:
            return self.response.decode('utf-8').strip()
        else:
            return None

    def close(self):
        self.socket.close()

# Function to check current connection
def check_connection():
    try:
        output = subprocess.check_output(['nmcli', '-t', '-f', 'DEVICE,STATE,CONNECTION', 'device'])
        lines = output.decode('utf-8').split('\n')
        for line in lines:
            parts = line.strip().split(':')
            if len(parts) >= 3 and parts[0] == 'wlan0' and parts[1] == 'connected':
                ssid = parts[2]
                return ssid
        return None
    except Exception:
        return None

# Function to check if connected to 'TELLO-' network
def is_connected_to_tello():
    ssid = check_connection()
    if ssid and ssid.startswith('TELLO-'):
        return ssid
    return None

# Function to scan for 'TELLO-' networks
def scan_for_tello():
    try:
        scan_output = subprocess.check_output(['nmcli', '-t', '-f', 'SSID', 'device', 'wifi', 'list'])
        available_ssids = scan_output.decode('utf-8').split('\n')
        for ssid in available_ssids:
            if ssid.startswith('TELLO-'):
                return ssid
        return None
    except Exception:
        return None

# Function to connect to 'TELLO-' network
def connect_to_tello(ssid):
    try:
        cad.lcd.clear()
        cad.lcd.write("Connecting to\n" + ssid[:16])
        subprocess.run(['nmcli', 'device', 'wifi', 'connect', ssid], check=True)
        time.sleep(2)
        return True
    except subprocess.CalledProcessError:
        cad.lcd.clear()
        cad.lcd.write("Failed to connect\nto " + ssid[:16])
        time.sleep(2)
        return False

# Function to display message to turn on the Tello drone
def prompt_turn_on_tello():
    cad.lcd.clear()
    cad.lcd.write("Please turn on\nTello drone")
    time.sleep(2)

# Function to check battery level
def check_battery():
    global tello
    if tello:
        # Send 'battery?' to get battery level
        if not tello.send_command('battery?'):
            return None
        response = tello.get_response()
        if response:
            # Clean the response
            response = response.strip()
            if response.isdigit():
                return int(response)  # Return as integer
            else:
                return None
        else:
            return None
    else:
        return None

# Function to handle button presses
def handle_button_press(button):
    global tello, is_flying, battery_level
    if tello is None:
        return
    if button == BUTTON_TAKEOFF_LANDING:
        # Check if button is held for 2 seconds
        start_time = time.time()
        while cad.switches[button].value == 1:
            if time.time() - start_time >= 2:
                if not is_flying:
                    # Check battery level before takeoff
                    battery_level = check_battery()
                    if battery_level is not None and battery_level <= LOW_BATTERY_THRESHOLD:
                        cad.lcd.set_cursor(0, 1)
                        cad.lcd.write("LOW BATTERY     ")
                        time.sleep(2)
                        # Restore the previous message
                        cad.lcd.set_cursor(0, 1)
                        cad.lcd.write("Takeoff: Hold 4")
                        return
                    cad.lcd.set_cursor(0, 1)
                    cad.lcd.write("Taking off     ")
                    success = tello.send_command('takeoff')
                    if success:
                        is_flying = True
                        # Update LCD to show new status
                        cad.lcd.clear()
                        if battery_level <= LOW_BATTERY_THRESHOLD:
                            cad.lcd.write(f"LOW BATTERY: {battery_level}%")
                        else:
                            cad.lcd.write(f"Battery: {battery_level}%")
                        cad.lcd.set_cursor(0, 1)
                        cad.lcd.write("Press 4 to Land")
                    else:
                        cad.lcd.set_cursor(0, 1)
                        cad.lcd.write("Takeoff failed ")
                else:
                    cad.lcd.set_cursor(0, 1)
                    cad.lcd.write("Landing        ")
                    success = tello.send_command('land')
                    if success:
                        is_flying = False
                        # Update LCD to show new status
                        cad.lcd.clear()
                        if battery_level <= LOW_BATTERY_THRESHOLD:
                            cad.lcd.write(f"LOW BATTERY: {battery_level}%")
                        else:
                            cad.lcd.write(f"Battery: {battery_level}%")
                        cad.lcd.set_cursor(0, 1)
                        cad.lcd.write("Takeoff: Hold 4")
                    else:
                        cad.lcd.set_cursor(0, 1)
                        cad.lcd.write("Landing failed ")
                time.sleep(1)
                return
            time.sleep(0.1)
    elif button == BUTTON_CAPTURE:
        # 카메라 캡처 기능
        cad.lcd.set_cursor(0, 1)
        cad.lcd.write("Capturing Photo")
        # Send 'streamon' command
        if tello.send_command('streamon'):
            # Wait for the stream to initialize
            time.sleep(2)
            # Open the video capture
            stream_url = 'udp://@0.0.0.0:11111'
            cap = cv2.VideoCapture(stream_url)
            if cap.isOpened():
                ret, frame = cap.read()
                if ret:
                    # Save the frame
                    timestamp = time.strftime("%Y%m%d_%H%M%S")
                    filename = f"capture_{timestamp}.jpg"
                    cv2.imwrite(filename, frame)
                    cad.lcd.set_cursor(0, 1)
                    cad.lcd.write("Photo Captured ")
                    print(f"Image saved as {filename}")
                else:
                    cad.lcd.set_cursor(0, 1)
                    cad.lcd.write("Capture Failed ")
                    print("Failed to capture frame.")
                cap.release()
            else:
                cad.lcd.set_cursor(0, 1)
                cad.lcd.write("Stream Failed  ")
                print("Failed to open video stream.")
            # Send 'streamoff' command
            tello.send_command('streamoff')
        else:
            cad.lcd.set_cursor(0, 1)
            cad.lcd.write("Streamon Failed")
            print("Failed to send 'streamon' command.")
        time.sleep(1)
        # Restore the previous message
        cad.lcd.set_cursor(0, 1)
        if is_flying:
            cad.lcd.write("Press 4 to Land")
        else:
            cad.lcd.write("Takeoff: Hold 4")
    elif is_flying:
        command_text = ""
        if button == BUTTON_FORWARD:
            command_text = "Forward 20cm   "
            tello.send_command('forward 20')
        elif button == BUTTON_BACKWARD:
            command_text = "Backward 20cm  "
            tello.send_command('back 20')
        elif button == BUTTON_LEFT:
            command_text = "Left 20cm      "
            tello.send_command('left 20')
        elif button == BUTTON_RIGHT:
            command_text = "Right 20cm     "
            tello.send_command('right 20')
        elif button == BUTTON_NAV_LEFT:
            command_text = "Rotate CCW 30° "
            tello.send_command('ccw 30')
        elif button == BUTTON_NAV_RIGHT:
            command_text = "Rotate CW 30°  "
            tello.send_command('cw 30')
        if command_text:
            # Update only the second line of the LCD
            cad.lcd.set_cursor(0, 1)
            cad.lcd.write(command_text)
            time.sleep(1)
            # Restore the previous message
            cad.lcd.set_cursor(0, 1)
            cad.lcd.write("Press 4 to Land")
    else:
        # Display message to take off first
        cad.lcd.set_cursor(0, 1)
        cad.lcd.write("Takeoff first  ")
        time.sleep(1)
        # Restore the previous message
        cad.lcd.set_cursor(0, 1)
        cad.lcd.write("Takeoff: Hold 4")

# Main function
def main():
    global tello, is_flying, battery_level
    previous_battery_level = None
    while True:
        # Check if connected to Tello network
        connected_ssid = is_connected_to_tello()
        if connected_ssid:
            # Try to initialize Tello object
            try:
                tello = Tello()
                is_flying = False  # Reset flight state
            except OSError as e:
                error_msg = str(e)
                cad.lcd.clear()
                cad.lcd.write("Socket error")
                cad.lcd.set_cursor(0, 1)
                if "Address already in use" in error_msg:
                    cad.lcd.write("Port in use")
                else:
                    cad.lcd.write("Other error")
                time.sleep(2)
                tello = None
                continue  # Go back to the start of the main loop

            # Successfully initialized Tello object
            cad.lcd.clear()
            cad.lcd.write("Connected to\n" + connected_ssid[:16])
            time.sleep(2)

            # Send 'command' to enter SDK mode
            if not tello.send_command('command'):
                cad.lcd.clear()
                cad.lcd.write("Failed to enter\nSDK mode")
                time.sleep(2)
                continue  # Restart the loop

            # Initial battery check
            battery_level = check_battery()
            if battery_level is None:
                cad.lcd.clear()
                cad.lcd.write("Battery check\nfailed")
                time.sleep(2)
                continue  # Restart the loop

            # Display initial battery level
            cad.lcd.clear()
            if battery_level <= LOW_BATTERY_THRESHOLD:
                cad.lcd.write(f"LOW BATTERY: {battery_level}%")
            else:
                cad.lcd.write(f"Battery: {battery_level}%")
            cad.lcd.set_cursor(0, 1)
            cad.lcd.write("Takeoff: Hold 4")
            previous_battery_level = battery_level

            last_battery_check = time.time()

            # Monitor connection and handle events
            while True:
                # Check if still connected
                connected_ssid = is_connected_to_tello()
                if not connected_ssid:
                    cad.lcd.clear()
                    cad.lcd.write("Lost connection")
                    time.sleep(2)
                    if tello:
                        tello.close()
                        tello = None
                    break  # Go back to scanning for Tello

                current_time = time.time()
                if current_time - last_battery_check >= BATTERY_CHECK_INTERVAL:
                    # Check battery level
                    new_battery_level = check_battery()
                    last_battery_check = current_time

                    if new_battery_level is not None:
                        # Update LCD only if battery level changed
                        if new_battery_level != battery_level:
                            battery_level = new_battery_level
                            cad.lcd.clear()
                            if battery_level <= LOW_BATTERY_THRESHOLD:
                                cad.lcd.write(f"LOW BATTERY: {battery_level}%")
                            else:
                                cad.lcd.write(f"Battery: {battery_level}%")
                            cad.lcd.set_cursor(0, 1)
                            if is_flying:
                                cad.lcd.write("Press 4 to Land")
                            else:
                                cad.lcd.write("Takeoff: Hold 4")
                    else:
                        cad.lcd.clear()
                        cad.lcd.write("Battery check")
                        cad.lcd.set_cursor(0, 1)
                        cad.lcd.write("failed")

                # Handle button presses
                for i in range(8):
                    if cad.switches[i].value == 1:
                        handle_button_press(i)

                time.sleep(0.1)
        else:
            # Not connected to Tello network
            prompt_turn_on_tello()
            # Scan for 'TELLO-' network
            tello_ssid = None
            while not tello_ssid:
                tello_ssid = scan_for_tello()
                if not tello_ssid:
                    cad.lcd.clear()
                    cad.lcd.write("Scanning for\nTello network")
                    time.sleep(2)

            # Attempt to connect to Tello network
            if not connect_to_tello(tello_ssid):
                cad.lcd.clear()
                cad.lcd.write("Retrying in 5 sec")
                time.sleep(5)
                continue  # Retry scanning and connecting

if __name__ == "__main__":
    main()
