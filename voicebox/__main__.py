import logging
import argparse
from voicebox.node import Node, MicrophoneStreamerThread

from voicebox.utils import extract_ip


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(name)s %(levelname)-8s  %(message)s',
    datefmt='(%H:%M:%S)'
)


def main():

    """
    Main function to start system

    provides a command line interface for interracting
    with the voicebox APIs.
    """
    
    parser = argparse.ArgumentParser(description='Voicebox')
    parser.add_argument('--port', required=True, type=int, help='Input port number')
    args = parser.parse_args()

    username = input("Username: ")
    ip = extract_ip()
    port = args.port

    while True:
        try:
            node = Node(username, port=port)
            break
        except OSError:
            port += 1
            print(f"Port in Use. Retrying {port}...")

    print(f"Welcome {username}! Others can call you at {ip}:{port}")

    MicrophoneStreamerThread.initiate_microphone_stream()

    while True:

        opt = input("> ")
        opt = opt.lower().replace(' ', '_')

        if opt in ('new_call', 'call', 'new_chat'):
            host = input("IP of machine to connect to: ")
            third_party_port = port

            if ':' in host:
                host, third_party_port = host.split(':')

            if host == ip and third_party_port == port:

                print("Cannot call yourself")
                continue

            node.connect_to_machine(host, int(third_party_port))

        elif opt in ('end_call',):

            print(node.connection_pool, 'opt', opt)

            address = input("Input the address of client to end: ")

            node.end_call(address)

        elif opt in ('view', 'view_machines'):
            print(node.connection_pool)

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
