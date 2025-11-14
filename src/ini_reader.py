import configparser
from typing import TypeAlias

ConfigData: TypeAlias = configparser.ConfigParser


def load_config(file_name: str) -> ConfigData:
    config_data = configparser.ConfigParser()
    config_data.read(file_name)
    return config_data


def find_comport_device(config_data: ConfigData, header: str) -> tuple[str, str]:
    device = config_data.get(header, 'device')
    com_port = config_data.get(header, 'port')
    return device, com_port


def get_rf_settings(
    config_data: ConfigData, header: str = 'RFSettings'
) -> tuple[str, str, str]:
    min_freq = config_data.get(header, 'min_freq')
    max_freq = config_data.get(header, 'max_freq')
    max_power = config_data.get(header, 'max_power')
    return min_freq, max_freq, max_power


if __name__ == '__main__':
    ini_file = 'configuration/rf_controller.ini'

    config_data = load_config(ini_file)
    rf_generator = find_comport_device(config_data, 'RFGenerator')
    vrg_settings = get_rf_settings(config_data)

    rf_device, rf_com_port = rf_generator
    min_freq, max_freq, max_power = vrg_settings

    print(f'{rf_device = }')
    print(f'{rf_com_port = }')
    print(f'{min_freq = } MHz')
    print(f'{max_freq = } MHz')
    print(f'{max_power = } W')
