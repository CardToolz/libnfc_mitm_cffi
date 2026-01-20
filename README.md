# libnfc_mitm_cffi
`nfc_mitm` is the main script in the `libnfc_mitm_cffi` project. It is an advanced tool designed to perform man-in-the-middle (MITM) attacks on NFC communications using the C Foreign Function Interface (CFFI). Leveraging the `libnfc` library, it allows users to intercept, analyze, and manipulate NFC data in real-time, facilitating security testing and research in NFC-based systems. Addidionally it provides the APDU logs replay capabilities.
## Installation and configuration
Flash OS on SD card using Raspberry Pi imager (use Raspberry Pi Zero 2 W as device and Raspberry Pi OS (64-bit) as OS) and run.

- Using sudo raspi-config enable SPI:
Interface Options -> SPI
Answer Yes to "Would you like the SPI interface to be enabled?"
- Using sudo raspi-config disable shell over serial, but leave serial device as enabled:
- Interface Options -> Serial port
Answer No to "Would you like a login shell to be accessible over enabled?"
Answer Yes to "Would you like the serial port hardware to be enabled?"


Setup python, libnfc and libffi libraries:
```bash
sudo apt install python3-full libffi-dev libnfc-dev
```
Modify config for libnfc in /etc/nfc/libnfc.conf:
```
allow_autoscan = true
allow_intrusive_scan = false
log_level = 1

device.name = "_PN532_UART"
device.connstring = "pn532_uart:/dev/ttyS0"

device.name = "_PN532_SPI"
device.connstring = "pn532_spi:/dev/spidev0.0:150000"
```
Clone repository
```bash
git clone https://github.com/CardToolz/libnfc_mitm_cffi
```
Setup python virtual environment:
```bash
cd libnfc_mitm_cffi
python -m venv venv
source ./venv/bin/activate
venv/bin/pip install -r requirements.txt

deactivate
```
After rebooting the NFC devices can be listed:
```bash
source ./venv/bin/activate
# test CFFI wrapper
python libnfc_ffi_test.py 
# test NFC MiTM
python nfc_mitm.py --list-devs
                   *** LibNFC re(p)lay tool ***
tag <---> initiator (relay) <---> target (relay) <---> original reader

nfc_mitm.py uses LibNFC ver 1.8.0
libNFC devices (2):
        _PN532_UART
        _PN532_SPI
Initiator dev num: 1
Target dev num: 0
Exiting...
deactivate
```
Further MiTM attack can be performed:

venv/bin/python nfc_mitm.py
- **Usage**:
    ```bash
    venv/bin/python nfc_mitm.py [OPTIONS] 
    ```
- **Command-Line Parameters**:
    - `-l`, `--list-devs`: List NFC devices and exit.
    - `-o`, `--log-fname <FILE>`: Specify output JSON log filename. Default is generated based on the current date and time.
    - `-n`, `--no-easy-framing`: Do not use easy framing; transfer data as frames instead of APDUs.
    - `-p`, `--print-log`: Print the APDU log to stdout after completion.
    - `-H`, `--hook-data`: Use a data hook function for custom data processing.
    - `-L`, `--log-level <LEVEL>`: Set the logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`). Default is `ERROR`.
    - `-t`, `--target <NUMBER>`: Specify the emulator device number. Default is `0`.
- **Initiator or Replay Options (mutually exclusive)**:
    - `-i`, `--initiator <NUMBER>`: Specify the reader device number. Default is `1`.
    - `-r`, `--replay <LOGFILE>`: Replay APDU data from a recorded log file instead of using a reader.
- **Usage Examples**:
    ```bash
    # List available NFC devices
    venv/bin/python nfc_mitm.py --list-devs

    # Run with default settings
    venv/bin/python nfc_mitm.py

    # Specify a custom log filename
    venv/bin/python nfc_mitm.py --log-fname my_log.json

    # Use no easy framing mode
    venv/bin/python nfc_mitm.py --no-easy-framing

    # Replay from a log file
    venv/bin/python nfc_mitm.py --replay previous_log.json

    # Set logging level to DEBUG
    venv/bin/python nfc_mitm.py --log-level DEBUG
    ```

## Tools Included

### nfc_mitm.py
- **Features**:
    - **Man-in-the-Middle Relay**: Relay NFC communication between a target and an initiator, allowing interception and logging.
    - **Device Enumeration**: List connected NFC devices for selection.
    - **Data Logging**: Record APDU exchanges in JSON format for analysis.
    - **Replay Functionality**: Replay recorded APDU logs to simulate NFC interactions.
    - **Custom Data Hook**: Process or modify data on-the-fly using a hook function.
    - **Configurable Logging Level**: Adjust the verbosity of logging output.

- **Description**: The primary script for conducting MITM attacks on NFC communications.

### apdu_processor.py
The `apdu_processor.py` module provides the data_hook function, which is crucial for processing and potentially modifying the APDU data during the relay. 

Data Processing with `data_hook()`:

The `data_hook()` function in `apdu_processor.py` is designed to intercept APDU data as it flows through the MITM relay.
The example implementation checks if the incoming data starts with the bytes 0xBA and 0xAD. If it does, it logs a "[+]Corrupt data" message and sets send_fragmented to True.
This function can be extended to mutate or alter the data before it's sent onward, as indicated by the # TODO comment.
### log_parser.py

### libnfc_ffi_test.py
