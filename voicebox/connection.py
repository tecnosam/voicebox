import socket
import logging

from threading import Thread
from voicebox.audio import Audio


class Connection:
    """
    Connection Class

    Represents a connection to a remote client, providing methods for sending and receiving data
    packets. It supports multiple packet handlers and encryption layers.

    Attributes:
        INT_BYTE_SIZE (int): The size of an integer in bytes used for packet size and type.
        PACKET_TYPES (list): List of possible packet types ('CONNECTION', 'MSG', 'AUDIO', 'VIDEO').

    Args:
        client (socket.socket): The socket representing the connection to the remote client.
        packet_handlers (list): List of functions to handle incoming packets.
        encryption_pipeline (list): List of encryptors to process incoming and outgoing data.

    Methods:
        __init__: Initializes a Connection instance.
        receive_data: Thread function for continuously receiving data packets.
        send_message: Sends a message packet to the remote client.
        decrypt_packet: Decrypts an incoming packet using the encryption pipeline.
        encrypt_payload: Encrypts an outgoing payload using the encryption pipeline.
        default_packet_handler: Default handler for incoming packets.
        kill: Terminates the connection and sets the kill switch.
        killed: Property indicating whether the connection has been terminated.
    """

    INT_BYTE_SIZE = 4
    PACKET_TYPES = ['CONNECTION', 'MSG', 'AUDIO', 'VIDEO']

    def __init__(
        self,
        client,
        packet_handlers: list,
        encryption_pipeline: list
    ):
        """
        Initialize a Connection instance.

        Args:
            client (socket.socket): The socket representing the connection to the remote client.
            packet_handlers (list): List of functions to handle incoming packets.
            encryption_pipeline (list): List of encryptors to process incoming and outgoing data.
        """

        self.socket: socket.socket = client

        self.__kill_switch = False

        self.on_hold = True

        self.encryption_pipeline = encryption_pipeline

        self.packet_handlers = [self.default_packet_handler] + packet_handlers

        self.packet_listener = Thread(target=self.receive_data)
        self.packet_listener.start()

    def receive_data(self):
        """
        Receive Data Packets from this connected User.
        """

        while True:
            try:
                if self.__kill_switch:
                    logging.debug("Switch Has been killed!")
                    break

                packet_size = self.socket.recv(self.INT_BYTE_SIZE)
                packet_size = int.from_bytes(packet_size, "big")

                if packet_size == 0:
                    logging.info("Your connection request was not accepted")
                    self.kill(inform_client=False)

                logging.debug("Receiving %s bytes of data...", packet_size)

                packet = self.socket.recv(packet_size)
                packet = self.decrypt_packet(packet)

                for packet_handler in self.packet_handlers:
                    packet = packet_handler(packet)

            except ConnectionResetError:
                logging.error("Connection to client lost: Adviced to kill connection")
            except OSError:
                logging.info("Channel already closed: Adviced to kill connection")

    def send_message(self, message, msg_type=1):
        """
        Send a message packet to the remote client.

        Args:
            message (Union[str, bytes]): The message to be sent.
            msg_type (int): The type of the message packet.
        Returns:
            str: A message indicating the status of the operation.
        """

        try:
            packet_type = int.to_bytes(msg_type, self.INT_BYTE_SIZE, "big")

            if isinstance(message, str):
                message = message.encode()

            payload = packet_type + message
            encrypted_payload = self.encrypt_payload(payload)

            packet_size = len(encrypted_payload)
            size = int.to_bytes(packet_size, self.INT_BYTE_SIZE, "big")

            self.socket.send(size)
            self.socket.send(encrypted_payload)

        except BrokenPipeError:
            logging.error("Socket No longer usable: Adviced to kill connection")
        except ConnectionResetError:
            logging.debug("Connection reset while sending packet")
            self.kill(inform_client=False)

    def decrypt_packet(self, packet: bytes):
        """
        Decrypt an incoming packet using the encryption pipeline.

        Args:
            packet (bytes): The incoming encrypted packet.

        Returns:
            bytes: The decrypted packet.
        """
        for encryptor in self.encryption_pipeline:
            packet = encryptor.decrypt(packet)
        return packet

    def encrypt_payload(self, payload: bytes):
        """
        Encrypt an outgoing payload using the encryption pipeline.

        Args:
            payload (bytes): The outgoing payload.

        Returns:
            bytes: The encrypted payload.
        """
        for encryptor in self.encryption_pipeline:
            payload = encryptor.encrypt(payload)
        return payload

    def default_packet_handler(self, packet):
        """
        Default handler for incoming packets, supporting various packet types.

        Args:
            packet (bytes): The incoming packet.

        Returns:
            bytes: The processed packet.
        """

        delimiter = self.INT_BYTE_SIZE
        packet_type, data = packet[:delimiter], packet[delimiter:]

        packet_type = int.from_bytes(packet_type, "big")

        if packet_type >= len(self.PACKET_TYPES):
            return packet

        if self.PACKET_TYPES[packet_type] == 'MSG':
            logging.info("MESSAGE RECEIVED: %s", data)

        elif self.PACKET_TYPES[packet_type] == 'CONNECTION':
            if data == b'SUCCESS':
                self.on_hold = False
                logging.info("Machines Connected successfully")
            elif data == b'IS_ALIVE':
                logging.info("Machine Connection Verified successfully")
            elif data == b'DISCONNECTED':
                logging.info("Machine has been disconnected")
                self.kill(inform_client=False)

        elif self.PACKET_TYPES[packet_type] == 'AUDIO':
            Audio.play_audio(data)

        return packet

    def kill(self, inform_client: bool = True):
        """
        Terminate the connection and set the kill switch.

        Args:
            inform_client (bool): Whether to inform the client before terminating the connection.
        """

        self.__kill_switch = True
        logging.debug("Kill Switch set")

        if inform_client:
            logging.debug("Informing Client...")
            self.send_message('DISCONNECTED', 0)
            self.socket.close()

    @property
    def killed(self):
        """
        Property indicating whether the connection has been terminated.

        Returns:
            bool: True if the connection has been terminated, False otherwise.
        """
        return self.__kill_switch
