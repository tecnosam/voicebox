import logging

import secrets

from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers import (
    Cipher,
    algorithms,
    modes
)
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

    KEY_SIZE = 2048

    INT_BYTE_SIZE = 4

    KEY_EXCHANGE_SIGNAL = 901

    def __init__(self, client_public_pem: bytes = None):

        self.__private_key = None
        self.__public_key = None

        if client_public_pem:
            self.client_public_key = self.convert_pem_to_key(client_public_pem)
        else:
            self.client_public_key = None

    def symmetric_encrypt(self, packet: bytes):

        sym_key = secrets.token_bytes(32)

        nonce = secrets.token_bytes(16)

        cipher = Cipher(
            algorithms.AES(sym_key),
            modes.CTR(nonce),
            backend=default_backend()
        )

        encryptor = cipher.encryptor()

        ciphertext = encryptor.update(packet) + encryptor.finalize()

        sym_key = nonce + sym_key

        return sym_key, ciphertext

    def symmetric_decrypt(self, ciphertext: bytes, key: bytes):

        nonce, key = key[:16], key[16:]

        cipher = Cipher(
            algorithms.AES(key),
            modes.CTR(nonce),
            backend=default_backend()
        )

        decryptor = cipher.decryptor()

        data = decryptor.update(ciphertext) + decryptor.finalize()

        return data

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
        #if payload[self.INT_BYTE_SIZE:] == self.public_pem:
        #    return payload

        sym_key, ciphertext = self.symmetric_encrypt(payload)

        encrypted_key = self.client_public_key.encrypt(
            sym_key,
            self.padding
        )

        keylen = len(encrypted_key)
        header = keylen.to_bytes(self.INT_BYTE_SIZE, byteorder='big')

        return header + encrypted_key + ciphertext

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

            keylen = int.from_bytes(packet[:self.INT_BYTE_SIZE], byteorder='big')

            key = packet[self.INT_BYTE_SIZE:keylen+self.INT_BYTE_SIZE]
            ciphertext = packet[keylen+self.INT_BYTE_SIZE:]

            sym_key = self._private_key.decrypt(
                key,
                self.padding
            )

            return self.symmetric_decrypt(ciphertext, sym_key)

        except ValueError as exc:

            logging.error(
                f"Warning:Unable to decrypt packet! {str(exc)}"
            )
            return packet

    def packet_handler(self, packet: bytes):

        delimeter = self.INT_BYTE_SIZE

        packet_type, data = packet[:delimeter], packet[delimeter:]

        packet_type = int.from_bytes(packet_type, 'big')

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

    @property
    def _private_key(self):

        if not self.__private_key:

            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=self.KEY_SIZE,
                backend=default_backend()
            )

            self.__private_key = private_key

        return self.__private_key

    @property 
    def public_key(self):

        if not self.__public_key:

            private_key = self._private_key

            self.__public_key = private_key.public_key()

        return self.__public_key

    @property 
    def public_pem(self) -> bytes:
        """
            The public pem is what we send to the client
            on the other end.
        """

        pem = self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )

        return pem

