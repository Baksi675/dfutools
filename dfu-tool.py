import typer
from serial import Serial
from serial.serialutil import SerialException
from pathlib import Path
import math
import os

FLASH_BASE = 0x08000000

ACK_CODE = 0xAA
NACK_CODE = 0xDD

CRC_LEN = 4

CMD_GET_VER = 0x01
CMD_GET_VER_LEN = 1 + CRC_LEN       # command code + crc

CMD_GET_CMDS = 0x02
CMD_GET_CMDS_LEN = 1 + CRC_LEN      # command code + crc

CMD_GET_CID = 0x03
CMD_GET_CID_LEN = 1 + CRC_LEN       # command code + crc

CMD_GET_RDP = 0x04              # command code + crc
CMD_GET_RDP_LEN = 1 + CRC_LEN

CMD_SET_RDP = 0x05
CMD_SET_RDP_LEN = 2 + CRC_LEN       # command code + enable status + crc

CMD_GET_WRP = 0x06
CMD_GET_WRP_LEN = 1 + CRC_LEN  # command code + crc

CMD_SET_WRP = 0x07
CMD_SET_WRP_LEN = 4 + CRC_LEN  # command code + start page + number of pages + crc 

CMD_ERASE = 0x08
CMD_ERASE_LEN = 3 + CRC_LEN   # command code + start page number + page number + crc

CMD_WRITE = 0x09
#CMD_WRITE_LEN                    # undefined

CMD_READ = 0x0A
CMD_READ_LEN = 6 + CRC_LEN       # command code + address + payload length + crc

CMD_PROGRAM = 0x0B
#CMD_PROGRAM_LEN               # undefined

CMD_JUMP = 0x0C
CMD_JUMP_LEN = 5 + CRC_LEN  # command code + address + crc

CMD_RST = 0x0D
CMD_RST_LEN = 1 + CRC_LEN           # command code + crc

app = typer.Typer()

def log_print(message: str) -> None:
    typer.echo(message)

def open_connection(port: str, baudrate: int) -> Serial:
    try:
        return Serial(port, baudrate, timeout=3)
    except SerialException as e:
        raise RuntimeError(f"Failed to open connection on {port}: {e}")

def calculate_crc(buff, length):
    crc = 0xFFFFFFFF

    for data in buff[:length]:
        crc ^= data

        for _ in range(32):
            if crc & 0x80000000:
                crc = (crc << 1) ^ 0x04C11DB7
            else:
                crc <<= 1

            crc &= 0xFFFFFFFF

    return crc

def handle_recv_packet(ser: Serial, debug: bool):
    msg_len = int.from_bytes(ser.read(1), "little")
    ack_info = int.from_bytes(ser.read(1), "little")

    if debug:
        log_print("received the following message")
        log_print(f"message length: {msg_len}")
        log_print(f"ack info: {hex(ack_info)}")

    if ack_info != ACK_CODE:
        return -1

    if msg_len < 5:
        return -1

    temp_data = ser.read(msg_len - 1)

    crc_bytes = temp_data[-4:]
    data = temp_data[:-4]

    if debug:
        log_print("data: " + " ".join(f"0x{b:02x}" for b in data))

    frame = bytearray()
    frame.append(msg_len)
    frame.append(ack_info)
    frame += data

    crc_recv = int.from_bytes(crc_bytes, "little")
    crc_calc = calculate_crc(frame, len(frame))

    if debug:
        log_print(f"crc: 0x{crc_recv:08x}\r\n")

    if crc_recv != crc_calc:
        return -1

    return data

def parse_hex(value: str) -> int:
    return int(value, 16)

@app.command()
def get_ver(
    port: str = typer.Option(..., "--port", "-p", help = "Device opened on serial port, e.g. /dev/ttyUSB0" ),
    baudrate: int = typer.Option(115200, "--baudrate", "-b", help = "Communication speed with target"),
    debug: bool = typer.Option(False, "--debug", "-d", help = "Enables the debug messages")
):
    """Get bootloader version."""

    packet_to_send = bytearray(255)
    packet_to_send[0] = CMD_GET_VER_LEN
    packet_to_send[1] = CMD_GET_VER

    crc = calculate_crc(packet_to_send, 2)
    packet_to_send[2:6] = crc.to_bytes(4, "little")

    try:
        with open_connection(port, baudrate) as ser:
            
            if debug:
                log_print("sending the following message")
                log_print(f"message length: {packet_to_send[0]}")
                log_print(f"command code: {hex(packet_to_send[1])}")
                log_print(f"crc: 0x{crc:08x}\r\n")

            ser.write(packet_to_send[:6])

            data_recv = handle_recv_packet(ser, debug)

            if data_recv == -1:
                raise typer.Exit(1)

            typer.echo(f"Bootloader version: {data_recv.decode("utf-8")}")

    except SerialException as e:
        typer.echo(f"Connection error: {e}")
        raise typer.Exit(1)

@app.command()
def get_cmds(
    port: str = typer.Option(..., "--port", "-p", help = "Device opened on serial port, e.g. /dev/ttyUSB0" ),
    baudrate: int = typer.Option(115200, "--baudrate", "-b", help = "Communication speed with target"),
    debug: bool = typer.Option(False, "--debug", "-d", help = "Enables the debug messages")
):
    """Get available command list."""

    packet_to_send = bytearray(255)
    packet_to_send[0] = CMD_GET_CMDS_LEN
    packet_to_send[1] = CMD_GET_CMDS

    crc = calculate_crc(packet_to_send, 2)
    packet_to_send[2:6] = crc.to_bytes(4, "little")

    try:
        with open_connection(port, baudrate) as ser:

            if debug:
                log_print("sending the following message")
                log_print(f"message length: {packet_to_send[0]}")
                log_print(f"command code: {hex(packet_to_send[1])}")
                log_print(f"crc: 0x{crc:08x}\r\n")

            ser.write(packet_to_send[:6])

            data_recv = handle_recv_packet(ser, debug)

            if data_recv == -1:
                raise typer.Exit(1)

            typer.echo(f"Supported bootloader commands:")

            for i in range(len(data_recv)):
                typer.echo(f"0x{data_recv[i]:02x}")
				

    except SerialException as e:
        typer.echo(f"Connection error: {e}")
        raise typer.Exit(1)

@app.command()
def get_cid(
    port: str = typer.Option(..., "--port", "-p", help = "Device opened on serial port, e.g. /dev/ttyUSB0" ),
    baudrate: int = typer.Option(115200, "--baudrate", "-b", help = "Communication speed with target"),
    debug: bool = typer.Option(False, "--debug", "-d", help = "Enables the debug messages")
):
    """Get MCU chip ID."""

    packet_to_send = bytearray(255)
    packet_to_send[0] = CMD_GET_CID_LEN
    packet_to_send[1] = CMD_GET_CID

    crc = calculate_crc(packet_to_send, 2)
    packet_to_send[2:6] = crc.to_bytes(4, "little")

    try:
        with open_connection(port, baudrate) as ser:

            if debug:
                log_print("sending the following message")
                log_print(f"message length: {packet_to_send[0]}")
                log_print(f"command code: {hex(packet_to_send[1])}")
                log_print(f"crc: 0x{crc:08x}\r\n")

            ser.write(packet_to_send[:6])

            data_recv = handle_recv_packet(ser, debug)

            if data_recv == -1:
                raise typer.Exit(1)

            cid = int.from_bytes(data_recv[:2], "little")
            typer.echo(f"Chip ID: 0x{cid:04X}")

    except SerialException as e:
        typer.echo(f"Connection error: {e}")
        raise typer.Exit(1)

@app.command(
    help="0xA5 - flash memory unprotected\n\n"
    "0x00 - flash memory protected"
)
def get_rdp(
    port: str = typer.Option(..., "--port", "-p", help = "Device opened on serial port, e.g. /dev/ttyUSB0" ),
    baudrate: int = typer.Option(115200, "--baudrate", "-b", help = "Communication speed with target"),
    debug: bool = typer.Option(False, "--debug", "-d", help = "Enables the debug messages")
):
    """Get MCU flash RDP status"""

    packet_to_send = bytearray(255)
    packet_to_send[0] = CMD_GET_RDP_LEN
    packet_to_send[1] = CMD_GET_RDP

    crc = calculate_crc(packet_to_send, 2)
    packet_to_send[2:6] = crc.to_bytes(4, "little")

    try:
        with open_connection(port, baudrate) as ser:

            if debug:
                log_print("sending the following message")
                log_print(f"message length: {packet_to_send[0]}")
                log_print(f"command code: {hex(packet_to_send[1])}")
                log_print(f"crc: 0x{crc:08x}\r\n")

            ser.write(packet_to_send[:6])

            data_recv = handle_recv_packet(ser, debug)

            if data_recv == -1:
                raise typer.Exit(1)

            typer.echo(f"Flash RDP: 0x{data_recv[0]:02x}")

    except SerialException as e:
        typer.echo(f"Connection error: {e}")
        raise typer.Exit(1)

@app.command(
    help="WARNING: After the RDP has been set, disabling it causes a flash memory mass erase.\n\n"
    "Automatically resets the MCU.\n\n"
    "Requires POR without a debugger attached to take effect."
)
def set_rdp(
    en_status: str = typer.Option(..., "--en_status", "-e", help = "Enable or disable flash read protection <enable|disable>"),
    port: str = typer.Option(..., "--port", "-p", help = "Device opened on serial port, e.g. /dev/ttyUSB0" ),
    baudrate: int = typer.Option(115200, "--baudrate", "-b", help = "Communication speed with target"),
    debug: bool = typer.Option(False, "--debug", "-d", help = "Enables the debug messages")
):
    """Set MCU flash RDP status."""

    packet_to_send = bytearray(255)
    packet_to_send[0] = CMD_SET_RDP_LEN
    packet_to_send[1] = CMD_SET_RDP
    
    if en_status == "enable":
        packet_to_send[2] = 0xEE
    elif en_status == "disable":
        packet_to_send[2] = 0xDD
    else:
        raise typer.BadParameter(
            "Invalid arguments"
        )
        
    crc = calculate_crc(packet_to_send, 3)
    packet_to_send[3:7] = crc.to_bytes(4, "little")

    try:
        with open_connection(port, baudrate) as ser:
            
            if debug:
                log_print("sending the following message")
                log_print(f"message length: {packet_to_send[0]}")
                log_print(f"command code: {hex(packet_to_send[1])}")
                log_print(f"enable status: {hex(packet_to_send[2])}")
                log_print(f"crc: 0x{crc:08x}\r\n")

            ser.write(packet_to_send[:7])

            data_recv = handle_recv_packet(ser, debug)

            if data_recv == -1:
                raise typer.Exit(1)

            typer.echo(f"Flash RDP set to {en_status}")

    except SerialException as e:
        typer.echo(f"Connection error: {e}")
        raise typer.Exit(1)

@app.command()
def get_wrp(
    port: str = typer.Option(..., "--port", "-p", help="Device opened on serial port, e.g. /dev/ttyUSB0"),
    baudrate: int = typer.Option(115200, "--baudrate", "-b", help="Communication speed with target"),
    debug: bool = typer.Option(False, "--debug", "-d", help = "Enables the debug messages")
):
    """Get write protection of flash pages."""

    packet_to_send = bytearray(255)
    packet_to_send[0] = CMD_GET_WRP_LEN
    packet_to_send[1] = CMD_GET_WRP

    crc = calculate_crc(packet_to_send, 2)
    packet_to_send[2:6] = crc.to_bytes(4, "little")

    try:
        with open_connection(port, baudrate) as ser:
            
            if debug:
                log_print("sending the following message")
                log_print(f"message length: {packet_to_send[0]}")
                log_print(f"command code: {hex(packet_to_send[1])}")
                log_print(f"crc: 0x{crc:08x}\r\n")

            ser.write(packet_to_send[:6])

            data_recv = handle_recv_packet(ser, debug)

            if data_recv == -1:
                raise typer.Exit(1)

            page_from = 0
            page_to = 3

            for byte_index, wrp_byte in enumerate(data_recv[:4]):
                for bit_index in range(8):
                    page = byte_index * 8 + bit_index
                    wp = (wrp_byte >> bit_index) & 1
                    typer.echo(f"Pages {page_from}-{page_to}: {'Protected' if wp == 0 else 'Unprotected'}")
                    page_from += 4
                    page_to += 4

    except SerialException as e:
        typer.echo(f"Connection error: {e}")
        raise typer.Exit(1)

@app.command(
    help="Automatically resets the MCU.\n\n"
    "For write protection flash memory pages are grouped together in groups of 4. Because of this command parameters are required to be multiples of 4.\n\n"
    "The first page of the flash is numbered as 0, the last page is 127."
)
def set_wrp(
    start_page: int = typer.Option(None, "--start_page", "-s", help="Page number to set write protection from (must be 0 or multiple of 4)"),
    num_page: int = typer.Option(None, "--num_page", "-n", help="Number of pages to set write protection of (must be multiple of 4)"),
    en_status: str = typer.Option(..., "--en_status", "-e", help = "Enable or disable write protection <enable|disable>"),
    port: str = typer.Option(..., "--port", "-p", help="Device opened on serial port, e.g. /dev/ttyUSB0"),
    baudrate: int = typer.Option(115200, "--baudrate", "-b", help="Communication speed with target"),
    debug: bool = typer.Option(False, "--debug", "-d", help = "Enables the debug messages")
):
    """Set write protection of flash pages."""

    if (start_page % 4 != 0) or (num_page % 4 != 0) or (num_page == 0) or (start_page + num_page > 128) or (start_page is None) or (num_page is None):
        raise typer.BadParameter(
            "Invalid arguments"
        )

    packet_to_send = bytearray(255)
    packet_to_send[0] = CMD_SET_WRP_LEN
    packet_to_send[1] = CMD_SET_WRP
    packet_to_send[2] = start_page
    packet_to_send[3] = num_page

    if en_status == "enable":
        packet_to_send[4] = 0xEE
    elif en_status == "disable":
        packet_to_send[4] = 0xDD
    else:
        raise typer.BadParameter(
            "Invalid arguments"
        )

    crc = calculate_crc(packet_to_send, 5)
    packet_to_send[5:9] = crc.to_bytes(4, "little")

    try:
        with open_connection(port, baudrate) as ser:
            
            if debug:
                log_print("sending the following message")
                log_print(f"message length: {packet_to_send[0]}")
                log_print(f"command code: {hex(packet_to_send[1])}")
                log_print(f"start page: {packet_to_send[2]}")
                log_print(f"number of pages: {packet_to_send[3]}")
                log_print(f"enable status: {packet_to_send[4]}")
                log_print(f"crc: 0x{crc:08x}\r\n")

            ser.write(packet_to_send[:9])

            data_recv = handle_recv_packet(ser, debug)

            if data_recv == -1:
                raise typer.Exit(1)

            typer.echo(f"WRP of specified pages set to {en_status}")

    except SerialException as e:
        typer.echo(f"Connection error: {e}")
        raise typer.Exit(1)

@app.command(
    help="The first page of the flash is numbered as 0, the last page is 127."
)
def erase(
    start_page: int = typer.Option(None, "--start_page", "-s", help="Page number to erase from (0 - 127)"),
    num_page: int = typer.Option(None, "--num_page", "-n", help="Number of pages to erase"),
    mass_erase: bool = typer.Option(False, "--mass_erase", "-m", help="Mass erase entire flash"),
    port: str = typer.Option(..., "--port", "-p", help = "Device opened on serial port, e.g. /dev/ttyUSB0" ),
    baudrate: int = typer.Option(115200, "--baudrate", "-b", help = "Communication speed with target"),
    debug: bool = typer.Option(False, "--debug", "-d", help = "Enables the debug messages")
):
    """Erases the flash"""

    if ((mass_erase == False) and (start_page == None or num_page == None)):
        raise typer.BadParameter(
            "Invalid arguments"
        )

    if ((mass_erase == False) and ((start_page < 0 or start_page > 127) or ((num_page < 1) or (start_page + num_page) > 128))):
        raise typer.BadParameter(
            "Invalid arguments"
        )

    if ((mass_erase == True) and ((start_page is not None) or (num_page is not None))):
        raise typer.BadParameter(
            "Invalid arguments"
        )

    packet_to_send = bytearray(255)
    packet_to_send[0] = CMD_ERASE_LEN
    packet_to_send[1] = CMD_ERASE

    if mass_erase == False:
        packet_to_send[2] = start_page
        packet_to_send[3] = num_page
    else:
        packet_to_send[2] = 0xFF
        packet_to_send[3] = 0

    crc = calculate_crc(packet_to_send, 4)
    packet_to_send[4:8] = crc.to_bytes(4, "little")

    try:
        with open_connection(port, baudrate) as ser:

            if debug:
                log_print("sending the following message")
                log_print(f"message length: {packet_to_send[0]}")
                log_print(f"command code: {hex(packet_to_send[1])}")
                log_print(f"start page: {packet_to_send[2]}")
                log_print(f"number of pages: {packet_to_send[3]}")
                log_print(f"crc: 0x{crc:08x}\r\n")

            ser.write(packet_to_send[:8])

            data_recv = handle_recv_packet(ser, debug)

            if data_recv == -1:
                raise typer.Exit(1)

            typer.echo(f"Erase successful")

    except SerialException as e:
        typer.echo(f"Connection error: {e}")
        raise typer.Exit(1)

@app.command(
    help="Flash memory is mapped between 0x08000000 - 0x0801FFFF"
)
def write(
    addr: str = typer.Option(..., "--addr", "-a", callback=parse_hex, help="Address in hex, e.g. 0x08004000"),
    file: Path = typer.Option(
    ...,
    "--file",
    "-f",
    exists=True,
    file_okay=True,
    dir_okay=False,
    readable=True,
    help="Path to firmware binary file"
    ),
    port: str = typer.Option(..., "--port", "-p", help = "Device opened on serial port, e.g. /dev/ttyUSB0" ),
    baudrate: int = typer.Option(115200, "--baudrate", "-b", help = "Communication speed with target"),
    debug: bool = typer.Option(False, "--debug", "-d", help = "Enables the debug messages")
):
    """Writes to the flash."""

    file_size = file.stat().st_size
    file_size_remaining = file_size
    current_addr = addr

    try:
        with open_connection(port, baudrate) as ser:
   
            with file.open("rb") as bin_image:

                while file_size_remaining:
                    if file_size_remaining >= 128:
                        payload = bin_image.read(128)
                        payload_size = 128
                        file_size_remaining -= 128
                    else:
                        payload = bin_image.read(file_size_remaining)
                        payload_size = file_size_remaining
                        file_size_remaining -= file_size_remaining

                    packet_to_send = bytearray(255)
                    packet_to_send[0] = 10 + payload_size      # command code + addr + payload length + crc + payload
                    packet_to_send[1] = CMD_WRITE
                    packet_to_send[2:6] = current_addr.to_bytes(4, "little")
                    packet_to_send[6] = payload_size
                    packet_to_send[7:7 + payload_size] = payload

                    crc = calculate_crc(packet_to_send, 7 + payload_size)
                    packet_to_send[7 + payload_size:11 + payload_size] = crc.to_bytes(4, "little")

                    if debug:
                        log_print("sending the following message")
                        log_print(f"message length: {packet_to_send[0]}")
                        log_print(f"command code: 0x{packet_to_send[1]:02X}")
                        log_print(f"address: 0x{current_addr:08X}")
                        log_print(f"payload size: {packet_to_send[6]} bytes")
                        log_print("payload: " + " ".join(f"0x{b:02x}" for b in payload))
                        log_print(f"crc: 0x{crc:08X}\r\n")

                    ser.write(packet_to_send[:11+payload_size])

                    data_recv = handle_recv_packet(ser, debug)

                    if data_recv == -1:
                        raise typer.Exit(1)

                    current_addr += payload_size

                typer.echo(f"Write successful")

    except SerialException as e:
        typer.echo(f"Connection error: {e}")
        raise typer.Exit(1)

@app.command(
    help="Flash memory is mapped between 0x08000000 - 0x0801FFFF"
)
def read(
    addr: str = typer.Option(..., "--addr", "-a", callback=parse_hex, help="Address in hex, e.g. 0x08004000"),
    num_bytes: int = typer.Option(..., "--num_bytes", "-n", help="Number of bytes to read"),
    file: Path = typer.Option(
    ...,
    "--file",
    "-f",
    file_okay=True,
    dir_okay=False,
    writable=True,
    help="Path to destination file"
    ),
    port: str = typer.Option(..., "--port", "-p", help = "Device opened on serial port, e.g. /dev/ttyUSB0" ),
    baudrate: int = typer.Option(115200, "--baudrate", "-b", help = "Communication speed with target"),
    debug: bool = typer.Option(False, "--debug", "-d", help = "Enables the debug messages")
):
    """Reads from the flash."""

    try:
        with open_connection(port, baudrate) as ser:
   
            with file.open("wb") as dest_file:

                remaining_bytes = num_bytes
                current_addr = addr

                while remaining_bytes:

                    packet_to_send = bytearray(255)
                    packet_to_send[0] = CMD_READ_LEN
                    packet_to_send[1] = CMD_READ
                    packet_to_send[2:6] = current_addr.to_bytes(4, "little")

                    if debug:
                        log_print("sending the following message")
                        log_print(f"message length: {packet_to_send[0]}")
                        log_print(f"command code: 0x{packet_to_send[1]:02X}")

                    if remaining_bytes >= 128:
                        packet_to_send[6] = 128
                        remaining_bytes -= 128

                        if debug:
                            log_print(f"address: 0x{current_addr:08X}")
                            log_print(f"payload size: {128} bytes")

                        current_addr += 128
                    else:
                        packet_to_send[6] = remaining_bytes

                        if debug:
                            log_print(f"address: 0x{current_addr:08X}")
                            log_print(f"payload size: {remaining_bytes} bytes")

                        current_addr += remaining_bytes
                        remaining_bytes -= remaining_bytes

                    crc = calculate_crc(packet_to_send, 7)
                    packet_to_send[7:11] = crc.to_bytes(4, "little")

                    if debug:
                        log_print(f"crc: 0x{crc:08X}\r\n")

                    ser.write(packet_to_send[:11])

                    data_recv = handle_recv_packet(ser, debug)

                    if data_recv == -1:
                        raise typer.Exit(1)

                    dest_file.write(data_recv)

                typer.echo(f"Read successful")

    except SerialException as e:
        typer.echo(f"Connection error: {e}")
        raise typer.Exit(1)

@app.command(
    help="The first page of the flash is numbered as 0, the last page is 127."
)
def program(
    start_page: int = typer.Option(None, "--start_page", "-s", help="Page number to erase from (0 - 127)"),
    file: Path = typer.Option(
    ...,
    "--file",
    "-f",
    exists=True,
    file_okay=True,
    dir_okay=False,
    readable=True,
    help="Path to firmware binary file"
    ),
    port: str = typer.Option(..., "--port", "-p", help = "Device opened on serial port, e.g. /dev/ttyUSB0" ),
    baudrate: int = typer.Option(115200, "--baudrate", "-b", help = "Communication speed with target"),
    debug: bool = typer.Option(False, "--debug", "-d", help = "Enables the debug messages")
):
    """Erases then write to the flash."""

    if (start_page is None or start_page < 0 or start_page > 127):
        raise typer.BadParameter(
            "Invalid arguments"
        )

    file_size = file.stat().st_size
    file_size_remaining = file_size
    current_page = start_page
    page_round = 0

    pages_needed = math.ceil(file_size / 1024)

    if start_page + pages_needed > 128:
        raise typer.BadParameter("File doesn't fit in specified location")

    try:
        with open_connection(port, baudrate) as ser:
   
            with file.open("rb") as bin_image:

                while file_size_remaining:
                    if page_round > 7:
                        current_page += 1
                        page_round = 0

                    if file_size_remaining >= 128:
                        payload = bin_image.read(128)
                        payload_size = 128
                        file_size_remaining -= 128
                    else:
                        payload = bin_image.read(file_size_remaining)
                        payload_size = file_size_remaining
                        file_size_remaining -= file_size_remaining

                    packet_to_send = bytearray(255)
                    packet_to_send[0] = 8 + payload_size  
                    packet_to_send[1] = CMD_PROGRAM
                    packet_to_send[2] = current_page
                    packet_to_send[3] = page_round
                    packet_to_send[4] = payload_size
                    packet_to_send[5:5 + payload_size] = payload
                    crc = calculate_crc(packet_to_send, 5 + payload_size)
                    packet_to_send[5 + payload_size:9 + payload_size] = crc.to_bytes(4, "little")

                    if debug:
                        log_print("sending the following message")
                        log_print(f"message length: {packet_to_send[0]}")
                        log_print(f"command code: 0x{packet_to_send[1]:02X}")
                        log_print(f"page: {current_page}")
                        log_print(f"page round: {page_round}")
                        log_print(f"payload size: {payload_size}")
                        log_print("payload: " + " ".join(f"0x{b:02x}" for b in payload))
                        log_print(f"crc: 0x{crc:08X}\r\n")

                    ser.write(packet_to_send[:9+payload_size])

                    data_recv = handle_recv_packet(ser, debug)

                    if data_recv == -1:
                        raise typer.Exit(1)

                    page_round += 1

                typer.echo(f"Program successful")

    except SerialException as e:
        typer.echo(f"Connection error: {e}")
        raise typer.Exit(1)

@app.command(
    help="Flash memory is mapped between 0x08000000 - 0x0801FFFF"
)
def jump(
    addr: str = typer.Option(..., "--addr", "-a", callback=parse_hex, help="Address in hex, e.g. 0x08004000"),
    port: str = typer.Option(..., "--port", "-p", help = "Device opened on serial port, e.g. /dev/ttyUSB0" ),
    baudrate: int = typer.Option(115200, "--baudrate", "-b", help = "Communication speed with target"),
    debug: bool = typer.Option(False, "--debug", "-d", help = "Enables the debug messages")
):
    """Jumps to the specified address"""

    packet_to_send = bytearray(255)
    packet_to_send[0] = CMD_JUMP_LEN
    packet_to_send[1] = CMD_JUMP

    packet_to_send[2:6] = addr.to_bytes(4, "little")

    crc = calculate_crc(packet_to_send, 6)
    packet_to_send[6:10] = crc.to_bytes(4, "little")

    try:
        with open_connection(port, baudrate) as ser:

            if debug:
                log_print("sending the following message")
                log_print(f"message length: {packet_to_send[0]}")
                log_print(f"command code: {hex(packet_to_send[1])}")
                log_print(f"address: 0x{addr:08X}")
                log_print(f"crc: 0x{crc:08x}\r\n")

            ser.write(packet_to_send[:10])

            data_recv = handle_recv_packet(ser, debug)

            if data_recv == -1:
                raise typer.Exit(1)

            typer.echo(f"Successful jump to {addr}")

    except SerialException as e:
        typer.echo(f"Connection error: {e}")
        raise typer.Exit(1)

@app.command()
def rst(
    port: str = typer.Option(..., "--port", "-p", help = "Device opened on serial port, e.g. /dev/ttyUSB0" ),
    baudrate: int = typer.Option(115200, "--baudrate", "-b", help = "Communication speed with target"),
    debug: bool = typer.Option(False, "--debug", "-d", help = "Enables the debug messages")
):
    """Resets the MCU."""

    packet_to_send = bytearray(255)
    packet_to_send[0] = CMD_RST_LEN
    packet_to_send[1] = CMD_RST

    crc = calculate_crc(packet_to_send, 2)
    packet_to_send[2:6] = crc.to_bytes(4, "little")

    try:
        with open_connection(port, baudrate) as ser:
            
            if debug:
                log_print("sending the following message")
                log_print(f"message length: {packet_to_send[0]}")
                log_print(f"command code: {hex(packet_to_send[1])}")
                log_print(f"crc: 0x{crc:08x}\r\n")

            ser.write(packet_to_send[:6])

            data_recv = handle_recv_packet(ser, debug)

            if data_recv == -1:
                raise typer.Exit(1)

            typer.echo(f"Successful reset")

    except SerialException as e:
        typer.echo(f"Connection error: {e}")
        raise typer.Exit(1)

if __name__ == "__main__": 
    app()
