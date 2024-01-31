import logging
import argparse
from kademlia.network import Server
from voicebox.node import Node, MicrophoneStreamerThread


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(name)s %(levelname)-8s  %(message)s',
    datefmt='(%H:%M:%S)'
)
server = Server()


async def run(port, bootstrap_ip=None, bootstrap_port=None):
    """
        Connects to a peer's DHT server.

        This function basically adds this machine to a DHT network
    """
    await server.listen(port)
    if bootstrap_ip and bootstrap_port:
        try:
            await server.bootstrap([(bootstrap_ip, bootstrap_port)])
        except OSError as exc:
            logging.error(
                "Error bootstrapping with node %s:%s = %s",
                bootstrap_ip,
                bootstrap_port,
                str(exc)
            )
            return False
    return True


async def setusername(username, ip, port):
    """
        Set's a username on the DHT
    """
    result = await server.get(username)
    if result is not None:
        return False
    await server.set(username, ip + ":" + str(port))
    return True


async def getusername(username):
    """
        Get's connection info linked to a username on DHT
    """
    result = await server.get(username)
    if result is None:
        return ""
    return result


def parse_args():

    """
        Parse command line arguments
    """
    parser = argparse.ArgumentParser(description='Voicebox')

    parser.add_argument(
        '--port',
        required=True,
        type=int,
        help='Input port number'
    )

    parser.add_argument(
        '--bootstrap_port',
        type=int,
        default=5678,
        help='Bootstrap node port number'
    )

    parser.add_argument(
        '--bootstrap_ip',
        type=str,
        default="192.168.0.1",
        help='Bootstrap node IP address'
    )

    args = parser.parse_args()

    return args


def initiate_call(node: Node):

    """
        Flow to initiate a connection with someone else
    """

    username = input("Input the username of the client to call: ")

    node.connect_to_machine_with_username(username)


def main():
    """
        Main function that puts everything all together
    """

    args = parse_args()

    # create a node on the network
    while True:
        try:
            username = input("Username: ")

            node = Node(username, port=args.port)
            break
        except ValueError as exc:
            logging.error("Error with username: %s", str(exc))

    # Welcome message
    print(
        f"Welcome {username}! Others can call you at {node.ip}:{node.port}"
    )

    # Initiate microphone
    MicrophoneStreamerThread.initiate_microphone_stream()

    # Apps menu
    while True:

        opt = input("> ").lower().replace(' ', '_')

        if opt in ('new_call', 'call', 'new_chat'):

            initiate_call(node)

        elif opt in ('end_call',):

            print(node.connection_pool, 'opt', opt)

            address = input("Input the ip of client to end: ")

            node.end_call(address)

        elif opt in ('toggle_mute', 'mute'):
            MicrophoneStreamerThread.MUTED = not MicrophoneStreamerThread.MUTED
            node.toggle_mute()

            print("Muted State: ", MicrophoneStreamerThread.MUTED)
            print("Node Muted State: ", node.muted)

        elif opt in ('send', 'send_msg'):
            msg = input("Msg: ")
            list(node.connection_pool.values())[0].send_message(msg, 1)

        elif opt in ('help', 'h'):

            print("Type 'call' to call, 'mute' to toggle microphone, 'send' to message")
            print("Type 'view' or 'view_machines' to view connected machines")
