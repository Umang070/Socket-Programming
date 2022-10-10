import socket
import random
import string
from threading import Thread
import os
import shutil
from pathlib import Path


def get_working_directory_info(working_directory):
    """
    Creates a string representation of a working directory and its contents.
    :param working_directory: path to the directory
    :return: string of the directory and its contents.
    """
    
    dirs = '\n-- ' + '\n-- '.join([i.name for i in Path(working_directory).iterdir() if i.is_dir()])
    files = '\n-- ' + '\n-- '.join([i.name for i in Path(working_directory).iterdir() if i.is_file()])
    dir_info = f'Current Directory: {working_directory}:\n|{dirs}{files}'
    return dir_info


def generate_random_eof_token():
    """Helper method to generates a random token that starts with '<' and ends with '>'.
     The total length of the token (including '<' and '>') should be 10.
     Examples: '<1f56xc5d>', '<KfOVnVMV>'
     return: the generated token.
     """
    eof_token = '<' + ''.join(random.sample((string.ascii_letters+string.digits),8)) + '>'
    return eof_token
    


def receive_message_ending_with_token(active_socket, buffer_size, eof_token):
    """
    Same implementation as in receive_message_ending_with_token() in client.py
    A helper method to receives a bytearray message of arbitrary size sent on the socket.
    This method returns the message WITHOUT the eof_token at the end of the last packet.
    :param active_socket: a socket object that is connected to the server
    :param buffer_size: the buffer size of each recv() call
    :param eof_token: a token that denotes the end of the message.
    :return: a bytearray message with the eof_token stripped from the end.
    """
    recv_data = bytearray()
    while True:
        recv_packet = active_socket.recv(buffer_size)
        recv_data.extend(recv_packet)
        if recv_packet[-10:] == eof_token.encode():
            recv_data = recv_data[:-10]
            break
    return recv_data    

def handle_cd(current_working_directory, new_working_directory):
    """
    Handles the client cd commands. Reads the client command and changes the current_working_directory variable 
    accordingly. Returns the absolute path of the new current working directory.
    :param current_working_directory: string of current working directory
    :param new_working_directory: name of the sub directory or '..' for parent
    :return: absolute path of new current working directory
    """
    
    new_dir_path = os.path.join(current_working_directory, new_working_directory)
    try:
        os.chdir(new_dir_path)
        return os.getcwd()
    except FileNotFoundError:
        print(f"Directory: {new_dir_path} does not exist")
        return 'Error '+f"Directory: {new_dir_path} does not exist"
    except NotADirectoryError:
        print(f"{new_dir_path} is not a directory")
        return 'Error '+ f"{new_dir_path} is not a directory"



def handle_mkdir(current_working_directory, directory_name):
    """
    Handles the client mkdir commands. Creates a new sub directory with the given name in the current working directory.
    :param current_working_directory: string of current working directory
    :param directory_name: name of new sub directory
    """
    final_directory = os.path.join(current_working_directory, directory_name)
    if not os.path.exists(final_directory):
        os.makedirs(final_directory)    
    print("final_directory ",final_directory)
    os.chdir(final_directory)
    return os.getcwd()  
    


def handle_rm(current_working_directory, object_name):
    """
    Handles the client rm commands. Removes the given file or sub directory. Uses the appropriate removal method
    based on the object type (directory/file).
    :param current_working_directory: string of current working directory
    :param object_name: name of sub directory or file to remove
    """
    isExist = os.path.exists(object_name)
    print(f"File or directory exists : {isExist}")
    if isExist:
        #first check object_name is file or directory
        is_directory = Path(object_name).is_dir()
        is_file = Path(object_name).is_file()
        
        #if object_name is file then remove
        if is_file:
            file_path = Path(object_name)
            file_path.unlink()
        # empty_dir =  r'%s' % object_name for literal path

        # if object_name is directory then removes
        elif is_directory:
            dir_path = os.path.join(current_working_directory, object_name)    
            # removing directory and sub directory as well as files inside sub directories
            shutil.rmtree(dir_path, ignore_errors=False)    
        return 'Directory/File Removed :'                    
    else:
        print("Neither directory nor file found at specified location")
        return 'Error ' + 'Neither directory nor file found at specified location'   
    
 
 


def handle_ul(current_working_directory, file_name, service_socket, eof_token):
    """
    Handles the client ul commands. First, it reads the payload, i.e. file content from the client, then creates the
    file in the current working directory.
    Use the helper method: receive_message_ending_with_token() to receive the message from the client.
    :param current_working_directory: string of current working directory
    :param file_name: name of the file to be created.
    :param service_socket: active socket with the client to read the payload/contents from.
    :param eof_token: a token to indicate the end of the message.
    """
    new_file_path = os.path.join(current_working_directory, file_name)

    file = open(new_file_path, "wb")  
    file_content = receive_message_ending_with_token(service_socket, 1024,eof_token)
    file.write(file_content)
    file.close()


def handle_dl(current_working_directory, file_name, service_socket, eof_token):
    """
    Handles the client dl commands. First, it loads the given file as binary, then sends it to the client via the
    given socket.
    :param current_working_directory: string of current working directory
    :param file_name: name of the file to be sent to client
    :param service_socket: active service socket with the client
    :param eof_token: a token to indicate the end of the message.
    """
    new_file_path = os.path.join(current_working_directory, file_name)
    
    file = open(new_file_path, "rb")    
    file_content = file.read()
    file_content_with_EOF = file_content + eof_token.encode()  
    service_socket.sendall(file_content_with_EOF)
    file.close()    
            
class ClientThread(Thread):
    def __init__(self, service_socket : socket.socket, address : str):
        Thread.__init__(self)
        self.service_socket = service_socket
        self.address = address
        self.eof_token = None  
        self.current_working_dir_info = None  
        self.working_directory = None   
        self.received_command_str = None

    def run(self):

        
        print("Connection from : ", self.address)

        # initialize the connection

        self.eof_token = generate_random_eof_token()

        # send random eof token

        self.service_socket.sendall(self.eof_token.encode())

        print("EOF TOKEN : ",self.eof_token)

        # establish working directory
        self.working_directory = os.getcwd()
        
        # send the current dir info

        self.current_working_dir_info = get_working_directory_info(self.working_directory)
        self.service_socket.sendall((self.current_working_dir_info+self.eof_token).encode())

        
        while True:
            self.received_command_str = receive_message_ending_with_token(self.service_socket,1024,self.eof_token).decode()
            
            print("Received command from client is : ",self.received_command_str)    
            # get the command and arguments and call the corresponding method
            if self.received_command_str.startswith('cd'):
                method_response = handle_cd(self.working_directory, (self.received_command_str.split(' ')[1:]))
                if method_response.startswith('Error'):
                    self.service_socket.sendall(method_response.encode())
                else:
                    self.working_directory = method_response
            elif self.received_command_str.startswith('mkdir'):
                self.working_directory =  handle_mkdir(self.working_directory,self.received_command_str.split(' ')[1])
            elif self.received_command_str.startswith('rm'):
                method_response = handle_rm(self.working_directory,self.received_command_str.split(' ')[1])
                if method_response.startswith('Error'):
                    self.service_socket.sendall(method_response.encode())
                else:
                    pass
            elif self.received_command_str.startswith('ul'):
                file_name = self.received_command_str.split(' ')[1]                
                handle_ul(self.working_directory,file_name,self.service_socket, self.eof_token)
            elif self.received_command_str.startswith('dl'):
                file_name = self.received_command_str.split(' ')[1]
                handle_dl(self.working_directory,file_name,self.service_socket,self.eof_token)
            elif self.received_command_str.startswith('exit'):
                break
            # send current dir info        
            self.current_working_dir_info = get_working_directory_info(self.working_directory)
            print("After Command Executed : ",self.current_working_dir_info)
            self.service_socket.sendall((self.current_working_dir_info+self.eof_token).encode())
        self.service_socket.close()
        print('Connection closed from:', self.address)

def main():
    HOST = "127.0.0.1"
    PORT = 65432

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen()
        print("Server is Listening on port", PORT)
        while True:
            service_socket, client_address = s.accept()
            clientThreadObj = ClientThread(service_socket, client_address)
            clientThreadObj.start()                

if __name__ == '__main__':
    main()
