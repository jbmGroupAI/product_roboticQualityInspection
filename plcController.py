# plcController.py

# Corrected import statement
from pymodbus.client import ModbusTcpClient
from pymodbus.exceptions import ModbusIOException

import time
import threading
import logging


class PlcCommunicate:
    """
    Class for communication with a PLC using Modbus TCP protocol.
    """

    def __init__(self, ip, port):
        """
        Initializes the PlcCommunicate object.

        Parameters:
        - ip (str): PLC IP address.
        - port (int): PLC port number.
        """
        self.plc_ip = ip
        self.plc_port = port
        self.client = None
        self.lock = threading.Lock()  # Lock to control PLC access
        self.connectionStatus = False

    def check_connection(self):
        """
        Checks whether the client is connected to the PLC.

        Returns:
        - bool: True if connected, False otherwise.
        """
        with self.lock:
            return self.client is not None and self.client.is_socket_open()

    def reconnect(self):
        """
        Reconnects to the PLC if the client is not connected.

        Returns:
        - bool: True if reconnected successfully, False otherwise.
        """
        with self.lock:
            if self.client is not None and not self.client.is_socket_open():
                self.client.close()
            self.client = ModbusTcpClient(self.plc_ip, port=self.plc_port)
            return self.client.connect()

    def connect(self):
        """
        Establishes a connection to the PLC.

        Returns:
        - bool: True if connected successfully, False otherwise.
        """
        with self.lock:
            try:
                self.client = ModbusTcpClient(self.plc_ip, port=self.plc_port)
                status = self.client.connect()
                self.connectionStatus = status
                return status
            except Exception as e:
                logging.error(f"Error in PLC Connect: {e}")
                time.sleep(5)
                return False

    def read_registers(self, address):
        if not self.check_connection():
            logging.warning("PLC not connected. Attempting to reconnect.")
            if not self.reconnect():
                logging.error("Unable to reconnect to PLC.")
                return []

        with self.lock:
            try:
                request_plc = self.client.read_holding_registers(address, count=1)

                #request_plc = self.client.read_holding_registers(address, 10)
                result = request_plc.registers
                return result[0]
            except Exception as e:
                logging.error(f"Error in PLC Read at address {address}: {e}")
                return []

    def read_all_bits(self, address):
        try:
            num_registers = 1
            bits_per_register = 10

            request_plc = self.client.read_holding_registers(address, num_registers)
            registers = request_plc.registers

            all_bits = []
            for reg_value in registers:
                for i in range(bits_per_register):
                    # Extract each bit using bitwise operations
                    bit_value = (reg_value >> i) & 0x01
                    all_bits.append(bit_value)

            return all_bits
        except Exception as e:
            print("Error in PLC Read All Bits", e)
            return []

    def write(self, address, value, sleep_time=0.01):
        """
        Writes a value to a register at the specified address in the PLC.

        Parameters:
        - address (int): Address of the register to be written.
        - value (int): Value to be written to the register.
        - sleep_time (float): Optional sleep time after the write operation.

        Returns:
        - str: "Success" if the operation is successful, "Fail" otherwise.
        """
        if not self.check_connection():
            logging.warning("PLC not connected. Attempting to reconnect.")
            if not self.reconnect():
                logging.error("Unable to reconnect to PLC.")
                return "Fail"

        with self.lock:
            try:
                self.client.write_register(address=address, value=value, unit=3)
                time.sleep(sleep_time)
                # logging.info(f"Write operation successful at address {address}")
                return "Success"
            except ModbusIOException as modbus_exception:
                logging.error(
                    f"Modbus IO error in PLC Write at address {address}: {modbus_exception}"
                )
                return "Fail"
            except Exception as e:
                logging.error(f"Error in PLC Write at address {address}: {e}")
                return "Fail"

    def close(self):
        """
        Closes the connection to the PLC.
        """
        with self.lock:
            if self.client is not None:
                self.client.close()
