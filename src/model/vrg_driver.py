from threading import Lock
from typing import Optional

import serial


class VRG:
    """
    Class that implements the driver for the Variable Frequency RF Generator (VRG),
    using pyserial instead of pyvisa.
    """

    def __init__(
        self,
        port: Optional[str] = None,
        baudrate: int = 9600,
        timeout: float = 1.0,
        freq_range: tuple[int | float, int | float] = (25, 42),
        max_power: int = 1000,
    ) -> None:
        self.port_name = port
        self.serial_port: Optional[serial.Serial] = None

        if self.port_name is not None:
            self.serial_port = self._open_connection(self.port_name, baudrate, timeout)

        self.lock = Lock()

        self.min_freq_limit = freq_range[0]
        self.max_freq_limit = freq_range[1]
        self.min_freq_setting = self.min_freq_limit
        self.max_freq_setting = self.max_freq_limit
        self.max_power_setting = max_power

        self.read_termination = '\r'
        self.write_termination = '\r'

    def _open_connection(
        self, port: str, baudrate: int, timeout: float
    ) -> serial.Serial:
        ser = serial.Serial(
            port=port, baudrate=baudrate, timeout=timeout, write_timeout=timeout
        )
        self.serial_port = ser
        return ser

    def _send_command(self, command: str) -> None:
        if not self.serial_port or not self.serial_port.is_open:
            raise RuntimeError(
                'Attempted to communicate with VRG, but no instrument is connected.'
            )

        with self.lock:
            try:
                full_command = command + self.write_termination
                self.serial_port.write(full_command.encode('utf-8'))
            except Exception as e:
                raise ConnectionError(f'Serial Communication Error: {e}')

        print(f'Command: "{command.strip()}"')

    def _send_query(self, query: str) -> str:
        if not self.serial_port or not self.serial_port.is_open:
            raise RuntimeError(
                'Attempted to communicate with VRG, but no instrument is connected.'
            )

        with self.lock:
            try:
                full_query = query + self.write_termination
                self.serial_port.reset_input_buffer()
                self.serial_port.write(full_query.encode('utf-8'))
                response = self._readline()

                # Handle unsolicited output
                while 'target' in response:
                    print(
                        f'    Received unexpected unsolicited output.\n    {query = }\n    {response = }'
                    )
                    self.serial_port.reset_input_buffer()
                    self.serial_port.write(full_query.encode('utf-8'))
                    response = self._readline()

            except Exception as e:
                print(f'Unexpected Error sending query: {e}')
                raise

        return response

    def _readline(self) -> str:
        """
        Read until the termination character is found.
        """
        line = bytearray()
        if self.serial_port:
            while True:
                char = self.serial_port.read(1)
                if not char:
                    break  # Timeout occurred
                line += char
                if char.decode('utf-8') == self.read_termination:
                    break
            return line.decode('utf-8').strip()
        else:
            return ''

    def flush_input_buffer(self) -> None:
        if not self.serial_port or not self.serial_port.is_open:
            return

        with self.lock:
            self.serial_port.reset_input_buffer()

    ####################################################################################
    ################################ ATTN Command ######################################
    ####################################################################################

    def ping(self) -> str:
        command = '!'
        return self._send_query(command)

    ####################################################################################
    ################################ Set Commands ######################################
    ####################################################################################

    def enable_echo(self) -> None:
        command = 'EE'
        self._send_command(command)
        self.echo_on = True

    def disable_echo(self) -> None:
        command = 'DE'
        self._send_command(command)
        self.echo_on = False

    def enable_rf(self) -> None:
        command = 'ER'
        self._send_command(command)

    def disable_rf(self) -> None:
        command = 'DR'
        self._send_command(command)

    def set_fwd_mode(self) -> None:
        command = 'PM0'
        self._send_command(command)

    def set_abs_mode(self) -> None:
        command = 'PM1'
        self._send_command(command)

    def set_rf_power(self, power: int) -> None:
        """
        Set the RF power output setting.

        Args:
            power (int): the desired output power in watts
        """
        if not isinstance(power, int):
            raise TypeError(f'Expected an int, but got {type(power).__name__}')

        if not (0 <= power <= self.max_power_setting):
            raise ValueError(
                f'Input {power} is out of bounds. Must be between 0 and {self.max_power_setting}.'
            )
        command = f'SP{power:04}'
        self._send_command(command)

    def set_min_freq(self, freq: int | float) -> None:
        """
        Set the minimum frequency within the frequency limits (typically 25-42 MHz)

        Args:
            freq (int | float): the desired minimum freqency setting
        """
        if not isinstance(freq, int | float):
            raise TypeError(f'Expected an int or float, but got {type(freq).__name__}.')

        if not (self.min_freq_setting <= freq <= self.max_freq_setting):
            raise ValueError(
                f'Minimum Frequency of {freq} MHz is out of range. Minimum frequency must be between {self.min_freq_limit} and {self.max_freq_limit} MHz.'
            )

        freq_kHz = int(freq * 1000)
        command = f'S1{freq_kHz:05d}'
        self._send_command(command)

    def set_max_freq(self, freq: int | float) -> None:
        """
        Set the maximum frequency within the frequency limits (typically 25-42 MHz)

        Args:
            freq (int | float): the desired maximum freqency setting
        """
        if not isinstance(freq, int | float):
            raise TypeError(f'Expected an int or float, but got {type(freq).__name__}.')

        if not (self.min_freq_setting <= freq <= self.max_freq_setting):
            raise ValueError(
                f'Maximum Frequency of {freq} MHz is out of range. Maximum frequency must be between {self.min_freq_limit} and {self.max_freq_limit} MHz.'
            )

        freq_kHz = int(freq * 1000)
        command = f'S2{freq_kHz:05d}'
        self._send_command(command)

    def set_freq(self, freq: int | float) -> None:
        """
        Set the frequency setting

        Args:
            freq (int | float): frequency setting in MHz
        """
        if not isinstance(freq, int | float):
            raise TypeError(f'Expected an int or float, but got {type(freq).__name__}')

        if not (self.min_freq_setting <= freq <= self.max_freq_setting):
            raise ValueError(
                f'Frequency {freq} MHz is out of range. Must be between {self.min_freq_setting:.2f} and {self.max_freq_setting:.2f} MHz.'
            )

        freq_kHz = int(freq * 1000)
        command = f'SF{freq_kHz:05d}'
        self._send_command(command)

    def autotune(self) -> None:
        command = 'TW'
        self._send_command(command)

    def narrow_autotune(self) -> None:
        command = 'TT'
        self._send_command(command)

    ####################################################################################
    ############################ Read State Commands ###################################
    ####################################################################################

    def read_fwd_power(self) -> int | None:
        command = 'RF'
        response = self._send_query(command).replace(command, '').strip()
        try:
            fwd_power = int(float(response))
            return fwd_power
        except ValueError as ve:
            print(f'    Error converting fwd power to int: {ve}')

    def read_rfl_power(self) -> int | None:
        command = 'RR'
        response = self._send_query(command).replace(command, '').strip()
        try:
            rfl_power = int(float(response))
            return rfl_power
        except Exception as e:
            print(f'    Error converting rfl power to int: {e}')

    def read_abs_power(self) -> int | None:
        command = 'RB'
        response = self._send_query(command).replace(command, '').strip()
        try:
            abs_power = int(float(response))
            return abs_power
        except Exception as e:
            print(f'    Error converting abs power to int: {e}')

    def read_factory_info(self) -> str:
        command = 'RI'
        return self._send_query(command)

    def read_status_byte(self) -> int:
        """
        Get the status byte from the VRG. For example, if theenable switch is off, the
        over temp warning is not on, and the interlock is not tripped, the byte
        generated will be `00000000` so the integer returned will be `0`. If the enable
        switch is on, the over temp warning is on, and the interlock is tripped, the
        byte generated will be `00000111`, so the integer returned will be `7`.

        Returns:
            int: a number that corresponds the bitwise integer built from the position of
            the enable switch, over temp state, and interlock state.
        """
        command = 'GS'
        response: str = self._send_query(command).replace(command, '').strip()
        status_byte = int(float(response))
        return status_byte

    def read_status(self) -> list[float | list[int]]:
        """
        Read the status of the VRG. The status list includes:
        [version number, status byte, 5V voltage, 12V voltage, main power volage, main power current, amp temperature, board temperature]
        [float         , int        , float     , float      , float            , float             , float          , float            ]
        Returns:
            list: List of statuses
        """
        command = 'RT'
        response: str = self._send_query(command)
        status: list = response.split()
        status = [float(item) for item in status]
        status[1] = int(status[1])
        return status

    ####################################################################################
    ########################### Read Settings Commands #################################
    ####################################################################################

    def read_power_setting(self) -> int | None:
        command = 'RO'
        response = self._send_query(command).replace(command, '').strip()
        try:
            power_setting = int(float(response))
            return power_setting
        except TypeError as te:
            print(f'    Error converting power setting to int: {te}')

    def read_freq_setting(self) -> float | None:
        command = 'RQ'
        response = self._send_query(command).replace(command, '').strip()
        try:
            # Multiply response by 1e-3 to convert to MHz
            freq_setting = float(response) * 1e-3
            return freq_setting
        except TypeError as te:
            print(f'    Error converting freq setting to float: {te}')

    def read_min_freq_setting(self) -> float | None:
        command = 'R1'
        response = self._send_query(command).replace(command, '').strip()
        try:
            min_freq = float(response) * 1e-3
            return min_freq
        except TypeError as te:
            print(f'    Error converting min freq to float: {te}')

    def read_max_freq_setting(self) -> float | None:
        command = 'R2'
        response = self._send_query(command).replace(command, '').strip()
        try:
            max_freq = float(response) * 1e-3
            return max_freq
        except TypeError as te:
            print(f'    Error converting max freq to float: {te}')


# Read command examples
# =============================================================================
# print(vrg.send_query('RQ')) # Read Frequency returns "RQ40650" for 40.65 MHz
# print(vrg.send_query('RO')) # Read Power Setting returns "RO0800" for 800 W
# print(vrg.send_query('R1')) # Read Min tune frequency returns "R125000"
# print(vrg.send_query('R2')) # Read Max tune frequency returns "R242000"
# print(vrg.send_query('RF')) # Read Forward Power returns "RF0000" when not enabled
# print(vrg.send_query('RR')) # Read Reflected Power returns "RF0000" when not enabled
# print(vrg.send_query('RB')) # Read Absorbed Power returns "RB0000.1" when not enabled
# print(vrg.send_query('RI')) # Read Factory Information returns "RI607 00171 022426 017180 00000 00000" 607 is serial number, 171 is num of reboots, 22426 is operating hours, 17180 is enabled hours, zeros are unimplementd options
# =============================================================================

# Write command examples
# =============================================================================
# vrg.send_command('ER') # Enable RF
# vrg.send_command('DR') # Disable RF
# vrg.send_command('PM0') # Set Power Control Mode to Forward Power Mode
# vrg.send_command('PM1') # Set Power Control Mode to Absorbed Power Mode
# vrg.send_command('TW') # Trigger a wide range auto tune (typically used)
# vrg.send_command('TT') # Trigger an narrow range auto tune
# vrg.send_command('SP0600') # Set RF power to 600 W
# vrg.send_command('SP0800') # Set RF power to 800 W
# vrg.send_command('SF41000') # Set frequency to 41.00 MHz
# vrg.send_command('SF40650') # Set frequency to 40.65 MHz
# =============================================================================
