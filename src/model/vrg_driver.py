from threading import Lock
from typing import Optional, cast

import pyvisa
import pyvisa.constants
from pyvisa.resources import MessageBasedResource


class VRG:
    """
    Class that implements the driver for the Oregon Physics Variable Frequency RF Generator (VRG).
    The driver implements the following 23 commands:

    ATTN COMMAND:
    * !: ping the VRG (returns `"WAZOO!"`)

    SET COMMANDS:
    * DE: disable echo
    * EE: enable echo
    * ER: enable RF power
    * DR: disable RF power
    * PM0: set forward power mode
    * PM1: set absorbed power mode
    * SPnnnn: set RF power in watts
    * S1nnnnn: set minimum allowable frequency setting
    * S2nnnnn: set maximum allowable frequency setting
    * SFnnnnn: set frequency in kHz
    * TW: wide-band autotune
    * TT: narrow-band autotune

    READ STATE COMMANDS:
    * RF: read forward power output
    * RR: read reflected power
    * RB: read absorbed power
    * RI: read factory information (serial number, num of boots, run hours, enabled hours, mas RF temp, shutdowns)
    * GS: read the status byte (RF on, overtemp, RF interlock error)
    * RT: read status: (version num, status [binary bit field], 5V voltage, 12V voltage, main power voltage, main power current, op-amp current, board temp)

    READ SETTINGS COMMANDS:
    * RO: read power setting
    * RQ: read frequency setting
    * R1: read minimum allowable frequency setting
    * R2: read maximum allowable frequency setting
    """

    def __init__(
        self,
        resource_name: Optional[str] = None,
        instrument: Optional[MessageBasedResource] = None,
        freq_range: tuple[int | float, int | float] = (25, 42),
        max_power: int = 1000,
    ) -> None:
        # Get the resource name and instrument
        self.resource_name = resource_name
        self.instrument = instrument

        # Use '@py' as the resource manager from pyvisa-py library (hidden import)
        self.rm = pyvisa.ResourceManager('@py')

        # Make a connection to the instrument if a resource name was given
        if self.instrument is None and self.resource_name is not None:
            self.instrument = self.open_connection(self.resource_name)

        # Create the threading lock object
        self.lock = Lock()

        # Set the hard frequecy limit range in MHz
        self.min_freq_limit = freq_range[0]
        self.max_freq_limit = freq_range[1]

        # Set the valid frequency setting range
        self.min_freq_setting = self.min_freq_limit
        self.max_freq_setting = self.max_freq_limit

        # Set the maximum allowable power setting in Watts
        self.max_power_setting = max_power

    def _send_query(self, query: str) -> str:
        """
        Send a command to the instrument and read the response.

        Args:
            query (str): query string to send to the VRG.

        Returns:
            str: Response from the instrument
        """
        if not self.instrument:
            raise RuntimeError(
                'Attempted to communicate with VRG, but no instrument is connected.'
            )

        with self.lock:
            try:
                self.instrument.write(query)
                response = self.instrument.read()

                # Check for spammy or unsolicited output and send the command again
                while 'target' in response:
                    print(
                        f'    Received unexpected unsolicited output.\n    {query = }\n    {response = }'
                    )
                    self.instrument.write(query)
                    response = self.instrument.read()

            except ConnectionError as ce:
                print(f'Serial Communication Error: {ce}')
                raise
            except Exception as e:
                print(f'Unexpected Error sending query: {e}')
                raise

        print(f'Query: "{query}"\nResponse: "{response}"')
        return response

    def _send_command(self, command: str) -> None:
        """
        Send a command to the instrument.

        Args:
            command (str): Command string to send to the VRG.

        Returns:
            None
        """
        if not self.instrument:
            raise RuntimeError(
                'Attempted to communicate with VRG, but no instrument is connected.'
            )

        with self.lock:
            try:
                self.instrument.write(command)
            except Exception as e:
                raise ConnectionError(f'Serial Communication Error: {e}')

        print(f'Command: "{command.strip("\n")}"')

    def open_connection(self, resource_name: str) -> MessageBasedResource:
        self.instrument = cast(
            MessageBasedResource, self.rm.open_resource(resource_name)
        )
        self.instrument.read_termination = '\r'
        self.instrument.write_termination = '\r'
        return self.instrument

    def flush_input_buffer(self) -> None:
        """
        Flush any unread data from the device's input buffer.
        Useful if previous reads were incomplete or out of sync.
        """
        if not self.instrument:
            return

        with self.lock:
            try:
                while True:
                    self.instrument.read_bytes(1024, break_on_termchar=False)
            except pyvisa.errors.VisaIOError as e:
                # Expected when no more data is available
                if e.error_code != pyvisa.constants.VI_ERROR_TMO:
                    raise

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
        Set the maximim frequency within the frequency limits (typically 25-42 MHz)

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
