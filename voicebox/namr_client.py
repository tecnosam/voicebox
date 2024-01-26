from typing import List

from voicebox.utils import (
    setup_client_socket
)


class NamrClient:
    """
        Namr is a service that maps connection
        information to a username.

        This class allows us to store connection info
        on a Namr server with a custom username.

        It also lets us probe the namr server for connection
        information associated with a particular username
    """

    namr_server: str

    @classmethod 
    def get_user(cls, username: str) -> List[str]:
        """
            Searches different Namr servers for a username.
            
            Each namr server ideally returns either the connection
            info that matches the username or nothing.

            Returns:
                List[str]: list of connection infos matched to the username.
        """

        for server in cls.namr_servers:

            conn_info = get_user_from_server(server, username)

            if not conn_info:
                continue

            yield conn_info

    @classmethod
    def set_username(cls, username: str, conn_info: str) -> bool:
        """
            Registers a username to a namr server.

            Returns:
                bool: Whether or not we where able to register
                the username.
        """

        status = False

        for server in cls.namr_servers:

            status = set_username_in_server(username, conn_info)
            if status:
                break

        return status

    @classmethod
    def get_user_from_server(
        cls,
        server: str,
        username: str
    ) -> str:
        """
            Sends a request to a namr server to get
            connection information associated with
            a username.
        """

        payload = f"G{username}"

        conn_info = cls.__send_namr_request(server, payload)

        return conn_info.decode('utf-8')

    @classmethod
    def set_username_in_server(
        cls,
        server: str,
        username: str,
        conn_info: str
    ) -> bool:
        """
            Sends a request to a namr server to register
            our connection info with a username

            Returns:

                bool: False if the username is already taken
        """

        payload = f"S{username} {conn_info}"

        status: bytes = cls.__send_namr_request(server, payload)

        return bool.from_bytes(status, 'little')

    @classmethod
    def __send_namr_request(cls, namr_server: str, payload: bytes) -> bytes:
        """
            Sends a request to a namr server.

            Request can be to either set a username or get a username.

            Typical response for setting is a boolean byte.
            Typical response for getting is a string of variable size.
        """

        ip, port = namr_server.split(':')
        socket = setup_client_socket(ip, port)

        # Send request
        socket.send(payload)

        # receive response
        response = socket.recv(1024)

        socket.close()

        return response
