# libnfc_mitm_cffi
`nfc_mitm` is the main script in the `libnfc_mitm_cffi` project. It is an advanced tool designed to perform man-in-the-middle (MITM) attacks on NFC communications using the C Foreign Function Interface (CFFI). Leveraging the `libnfc` library, it allows users to intercept, analyze, and manipulate NFC data in real-time, facilitating security testing and research in NFC-based systems. Addidionally it provides the APDU logs replay capabilities.

## Tools Included

### nfc_mitm.py

- **Description**: The primary script for conducting MITM attacks on NFC communications.
- **Usage**:
    ```bash
    nfc_mitm.py [OPTIONS]
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
- **Features**:
    - **Man-in-the-Middle Relay**: Relay NFC communication between a target and an initiator, allowing interception and logging.
    - **Device Enumeration**: List connected NFC devices for selection.
    - **Data Logging**: Record APDU exchanges in JSON format for analysis.
    - **Replay Functionality**: Replay recorded APDU logs to simulate NFC interactions.
    - **Custom Data Hook**: Process or modify data on-the-fly using a hook function.
    - **Configurable Logging Level**: Adjust the verbosity of logging output.
- **Usage Examples**:
    ```bash
    # List available NFC devices
    nfc_mitm.py --list-devs

    # Run with default settings
    nfc_mitm.py

    # Specify a custom log filename
    nfc_mitm.py --log-fname my_log.json

    # Use no easy framing mode
    nfc_mitm.py --no-easy-framing

    # Replay from a log file
    nfc_mitm.py --replay previous_log.json

    # Set logging level to DEBUG
    nfc_mitm.py --log-level DEBUG
    ```
### apdu_processor.py
The `apdu_processor.py` module provides the data_hook function, which is crucial for processing and potentially modifying the APDU data during the relay. 

Data Processing with `data_hook()`:

The `data_hook()` function in `apdu_processor.py` is designed to intercept APDU data as it flows through the MITM relay.
The example implementation checks if the incoming data starts with the bytes 0xBA and 0xAD. If it does, it logs a "[+]Corrupt data" message and sets send_fragmented to True.
This function can be extended to mutate or alter the data before it's sent onward, as indicated by the # TODO comment.
### log_parser.py

### libnfc_ffi_test.py

### libnfc_ffi_test.py
