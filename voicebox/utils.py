import socket
import logging


def extract_ip():
    st = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        st.connect(('10.255.255.255', 1))
        ip = st.getsockname()[0]
    except OSError:
        logging.debug("OS ERROR, defaulting to home address")
        ip = '127.0.0.1'

    return ip


def setup_server_socket(port: int):
    host = extract_ip()
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    logging.debug(f"Created Socket. binding connection to {host} at {port}...")
    server.bind((host, port))

    logging.debug("Done. You're all set Network wise")

    return server


def setup_client_socket(host, port):
    try:
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect((host, port))

        return client
    except OSError as e:
        client = None

    return client

