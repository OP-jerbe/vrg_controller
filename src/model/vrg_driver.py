"""
vrg_driver.py

Description: This driver contains the VRG class which can control the
             Oregon Physics variable frequency RF generator.

Built with Python version 3.13.3

Author: Joshua Erbe
Company: Oregon Physics, LLC.
Version 1.0.0
"""

from threading import Lock
from typing import Optional

import serial


class VRG:
    """
    Class that implements the driver for the Variable Frequency RF Generator (VRG),
    Args:
        port (str | None): The COM port where the VRG is connected. Default is None.
        freq_range (tuple(float | float)): The operating frequency range in MHz. Default is (25, 42). Set in firmware at factory.
        max_power (int): The maximum power output in watts. Default is 800. Set in firmware at factory.

    ***Example usage:***
    >>> vrg = VRG('COM1')               # Connects to the VRG on COM1.
    >>> vrg.ping()                      # Returns "WAZOO!" (used to safely verify communication with VRG).
    >>> vrg.set_abs_mode()              # Sets the power delivery mode to absorbed mode (preferred).
    >>> vrg.freq                        # Reads the current frequency setting (e.g. 38.45 MHz).
    >>> vrg.freq = 39.20                # Sets the frequency to 39.20 MHz.
    >>> vrg.autotune()                  # Asks the vrg to find the optimal frequency for minimum reflected power.
    >>> vrg.power                       # Reads the current power setting (e.g. 500 W).
    >>> vrg.power = 300                 # Sets the power output to 300 W.
    >>> vrg.is_enabled                  # Reads the state of the enable switch on the front panel (True[Up/On] or False[Down/Off]).
    >>> vrg.is_interlocked              # Reads the state of the interlock circuit (True[interlocked] or False[interlock satisfied]).
    >>> vrg.is_output_enabled           # Reads the state of the software's output enabled signal (True if enabled, False if not).
    >>> vrg.is_output_enabled = True    # Enables RF power output.
    >>> vrg.fwd_power                   # Reads the forward power delivered to the load.
    >>> vrg.rfl_power                   # Reads the power reflected by the load.
    >>> vrg.abs_power                   # Reads the power absorbed by the load (forward minus reflected power).
    >>> vrg.is_output_enabled = False   # Disables the RF power output.
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
        """
        Sends a command string to the VRG without expecting a response.

        Args:
            command (str): The command string to send to the instrument.
                The carriage return termination character is appended automatically.
        """
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
                raise ConnectionError(f'Serial Communication Error\n\n{str(e)}')

        print(f'Command: "{command.strip()}"')

    def _send_query(self, query: str) -> str:
        """
        Sends a query command to the VRG, reads the response, and handles unsolicited output.

        Args:
            query (str): The query command string to send.
                The carriage return termination character is appended automatically.

        Returns:
            str: The decoded and stripped string response received from the instrument.
        """
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
        Reads data from the serial port until the carriage return termination character is found.

        Returns:
            str: The decoded and stripped line of response data.
        """
        if not self.serial_port:
            raise RuntimeError('No serial port connection.')

        return (
            self.serial_port.read_until(self._term_char.encode('utf-8'))
            .decode('utf-8')
            .strip()
        )

    @staticmethod
    def open_connection(
        port: str, baudrate: int = 9600, timeout: float = 1.0
    ) -> serial.Serial | None:
        """
        Establishes a serial connection to the instrument at the specified COM port.

        Args:
            port (str): The COM port where the VRG is connected (e.g., 'COM3' or '/dev/ttyUSB0').
                The port name is automatically converted to uppercase.
            baudrate (int): The serial communication baud rate in bits per second. Defaults to 9600.
            timeout (float): The read and write timeout in seconds. Defaults to 1.0.

        Returns:
            serial.Serial | None: The active `serial.Serial` object if the connection is successful,
                or None if the connection attempt failed.
        """
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
        """
        Clears (flushes) the input buffer of the serial port, discarding any data
        that may have been received but not yet read.
        """
        if not self.serial_port or not self.serial_port.is_open:
            return

        with self._lock:
            self.serial_port.reset_input_buffer()

    ####################################################################################
    ################################ VRG Commands ######################################
    ####################################################################################

    def ping(self) -> str:
        """
        Sends a simple ping command to the VRG to check for communication and response.

        Returns:
            str: The raw response from the instrument, which is expected to be "WAZOO!".
        """
        command = '!'
        return self._send_query(command)

    def enable_echo(self) -> None:
        """
        Enables command echoing from the VRG. When enabled, the instrument repeats
        the command sent back to the driver before executing it.
        """
        command = 'EE'
        self._send_command(command)

    def disable_echo(self) -> None:
        """
        Disables command echoing from the VRG. The instrument will not repeat the
        command sent back to the driver.
        """
        command = 'DE'
        self._send_command(command)

    def set_fwd_mode(self) -> None:
        """
        Sets the power output display mode to **Forward** mode.

        This mode corresponds to a **white background** on the instrument's display.
        """
        command = 'PM0'
        self._send_command(command)

    def set_abs_mode(self) -> None:
        """
        Sets the power output display mode to **Absorbed** mode.

        This mode corresponds to a **black background** on the instrument's display,
        showing the power actually absorbed by the load (Forward Power - Reflected Power).
        """
        command = 'PM1'
        self._send_command(command)

    def autotune(self) -> None:
        """
        Initiates a broad Autotune procedure on the VRG.

        This command tells the instrument to search across a wide frequency range
        to find the frequency at which the reflected power is minimized.
        """
        command = 'TW'
        self._send_command(command)

    def narrow_autotune(self) -> None:
        """
        Initiates a narrow Autotune procedure on the VRG.

        This command is similar to `autotune` but restricts the search window to a smaller freqency window.
        """
        command = 'TT'
        self._send_command(command)

    # --- Hardware Status Getters ---

    @property
    def is_enabled(self) -> bool:
        """
        GETTER: Reads the state of the physical enable toggle switch on the VRG.

        Returns:
            bool: True if the enable switch is in the 'up' (ON) position, False if in the 'down' (OFF) position.
        """
        status_int = self.status_byte
        # Third from the last char is the enable switch I/O bit.
        enable_bit: str = bin(status_int)[-3]  # convert to binary string
        return enable_bit == '1'

    @property
    def is_overtemp(self) -> bool:
        """
        GETTER: Reads the internal overtemperature protection status of the VRG.

        Returns:
            bool: True if the VRG is currently reporting an overtemperature condition, False otherwise.
        """
        status_int = self.status_byte
        # second from the last char is the overtemp bit
        overtemp_bit: str = bin(status_int)[-2]  # convert to binary string
        return overtemp_bit == '1'

    @property
    def is_interlocked(self) -> bool:
        """
        GETTER: Reads the status of the safety interlock circuit.

        Returns:
            bool: True if the safety interlock is open (circuit interrupted), False if the interlock is closed (safe).
        """
        status_int = self.status_byte
        # Last char is the interlock bit.
        interlock_bit: str = bin(status_int)[-1]  # convert to binary string
        return interlock_bit == '1'

    @property
    def is_overcurrent(self) -> bool:
        """
        GETTER: Reads the internal overcurrent protection status of the VRG.

        Returns:
            bool: True if the VRG is currently reporting an overcurrent condition, False otherwise.
        """
        # The second item in the status list is the status byte.
        status_int = int(self.status[1])
        # The fourth from the last char is the overcurrent I/O bit.
        overcurrent_bit: str = bin(status_int)[-4]  # convert to binary string
        return overcurrent_bit == '1'

    # --- Software RF output enabled setting ---

    @property
    def output_enabled(self) -> bool:
        """
        GETTER: Reads the software RF output enabled state.

        Returns:
            bool: True if the software output is enabled, False otherwise.
        """
        # The second item in the status list is the status byte.
        status_int = int(self.status[1])
        # The last char is the software enabled bit.
        enable_bit: str = bin(status_int)[-1]  # convert to binary string
        return enable_bit == '1'

    @output_enabled.setter
    def output_enabled(self, enable: bool) -> None:
        """
        SETTER: Writes the enable state in the software to allow or disallow RF output.

        Args:
            enable (bool): Boolean state to set the software RF output control.
                True enables the output ('ER' command); False disables it ('DR' command).
        """
        if not isinstance(enable, bool):
            raise TypeError(f'Expected bool but got {type(enable).__name__}.')
        if enable:
            command = 'ER'
        else:
            command = 'DR'
        self._send_command(command)

    # --- Power Setting ---

    @property
    def power(self) -> int:
        """
        GETTER: Reads the currently set output power level of the VRG.

        Returns:
            int: The configured power level in watts (W).
        """
        command = 'RO'
        response = self._send_query(command).replace(command, '').strip()
        return int(float(response))

    @power.setter
    def power(self, value: int) -> None:
        """
        SETTER: Sets the desired power output level of the VRG.

        Args:
            value (int): Desired power level in watts (W). The value must be between 0 and
                the maximum configured power (`self._max_power`).
        """
        if not isinstance(value, int):
            raise TypeError(f'Expected int, but got {type(value).__name__}')

        if not (0 <= value <= self._max_power):
            raise ValueError(
                f'Power setting {value} is out of the valid range (0-{self._max_power} W)'
            )

        command = f'SP{value:04d}'
        self._send_command(command)

    # --- Frequency Setting ---

    @property
    def freq(self) -> float:
        """
        GETTER: Reads the currently set output frequency of the VRG.

        Returns:
            float: The configured frequency in megahertz (MHz).
        """
        command = 'RQ'
        response = self._send_query(command).replace(command, '').strip()
        return float(response) * 1e-3

    @freq.setter
    def freq(self, value: float) -> None:
        """
        SETTER: Sets the desired output frequency of the VRG.

        Args:
            value (int | float): Desired frequency setting in megahertz (MHz). The value must be
                within the currently allowed range (`self._min_freq` to `self._max_freq`).
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
        """
        GETTER: Reads the currently set minimum allowable output frequency of the VRG.

        Returns:
            float: The minimum frequency limit in megahertz (MHz).
        """
        command = 'R1'
        response = self._send_query(command).replace(command, '').strip()
        # Multiply by 1e-3 to convert kHz to MHz.
        self._min_freq = float(response) * 1e-3
        return self._min_freq

    @min_freq.setter
    def min_freq(self, value: float) -> None:
        """
        SETTER: Sets the minimum allowable output frequency within the VRG's hard frequency limits.

        Args:
            value (int | float): Desired minimum frequency limit in megahertz (MHz).
                Must be between within the frequency range set by the `freq_range` argument.
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
        """
        GETTER: Reads the currently set maximum allowable output frequency of the VRG.

        Returns:
            float: The maximum frequency limit in megahertz (MHz).
        """
        command = 'R2'
        response = self._send_query(command).replace(command, '').strip()
        # Multiply by 1e-3 to convert kHz to MHz.
        self._max_freq = float(response) * 1e-3
        return self._max_freq

    @max_freq.setter
    def max_freq(self, value: float) -> None:
        """
        SETTER: Sets the maximum allowable output frequency within the VRG's hard frequency limits.

        Args:
            value (int | float): Desired maximum frequency limit in megahertz (MHz).
                Must be between within the frequency range set by the `freq_range` argument.
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
        """
        GETTER: Reads the measured **Forward Power** output by the VRG.

        Returns:
            int: The forward power in watts (W).
        """
        command = 'RF'
        response = self._send_query(command).replace(command, '').strip()
        fwd_power = int(float(response))
        return fwd_power

    @property
    def rfl_power(self) -> int:
        """
        GETTER: Reads the measured **Reflected Power** (power returned from the load) by the VRG.

        Returns:
            int: The reflected power in watts (W).
        """
        command = 'RR'
        response = self._send_query(command).replace(command, '').strip()
        rfl_power = int(float(response))
        return rfl_power

    @property
    def abs_power(self) -> int:
        """
        GETTER: Reads the calculated **Absorbed Power** (Forward Power - Reflected Power).

        Returns:
            int: The absorbed power in watts (W).
        """
        command = 'RB'
        response = self._send_query(command).replace(command, '').strip()
        abs_power = int(float(response))
        return abs_power

    # --- Read unit infos ---

    @property
    def factory_info(self) -> str:
        """
        GETTER: Reads the raw factory information string from the VRG.

        The response is a space-separated string containing various operational and manufacturing data:

        Example: "607 00171 022426 017180 00000 00000"

        * **Serial Number:** First value (e.g., '607')
        * **Number of Reboots:** Second value (e.g., '00171')
        * **Operating Hours:** Third value (e.g., '022426')
        * **Enabled Hours:** Fourth value (e.g., '017180')
        * **Unimplemented Options:** Remaining zero values.

        Returns:
            str: The raw, space-separated string of factory information from the instrument.
        """
        command = 'RI'
        return self._send_query(command).replace(command, '').strip()

    @property
    def status_byte(self) -> int:
        """
        GETTER: Reads the raw status byte from the VRG.

        This integer value contains the bitwise status of several key safety and operational indicators,
        including the **enable switch**, **overtemperature warning**, and **safety interlock** states.

        The returned integer corresponds to a bitmask where specific bits indicate the status:

        * **Bit 0 (LSB):** Interlock Status (1 = Unsatisfied/Open; 0 = Satisfied/Closed)
        * **Bit 1:** Overtemperature Warning (1 = Warning/Active; 0 = Normal)
        * **Bit 2:** Enable Switch Position (1 = Up/ON; 0 = Down/OFF)

        All possible states for these three bits:
        0 (000): Enable OFF, Overtemp OFF, Interlock Satisfied
        1 (001): Enable OFF, Overtemp OFF, Interlock Unsatisfied
        2 (010): Enable OFF, Overtemp ON, Interlock Satisfied
        3 (011): Enable OFF, Overtemp ON, Interlock Unsatisfied
        4 (100): Enable ON, Overtemp OFF, Interlock Satisfied
        5 (101): Enable ON, Overtemp OFF, Interlock Unsatisfied
        6 (110): Enable ON, Overtemp ON, Interlock Satisfied
        7 (111): Enable ON, Overtemp ON, Interlock Unsatisfied

        Returns:
            int: An integer corresponding to the bitmask of the status indicators.
        """
        command = 'GS'
        response: str = self._send_query(command).replace(command, '').strip()
        status_byte = int(float(response))
        return status_byte

    @property
    def status(self) -> list[int | float]:
        """
        GETTER: Reads the comprehensive operational status of the VRG.

        The returned list contains various parameters related to firmware, internal voltages,
        temperatures, and power conditions, formatted as:

        [
            version_number (float),
            status_byte (int),
            5V_voltage (float),
            12V_voltage (float),
            main_power_voltage (float),
            main_power_current (float),
            amp_temperature (float),
            board_temperature (float)
        ]

        Note: The `status_byte` in this list is **not** the same as the value returned by
        the dedicated `status_byte` property (`GS` command). Consult the VRG manual
        for the specific bit definitions of this status byte.

        Returns:
            list[int | float]: A list of mixed integer and float values representing the
                current state of the instrument's operational parameters.
        """
        command = 'RT'
        response: str = self._send_query(command).replace(command, '').strip()
        status: list = response.split()
        status = [float(item) for item in status]
        status[1] = int(status[1])
        return status
