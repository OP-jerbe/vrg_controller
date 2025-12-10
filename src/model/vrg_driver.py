from threading import Lock
from typing import Optional

import serial


class VRG:
    """
    Class that implements the driver for the Variable Frequency RF Generator (VRG),
    Args:
        port (str | None): The COM port where the VRG is connected. Default is None.
        freq_range (tuple(float | float)): The operating frequency range in MHz. Default is (25, 42). Set in hardware at factory.
        max_power (int): The maximum power output in watts. Default is 800. Set in hardware at factory.
    """

    def __init__(
        self,
        com_port: Optional[str] = None,
        freq_range: tuple[float, float] = (25, 42),
        max_power: int = 800,
    ) -> None:
        self._lock = Lock()
        self._com_port = com_port
        self._min_freq_hard_limit = freq_range[0]
        self._max_freq_hard_limit = freq_range[1]
        self._max_power = max_power
        self._power_mode: int  # 0 = forward power mode, 1 = absorbed power mode

        # Init the allowable frequency range to be the hardware frequency limits.
        self._min_freq = self._min_freq_hard_limit
        self._max_freq = self._max_freq_hard_limit

        # Termination character for serial read/write
        self._term_char = '\r'

        # Try to connect to the VRG if a COM port was given.
        self.serial_port: Optional[serial.Serial] = None
        if self._com_port is not None:
            self.serial_port = self.open_connection(self._com_port)

    ####################################################################################
    ############################### Serial Commands ####################################
    ####################################################################################

    def _send_command(self, command: str) -> None:
        if not self.serial_port or not self.serial_port.is_open:
            raise RuntimeError(
                'Attempted to communicate with VRG, but no instrument is connected.'
            )

        if not command.endswith(self._term_char):
            command += self._term_char

        with self._lock:
            try:
                self.serial_port.write(command.encode('utf-8'))
            except Exception as e:
                raise ConnectionError(f'Serial Communication Error: {e}')

        print(f'Command: "{command.strip()}"')

    def _send_query(self, query: str) -> str:
        if not self.serial_port or not self.serial_port.is_open:
            raise RuntimeError(
                'Attempted to communicate with VRG, but no instrument is connected.'
            )
        if not query.endswith(self._term_char):
            query += self._term_char

        with self._lock:
            try:
                self.serial_port.reset_input_buffer()
                self.serial_port.write(query.encode('utf-8'))
                response = self._readline()

                # Handle unsolicited output.
                # Sometimes VRG outputs weird, spammy respoonses repeating "target".
                # This while-loop throws that garbage away and resends the query.
                while 'target' in response:
                    print(
                        f'    Received unexpected unsolicited output.\n    {query = }\n    {response = }'
                    )
                    self.serial_port.reset_input_buffer()
                    self.serial_port.write(query.encode('utf-8'))
                    response = self._readline()

            except Exception as e:
                print(f'Unexpected Error sending query: {e}')
                raise

        return response

    def _readline(self) -> str:
        """
        Read until the carriage return termination character is found.
        """
        if not self.serial_port or not self.serial_port.is_open:
            raise RuntimeError(
                'Attempted to communicate with VRG, but no instrument is connected.'
            )

        return (
            self.serial_port.read_until(self._term_char.encode('utf-8'))
            .decode('utf-8')
            .strip()
        )

    def open_connection(
        self, port: str, baudrate: int = 9600, timeout: float = 1.0
    ) -> serial.Serial | None:
        try:
            return serial.Serial(
                port=port.upper(),
                baudrate=baudrate,
                timeout=timeout,
                write_timeout=timeout,
            )

        except Exception as e:
            print(f'Failed to make a serial connection to {port}.\n\n{str(e)}')
            return None

    def flush_input_buffer(self) -> None:
        if not self.serial_port or not self.serial_port.is_open:
            return

        with self._lock:
            self.serial_port.reset_input_buffer()

    ####################################################################################
    ################################ VRG Commands ######################################
    ####################################################################################

    def ping(self) -> str:
        command = '!'
        return self._send_query(command)

    def enable_echo(self) -> None:
        command = 'EE'
        self._send_command(command)

    def disable_echo(self) -> None:
        command = 'DE'
        self._send_command(command)

    def set_fwd_mode(self) -> None:
        """Sets the power output mode to Forward mode (white background screen)"""
        command = 'PM0'
        self._send_command(command)

    def set_abs_mode(self) -> None:
        """Sets the power output mode to Absorbed mode (black background screen)"""
        command = 'PM1'
        self._send_command(command)

    def autotune(self) -> None:
        """
        Tells the VRG to search for the frequency at which the reflected power
        is minimized.
        """
        command = 'TW'
        self._send_command(command)

    def narrow_autotune(self) -> None:
        """
        Tells the VRG to search for the frequency at which the reflected power
        is minimized. Similar to autotune but searches a smaller window.
        """
        command = 'TT'
        self._send_command(command)

    # --- Hardware Status Getters ---

    @property
    def is_enabled(self) -> bool:
        """GETTER: Reads the enable toggle switch state (True=up/on, False=down/off)."""
        status = self.status_byte
        # Third from the last char is the enable switch I/O bit.
        enable_bit: str = bin(status)[-3]
        return enable_bit == '1'

    @property
    def is_overtemp(self) -> bool:
        """GETTER: Reads the overtemp status."""
        status = self.status_byte
        # second from the last char is the overtemp bit
        overtemp_bit: str = bin(status)[-2]
        return overtemp_bit == '1'

    @property
    def is_interlocked(self) -> bool:
        """GETTER: Reads the interlock status."""
        status = self.status_byte
        # Last char is the interlock bit.
        interlock_bit: str = bin(status)[-1]
        return interlock_bit == '1'

    # --- Software RF output enabled setting ---

    @property
    def is_output_enabled(self) -> bool:
        """GETTER: Reads the software RF output enabled state."""
        # The second item in the status list is the status byte.
        status_byte = int(self.status[1])
        # The last char is the software enabled bit.
        enable_bit: str = bin(status_byte)[-1]
        return enable_bit == '1'

    @is_output_enabled.setter
    def is_output_enabled(self, enable: bool) -> None:
        """
        SETTER: Writes the enable state in the software to allow or disallow RF output.

        Args:
            enable (bool): Boolean to tell the VRG to output RF power.
        """
        if enable:
            command = 'ER'
        else:
            command = 'DR'
        self._send_command(command)

    # --- Power Setting ---

    @property
    def power(self) -> int:
        command = 'RO'
        response = self._send_query(command).replace(command, '').strip()

        try:
            return int(float(response))

        except TypeError as e:
            print(f'Error converting power setting to int\n\n{str(e)}')
            raise

        except Exception as e:
            print(f'Unexpected Error\n\n{str(e)}')
            raise

    @power.setter
    def power(self, value: int) -> None:
        """
        Set the power level of the VRG.

        Args:
            value (int): Desired power level in watts.
        """
        if not isinstance(value, int):
            raise TypeError(f'Expected an int, but got {type(value).__name__}')

        if not (0 <= value <= self._max_power):
            raise ValueError(
                f'Power setting {value} is out of the valid range (0-{self._max_power} W)'
            )

        command = f'SP{value:04d}'
        self._send_command(command)

    # --- Frequency Setting ---

    @property
    def freq(self) -> float:
        command = 'RQ'
        response = self._send_query(command).replace(command, '').strip()

        try:
            # Multiply response by 1e-3 to convert to MHz.
            return float(response) * 1e-3

        except TypeError as e:
            print(f'Error converting frequency setting to float\n\n{str(e)}')
            raise

        except Exception as e:
            print(f'Unexpected Error\n\n{str(e)}')
            raise

    @freq.setter
    def freq(self, value: int | float) -> None:
        """
        Set the frequency of the VRG.

        Args:
            freq (int | float): Frequency setting in MHz.
        """
        if not isinstance(value, int | float):
            raise TypeError(f'Expected an int or float, but got {type(value).__name__}')

        if not (self._min_freq <= value <= self._max_freq):
            raise ValueError(
                f'Frequency {value} MHz is out of range. Must be between {self._min_freq:.2f} and {self._max_freq:.2f} MHz.'
            )

        # Multiply by 1000 to convert MHz to kHz.
        freq_kHz = int(value * 1000)
        command = f'SF{freq_kHz:05d}'
        self._send_command(command)

    # --- Frequency Range Setting ---

    @property
    def min_freq(self) -> float:
        command = 'R1'
        response = self._send_query(command).replace(command, '').strip()

        try:
            # Multiply by 1e-3 to convert kHz to MHz.
            self._min_freq = float(response) * 1e-3
            return self._min_freq

        except TypeError as e:
            print(f'Error converting min freq to float\n\n{str(e)}')
            raise

        except Exception as e:
            print(f'Unexpected Error\n\n{str(e)}')
            raise

    @min_freq.setter
    def min_freq(self, value: int | float) -> None:
        """
        Set the minimum allowable frequency output within the the hard frequency limits (typically 25-42 MHz)

        Args:
            value (int | float): Desired minimum frequency in MHz.
        """
        if not isinstance(value, int | float):
            raise TypeError(
                f'Expected an int or float, but got {type(value).__name__}.'
            )

        if not (self._min_freq_hard_limit <= value <= self._max_freq_hard_limit):
            raise ValueError(
                f'Minimum Frequency of {value} MHz is out of range. Minimum frequency must be between {self._min_freq_hard_limit} and {self._max_freq_hard_limit} MHz.'
            )
        # Multiply by 1000 to convert to MHz to kHz.
        freq_kHz = int(value * 1000)
        command = f'S1{freq_kHz:05d}'
        self._send_command(command)
        self._min_freq = value

        # Make sure the freq setting isn't below the new minimum allowable freqency.
        if self.freq < self._min_freq:
            self.freq = self._min_freq

    @property
    def max_freq(self) -> float:
        command = 'R2'
        response = self._send_query(command).replace(command, '').strip()

        try:
            # Multiply by 1e-3 to convert kHz to MHz.
            self._max_freq = float(response) * 1e-3
            return self._max_freq

        except TypeError as e:
            print(f'Error converting max frequency to float\n\n{str(e)}')
            raise

        except Exception as e:
            print(f'Unexpected Error\n\n{str(e)}')
            raise

    @max_freq.setter
    def max_freq(self, value: int | float) -> None:
        """
        Set the maximum allowable frequency output within the the hard frequency limits (typically 25-42 MHz)

        Args:
            value (int | float): Desired maximum frequency in MHz.
        """
        if not isinstance(value, int | float):
            raise TypeError(
                f'Expected an int or float, but got {type(value).__name__}.'
            )

        if not (self._min_freq_hard_limit <= value <= self._max_freq_hard_limit):
            raise ValueError(
                f'Maximum Frequency of {value} MHz is out of range. Maximum frequency must be between {self._min_freq_hard_limit} and {self._max_freq_hard_limit} MHz.'
            )

        # Multiply by 1000 to convert MHz to kHz.
        freq_kHz = int(value * 1000)
        command = f'S2{freq_kHz:05d}'
        self._send_command(command)
        self._max_freq = value

        # Make sure the freq setting isn't above the new maximum allowable frequncy.
        if self.freq > self._max_freq:
            self.freq = self._max_freq

    # --- Read Power Output ---

    @property
    def fwd_power(self) -> int:
        """GETTER: Reads the forward power."""
        command = 'RF'
        response = self._send_query(command).replace(command, '').strip()
        fwd_power = int(float(response))
        return fwd_power

    @property
    def rfl_power(self) -> int:
        """GETTER: Reads the reflected power."""
        command = 'RR'
        response = self._send_query(command).replace(command, '').strip()
        rfl_power = int(float(response))
        return rfl_power

    @property
    def abs_power(self) -> int:
        """GETTER" Reads the absorbed power."""
        command = 'RB'
        response = self._send_query(command).replace(command, '').strip()
        abs_power = int(float(response))
        return abs_power

    # --- Read unit infos ---

    @property
    def factory_info(self) -> str:
        """
        GETTER: Reads the factory info.

        Read Factory Information example return: "607 00171 022426 017180 00000 00000"
        607 is serial number
        171 is num of reboots
        22426 is operating hours
        17180 is enabled hours
        zeros are unimplementd options
        """
        command = 'RI'
        return self._send_query(command).replace(command, '').strip()

    @property
    def status_byte(self) -> int:
        """
        Reads the status byte from the VRG. For example, if the enable switch is off (down),
        the over temp warning is not on, and the interlock is satisfied, the byte
        generated will be `00000000` so the integer returned will be `0`. If the enable
        switch is on (up), the over temp warning is on, and the interlock unsatisfied, the
        byte generated will be `00000111`, so the integer returned will be `7`.

        Returns:
            int: a number that corresponds to the bitwise integer built from the position of
            the enable switch, over temp state, and interlock state.
        """
        command = 'GS'
        response: str = self._send_query(command).replace(command, '').strip()
        status_byte = int(float(response))
        return status_byte

    @property
    def status(self) -> list[int | float]:
        """
        Reads the status of the VRG. The status list includes:
        [version number, status byte, 5V voltage, 12V voltage, main power voltage, main power current, amp temperature, board temperature]
        [float         , int        , float     , float      , float             , float             , float          , float            ]

        Note: `status byte` here is not the same as `read_status_byte`. See VRG manual for difference.

        Returns:
            list: List of statuses
        """
        command = 'RT'
        response: str = self._send_query(command).replace(command, '').strip()
        status: list = response.split()
        status = [float(item) for item in status]
        status[1] = int(status[1])
        return status
