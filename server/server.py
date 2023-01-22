import os
import socket
import threading
import ssl
from pickle import dumps, loads
import re
import time

import numpy as np

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2' 

#Constants for holding information about connections
connections = []
total_connections = 0

COMMANDS = {
    '/list': 0,
    '/private': 1,
    '/accept': 3,
    '/tau': 4,
    '/pp': 5,
    '/drop': 6,
}

class Client(threading.Thread):
    def __init__(self, socket, address, _id, signal):
        threading.Thread.__init__(self)
        self.socket = socket
        self.address = address
        self.id = _id
        # self.name = name
        self.signal = signal
        self.ready_to_connect = False
        self.partner_id = None
        self.is_now_connecting = False

        self.iter = 0
        self.flag_accept = False

        wellcome_message = dumps({'type': 888, 'data': '[!] Connection successful.\nUse command: /list, /private, /accept, /pp, /drop'})
        self.socket.sendall(wellcome_message)
    
    def __str__(self):
        return f'{str(self.id)} {str(self.address)}'
    
    def run(self):
        while self.signal:
            try:
                data = self.socket.recv(1024)
            except:
                print(f'Client {str(self.address)} has disconnected')
                self.signal = False
                connections.remove(self)
                break
            if data:
                self.handle_event(data)

    def handle_event(self, data):
        prepared_data = self.prepare_data(data)
        event_handlers = {
            0: self.send_list,
            1: self.request_connection,
            2: self.sendall_message,
            3: self.private_start,
            4: self.send_tau,
            5: self.send_private_message,
            6: self.dropped_params,
            7: self.__error_sender
        }
        event_type = prepared_data.get('type')
        if event_type in event_handlers:
            event_handlers[event_type](prepared_data)
        else:
            self.error_sender('Unknown event type')

    def prepare_data(self, data):
        data = loads(data)
        print(self.id, 'receve', data)
        if type(data) == dict:
            prepared_data = {'type': 5, 'data': data['/pp']}
            return prepared_data

        match = re.match(r'(\/(private)\s(\d+)|\/(tau)\s(-1|1)$|\/(list|drop|accept)$|[^/]+)', data)
        command_arg = match.group().split(' ') if match else [None, None]
        command, arg = command_arg[0], command_arg[-1]
        # print(f'command {command}\n', f'arg {arg}')
        if command in COMMANDS:
            if command == '/private':
                prepared_data = {'type': COMMANDS[command], 'to': int(arg)}
            elif command == '/tau':
                prepared_data = {'type': COMMANDS[command], 'tau': int(arg)}
            else:
                prepared_data = {'type': COMMANDS[command]}
        else:
            if data[0] == '/':
                prepared_data = {'type': 7, 'data': 'Error command, use /list, /private, /accept, /pp, /drop'}
            else:
                prepared_data = {'type': 2, 'data': data}
        print(prepared_data)
        return prepared_data

    def send_list(self, prepared_data=None):
        id_list = [client.id for client in connections if client.id != self.id]
        message_list = f'Your ID: {self.id}\nUsers list {id_list}'
        message = dumps({'type': 0, 'data': message_list})
        self.socket.sendall(message)

    def request_connection(self, prepared_data):
        to_id = prepared_data.get('to')
        try:
            if not self.is_now_connecting:
                for client in connections:
                    if client.id == to_id and client.id != self.id and not client.is_now_connecting:
                        client.is_now_connecting = True
                        socket_to = client.socket
                        partner_id = client.id

                message = dumps({'type': 1, 'data': f'Private request from the user ID[{self.id}]'})
                socket_to.sendall(message)
                self.flag_accept = True
                self.ready_to_connect = True
                self.partner_id = partner_id
                self.is_now_connecting = True
            else:
                raise Exception
        except:
            prepared_data = {'data': 'Error private connection (check /list) or use /accept'}
            self.__error_sender(prepared_data)

    def sendall_message(self, prepared_data):
        data = prepared_data.get('data')
        message = dumps({'type': 2, 'data': data, 'from': str(self.id)})
        for client in connections:
            if client.id != self.id:
                client.socket.sendall(message)

    def private_start(self, prepared_data=None):
        try:
            partner_id, parther_socket = [(client.id, client.socket) for client in connections \
                                          if client.ready_to_connect == True and client.partner_id == self.id][0]
            self.partner_id = partner_id
            self.ready_to_connect = True
            self.is_now_connecting = True
            self.private_run(parther_socket)
        except:
            prepared_data = {'data': 'Error /accept, use /private [id]'}
            self.__error_sender(prepared_data)

    def private_run(self, parther_socket):
        if self.iter != 800:
            random_bytes_matrix = self.random_bytes()
            message = dumps({'type': 3, 'rand_matrix': random_bytes_matrix})
            self.socket.sendall(message)
            parther_socket.sendall(message)
            self.iter += 1
        else:
            print('ended')
            print(self.iter)
            self.iter = 0
            message = dumps({'type': 777, 'data': 'The key is formed.'})
            self.socket.sendall(message)
            parther_socket.sendall(message)

    def send_tau(self, prepared_data):
        tau = prepared_data.get('tau')
        try:
            parther_socket = [client.socket for client in connections \
                              if client.ready_to_connect == True and client.partner_id == self.id][0]
            message = dumps({'type': 4, 'tau': tau})
            parther_socket.sendall(message)
            time.sleep(1e-323)
            # time.sleep(3)
            if self.flag_accept:
                self.private_start()

        except:
            prepared_data = {'data': 'Error tau'}
            self.__error_sender(prepared_data)

    def send_private_message(self, prepared_data):
        data = prepared_data.get('data')
        try:
            parther_socket = [client.socket for client in connections \
                              if client.ready_to_connect == True and client.partner_id == self.id][0]
            message = dumps({'type': 5, 'id': self.id, 'data': data})
            parther_socket.sendall(message)
        except:
            prepared_data = {'data': 'Use /private [ID].'}
            self.__error_sender(prepared_data)
            self.dropped_params()
    
    def dropped_params(self, prepared_data=None):
        self.partner_id = None
        self.ready_to_connect = False
        self.is_now_connecting = False
        self.iter = 0
        self.flag_accept = False
        message = dumps({'type': 999, 'data': 'All params have been dropped'})
        self.socket.sendall(message)

    def __error_sender(self, prepared_data):
        text_error = prepared_data['data']
        message = dumps({'type': 6, 'data': text_error})
        self.socket.sendall(message)

    def random_bytes(self):
        k = 64
        n = 8
        l = 255
        return np.random.randint(-l, l + 1, [k, n])  # gen bytes (l=255)


class Server:
    def __init__(self, cert_filename, key_filename):
        print('Starting the server')
        self.context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        self.context.load_cert_chain(certfile=cert_filename, keyfile=key_filename)
        print('[SYSTEM] The server is running')

    def start(self, host='localhost', port=10023):
        #Create new server socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind((host, port))
        sock.listen(5)
        self.thread_connection(sock)

    #Wait for new connections
    def newConnections(self, socket):
        while True:
            sock, address = socket.accept()
            try:
                wrapped_socket = self.context.wrap_socket(sock, server_side=True)
                global total_connections
                connections.append(Client(wrapped_socket, address, total_connections, True))
                connections[len(connections) - 1].start()
                print(f'New connection at ID {str(connections[len(connections) - 1])}')
                total_connections += 1
            except:
                print(f'[ALERT] The client {address} has an unknown SSL certificate')

    def thread_connection(self, server_socket):
        #Create new thread to wait for connections
        newConnectionsThread = threading.Thread(target = self.newConnections, args = (server_socket,))
        newConnectionsThread.start()


if __name__ == '__main__':
    server = Server("server/server.crt", "server/server.key")
    server.start('localhost', 10023)