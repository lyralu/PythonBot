#!/usr/bin/env python3

import os, sys, socket, string, time, datetime, ConfigParser, optparse
from sqlite3 import dbapi2 as sqlite
from time import sleep
from sys import exit

#get the connection info from the config File
config = ConfigParser.ConfigParser()
config.read("config.ini")

irc = { "host": config.get("connect", "host"), "port": config.get("connect", "port"), "nick": config.get("connect", "nick"), "server": config.get("connect", "server"), "channel": config.get("connect", "channel")}
irc_msg = { "time": " ", "channel": " ", "user": " ", "message": " "}
logging = False


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
	s.send(bytes('NICK %s\r\n' % irc["nick"]))
	s.send(bytes('USER %s %s pyBot : %s\r\n' % (irc["nick"], irc["host"], irc["nick"])))
	s.send(bytes('JOIN %s\r\n' % (irc["channel"])))

def close_irc(s, connection, cursor):
	close_db(connection, cursor)
	s.close()
	pf = os.getpid()
	os.kill(pf, SIGTERM)
	sys.exit()

#*********MessageHandeling*********

def handle_message(s, data, connection, cursor):
	full_msg = string.split(data)
	irc_msg["message"] = " ".join(full_msg[3:])
	irc_msg["user"] = full_msg[0].split("!")
	irc_msg["user"] = irc_msg["user"][0].replace(":", "")
	irc_msg["time"] = time.time()
	irc_msg["channel"] = irc["channel"]
 	
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
	#handling messages	
	if full_msg[1] == "PRIVMSG" and full_msg[2] != irc["nick"] and irc["nick"] not in irc_msg["message"]:
		print("Logging: %s" % logging)	
		if logging:
			logDatabase(irc_msg, cursor)
		if "!ping" in irc_msg["message"]:
			msg = ("PRIVMSG "+irc["channel"]+ " :pong!\r\n")
			send_msg(s, msg)
			
	#commands to the bot	
	if (full_msg[1] == "PRIVMSG" and full_msg[2] != irc["nick"]) or (irc["nick"] in irc_msg["message"]):
		if ("Help") in irc_msg["message"]:
			commands(s, irc_msg, irc)
		if "do log" in irc_msg["message"]:
			HandleLogging("true")
			print("Logging: %s" % logging)	
			msg = ("PRIVMSG "+irc["channel"]+ " :Chat log activated\r\n")
			send_msg(s, msg) 
		if "do not log" in irc_msg["message"]:
			HandleLogging("false")
			msg = ("PRIVMSG "+irc["channel"]+ " :Chat log deactivated\r\n")
			send_msg(s, msg) 
		if ("show log") in irc_msg["message"]:
			selectAll(s, cursor, irc_msg["channel"])
		if ("show user") in irc_msg["message"]:
			selectUser(s, cursor, irc_msg)
		if("show last action") in irc_msg["message"]:
			selectLastAction(s, cursor, irc_msg["channel"])
		if("last seen = ") in irc_msg["message"]:
			search_user = irc_msg["message"].split("=")
			search_user = search_user[1].replace("=", "")
			selectLastSeen(s, cursor, search_user, irc_msg["user"])
		if ("quit") in irc_msg["message"]:
			send_msg(s, ("PRIVMSG "+irc["channel"]+ " :Bye!\r\n"))
			close_irc(s, connection, cursor)
				

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
		action="store_true", default=False, dest="daemon",
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

def selectAll(s, cursor, channel):
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
			send_msg(s, "PRIVMSG "+ channel+ " :" +time +user+message+"\r\n")
	else:
		send_msg(s, "PRIVMSG "+ channel+ " :Sorry log is empty\r\n")

	

def selectUser(s, cursor, irc_msg):
	cursor.execute("SELECT max(TimeSt), User FROM CompleteChat")
	max_user = cursor.fetchone()[1]
	if max_user is not None:
		send_msg(s, "PRIVMSG "+ irc_msg["channel"]+ " :Last action from user: "+max_user+"\r\n")
	else:
		send_msg(s, "PRIVMSG "+ irc_msg["channel"]+ " :Sorry log is empty\r\n")

def selectLastAction(s, cursor, channel):
	cursor.execute("SELECT max(TimeSt), User, Message FROM CompleteChat WHERE Channel = '%s'" % channel)
	#fetchone gives one tuple back
	result = cursor.fetchone()
	#if the table is empty fetchone will return None
	if result[0] is not None:
		timestp = result[0]
		time = datetime.datetime.fromtimestamp(timestp).strftime("[%Y-%m-%d %H:%M:%S]")
		user = result[1]
		message = result[2]
		send_msg(s, "PRIVMSG "+ channel+ " :" +time +user+message+"\r\n")
	else:
		send_msg(s, "PRIVMSG "+ channel+ " :Sorry log is empty\r\n")

def addNewUser(cursor, time, channel, user):
	cursor.execute("SELECT User FROM AllUsers WHERE User= '%s'" % user)
	result = cursor.fetchone()
	#if there is a result the user is already in the database only the time and channel must be updated
	if result is not None:
		update_tableUser(cursor, time, channel, user)
		print ("User update successful")
		cursor.execute("SELECT * FROM AllUsers")
		for row in cursor:
			print row
	else:
		insert_tableUser(cursor, time, channel, user)
		print ("User insert successful")
		cursor.execute("SELECT * FROM AllUsers")
		for row in cursor:
			print row

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
		
