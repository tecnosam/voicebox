import logging

from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend


class BaseEncryptor:

    KEY_EXCHANGE_SIGNAL = 900

    def __init__(self, *args, **kwargs):

        raise NotImplementedError("Cannot Initialize from BaseEncryptor")

    def encrypt(self, payload: bytes):

        raise NotImplementedError()

    def decrypt(self, packet: bytes):

        raise NotImplementedError()

    def hash(self, payload):

        raise NotImplementedError()

    def packet_handler(self, packet):

        return packet

    @classmethod
    @property
    def public_pem(cls):

        return None


class RSAEncryptor(BaseEncryptor):

    __private_key = None

    __public_key = None

    INT_BYTE_SIZE = 4

    KEY_EXCHANGE_SIGNAL = 901

    def __init__(self, client_public_pem: bytes = None):

        if client_public_pem:
            self.client_public_key = self.convert_pem_to_key(client_public_pem)
        else:
            self.client_public_key = None

    def encrypt(self, payload: bytes):
        """
            We'd like to encrypt messages in the client's
            public key so they can decrypt it
        """

        if not self.client_public_key:
            return payload

        # If we are transmitting our public 
        # Key, we don't need to encrypr ir
        # for the sake of key exchange
        if payload[self.INT_BYTE_SIZE:] == self.public_pem:
            return payload

        if len(payload) < 1000:
            print(payload, self.public_pem, payload == self.public_pem)
            print(f"\n\n Encrypting {len(payload)} with {self.client_public_key}\n\n")
        return self.client_public_key.encrypt(
            payload,
            self.padding
        )

    def decrypt(self, packet: bytes):

        """
            When someone sends a packet to us encrypted
            with our public key, we'd like to decrypt it 
            with our private key
        """

        try:
            # If we don't have a private key, 
            # There's no way the client has a
            # public key
            if not self.__private_key:
                return packet

            logging.debug("Decrypting packet with RSA algorithm")

            return self._private_key.decrypt(
                packet,
                self.padding
            )
        except ValueError:

            logging.error("Warning:Unable to decrypt packet!")
            return packet

    def packet_handler(self, packet: bytes):

        delimeter = self.INT_BYTE_SIZE

        packet_type, data = packet[:delimeter], packet[delimeter:]

        packet_type = int.from_bytes(packet_type, 'big')

        logging.debug(f"{packet_type}- {self.KEY_EXCHANGE_SIGNAL}received")

        if packet_type == self.KEY_EXCHANGE_SIGNAL:

            self.client_public_key = self.convert_pem_to_key(data)
            logging.info(f"Received Client's public key {self.client_public_key}!")

        return packet

    @classmethod
    def convert_pem_to_key(cls, pem: bytes):

        return serialization.load_pem_public_key(
            pem,
            backend=default_backend()
        )

    @classmethod
    @property 
    def padding(cls):

        return padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )

    @classmethod
    @property
    def _private_key(cls):

        if not cls.__private_key:

            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
                backend=default_backend()
            )

            cls.__private_key = private_key

        return cls.__private_key

    @classmethod
    @property 
    def public_key(cls):

        if not cls.__public_key:

            private_key = cls._private_key

            cls.__public_key = private_key.public_key()

        return cls.__public_key

    @classmethod 
    @property 
    def public_pem(cls) -> bytes:
        """
            The public pem is what we send to the client
            on the other end.
        """

        pem = cls.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )

        return pem

