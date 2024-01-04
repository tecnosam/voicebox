import logging

from typing import Dict

from threading import Thread
from concurrent.futures import ThreadPoolExecutor, as_completed

import pyaudio

from voicebox.connection import Connection
from voicebox.audio import Audio
from voicebox.utils import setup_server_socket, setup_client_socket


class MicrophoneStreamerThread:

    pool = ThreadPoolExecutor()

    MUTED = False

    @classmethod
    def initiate_microphone_stream(cls):

        cls.stream = cls.stream_microphone()
        cls.stream.start_stream()

    @staticmethod
    def callback(in_data, frame_count, time_info, status):
        # print(frame_count, time_info, status)

        if not MicrophoneStreamerThread.MUTED:
            futures = []
            for node in Node.nodes:

                # node.broadcast_audio(in_data)
                futures.append(MicrophoneStreamerThread.pool.submit(
                    node.broadcast_audio,
                    in_data
                ))

            for future in as_completed(futures):

                future
                # logging.debug(f"{future} completed. Transmitted audio feed...")

            del futures
        return in_data, pyaudio.paContinue

    @staticmethod
    def stream_microphone():

        return Audio.record(MicrophoneStreamerThread.callback)


class Node:

    nodes = []

    def __init__(self, username: str, port: int = 4000):

        self.port = port
        self.username = username

        self.connection_pool: Dict[str, Connection] = {}  # nodes user is connected to
        self.muted = False

        self.socket = setup_server_socket(self.port)

        # Listen on socket
        self.listener_thread = Thread(target=self.listen, daemon=True)
        self.listener_thread.start()

        Node.nodes.append(self)

    def toggle_mute(self):
        self.muted = not self.muted

    def log(self, msg):
        logging.info(f"{self.username}: {msg}")

    def listen(self):
        """Listen for new connections"""

        self.log("Socket Listening For new Connections...")

        self.socket.listen()
        while True:

            client, address_tuple = self.socket.accept()

            if self.validate_connection(address_tuple):
                address, _ = address_tuple
                self.connection_pool[address] = Connection(client)
                self.connection_pool[address].send_message("CONNECTION_SUCCESS", 0)

                self.log(f"Received Connection from {address}")
            else:
                client.close()

    def connect_to_machine(self, host: str, port: int):

        machine_socket = setup_client_socket(host, port)

        if machine_socket is None:
            logging.error(f"Node {self.username}: {host} is Unreachable")
            return

        machine_connection = Connection(machine_socket)
        self.connection_pool[host] = machine_connection

    def broadcast_audio(self, audio_stream):
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
                print("Connection Killed while Broadcasting")
                self.end_call(addr, inform_connection=False)
                continue

            connection.send_message(audio_stream, 2)

    def end_call(self, addr: str, inform_connection: bool = True):

        connection = self.connection_pool.pop(addr, None)

        if not addr:

            print("Not Found!")
            logging.error(f"Cannot find Address {addr} in pool")
            return 
 
        if inform_connection:
            connection.kill()

    @staticmethod
    def validate_connection(address: str) -> bool:

        return bool(input("Would you like to connect to this client at {}? ".format(address)))

