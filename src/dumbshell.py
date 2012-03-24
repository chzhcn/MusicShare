'''
Created on Mar 22, 2012

@author: chiz
'''

import socket;
import pickle;

tel = {'jack' : 4098, 'sape' : 4139, 'guido' : 4127};

class DumbShell(object):
    '''
    classdocs
    '''


    def __init__(self):
        '''
        Constructor
        '''
        print "in init of dumb shell"

        
    def run(self):
        
        while (True) :
#            print ">",
            command_str = raw_input("> ");
#            print command_str;
            
            command = command_str.split(' ');
            
            print command;

            if command[0] == 'p' :
                print "p is input"
                
            elif command[0] == 'pp':
                print "pp is input"
                
            elif command[0] == 'create':
            
                host = command[1];
                port = command[2];
            
 #               self.send_host = host;
 #               self.sned_port = port;
        
                self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM);
        
                self.s.bind((host, int(port)));
        
                self.s.listen(5);
                
            elif command[0] == 'recv' :
                
                client, address = self.s.accept();
                
                data = client.recv(1024);
                data = pickle.loads(data);
                print data;
                client.close();
                print address;
#                self.recv_host = address;
                
            elif command[0] == 'send' :
            
                data = command[1];
                
                send_host = command[2];
                send_port = command[3];
                
                self.ss = socket.socket(socket.AF_INET, socket.SOCK_STREAM);
                
 #               self.ss.bind(('localhost', 12222));
                
                self.ss.connect((send_host, int(send_port)));
                
                
                data = pickle.dumps(tel);
                self.ss.send(data);
                
                