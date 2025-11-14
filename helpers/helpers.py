import sys
from pathlib import Path

from src.ini_reader import find_comport_device, get_rf_settings, load_config


def get_root_dir() -> Path:
    """
    Get the path to the root directory of where the script is being run from.

    Returns (Path):
        The Path object to the root directory.
    """
    if getattr(sys, 'frozen', False):  # Check if running from the PyInstaller EXE
        return Path(getattr(sys, '_MEIPASS', '.'))
    else:  # Running in a normal Python environment
        return Path(__file__).resolve().parents[1]


def get_ini_info() -> tuple[str | None, tuple[str, str, str]]:
    """
    Get the initialization information from the .ini file.

    Returns [tuple(str | None, tuple(str, str, str))]:
        The RF generator's COM port number and its specs.\n
        Or if the device is set to 'None', rf_com_port is returned as None.
    """
    root_dir: Path = get_root_dir()
    ini_file: str = 'configuration/rf_controller.ini'
    ini_file_path: str = str(root_dir / ini_file)
    config_data = load_config(ini_file_path)
    rf_generator = find_comport_device(config_data, 'RFGenerator')
    device: str = rf_generator[0]
    rf_com_port: str | None = rf_generator[1]
    if device == 'None':
        rf_com_port = None
    rf_settings = get_rf_settings(config_data)

    return rf_com_port, rf_settings


def convert_num_to_bits(num: int) -> list[int]:
    num_as_byte: str = format(num, '04b')
    bits: list[int] = [int(digit) for digit in num_as_byte]
    return bits
