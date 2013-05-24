#IRCBotIB

As a student project i had the task to do an IRC Bot on a unix system. I was super new in that field, but now i proudly present my Bot written in Python.

####The Bot is able to:
* connect to a server and a channel
* log the channel and every user, ever joined the channel while the bot was online, in a SQLite database
* logging can be switched on and off
* From the DB the Bot gives you:
    * the complete log of the channel
    * the last entry on the log
    * the who did the last action in the log
    * when and where a specific user last joined
* Change and show the current topic of the channel
* Change his nick be request
* run a daemon
* get and send private messages
* Read connection values and other configuration stuff from a config-file
* print RSS Feeds

This is the first time i wrote something in python, so don't be mad if it's not really pythonic or not a clean code. 

####What I used:
* python: the python interpreter must be installed
* sqlite3: install if necessary
* feedparser: a Python lib to parse the RSS Feeds. Can be installed on linux with: "sudo easy_install feedparser"

Have a look at the man to get more information.
