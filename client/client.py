import socket
import threading
import sys, os
from pickle import dumps, loads
import ssl

import numpy as np

from Tpm.TPM import *
from Cipher.RNN_cipher import *
from Cipher.utils import pad, unpad

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'  

class Client:
    def __init__(self, cert_file_name):
        self.context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        self.context.verify_mode = ssl.CERT_REQUIRED
        self.context.check_hostname = True
        self.context.load_verify_locations(cert_file_name)

        k = 64
        n = 8
        l = 255
        self.machine = TPM(k, n, l)
        self.update_rule = 'random_walk'

        self.cipher = RNN_Cipher(use_saved_weights=False)
        self.de_cipher = RNN_Cipher(use_saved_weights=False)
        self.key_ready = False

    def connect(self, host='localhost', port=10023, server_hostname='localhost'):
        #Attempt connection to server
        try:
            self.socket = self.context.wrap_socket(socket.socket(socket.AF_INET), server_hostname=server_hostname)
            self.socket.connect((host, port))
            self.start()
        except:
            print('Could not make a connection to the server.\nPlease verify the authenticity of the certificate.')
            sys.exit(0)

    def start(self):
        #Create new thread to wait for data
        receiveThread = threading.Thread(target = self.receive, args = (self.socket, True))
        receiveThread.start()
        self.send_message()

    #Wait for incoming data from server
    def receive(self, socket, signal):
        while signal:
            try:
                data = socket.recv(4096)
                self.__recv_handler(data)
            except:
                print('You have been disconnected from the server.')
                signal = False
                break

    def __recv_handler(self, data):
        recv_msg = loads(data)
        recv_handlers = {
            0: self.display_data, # /list
            1: self.display_data, # req private
            2: self.display_chat, # message
            3: self.get_matrix, # get matrix
            4: self.get_tau, # get tau
            5: self.get_private_message, # get private message
            6: self.display_data, # error
            777: self.key_expansion, # key expansion
            888: self.display_data, # hello info
            999: self.drop_params # reset parameters
        }
        recv_type = recv_msg.get('type')
        if recv_type in recv_handlers:
            recv_handlers[recv_type](recv_msg)

    def display_data(self, recv_msg):
        print(recv_msg['data'])
    
    def display_chat(self, recv_msg):
        print(f"User ID[{recv_msg['from']}]: {recv_msg['data']}")

    def get_matrix(self, recv_msg):
        matrix = recv_msg['rand_matrix']
        tau = self.machine(matrix)
        message = dumps(f'/tau {tau}')
        self.socket.sendall(message)
    
    def get_tau(self, recv_msg):
        tau_partner = recv_msg['tau']
        self.machine.update(tau_partner, self.update_rule)
    
    def get_private_message(self, recv_msg):
        data, partner_id = recv_msg['data'], recv_msg['id']
        if self.key_ready:
            decrypted_data = self.de_cipher.Decrypt(data)
            message = unpad(decrypted_data, 8).decode("utf-8")
            print(f'Secret message from [{partner_id}]: {message}')

    def create_key(self, W):
        length, block_size = W.shape
        x_train = np.array(list(np.random.bytes(length * block_size)))
        x_train = np.reshape(x_train, (length, block_size)) / 256
        y_train = np.abs(W) / 256
        return (x_train, y_train)

    def key_expansion(self, recv_msg):
        print(recv_msg['data'])
        secret_weight = self.machine.W
        x_train, y_train = self.create_key(secret_weight)
        self.cipher.KeyExpansion(x_train, y_train)
        self.de_cipher.KeyExpansion(x_train, y_train)
        self.key_ready = True

    def send_private_message(self, message):
        if self.key_ready:
            message = pad(bytes(message, 'utf-8'), 8)
            encrypted_data = self.cipher.Encrypt(message)
            data = dumps({'/pp': encrypted_data})
            self.socket.sendall(data)
    
    def drop_params(self, recv_msg):
        k = 64
        n = 8
        l = 255
        self.machine = TPM(k, n, l)
        self.cipher = RNN_Cipher(use_saved_weights=False)
        self.de_cipher = RNN_Cipher(use_saved_weights=False)
        self.key_ready = False
        print(recv_msg['data'])
            
    def __send_handler(self, message):       
        if message[:3] == '/pp':
            self.send_private_message(message[4:])
        else:
            self.socket.sendall(dumps(message))

    def send_message(self):
            #Send data to server
            while True:
                try:
                    message = input()
                    if message:
                        self.__send_handler(message)
                except KeyboardInterrupt:
                    print('You have logged out of the server.')
                    self.socket.close()
                    break
    
        


if __name__ == '__main__':
    host = 'localhost'
    port = 10023
    client = Client("server.crt")
    client.connect(host, port, 'localhost')