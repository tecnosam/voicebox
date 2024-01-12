import socket
import logging


def extract_ip():
    """
    Extract the local IP address of the current machine.

    This function creates a temporary socket and connects to a known external server
    to retrieve the local IP address. If unsuccessful, it defaults to '127.0.0.1'.

    Returns:
        str: The local IP address of the machine.

    Example:
        local_ip = extract_ip()
        print(f"Local IP address: {local_ip}")
    """
    st = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        st.connect(('10.255.255.255', 1))
        ip = st.getsockname()[0]
    except OSError:
        logging.debug("OS ERROR, defaulting to home address")
        ip = '127.0.0.1'

    return ip


def setup_server_socket(port: int):
    """
    Set up a server socket bound to the local machine's IP address and a specified port.

    Args:
        port (int): The port number on which the server will listen for connections.

    Returns:
        socket.socket: The server socket ready to accept incoming connections.

    Example:
        server_socket = setup_server_socket(8080)
        print("Server socket set up and listening for connections.")
    """
    host = extract_ip()
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    logging.debug(
        "Created Socket. Binding connection to %s at %s...",
        host,
        port
    )
    server.bind((host, port))

    logging.debug("Done. You're all set Network-wise")

    return server


def setup_client_socket(host, port):
    """
    Set up a client socket and connect to a specified host and port.

    Args:
        host (str): The IP address or hostname of the server to connect to.
        port (int): The port number on the server to establish the connection.

    Returns:
        socket.socket or None: A connected client socket if the connection is successful,
                               otherwise, returns None.

    Raises:
        OSError: If an error occurs while setting up or connecting the socket.

    Example:
        client_socket = setup_client_socket('127.0.0.1', 8080)
        if client_socket:
            # Perform operations with the connected client_socket
        else:
            print("Failed to establish a connection.")
    """
    try:
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect((host, port))

    except OSError:
        client = None

    return client
