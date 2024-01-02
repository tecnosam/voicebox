from networking.node import Node, MicrophoneStreamerThread

from networking.utils import extract_ip

PORT = 4000


def main():

    global PORT
    print("LOL", extract_ip())

    username = input("Username: ")

    while True:
        try:
            node = Node(username, port=PORT)
            break
        except OSError:
            PORT += 1
            print(f"Port in Use. Retrying {PORT}...")


    # test = Node('test 2', port=5000)

    while True:

        opt = input("> ")
        opt = opt.lower().replace(' ', '_')

        if opt in ('new_call', 'call', 'new_chat'):
            host = input("IP of machine to connect to: ")
            port = PORT

            if ':' in host:
                host, port = host.split(':')

            node.connect_to_machine(host, int(port))

        elif opt in ('view', 'view_machines'):
            print(node.connection_pool)

        elif opt in ('toggle_mute', 'mute'):
            MicrophoneStreamerThread.MUTED = not MicrophoneStreamerThread.MUTED
            node.toggle_mute()

        elif opt in ('send', 'send_msg'):
            msg = input("Msg: ")
            list(node.connection_pool.values())[0].send_message(msg, 1)

        elif opt in ('help', 'h'):

            print("Type 'call' to call, 'mute' to toggle microphone, 'send' to message")

