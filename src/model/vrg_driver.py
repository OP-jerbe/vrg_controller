from threading import Lock
from typing import Optional, cast

import pyvisa
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
        self.resource_name = resource_name
        self.instrument = instrument
        self.rm = pyvisa.ResourceManager('@py')

        if self.instrument is None and self.resource_name is not None:
            self.instrument = self.open_connection(self.resource_name)
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
            except Exception as e:
                raise ConnectionError(f'Serial Communication Error: {e}')

        print(f'Query: "{query}"\nResponse:')
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

        Returns:
            str: command string ("SFnnnnn")
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

    def read_fwd_power(self) -> str:
        command = 'RF'
        return self._send_query(command)

    def read_rfl_power(self) -> str:
        command = 'RR'
        return self._send_query(command)

    def read_abs_power(self) -> str:
        command = 'RB'
        return self._send_query(command)

    def read_factory_info(self) -> str:
        command = 'RI'
        return self._send_query(command)

    def read_status_byte(self) -> str:
        command = 'GS'
        return self._send_query(command)

    def read_status(self) -> str:
        command = 'RT'
        return self._send_query(command)

    ####################################################################################
    ########################### Read Settings Commands #################################
    ####################################################################################

    def read_power_setting(self) -> str:
        command = 'RO'
        return self._send_query(command)

    def read_freq_setting(self) -> str:
        command = 'RQ'
        return self._send_query(command)

    def read_min_freq_setting(self) -> str:
        command = 'R1'
        return self._send_query(command)

    def read_max_freq_setting(self) -> str:
        command = 'R2'
        return self._send_query(command)


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
