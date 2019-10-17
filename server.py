#!/usr/bin/env python3

from socket import AF_INET, socket, SOCK_STREAM
from threading import Thread
import json
import traceback

# Empty dictionaries to hold relevant data
clients = {}
addresses = {}

# Define
HOST = '0.0.0.0'
PORT = 33000
BUFSIZ = 4096
ADDR = (HOST, PORT)
SERVER = socket(AF_INET, SOCK_STREAM)
SERVER.bind(ADDR)


def accept_incoming_connections():
    """Sets up handling for incoming clients."""
    while True:
        client, client_address = SERVER.accept()
        print("%s:%s has connected." % client_address)
        addresses[client] = client_address
        Thread(target=handle_client, args=(client,)).start()


def handle_client(client): # Takes client socket as argument.
    """Handles a single client connection."""
    try:
        while True:
            # Get message
            message_bytes = client.recv(BUFSIZ)

            message_split = message_bytes.split(b'({(')[:-1]

            for message_iteration in message_split:
                # Get to string
                message_raw = message_iteration.decode('utf8')

                # Decode message
                try:
                    message_data = json.loads(message_raw)
                except:
                    print("INVALID MESSAGE")
                    print("Message: " + str(message_raw))
                    print(traceback.format_exc())

                # Conditionally handle the message
                if(message_data.get('mode') == 'setup'):
                    name = message_data.get('data')
                    clients[client] = name

                elif(message_data.get('mode') == 'escape'):
                    # Remove client from server
                    del clients[client]
                    client.close()

                    # Send message to other clients
                    to_send = {
                        'from':'SERVER',
                        'mode':'message',
                        'data':f'{name} has left the chat'
                    }
                    broadcast(json.dumps(to_send).encode('utf8'))
                    print("%s has disconnected." % name)
                    break

                elif(message_data.get('mode') == 'message'):
                    broadcast(message_iteration)

                elif(message_data.get('mode') == 'image'):
                    # Receive the image
                    length = message_data.get('data').get('length')
                    image = client.recv(length)

                    # Send the image to clients
                    for sock in clients:
                        sock.send(message_iteration)
                        sock.send(image)
    except:
        try:
            print("%s has disconnected." % clients[client]) 
            print(traceback.format_exc())
            del clients[client]
        except: pass
        try: client.close()
        except: pass
        try: broadcast(json.dumps(to_send).encode('utf8'))
        except: pass
        


def broadcast(msg, prefix=""): # prefix is for name identification.
    """Broadcasts a message to all the clients."""
    for sock in clients:
        sock.send(msg)


if __name__ == "__main__":
    SERVER.listen(5) # Listens for 5 connections at max.
    print("Waiting for connection...")
    ACCEPT_THREAD = Thread(target=accept_incoming_connections)
    ACCEPT_THREAD.start() # Starts the infinite loop.
    ACCEPT_THREAD.join()
    SERVER.close()