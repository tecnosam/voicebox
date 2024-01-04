import socket

from typing import Union

import logging

from voicebox.data_utils import MessageStack

from voicebox.audio import Audio

from threading import Thread

from base64 import b64encode, b64decode


class Connection:

    INT_BYTE_SIZE = 4

    PACKET_TYPES = ['CONNECTION', 'MSG', 'AUDIO', 'VIDEO']

    def __init__(
        self,
        client,
        packet_handlers: list = []
    ):

        self.socket: socket.socket = client

        self.__kill_switch = False

        self.on_hold = False

        self.packet_handlers = [self.default_packet_handler] + packet_handlers

        self.packet_listener = Thread(target=self.receive_data)
        self.packet_listener.start()

        self.messages = MessageStack()

    def receive_data(self):
        """Receive Data Packets from this connected User"""

        while True:
            try:

                if self.__kill_switch:
                    print("Switch Has been killed!")
                    break

                packet_size = self.socket.recv(self.INT_BYTE_SIZE)
                packet_size = int.from_bytes(packet_size, "big")

                if packet_size == 0:
                    logging.info("Your connection request was not accepted")
                    self.kill(inform_client=False)

                logging.debug("Receiving {} bytes of data...".format(packet_size))

                packet = self.socket.recv(packet_size)
                packet = self.decrypt_packet(packet)

                for packet_handler in self.packet_handlers:
                    packet = packet_handler(packet)

            except ConnectionResetError:
                logging.error("Connection to client lost: Adviced to kill connection")
            except OSError:

                logging.info("Channel already closed: Adviced to kill connection")

    def send_message(self, message, msg_type=1):

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

            return "Done"
        except BrokenPipeError:

            logging.error("Socket No longer usable: Adviced to kill connection")

        except ConnectionResetError:

            logging.debug("Connection reset while sending packet")
            self.kill(inform_client=False)

    @staticmethod
    def decrypt_packet(packet: bytes):

        return packet

    @staticmethod
    def encrypt_payload(payload: bytes):
        return payload

    def default_packet_handler(self, packet):

        delimiter = self.INT_BYTE_SIZE
        packet_type, data = packet[:delimiter], packet[delimiter:]

        packet_type = int.from_bytes(packet_type, "big")

        if packet_type >= len(self.PACKET_TYPES):
            return packet

        if self.PACKET_TYPES[packet_type] == 'MSG':
            logging.info("MESSAGE RECEIVED: {}".format(data))

        elif self.PACKET_TYPES[packet_type] == 'CONNECTION':
            if data == b'SUCCESS':
                logging.info("Machines Connected successfully")

            elif data == b'IS_ALIVE':
                logging.info("Machine Connection Verified successfully")

            elif data == b'DISCONNECTED':
                print("Disconnect received")
                logging.info("Machine has been disconnected")

                # Informed by the client 
                # So we don't need to inform 
                # the client
                self.kill(inform_client=False)

        elif self.PACKET_TYPES[packet_type] == 'AUDIO':
            Audio.play_audio(data)

        return packet

    def kill(self, inform_client: bool = True):

        self.__kill_switch = True
        print("Kill Switch Set")

        if inform_client:
            print("Informing client...")
            logging.debug("Informing Client")
            self.send_message('DISCONNECTED', 0)

            self.socket.close()

    @property 
    def killed(self):

        return self.__kill_switch

