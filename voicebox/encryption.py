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

    """
    BaseEncryptor Class

    Base class for encryptors providing methods for encryption, decryption, and hashing.

    Methods:
        encrypt: Encrypts the payload (to be implemented by subclasses).
        decrypt: Decrypts the packet (to be implemented by subclasses).
        hash: Computes the hash of the payload (to be implemented by subclasses).
        packet_handler: Default packet handler that returns the packet unchanged.
        public_pem: Property representing the public PEM key, returns None by default.

    Attributes:
        KEY_EXCHANGE_SIGNAL (int): A constant representing the key exchange signal.
    """

    KEY_EXCHANGE_SIGNAL = 900

    def encrypt(self, payload: bytes):
        """
        Encrypts the payload.

        Args:
            payload (bytes): The payload to be encrypted.

        Raises:
            NotImplementedError: This method should be implemented by subclasses.
        """

        raise NotImplementedError()

    def decrypt(self, packet: bytes):
        """
        Decrypts the packet.

        Args:
            packet (bytes): The encrypted packet to be decrypted.

        Raises:
            NotImplementedError: This method should be implemented by subclasses.
        """
        raise NotImplementedError()

    def hash(self, payload):
        """
        Computes the hash of the payload.

        Args:
            payload: The payload to be hashed.

        Raises:
            NotImplementedError: This method should be implemented by subclasses.
        """
        raise hash(payload)

    def packet_handler(self, packet):
        """
        Default packet handler that returns the packet unchanged.
        When an Encryptor is added to a Connection, this method
        is to be registered as part of the packet_handlers

        Args:
            packet: The packet to be handled.

        Returns:
            The unchanged packet.
        """
        return packet

    @property
    def public_pem(self):
        """
        Property representing the public PEM key, returns None by default.

        Returns:
            None: This method should be implemented by subclasses.
        """
        return None


class RSAEncryptor(BaseEncryptor):

    """
    RSAEncryptor Class

    Subclass of BaseEncryptor implementing RSA encryption and decryption.

    Attributes:
        KEY_SIZE (int): The size of the RSA key.
        INT_BYTE_SIZE (int): The size of an integer in bytes used for header information.
        KEY_EXCHANGE_SIGNAL (int): A constant representing the key exchange signal.

    Methods:
        __init__: Initializes an RSAEncryptor instance.
        symmetric_encrypt: Performs symmetric encryption using AES.
        symmetric_decrypt: Performs symmetric decryption using AES.
        encrypt: Encrypts the payload using RSA and symmetric encryption.
        decrypt: Decrypts the packet using RSA and symmetric decryption.
        packet_handler: Handles packets, including key exchange signals.
        convert_pem_to_key: Converts PEM-formatted bytes to a key object.
        padding: Property representing the padding used for encryption.
        _private_key: Property representing the private key.
        public_key: Property representing the public key.
        public_pem: Property representing the public PEM key.

    Args:
        client_public_pem (bytes, optional): The public PEM key of the client.

    Properties:
        public_key: Property representing the public key.
        public_pem: Property representing the public PEM key.
    """

    KEY_SIZE = 2048

    INT_BYTE_SIZE = 4

    KEY_EXCHANGE_SIGNAL = 901

    def __init__(self, client_public_pem: bytes = None):

        """
        Initializes an RSAEncryptor instance.

        Args:
            client_public_pem (bytes, optional): The public PEM key of the client.
        """

        super().__init__()

        self.__private_key = None
        self.__public_key = None

        if client_public_pem:
            self.client_public_key = self.convert_pem_to_key(client_public_pem)
        else:
            self.client_public_key = None

    def symmetric_encrypt(self, packet: bytes):
        """
        Performs symmetric encryption using AES.

        Args:
            packet (bytes): The packet to be symmetrically encrypted.

        Returns:
            tuple: A tuple containing the symmetric key and the ciphertext.
        """
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
        """
        Performs symmetric decryption using AES.

        Args:
            ciphertext (bytes): The ciphertext to be symmetrically decrypted.
            key (bytes): The symmetric key.

        Returns:
            bytes: The decrypted data.
        """
        nonce, key = key[:16], key[16:]

        cipher = Cipher(
            algorithms.AES(key),
            modes.CTR(nonce),
            backend=default_backend()
        )

        decryptor = cipher.decryptor()

        data = decryptor.update(ciphertext) + decryptor.finalize()

        return data

    def encrypt(self, payload: bytes) -> bytes:
        """
            We'd like to encrypt messages in the client's
            public key so they can decrypt it.

            We generate a random cipher key and nonce, encrypt
            it with client's public key, then encrypt the payload
            with the generated cipher key.

            Returns:
                bytes: combination of key length, key, and ciphertext
        """

        if not self.client_public_key:
            return payload

        sym_key, ciphertext = self.symmetric_encrypt(payload)

        encrypted_key = self.client_public_key.encrypt(
            sym_key,
            self.padding
        )

        keylen = len(encrypted_key)
        header = keylen.to_bytes(self.INT_BYTE_SIZE, byteorder='big')

        return header + encrypted_key + ciphertext

    def decrypt(self, packet: bytes) -> bytes:

        """
            When someone sends a packet to us encrypted
            with our public key, we'd like to decrypt it
            with our private key.

            This function decrypts the cipher key and nonce,
            from our private key then uses the cihper key and
            nonce to decrypt the packet itself.

            Returns:
                bytes: Decrypted packet
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
                "Warning: Unable to decrypt packet, %s",
                str(exc)
            )
            return packet

    def packet_handler(self, packet: bytes) -> bytes:
        """
        We would like to listen for the client's
        public key so we can use it to encrypt messages.

        We process the packet if it's type matches our
        key exchange signal.

        Returns:
            bytes: packet for the next handler to process.
        """

        delimeter = self.INT_BYTE_SIZE

        packet_type, data = packet[:delimeter], packet[delimeter:]

        packet_type = int.from_bytes(packet_type, 'big')

        if packet_type == self.KEY_EXCHANGE_SIGNAL:

            self.client_public_key = self.convert_pem_to_key(data)
            logging.debug("Received Client's public key!")

        return packet

    @classmethod
    def convert_pem_to_key(cls, pem: bytes):
        """
        Converts PEM-formatted bytes to a key object.

        Args:
            pem (bytes): The PEM-formatted bytes.

        Returns:
            Key: The key object.
        """
        return serialization.load_pem_public_key(
            pem,
            backend=default_backend()
        )

    @classmethod
    @property
    def padding(cls):
        """
        Property representing the padding used for encryption.

        Returns:
            padding.OAEP: The OAEP padding.
        """
        return padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )

    @property
    def _private_key(self):
        """
        Property representing the private key.

        If a private key hasn't been generated yet,
        it generates one.

        Returns:
            _private_key: The RSA private key
        """

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
        """
        Property representing the public key.

        Returns:
            public_key: The public key.
        """
        if not self.__public_key:

            private_key = self._private_key

            self.__public_key = private_key.public_key()

        return self.__public_key

    @property
    def public_pem(self) -> bytes:
        """
            The public PEM is what we send to the client
            on the other end.
        """

        pem = self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )

        return pem
