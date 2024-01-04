import logging

from typing import Dict

from threading import Thread
from concurrent.futures import ThreadPoolExecutor

import pyaudio

from voicebox.connection import Connection
from voicebox.audio import Audio
from voicebox.utils import setup_server_socket, setup_client_socket


class MicrophoneStreamerThread:

    pool = ThreadPoolExecutor()

    MUTED = False

    def __init__(self):

        self.stream = self.stream_microphone()
        self.stream.start_stream()

    @staticmethod
    def callback(in_data, frame_count, time_info, status):
        # print(frame_count, time_info, status)

        if not MicrophoneStreamerThread.MUTED:
            for node in Node.nodes:
                node.broadcast_audio(in_data)
                # MicrophoneStreamerThread.pool.submit(node.broadcast_audio, in_data)

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

            client, address = self.socket.accept()

            if self.validate_connection(address):
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

        for addr in self.connection_pool:

            connection = self.connection_pool[addr]

            if connection.on_hold:
                continue

            connection.send_message(audio_stream, 2)

    @staticmethod
    def validate_connection(address: str) -> bool:

        return bool(input("Would you like to connect to this client at {}? ".format(address)))


microphone_streamer = MicrophoneStreamerThread()

