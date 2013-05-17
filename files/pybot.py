#!/usr/bin/env python3

from sqlite3 import dbapi2 as sqlite
from time import sleep
from sys import exit
import os
import socket

irc = { "host": "localhost", "port": "6667", "nick": "myBot", "server": "localhost", "channel": "#test"}


def connect_irc(irc):
	try:		
		for i in socket.getaddrinfo(irc["host"],irc["port"], socket.AF_UNSPEC, socket.SOCK_STREAM):
			af, socktype, proto, canonname, sa = i
			try:
				s = socket.socket(af, socktype, proto)
			except socket.error as msg:
				s= None
				continue
			try:
				s.connect(sa)
			except socket.error as msg:
				s.close()
				s = None
				continue
			break
		if s is None:
			exit(1)
		connect_channel(s, irc)
		while True:
			data = s.recv(1024).decode("utf-8")
			if data:
				print(data)
				handle_message(s, data)
			else:
				break

	except KeyboardInterrupt:
		s.close()
		exit(1)

def connect_channel(s, irc):
	s.send(bytes('NICK %s\r\n' % irc["nick"]))
	s.send(bytes('USER %s %s pyBot : %s\r\n' % (irc["nick"], irc["host"], irc["nick"])))
	s.send(bytes('JOIN %s\r\n' % (irc["channel"])))

def handle_message(s, data):
	if "PING " in data:
		msg = "PONG"
		send_msg(s, msg)

	if "PRIVMSG %s :!ping" % irc["channel"] in data:
		msg = "PRIVMSG %s :pong!\r\n" % irc["channel"]
		send_msg(s, msg)

	if ("PRIVMSG %s :%s" % (irc["channel"], irc["nick"])) in data:
		msg = "PRIVMSG %s :Hello I'm an IRC Bot made by IBoehmer\r\n" % irc["channel"]
		send_msg(s, msg) 
	if ("PRIVMSG %s :-q" % irc["channel"]) in data:
		msg = "PRIVMSG %s :Your sure I should quit [j/n]\r\n" % irc["channel"]
		send_msg(s, msg)

		while msg:
			answer = raw_input("j/n")

			if (answer == ("PRIVMSG %s :j" % irc["channel"])):
				msg_state = "%s :Disconnecting...\r\n" % irc["channel"]
				send_msg(s, msg_state)
				s.close()
				return(0)
			elif (answer == ("PRIVMSG %s :n" % irc["channel"])):
				msg_state = "PRIVMSG %s :Ok, I stay\r\n" % irc["channel"]
				send_msg(s, msg_state)
				break;
			else:
				msg_state = "PRIVMSG %s :Could not read answer\r\n" % irc["channel"]
				send_msg(s, msg_state)
				break;
		

def send_msg(s, msg):
	s.send(bytes("%s" % (msg)))

	if __debug__:
		print(msg)

#**************SQLite**************

def create_db_connection():
	try:
		#directory for chatlog
		directory = "log/sqlite.db"
		#checks if the folder "log" exists
		if not os.path.isdir("log"):
			print("Database directory does not exist")
			exit(1)				
		connection = sqlite.connect(directory)
			
	except sqlite.Error:
		print(sqlite.Error)
		exit(1)
	#only return if no except happens
	else:
		return connection

def connect_db(connection):
	try:
		cursor = connection.cursor()
	except sqlite.Error:
		print(sqlite.Error)
		exit(1)
	finally:
		return cursor

def create_table(cursor):
	cursor.execute('''CREATE TABLE IF NOT EXISTS logging(timestamp DATE, line TEXT)''')
	
def close_db(connection, cursor):
	cursor.close()
	connection.commit()
	connection.close()

#**************Main**************

def main():
	connection = create_db_connection()
	cursor = connect_db(connection)
	create_table(cursor)
	close_db(connection, cursor)
	connect_irc(irc)

if __name__ == "__main__":
	main()
		
