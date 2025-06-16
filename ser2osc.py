#!/user/bin/python3
"""
pyinstaller --clean --onefile --add-data "devcon.exe;." ser2osc.py
"""
import json
import serial
import time
import sys
import os
import serial.tools.list_ports as list_ports
import subprocess
from pythonosc import udp_client

# ----- constants -----
VERSION = "2025-06-16"
print(f"ser2osc version: {VERSION}")

# ----- functions -----
def find_serial_port(serialName="USB"):
    ports = list_ports.comports()
    for port in ports:
        if serialName in port.description:
            return port.device
    return None

def readConfigFile(configFile):
    if not os.path.exists(configFile):
        print(f"Config file {configFile} does not exist.")
        config = {
            "serialPort": "auto",
            "serialName": "USB",
            "baudRate": "9600",
            "oscAddresses": [
                "/restart",
                "/stop",
                "/light",
            ],
            "oscHost": "127.0.0.1",
            "oscPort": "8010",
            "arduinoDriver" : "USB\\VID_1A86&PID_7523"
        }
        # Serialize the config to a file
        jsonObject = json.dumps(config, indent=4)
        with open(configFile, 'w') as f:
            f.write(jsonObject)
        
        return config
    with open(configFile, 'r') as f:
        config = json.load(f)
    return config

def getSerialPort(config):
    if config["serialPort"] == "auto":
        serialPort = find_serial_port(config["serialName"])
        if not serialPort:
            print(f"Could not find serial port for {config['serialName']}.")
            input("Press Enter to continue or Ctrl+C to exit...")
            sys.exit(1)
    else:
        serialPort = config["serialPort"]
    return serialPort

def main():
    # Get curent working directory
    try:
        thisFile = __file__
    except NameError:
        thisFile = sys.argv[0]
    thisFile = os.path.abspath(thisFile)
    if getattr(sys, 'frozen', False):
        # If the application is frozen (e.g., using PyInstaller)
        cwd = os.path.dirname(sys.executable)
        bundelDir = sys._MEIPASS
    else:
        # If the application is not frozen
        cwd = os.path.dirname(thisFile)
        bundelDir = cwd
        
    print(f"Current working directory: {cwd}")
    
    #get file name without extension of the script
    myName = os.path.splitext(os.path.basename(thisFile))[0]
    print(f"Script name: {myName}")
    configFile = os.path.join(cwd, f"{myName}.json")
    config = readConfigFile(configFile)

    serialPort = getSerialPort(config)
    baudRate = int(config["baudRate"])
    oscHost = config["oscHost"]
    oscPort = int(config["oscPort"])
    
    print(f"Using serial port: {serialPort} at {baudRate} baud")
    print(f"Using OSC host: {oscHost} on port {oscPort}")

    # Create OSC client
    client = udp_client.SimpleUDPClient(oscHost, oscPort)

    # Open serial port anda test if driver is working
    noSerial = True
    while noSerial:
        try:
            ser = serial.Serial(serialPort, baudRate, timeout=1)
            print("Serial port opened successfully.")
            noSerial = False
        except serial.SerialException as e:
            print(f"Error opening serial port: {e}")
            if "PermissionError" in str(e):
                print("Permission error.")
                print("Restarting the Arduino driver...")
                # Restart the Arduino driver using devcon
                print(f"Using driver {config['arduinoDriver']}")
                devconFile = os.path.join(bundelDir, "devcon.exe")
                if not os.path.exists(devconFile):
                    print(f"devcon.exe not found in {bundelDir}.")
                    input("Press Enter to continue or Ctrl+C to exit...")
                    sys.exit(1)
                subprocess.run([devconFile, "disable", config["arduinoDriver"]])
                subprocess.run([devconFile, "enable", config["arduinoDriver"]])
            else:
                print("Serial port not found. Retrying in 5 seconds...")
                time.sleep(5)
        except Exception as e:
            print(f"Unexpected error: {e}")
            input("Press Enter to continue or Ctrl+C to exit...")
            sys.exit(1)

    try:
        while ser.is_open:
            if ser.in_waiting > 0:
                line = ser.readline().strip().decode('utf-8')
                print(f"Received: {line}")
                if line.isnumeric():
                    x = int(line)
                    client.send_message(config["oscAddresses"][x], 1)
                    addres = config["oscAddresses"][x]
                    print(f"Sent OSC message to: {addres}")
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("Exiting...")
    finally:
        ser.close()
        
# ----- main -----
if __name__ == "__main__":
    main()
