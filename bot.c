#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
#include <unistd.h>

//#include "libircclient.h"

#define TRUE 1
#define FALSE 0


struct globalArguments_t
{
	char *host; // console Argument: -h
	char *port; // console Argument: -p
	char *channel; // console Argument: -c
	char *nick; //console Argument: -n
} globalArguments;

void defaultGlobalArguments()
{
	globalArguments.host = NULL;
	globalArguments.port = NULL;
	globalArguments.channel = NULL;
	globalArguments.nick = NULL;
}

// In case the user don't want the default globalArguments the var will be read in the console
void SetArguments(int argc, char * argv[])
{
	int opt = 0;
	char *optString = "h:p:c:n:";

	//getopt = Funktion to read Paramter with var, bsp. -n botName	
	while ((opt = getopt(argc, argv, optString)) >= 0)
	{
		switch(opt)
		{
			case 'h':
			globalArguments.host = optarg;
			break;

			case 'p':
			globalArguments.port = optarg;
			break;

			case 'c':
			globalArguments.channel = optarg;
			break;

			case 'n':
			globalArguments.nick = optarg;
			break;
		}	
	}
}

//Displays globalArguments in the console
void ShowArguments()
{
	printf("Host: %s\n", globalArguments.host);
	printf("Port: %s\n", globalArguments.port);
	printf("Channel: %s\n", globalArguments.channel);
	printf("Nick: %s\n", globalArguments.nick);
}

int main (int argc, char * argv[]) 
{
	defaultGlobalArguments();
	SetArguments(argc, argv);
	ShowArguments();

	return 0;
}
