import socket

from typing import Union

from voicebox.data_utils import MessageStack

from voicebox.audio import Audio

from threading import Thread

from base64 import b64encode, b64decode


class Connection:

    INT_BYTE_SIZE = 4

    PACKET_TYPES = ['CONNECTION', 'MSG', 'AUDIO', 'VIDEO']

    def __init__(self, client, packet_handlers: list = []):

        self.socket: socket.socket = client

        self.packet_handlers = [self.default_packet_handler] + packet_handlers

        self.packet_listener = Thread(target=self.receive_data)
        self.packet_listener.start()

        self.messages = MessageStack()

        self.on_hold = False

    def receive_data(self):
        """Receive Data Packets from this connected User"""

        while True:
            packet_size = self.socket.recv(self.INT_BYTE_SIZE)
            packet_size = int.from_bytes(packet_size, "big")

            print("Receiving {} bytes of data...".format(packet_size))

            packet = self.socket.recv(packet_size)
            packet = self.decrypt_packet(packet)

            for packet_handler in self.packet_handlers:
                packet = packet_handler(packet)

    def send_message(self, message, msg_type=1):

        packet_type = int.to_bytes(msg_type, self.INT_BYTE_SIZE, "big")

        if isinstance(message, str):
            message = message.encode()

        payload = packet_type + message
        encrypted_payload = self.encrypt_payload(payload)

        packet_size = len(encrypted_payload)
        size = int.to_bytes(packet_size, self.INT_BYTE_SIZE, "big")

        self.socket.send(size)
        self.socket.send(encrypted_payload)

        return "Done"

    @staticmethod
    def decrypt_packet(packet: bytes):

        return b64decode(packet)

    @staticmethod
    def encrypt_payload(payload: bytes):
        return b64encode(payload)

    def default_packet_handler(self, packet):

        delimiter = self.INT_BYTE_SIZE
        packet_type, data = packet[:delimiter], packet[delimiter:]

        packet_type = int.from_bytes(packet_type, "big")

        if packet_type >= len(self.PACKET_TYPES):
            return packet

        if self.PACKET_TYPES[packet_type] == 'MSG':
            print("MESSAGE RECEIVED: {}".format(data))

        elif self.PACKET_TYPES[packet_type] == 'CONNECTION':
            if data == b'SUCCESS':
                print("Machines Connected successfully")

            elif data == b'IS_ALIVE':
                print("Machine Connection Verified successfully")

            elif data == b'DISCONNECTED':
                print("Machine has been disconnected")

        elif self.PACKET_TYPES[packet_type] == 'AUDIO':
            Audio.play_audio(data)

        return packet
