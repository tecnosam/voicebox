import logging

from typing import Dict, List, Type

from threading import Thread

import pyaudio

from voicebox.connection import Connection
from voicebox.audio import Audio
from voicebox.utils import (
    setup_server_socket,
    setup_client_socket,
    extract_ip
)

from voicebox.encryption import (
    BaseEncryptor,
    RSAEncryptor
)

from voicebox.namr_client import (
    NamrClient
)


class MicrophoneStreamerThread:
    """
    MicrophoneStreamerThread Class

    Class responsible for streaming microphone audio to connected nodes.

    Attributes:
        MUTED (bool): Class-level attribute representing the mute state.
    """
    MUTED = False

    @classmethod
    def initiate_microphone_stream(cls):
        """
        Initiates the microphone stream.

        Starts the microphone stream by calling the stream_microphone method.
        """
        cls.stream = cls.stream_microphone()
        cls.stream.start_stream()

    @staticmethod
    def callback(in_data, frame_count, time_info, status):

        """
        Callback function for handling audio stream data.

        Args:
            in_data: Input audio data.
            frame_count: Number of frames.
            time_info: Time information.
            status: Status information.

        Returns:
            tuple: A tuple containing the in_data and the continuation status.
        """

        logging.debug(
            "Audio Stream: %s %s %s",
            frame_count,
            time_info,
            status
        )

        if not MicrophoneStreamerThread.MUTED:
            for node in Node.nodes:

                node.broadcast_audio(in_data)

        return in_data, pyaudio.paContinue

    @staticmethod
    def stream_microphone():
        """
        Streams audio from the microphone.

        Returns:
            stream: The audio stream.
        """
        return Audio.record(MicrophoneStreamerThread.callback)


class Node:
    """
        Node Class

        Class representing a network node.

    """
    nodes = []

    def __new__(cls, username: str, port: int):
        """
            Overloading __new__ so we can check if the
            username is already taken
        """

        logging.debug(
            "Checking username %s against Naming systems...",
            username
        )

        # Check username in Namr Server 
        client = list(NamrClient.get_user(username))

        if client:
            logging.error("username already taken by %s", client[0])

            raise ValueError("username is taken")

        # Check username in DHT

        # create the Node instance
        # We make sure the instance is created
        # first before registering the username
        # in namr or DHT
        instance = super().__new__(cls)

        ip = extract_ip()
        response = NamrClient.set_username(username, f"{ip}:{port}")

        # Finally return the created instance
        return instance

    def __init__(
        self,
        username: str,
        port: int = 4000
    ):
        """
        Initializes a Node instance.

        Args:
            username (str): The username of the node.
            port (int): The port to listen on (default is 4000).
        """
        self.port = port
        self.username = username

        self.__encryption_pipeline: List[Type[BaseEncryptor]] = [
            RSAEncryptor,
        ]

        self.connection_pool: Dict[str, Connection] = {}  # nodes user is connected to
        self.muted = False

        self.socket = setup_server_socket(self.port)

        # Listen on socket
        self.listener_thread = Thread(target=self.listen, daemon=True)
        self.listener_thread.start()

        Node.nodes.append(self)

    def toggle_mute(self):
        """
        Toggles the mute state of the node.
        """
        self.muted = not self.muted

    def log(self, msg):
        """
        Logs a message with the node's username.

        Args:
            msg: The message to be logged.
        """
        logging.info("%s: %s", self.username, msg)

    def add_new_connection(
        self,
        address,
        machine_socket,
    ):
        """
        Adds a new connection to the node.
        Also initializes the encryption pipeline
        and starts the key exchange process.

        Args:
            address: The address of the new connection.
            machine_socket: The socket of the new connection.
        """
        encryption_pipeline: List[BaseEncryptor] = [
            encryptor()
            for encryptor in self.encryption_pipeline
        ]

        encryption_packet_handlers = [
            encryptor.packet_handler
            for encryptor in encryption_pipeline
        ]

        self.connection_pool[address] = Connection(
            machine_socket,
            packet_handlers=encryption_packet_handlers,
            encryption_pipeline=encryption_pipeline
        )

        self.perform_key_exchange(address)

        self.connection_pool[address].send_message("SUCCESS", 0)

    def perform_key_exchange(self, address):
        """
        Performs key exchange with a connected node.

        Args:
            address: The address of the connected node.
        """
        encryption_pipeline = self.connection_pool[address].encryption_pipeline

        for encryptor in encryption_pipeline:

            pem = encryptor.public_pem

            if pem is not None:

                self.connection_pool[address].send_message(
                    pem,
                    encryptor.KEY_EXCHANGE_SIGNAL
                )

    def listen(self):
        """Listen for new connections"""

        self.log("Socket Listening For new Connections...")

        self.socket.listen()
        while True:

            client, address_tuple = self.socket.accept()

            if self.validate_connection(address_tuple):
                address, _ = address_tuple

                self.add_new_connection(address, client)

                self.log(f"Received Connection from {address}")
            else:
                client.close()

    def connect_to_machine(self, host: str, port: int):
        """
        Connects to a machine with the specified host and port.

        Called when the Node wants to call another Node in the
        network.

        Args:
            host (str): The host to connect to.
            port (int): The port to connect to.
        """
        machine_socket = setup_client_socket(host, port)

        if machine_socket is None:
            logging.error(
                "Node %s: %s is Unreachable",
                self.username,
                host
            )
            return

        self.add_new_connection(host, machine_socket)

    def broadcast_audio(self, audio_stream):
        """
        Broadcasts audio to connected nodes.

        Args:
            audio_stream: The audio stream to broadcast.
        """
        if self.muted:
            return

        addresses = list(self.connection_pool.keys())

        for addr in addresses:

            connection = self.connection_pool.get(addr)

            if not connection:
                # Connection was killed in another thread
                continue

            if connection.on_hold:
                continue

            if connection.killed:
                # We were informed by the connection
                # So we don't need to inform the connection
                logging.info(
                    "Connection to %s Killed while Broadcasting",
                    addr
                )
                self.end_call(addr, inform_connection=False)
                continue

            connection.send_message(audio_stream, 2)

    def end_call(self, addr: str, inform_connection: bool = True):
        """
        Ends a call with a connected node.

        Removes the connection from our connection pool and
        kills the connection.

        Args:
            addr: The address of the connected node.
            inform_connection (bool): Whether to inform the connected node (default is True).
        """
        connection = self.connection_pool.pop(addr, None)

        if not addr:
            logging.error("Cannot find Address %s in pool", addr)
            return

        if inform_connection:
            connection.kill()

    @staticmethod
    def validate_connection(address: str) -> bool:
        """
        Validates a new connection.

        Args:
            address: The address of the potential new connection.

        Returns:
            bool: True if the connection is valid, False otherwise.
        """
        return bool(address)

        # return bool(input("Would you like to connect to this client at {}? ".format(address)))

    @property
    def encryption_pipeline(self) -> List[BaseEncryptor]:
        """
        Property representing the encryption pipeline.

        Returns:
            List[BaseEncryptor]: The encryption pipeline.
        """
        return self.__encryption_pipeline

    @encryption_pipeline.setter
    def encryption_pipeline(
        self,
        encryption_pipeline: List[BaseEncryptor]
    ):
        """
        Setter for the encryption pipeline.

        Args:
            encryption_pipeline: The new encryption pipeline.
        """
        for encryptor in encryption_pipeline:

            self.append_to_encryption_pipeline(encryptor)

    def append_to_encryption_pipeline(self, encryptor: BaseEncryptor):
        """
        Appends an encryptor to the encryption pipeline.

        Args:
            encryptor: The encryptor to append.
        """
        if not isinstance(encryptor, type(BaseEncryptor)):

            raise ValueError(
                "Encryptor must extend from BaseEncryptor"
            )

        self.__encryption_pipeline.append(encryptor)
