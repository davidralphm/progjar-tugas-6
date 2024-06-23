import sys
import os
import json
import uuid
import logging
import socket
from queue import  Queue

REALM_1_ADDRESS = (('127.0.0.1', 9000))
REALM_2_ADDRESS = (('127.0.0.1', 9001))

class Chat:
	def __init__(self):
		self.sessions = {}
		self.users = {}
		self.groups = {}

		self.users['messi'] = {
			'nama': 'Lionel Messi',
			'negara': 'Argentina',
			'password': 'surabaya',
			'incoming' : {},
			'outgoing': {}
		}

		self.users['henderson'] = {
			'nama': 'Jordan Henderson',
			'negara': 'Inggris',
			'password': 'surabaya',
			'incoming': {},
			'outgoing': {}
		}

		self.users['lineker'] = {
			'nama': 'Gary Lineker',
			'negara': 'Inggris',
			'password': 'surabaya',
			'incoming': {},
			'outgoing':{}
		}

		self.groups['group1'] = {
			'messi',
			'henderson',
			'lineker'
		}

		self.groups['group3'] = {
			'messi',
			'henderson',
			'lineker',
			'test1',
			'test2',
			'test3'
		}

	def proses(self,data):
		j = data.split(" ")

		try:
			command = j[0].strip()

			if (command == 'auth'):
				username = j[1].strip()
				password = j[2].strip()

				logging.warning("AUTH: auth {} {}" . format(username, password))

				return self.autentikasi_user(username, password)
			elif (command == 'send'):
				sessionid = j[1].strip()
				usernameto = j[2].strip()

				message = ""

				for w in j[3:]:
					message = "{} {}" . format(message, w)

				usernamefrom = self.sessions[sessionid]['username']

				logging.warning("SEND: session {} send message from {} to {}" . format(sessionid, usernamefrom, usernameto))
				
				return self.send_message(sessionid, usernamefrom, usernameto, message)
			elif (command == 'send_multirealm'):
				usernamefrom = j[1].strip()
				usernameto = j[2].strip()

				message = ""

				for w in j[3:]:
					message = "{} {}" . format(message, w)

				logging.warning("SEND_MULTIREALM: send message from {} to {}" . format(usernamefrom, usernameto))
				
				return self.recv_message_multirealm(usernamefrom, usernameto, message)
			elif (command == 'inbox'):
				sessionid = j[1].strip()
				username = self.sessions[sessionid]['username']

				logging.warning("INBOX: {}" . format(sessionid))
				
				return self.get_inbox(username)
			else:
				return {
					'status': 'ERROR',
					'message': '**Protocol Tidak Benar'
				}

		except KeyError:
			return {
				'status': 'ERROR',
				'message' : 'Informasi tidak ditemukan'
			}

		except IndexError:
			return {
				'status': 'ERROR',
				'message': '--Protocol Tidak Benar'
			}

	def autentikasi_user(self, username, password):
		if (username not in self.users):
			return {
				'status': 'ERROR',
				'message': 'User Tidak Ada'
			}

		if (self.users[username]['password'] != password):
			return {
				'status': 'ERROR',
				'message': 'Password Salah'
			}

		tokenid = str(uuid.uuid4()) 
		
		self.sessions[tokenid] = {
			'username': username,
			'userdetail':self.users[username]
		}

		return { 'status': 'OK', 'tokenid': tokenid }
	
	def get_user(self, username):
		if (username not in self.users):
			return False

		return self.users[username]

	def get_group(self, group):
		if (group not in self.groups):
			return False

		return self.groups[group]

	def send_another_realm(self, username_from, username_dest, message):
		command = f'send_multirealm {username_from} {username_dest} {message}'.encode(encoding='utf-8')
		recv = ''
		result = {
			'status' : 'ERROR',
			'message' : 'Gagal'
		}

		sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		try:
			sock.connect(REALM_2_ADDRESS)
			sock.sendall(command)

			while True:
				data = sock.recv(64)
				print(f'got data: {data.decode()}')

				if data:
					recv = f'{recv}{data.decode()}'

					if recv[-4:] == '\r\n\r\n':
						print('end')
						result = json.loads(recv)
						break

			sock.close()
		except Exception as e:
			print(str(e))

		print(result)

		return result

	def send_message(self, sessionid, username_from, username_dest, message):
		# Cek session
		if (sessionid not in self.sessions):
			return {
				'status': 'ERROR',
				'message': 'Session Tidak Ditemukan'
			}

		# Cek user pengirim
		s_fr = self.get_user(username_from)

		# Jika user pengirim tidak ada
		if (s_fr == False):
			return {
				'status': 'ERROR',
				'message': 'User Tidak Ditemukan'
			}
		
		# Coba kirim private message
		result = self.send_message_private(username_from, username_dest, message)

		if result['status'] == 'OK':
			return result

		# Coba kirim group message
		result = self.send_message_group(username_from, username_dest, message)

		if result['status'] == 'OK':
			return result
		
		# Coba kirim multi - realm message
		return self.send_another_realm(username_from, username_dest, message)

	def send_message_private(self, username_from, username_dest, message):
		s_to = self.get_user(username_dest)

		# Jika user tujuan tidak ditemukan di realm ini
		if s_to == False:
			return {
				'status': 'ERROR',
				'message': 'User / Group Tidak Ditemukan'
			}

		self.put_message_in_inbox(username_from, username_dest, message)

		return {
			'status': 'OK',
			'message': 'Message Sent'
		}

	def send_message_group(self, username_from, username_dest, message):
		s_to = self.get_group(username_dest)

		# Jika group tujuan tidak ditemukan di realm ini
		if s_to == False:
			return {
				'status': 'ERROR',
				'message': 'User / Group Tidak Ditemukan'
			}

		# Jika user tidak ada di dalam group ini
		if username_from not in s_to:
			return {
				'status': 'ERROR',
				'message': 'User / Group Tidak Ditemukan'
			}

		for user in s_to:
			if user in self.users:
				self.put_message_in_inbox(username_dest, user, f'({username_from}): {message}')
			else:
				self.send_another_realm(username_dest, user, f'({username_from}): {message}')
		
		return {
			'status': 'OK',
			'message': 'Message Sent'
		}
	
	def put_message_in_inbox(self, username_from, username_dest, message):
		s_to = self.get_user(username_dest)

		if s_to == False:
			return

		message = {
			'msg_from': username_from,
			'msg_to': username_dest,
			'msg': message
		}

		inqueue_receiver = s_to['incoming']

		try:
			inqueue_receiver[username_from].put(message)
		except KeyError:
			inqueue_receiver[username_from] = Queue()
			inqueue_receiver[username_from].put(message)
		
	def recv_message_multirealm(self, username_from, username_dest, message):
		result = self.send_message_private(username_from, username_dest, message)

		if result['status'] == 'OK':
			return result
		
		return self.send_message_group(username_from, username_dest, message)

	def get_inbox(self, username):
		s_fr = self.get_user(username)
		incoming = s_fr['incoming']
		msgs={}

		for users in incoming:
			msgs[users] = []

			while not incoming[users].empty():
				msgs[users].append(s_fr['incoming'][users].get_nowait())
			
		return {
			'status': 'OK',
			'messages': msgs
		}


if __name__ == "__main__":
	j = Chat()
	sesi = j.proses("auth messi surabaya")
	print(sesi)
	#sesi = j.autentikasi_user('messi','surabaya')
	#print sesi
	tokenid = sesi['tokenid']
	print(j.proses("send {} henderson hello gimana kabarnya son " . format(tokenid)))
	print(j.proses("send {} messi hello gimana kabarnya mess " . format(tokenid)))

	#print j.send_message(tokenid,'messi','henderson','hello son')
	#print j.send_message(tokenid,'henderson','messi','hello si')
	#print j.send_message(tokenid,'lineker','messi','hello si dari lineker')


	print("isi mailbox dari messi")
	print(j.get_inbox('messi'))
	print("isi mailbox dari henderson")
	print(j.get_inbox('henderson'))
















