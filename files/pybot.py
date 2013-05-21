#!/usr/bin/env python3

from sqlite3 import dbapi2 as sqlite
from time import sleep
from sys import exit
import time, datetime
import sys, getopt
import string
import os
import socket

irc = { "host": "localhost", "port": "6667", "nick": "myBot", "server": "localhost", "channel": "#test"}
irc_msg = { "time": " ", "channel": " ", "user": " ", "message": " "}
logging = False

def connect_irc(irc, cursor):
	try:		
		for i in socket.getaddrinfo(irc["host"],irc["port"], socket.AF_UNSPEC, socket.SOCK_STREAM):
			af, socktype, proto, canonname, sa = i
			try:
				s = socket.socket(af, socktype, proto)
			except socket.error as msg:
				s.close()
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
				handle_message(s, data, cursor)
			else:
				break

	except KeyboardInterrupt:
		s.close()
		exit(1)

def connect_channel(s, irc):
	s.send(bytes('NICK %s\r\n' % irc["nick"]))
	s.send(bytes('USER %s %s pyBot : %s\r\n' % (irc["nick"], irc["host"], irc["nick"])))
	s.send(bytes('JOIN %s\r\n' % (irc["channel"])))

def handle_message(s, data, cursor):
	full_msg = string.split(data)
	irc_msg["message"] = " ".join(full_msg[3:])
	irc_msg["user"] = full_msg[0].split("!")
	irc_msg["user"] = irc_msg["user"][0].replace(":", "")
	irc_msg["time"] = time.time()
	irc_msg["channel"] = irc["channel"]
 	
	if full_msg[0] == "PING":
		msg = "PONG"
		send_msg(s, msg)
	if full_msg[1] == "JOIN" and irc_msg["user"] != irc["nick"]:
		msg = ("PRIVMSG "+irc_msg["user"]+ " :Welcome\r\n")
		send_msg(s, msg)
		
		print("Logging: %s" % logging)	
		if logging:
			irc_msg["message"]= ("%s joined channel" % irc_msg["user"])
			logDatabase(irc_msg, cursor)
	if full_msg[1] == "PRIVMSG" and full_msg[2] != irc["nick"]:
		print("Logging: %s" % logging)	
		if logging:
			logDatabase(irc_msg, cursor)
		if "!ping" in irc_msg["message"]:
			msg = ("PRIVMSG "+irc["channel"]+ " :pong!\r\n")
			send_msg(s, msg)
		if ("Show log") in irc_msg["message"]:
			selectFrom_table(s, cursor)
			
	if full_msg[1] == "PRIVMSG" and full_msg[2] != irc["nick"] and irc["nick"] in irc_msg["message"]:
		if ("Help") in irc_msg["message"]:
			commands(s, irc_msg, irc)
		if " log" in irc_msg["message"]:
			HandleLogging("true")
			print("Logging: %s" % logging)	
			msg = ("PRIVMSG "+irc["channel"]+ " :Chat log activated\r\n")
			send_msg(s, msg) 
		if " !log" in irc_msg["message"]:
			HandleLogging("false")
			msg = ("PRIVMSG "+irc["channel"]+ " :Chat log deactivated\r\n")
			send_msg(s, msg) 
'''	

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
		
'''	

def send_msg(s, msg):
	s.send(bytes("%s" % (msg)))

	if __debug__:
		print(msg)

def commands(s, irc_msg, irc):
	send_msg(s, ("PRIVMSG "+irc_msg["user"]+" :"+irc["nick"]+" log - Activates chat log\r\n"))
	send_msg(s, ("PRIVMSG "+irc_msg["user"]+" :"+irc["nick"]+" !log - Deactivates chat log\r\n"))

def HandleLogging(value):
	global logging
	elif value == "true":
		logging = True
		print("Logging changed to %s" % logging)
		return logging
	else:
		logging = False
		print("Logging changed to %s" % logging)
		return logging

def logDatabase(irc_msg, cursor):
		if __debug__:
			print("Insert into database")
		insert_table(cursor, irc_msg)
		
		cursor.execute("SELECT * FROM CompleteChat")
		print("the database now contains:")
		for row in cursor:
			print row

#***********Command line parameters********
def GetArguments(irc, argv):
	try:
		opts, args = getopt.getopt(argv, "h:c:n:", ["host=", "channel=", "nick="])
	except getopt.GetoptError:
		print ("Use: pybot.py -h <host> -c <channel> -n <nick>")
		exit(1)
	
	for opt, arg in opts:
		if opt in ("-h", "--host"):
			irc["host"] = arg
		elif opt in ("-c", "--channel"):
			irc["channel"] = arg
		elif opt in ("-n", "--nick"):
			irc["nick"] = arg
	
	print("Value change successful")
			


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
	cursor.execute("CREATE TABLE IF NOT EXISTS CompleteChat(Time TIMESTAMP, Channel TEXT, User TEXT, Message TEXT)")

def insert_table(cursor, irc_msg):
	cursor.execute("INSERT INTO CompleteChat VALUES (?,?,?,?)", (irc_msg["time"], irc_msg["channel"], irc_msg["user"], irc_msg["message"]))

def selectFrom_table(s, cursor):
	cursor.execute("SELECT Min(User) FROM CompleteChat ")
	user = cursor.fetchone()
	#send_msg(s, "PRIVMSG "+irc_msg["channel"]+ " : Last User:" +user[0][0]+"\r\n")
	print (user[0][0])
		
	
	
def close_db(connection, cursor):
	cursor.close()
	connection.commit()
	connection.close()

#**************Main**************

def main():
	#if the user dos not give any command line parameters the default values will be used
	if sys.argv > 1:	
		GetArguments(irc, sys.argv[1:])
	connection = create_db_connection()
	cursor = connect_db(connection)
	create_table(cursor)
	connect_irc(irc, cursor)
	close_db(connection, cursor)
	

if __name__ == "__main__":
	main()
		
