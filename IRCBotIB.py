#!/usr/bin/env python3

import os, sys, socket, string, time, datetime, ConfigParser, optparse
from sqlite3 import dbapi2 as sqlite
from time import sleep
from sys import exit

#get the connection info from the config File
config = ConfigParser.ConfigParser()
config.read("config.ini")

irc = { "host": config.get("connect", "host"), "port": config.get("connect", "port"), "nick": config.get("connect", "nick"), "server": config.get("connect", "server"), "channel": config.get("connect", "channel")}
irc_msg = { "time": " ", "channel": " ", "user": " ", "message": " ", "reciever": " "}
logging = config.getboolean("bot", "log")

	

def connect_irc(irc, connection, cursor):
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
			sys.exit(1)
		connect_channel(s, irc)
		while True:
			data = s.recv(1024).decode("utf-8")
			if data:
				print(data)
				handle_message(s, data, connection, cursor)
			else:
				break

	except KeyboardInterrupt:
		s.close()
		sys.exit(1)

def connect_channel(s, irc):
	s.send(bytes("NICK %s\r\n" % irc["nick"]))
	s.send(bytes("USER %s %s IRCBotIB : %s\r\n" % (irc["nick"], irc["host"], irc["nick"])))
	s.send(bytes("JOIN %s\r\n" % (irc["channel"])))

def close_irc(s, connection, cursor):
	close_db(connection, cursor)
	s.close()
	closeDaemon()
	sys.exit()

#*********MessageHandeling*********

def handle_message(s, data, connection, cursor):
	full_msg = string.split(data)
	irc_msg["message"] = " ".join(full_msg[3:])
	irc_msg["user"] = full_msg[0].split("!")
	irc_msg["user"] = irc_msg["user"][0].replace(":", "")
	irc_msg["reciever"] = full_msg[2]
	irc_msg["time"] = time.time()
	irc_msg["channel"] = irc["channel"]
	
	#if the message wan't send in the general cahnnel it was a priavte msg from a user, he will be the reciever of the answer	
	if irc_msg["reciever"] != irc_msg["channel"]:
		irc_msg["reciever"] = irc_msg["user"]
 	
	if full_msg[0] == "PING":
		msg = "PONG"
		send_msg(s, msg)
	#handling join
	if full_msg[1] == "JOIN" and irc_msg["user"] != irc["nick"]:
		addNewUser(cursor, irc_msg["time"], irc_msg["channel"], irc_msg["user"])
		msg = ("PRIVMSG "+irc_msg["user"]+ " :Welcome "+irc_msg["user"]+"! Ask for '"+irc["nick"]+" Help' if you need any.\r\n")
		send_msg(s, msg)
		
		print("Logging: %s" % logging)	
		if logging:
			irc_msg["message"]= (" joined the channel")
			logDatabase(irc_msg, cursor)
	#handling if user leaves channel or quits
	if full_msg[1] == "PART" and irc_msg["user"] != irc["nick"]:
		if logging:
			irc_msg["message"]= (" left the channel")
			logDatabase(irc_msg, cursor)
	if full_msg[1] == "QUIT" and irc_msg["user"] != irc["nick"]:
		if logging:
			irc_msg["message"]= (" left irc")
			logDatabase(irc_msg, cursor)
	if full_msg[1] == "TOPIC":
		send_msg(s, ("PRIVMSG "+irc_msg["reciever"]+ " :The current channel topic is"+irc_msg["message"]+"\r\n"))
	
	#handling the non commands to the bot
	if full_msg[1] == "PRIVMSG" and irc["nick"] not in irc_msg["message"]:
		print("Logging: %s" % logging)	
		if logging:
			logDatabase(irc_msg, cursor)
		if "!ping" in irc_msg["message"]:
			msg = ("PRIVMSG "+irc_msg["reciever"]+ " :pong!\r\n")
			send_msg(s, msg)
		if "hi" in irc_msg["message"] or "Hi" in irc_msg["message"]:
			send_msg(s, "PRIVMSG "+irc_msg["reciever"]+ " :Hi whats up?\r\n")
		if "hello" in irc_msg["message"] or "Hello" in irc_msg["message"]:
			send_msg(s, "PRIVMSG "+irc_msg["reciever"]+ " :Hello how are you doing?\r\n")
		if "Guten Tag" in irc_msg["message"] or "guten tag" in irc_msg["message"]:
			send_msg(s, "PRIVMSG "+irc_msg["reciever"]+ " :Oh your german! Ihnen auch einen guten Tag!\r\n")
		if "Talk to me" in irc_msg["message"]:
			send_msg(s, "PRIVMSG "+irc_msg["reciever"]+ " :Sorry I'm only a prototype, I don't have so many features\r\n")
	
			
	#commands to the bot: <botnick> <command>
	if full_msg[1] == "PRIVMSG" or irc["nick"] in irc_msg["message"]:
		if "Help" in irc_msg["message"] or ("help" in irc_msg["message"]):
			commands(s, irc_msg, irc)
		if "do log" in irc_msg["message"]:
			HandleLogging("true")
			print("Logging: %s" % logging)	
			msg = ("PRIVMSG "+irc_msg["reciever"]+ " :Chat log activated\r\n")
			send_msg(s, msg) 
		if "do not log" in irc_msg["message"]:
			HandleLogging("false")
			msg = ("PRIVMSG "+irc_msg["reciever"]+ " :Chat log deactivated\r\n")
			send_msg(s, msg) 
		if ("show log") in irc_msg["message"]:
			selectAll(s, cursor, irc_msg)
		if ("show user") in irc_msg["message"]:
			selectUser(s, cursor, irc_msg)
		if("show last action") in irc_msg["message"]:
			selectLastAction(s, cursor, irc_msg)
		if("last seen =") in irc_msg["message"]:
			search_user = irc_msg["message"].split("=")
			search_user = search_user[1].replace("= ", "")
			selectLastSeen(s, cursor, search_user, irc_msg["reciever"])
		if ("quit") in irc_msg["message"]:
			send_msg(s, ("PRIVMSG "+irc_msg["reciever"]+ " :Bye!\r\n"))
			if irc_msg["reciever"] != irc_msg["channel"]:
				send_msg(s, ("PRIVMSG "+irc_msg["channel"]+ " :Bye!\r\n"))
			close_irc(s, connection, cursor)
		#channel features
		if ("topic") in irc_msg["message"]:
			if ("set") in irc_msg["message"]:			
				setTopic(s, irc_msg)
			else:
				s.send(bytes("TOPIC %s\r\n" % irc_msg["channel"]))
		if ("change nick =") in irc_msg["message"]:
			changeNick(s, irc_msg, irc)
		if ("list user") in irc_msg["message"]:
			s.send(bytes("NAMES %s\r\n" % (irc["channel"])))
		if ("go to") in irc_msg["message"]:
			changeChannel(s, irc_msg)


def send_msg(s, msg):
	s.send(bytes("%s" % (msg)))

	if __debug__:
		print(msg)

def commands(s, irc_msg, irc):
	send_msg(s, ("PRIVMSG "+irc_msg["user"]+" :"+irc["nick"]+" do log - Activates chat log\r\n"))
	send_msg(s, ("PRIVMSG "+irc_msg["user"]+" :"+irc["nick"]+" do not log - Deactivates chat log\r\n"))
	send_msg(s, ("PRIVMSG "+irc_msg["user"]+" :"+irc["nick"]+" show log - Shows complete log of the channel\r\n"))
	send_msg(s, ("PRIVMSG "+irc_msg["user"]+" :"+irc["nick"]+" show user - Shows last user in the log\r\n"))
	send_msg(s, ("PRIVMSG "+irc_msg["user"]+" :"+irc["nick"]+" show last action - Shows last action from the channel\r\n"))
	send_msg(s, ("PRIVMSG "+irc_msg["user"]+" :"+irc["nick"]+" last seen =<usernick> - Shows when and on which channel the user join the last time (No Space between = and nick!!)\r\n"))
	send_msg(s, ("PRIVMSG "+irc_msg["user"]+" :"+irc["nick"]+" show topic - Show the topic of the current channel\r\n"))
	send_msg(s, ("PRIVMSG "+irc_msg["user"]+" :"+irc["nick"]+" set topic =<newTopic> - Set a new topic for current channel (No Space between = and topic!!)\r\n"))
	send_msg(s, ("PRIVMSG "+irc_msg["user"]+" :"+irc["nick"]+" change nick =<newNick> - Change Bots nickname (No Space between = and topic!!)\r\n"))
	send_msg(s, ("PRIVMSG "+irc_msg["user"]+" :"+irc["nick"]+" got to =<#newChannel> - Bot switchs to other Channel (No Space between = and topic!!)\r\n"))
	send_msg(s, ("PRIVMSG "+irc_msg["user"]+" :"+irc["nick"]+" quit - Bot leaves IRC\r\n"))


def HandleLogging(value):
	global logging
	if value == "true":
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

#************IRC Options*********************
def setTopic(s, irc_msg):
	topic = irc_msg["message"].split("=")
	topic = topic[1].replace("= ", "")
	s.send(bytes("TOPIC %s %s\r\n" % (irc_msg["channel"], topic)))
	send_msg(s, ("PRIVMSG "+irc_msg["reciever"]+ " : channel topic changed into:"+topic+"\r\n"))
	if irc_msg["reciever"] != irc_msg["channel"]:
		send_msg(s, ("PRIVMSG "+irc_msg["channel"]+ " : "+irc_msg["user"]+" changed channel topic into:"+topic+"\r\n"))

def changeNick(s, irc_msg, irc):
	newNick = irc_msg["message"].split("=")
	newNick = newNick[1].replace("= ", "")
	if len(newNick) < 2:
		send_msg(s, ("PRIVMSG "+irc_msg["reciever"]+ " :Nickname can only be one word!\r\n"))
		pass
	else:
		irc["nick"] = newNick
		s.send(bytes("NICK %s\r\n" % irc["nick"]))	

def changeChannel(s, irc_msg):
	newChannel = irc_msg["message"].split("=")
	newChannel = newChannel[1].replace("= ", "")
	if "#" in newChannel:
		s.send(bytes("JOIN %s\r\n" % newChannel))
		send_msg(s, ("PRIVMSG "+irc_msg["reciever"]+ " :"+irc["nick"]+" is now in channel: "+newChannel+"\r\n"))
		if irc_msg["reciever"] != irc_msg["channel"]:
			send_msg(s, ("PRIVMSG "+irc_msg["channel"]+ " :"+irc["nick"]+" is now in channel: "+newChannel+"\r\n"))
	else:
		send_msg(s, ("PRIVMSG "+irc_msg["reciever"]+ " :A Channel name must begin with a '#'\r\n"))
		pass
	

#***********Command line parameters********
def parse_options():
	parser = optparse.OptionParser()

	parser.add_option(
		"-s", "--server",
		action="store", default=irc["host"], dest="host",
		help = "Set custom host/server")

	parser.add_option(
		"-c", "--channel",
		action="store", default=irc["channel"], dest="channel",
		help = "Set custom channel")

	parser.add_option(
		"-n", "--nick",
		action="store", default=irc["nick"], dest="nick",
		help = "Rename Bot")

	parser.add_option(
		"-d", "--daemon",
		action="store_true", 
		default= config.getboolean("bot", "daemon"), 
		dest="daemon",
		help = "Turn daemon mode on")

	(opts, args) = parser.parse_args()

	return opts, args

#the parsed values from the consol overwrite the default values
def SwitchValues(opts):
	irc["host"] = opts.host
	irc["channel"] = opts.channel
	irc["nick"] = opts.nick

	if opts.daemon:
		daemonize()

#******************Deamon***********

def daemonize():
	# Fork a child and end the parent (detach from parent)
        try:
            pid = os.fork()
            if pid > 0:
                sys.exit(0) # End parent
        except OSError, e:
            sys.stderr.write("First fork failed: %d (%s)\n" % (e.errno, e.strerror))
            sys.exit(-2)

        # Change some defaults so the daemon doesn't tie up dirs, etc.
        os.setsid()
        os.umask(0)

        # Fork a child and end parent (so init now owns process)
        try:
            pid = os.fork()
            if pid > 0:
                try:
                    f = file("IRCBotIB.pid", "w")
                    f.write(str(pid))
                    f.close()
                except IOError, e:
                    sys.stderr.write(repr(e))
                sys.exit(0) # End parent
        except OSError, e:
            sys.stderr.write("Second fork failed: %d (%s)\n" % (e.errno, e.strerror))
            sys.exit(-2)

        # Close STDIN, STDOUT and STDERR so we don't tie up the controlling
        # terminal
        for fd in (0, 1, 2):
            try:
                os.close(fd)
            except OSError:
                pass

def closeDaemon():
	pid = None
	try:
            f = file("IRCBotIB.pid", "r")
            pid = int(f.readline())
            f.close()
            os.unlink("IRCBotIB.pid")
        except ValueError, e:
            sys.stderr.write("Error in pid file 'IRCBotIB.pid'. Aborting\n")
            sys.exit(-1)
        except IOError, e:
            pass

        if pid:
            os.kill(pid, 15)
        else:
            sys.stderr.write("IRCBotIB not running or no PID file found\n")


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
	cursor.execute("CREATE TABLE IF NOT EXISTS CompleteChat(TimeSt TIMESTAMP, Channel TEXT, User TEXT, Message TEXT)")
	cursor.execute("CREATE TABLE IF NOT EXISTS AllUsers(TimeSt TIMESTAMP, Channel TEXT, User TEXT)")

def insert_table(cursor, irc_msg):
	cursor.execute("INSERT INTO CompleteChat VALUES (?,?,?,?)", (irc_msg["time"], irc_msg["channel"], irc_msg["user"], irc_msg["message"]))

def insert_tableUser(cursor, time, channel, user):
	cursor.execute("INSERT INTO AllUsers VALUES (?,?,?)", (time, channel, user))

def update_tableUser(cursor, time, channel, user):
	cursor.execute("UPDATE AllUsers SET TimeSt=?, Channel=? WHERE User=?", (time, channel, user))

def selectAll(s, cursor, irc_msg):
	cursor.execute("SELECT * FROM CompleteChat")
	#fetchall gives a list of tuple e.g. [(u'12:15', u'#test', u'myNick', u':Hi'), (u'12:45', u'#test'....)]
	result = cursor.fetchall()
	#if the table is not empty print the log
	if result:
		for x in result:
			timestp = x[0]
			time = datetime.datetime.fromtimestamp(timestp).strftime("[%Y-%m-%d %H:%M:%S]")
			channel = x[1]
			user = x[2]
			message = x[3]
			send_msg(s, "PRIVMSG "+irc_msg["reciever"]+ " :" +time +user+message+"\r\n")
	else:
		send_msg(s, "PRIVMSG "+irc_msg["reciever"]+ " :Sorry log is empty\r\n")

	

def selectUser(s, cursor, irc_msg):
	cursor.execute("SELECT max(TimeSt), User FROM CompleteChat")
	max_user = cursor.fetchone()[1]
	if max_user is not None:
		send_msg(s, "PRIVMSG "+ irc_msg["reciever"]+ " :Last action from user: "+max_user+"\r\n")
	else:
		send_msg(s, "PRIVMSG "+ irc_msg["reciever"]+ " :Sorry log is empty\r\n")

def selectLastAction(s, cursor, irc_msg):
	cursor.execute("SELECT max(TimeSt), User, Message FROM CompleteChat WHERE Channel = '%s'" % irc_msg["channel"])
	#fetchone gives one tuple back
	result = cursor.fetchone()
	#if the table is empty fetchone will return None
	if result[0] is not None:
		timestp = result[0]
		time = datetime.datetime.fromtimestamp(timestp).strftime("[%Y-%m-%d %H:%M:%S]")
		user = result[1]
		message = result[2]
		send_msg(s, "PRIVMSG "+ irc_msg["reciever"]+ " :" +time +user+message+"\r\n")
	else:
		send_msg(s, "PRIVMSG "+ irc_msg["reciever"]+ " :Sorry log is empty\r\n")

def addNewUser(cursor, time, channel, user):
	cursor.execute("SELECT User FROM AllUsers WHERE User= '%s'" % user)
	result = cursor.fetchone()
	#if there is a result the user is already in the database only the time and channel must be updated
	if result is not None:
		update_tableUser(cursor, time, channel, user)
		print ("User update successful")
	else:
		insert_tableUser(cursor, time, channel, user)
		print ("User insert successful")

def selectLastSeen(s, cursor, user, sender):
	cursor.execute("SELECT  TimeSt, Channel FROM AllUsers WHERE User = '%s'" % user)
	result = cursor.fetchone()
	if result is not None:
		time = datetime.datetime.fromtimestamp(result[0]).strftime("[%Y-%m-%d %H:%M:%S]")
		channel = result[1]
		send_msg(s, "PRIVMSG "+ sender+ " :" +user+" was last seen: "+time+ " in Channel: " +channel+"\r\n")
	else:
		send_msg(s, "PRIVMSG "+ sender+ " :"+user+" is not in database!\r\n")
	
	
def close_db(connection, cursor):
	cursor.close()
	connection.commit()
	connection.close()

#**************Main**************

def main():
	#if the user dos not give any command line parameters the default values will be used
	if sys.argv > 1:
		(opts, args) = parse_options()
		SwitchValues(opts)
	connection = create_db_connection()
	cursor = connect_db(connection)
	create_table(cursor)
	connect_irc(irc, connection, cursor)


	

if __name__ == "__main__":
	main()
		
