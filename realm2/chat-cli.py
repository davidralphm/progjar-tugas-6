import socket
import os
import json

TARGET_IP = "127.0.0.1"
TARGET_PORT = 9000

class ChatClient:
    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_address = (TARGET_IP,TARGET_PORT)
        self.sock.connect(self.server_address)

        self.tokenid = ""

    def proses(self, cmdline):
        j = cmdline.split(" ")

        try:
            command = j[0].strip()

            if (command == 'auth'):
                username = j[1].strip()
                password = j[2].strip()

                return self.login(username, password)
            elif (command == 'send'):
                usernameto = j[1].strip()
                message = j[2]

                for w in j[3:]:
                   message = "{} {}" . format(message,w)

                return self.sendmessage(usernameto, message)
            elif (command == 'inbox'):
                return self.inbox()
            else:
                return "*Maaf, command tidak benar"

        except IndexError:
                return "-Maaf, command tidak benar"

    def sendstring(self, string):
        try:
            self.sock.sendall(string.encode())
            receivemsg = ""

            while True:
                data = self.sock.recv(64)

                # print("diterima dari server",data)

                if data:
                    receivemsg = "{}{}" . format(receivemsg, data.decode()) # data harus didecode agar dapat di operasikan dalam bentuk string

                    if receivemsg[-4:] == '\r\n\r\n':
                        # print("end of string")
                        return json.loads(receivemsg)
        except Exception as e:
            print(str(e))
            self.sock.close()

            return {
                'status' : 'ERROR',
                'message' : 'Gagal'
            }

    def login(self, username, password):
        string = "auth {} {}\r\n" . format(username, password)
        result = self.sendstring(string)

        if result['status'] == 'OK':
            self.tokenid=result['tokenid']

            return "username {} logged in, token {} " .format(username, self.tokenid)
        
        return "Error, {}" . format(result['message'])
    
    def sendmessage(self, usernameto="xxx", message="xxx"):
        if (self.tokenid == ""):
            return "Error, not authorized"

        string="send {} {} {}\r\n" . format(self.tokenid, usernameto, message)
        print(string)
        result = self.sendstring(string)
        
        if result['status'] == 'OK':
            return "message sent to {}" . format(usernameto)
        
        return "Error, {}" . format(result['message'])

    def inbox(self):
        if (self.tokenid == ""):
            return "Error, not authorized"

        string="inbox {}\r\n" . format(self.tokenid)
        result = self.sendstring(string)

        if result['status'] == 'OK':
            output = ''
            messages = result['messages']

            for k, v in messages.items():
                if len(v) == 0:
                    continue

                if output == '':
                    output = f'{k}\n'
                else:
                    output = f'{output}\n\n{k}\n'

                for i in v:
                    output = f'{output}\t{i["msg"]}\n'
                    # print(f'\t{i["msg"]}')
            
            if output == '':
                return 'No new messages'
                
            return output
            # return "{}" . format(json.dumps(result['messages']))

        return "Error, {}" . format(result['message'])

if __name__ == "__main__":
    cc = ChatClient()

    while True:
        cmdline = input("Command {} : " . format(cc.tokenid))
        print(cc.proses(cmdline))