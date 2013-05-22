all: IRCBotIB.1

A2X?=a2x

IRCBotIB.1: asciidoc.conf IRCBotIB.man
	${A2X} -f manpage --verbose --asciidoc-opts="-f asciidoc.conf" IRCBotIB.man
clean:
	rm -f IRCBotIB.xml IRCBotIB.1 IRCBotIB.html
