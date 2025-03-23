import os
from config import *

class CLIManager:
    def __init__(self, ):
        self.initial_message()
    
    def initial_message(self):
        print("Welcome to the CLI Manager, write 'help' to see the available commands")
    
    def handle_help(self,):
        print("Available commands:")
        print("help: Display this message")
        print("exit: Exit the CLI")
    
    def get_information(self):
        running_conf =  Config()
        valid = False
        while not valid:
            print("Encrypt(1) or Decrypt(2)?")
            choice = input().strip()
            if choice == "1":
                running_conf.encrypt = True
                valid = True
            elif choice == "2":
                running_conf.encrypt = False
                valid = True
            elif choice == "help":
                self.handle_help()
            elif choice == "exit":
                exit()
            else:
                print("Invalid choice, please try again")
                
        valid = False
        while not valid:
            print("Enter the path of the file to encrypt/decrypt")
            path = input().strip()
            if path == "help":
                self.handle_help()
            elif path == "exit":
                exit()
            if os.path.exists(path):
                running_conf.path = path
                valid = True
            else:
                print("Invalid path, please try again")
                
        valid = False
        while not valid and running_conf.encrypt:
            print("Do you want to keep the folder (1) or delete it (2)?")
            folder_choice = input().strip()
            if folder_choice == "1":
                running_conf.keep_folder = True
                valid = True
            elif folder_choice == "2":
                running_conf.keep_folder = False
                valid = True
            elif folder_choice == "help":
                self.handle_help()
            elif folder_choice == "exit":
                exit()
            else:
                print("Invalid choice, please try again")
                
        valid = False
        while not valid:
            print(f"Enter the key of length {KEY_LEN} ")
            key = input().strip()
            if key == "help":
                self.handle_help()
            elif key == "exit":
                exit()
            if len(key) == KEY_LEN:
                running_conf.key = key
                valid = True
            else:
                print("Invalid key, please try again")
            
        return running_conf
         
         
         
         
class Config:
    def __init__(self):
        self.encrypt = None #True if encrypting, False if decrypt
        self.path = None
        self.key = None
        self.keep_folder = None
        