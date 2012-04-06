'''
Created on Mar 25, 2012

@author: Yong
'''

import socket, time
import threading
import sys
import select
import os
import ast
import pickle

from Music_Info import Music_Info
#Primary Server
CS_Primary_Request_IP = '127.0.0.1'; CS_Primary_Request_Port = 12345;
#Secondary Server
CS_Backup_Request_IP = '127.0.0.1'; CS_Backup_Request_Port = 12347;
#Local Server
Self_Server_Ip = '127.0.0.1'; Self_Server_Port = 50000 ;

BEAT_PERIOD = 5;BUFFER_SIZE = 1024;MESSAGE = 'PyHB'

class Client(threading.Thread):
    def __init__(self, threadname):
        threading.Thread.__init__(self, name=threadname)

        self.thread_stop = False
        self.connection_state = False
        self.connectserver()
        self.username = None
        self.log_open = False
        self.UT = []
        self.s
        # self.send_socket
        
        self.music_table = {}
       
        self.listening_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listening_addr = (socket.gethostbyname(socket.gethostname()), 0)
        self.listening_sock.bind(self.listening_addr)
        self.listening_addr = self.listening_sock.getsockname()
        print "in _init_"
        print self.listening_addr
        # FIXME: sending listening_addr to server    
        

        self.send_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM);
        
               
    def connectserver(self):
        # Try Primary Server
        print "Request Primary Server in next 30s, please wait"
        past = time.time();
        self.t = 0
        while self.t < 30:
            try: 
                    self.s = socket.create_connection((CS_Primary_Request_IP, CS_Primary_Request_Port), 10)
                    self.connection_state = True
                    print "Connected to Primary Server!!!"
                    break
            except: 
                    self.connection_state = False
                    
            self.t = time.time() - past

        # Try Secondary server
        if self.connection_state == False:
            print "Primary Server fails,.............." 
            print "Request Secondary Server in next 30s,please wait"
            past = time.time();
            self.t = 0
            while self.t < 30:
                try: 
                        self.s = socket.create_connection((CS_Backup_Request_IP, CS_Backup_Request_Port), 10)
                        self.connection_state = True
                        print "Connected to Secondary Server!!!"
                        break
                except: 
                        self.connection_state = False
    
                self.t = time.time() - past

        # Give user feedback and close the program   
        if self.connection_state == False:
            print "Secondary Server fails,,.............."
            time.sleep(1)
            print "We are sorry for the inconvenience,the program will close in next 10 seconds"
            past = time.time()
            self.t = 0
            while self.t < 10:
                self.t = time.time() - past
            sys.exit()
        
    def run(self):
        #print ('Sending Heartbeat to IP %s , port %d\n') % (CS_Primary_Request_IP, CS_Primary_Request_Port)    
        while (not self.thread_stop) and (self.connection_state):
            if os.path.isfile('CS_HB_Sentout.log.txt'):
                f = file('CS_HB_Sentout.log', 'a')
            else:
                f = file('CS_HB_Sentout.log', 'w')
                
            try:
                message = ('PyHB',)
                self.s.send(str(message))
                #self.s.send(MESSAGE)
            except:
                print "HB cannot send to server" 
            log = "Heartbeat is sent out, Time: %s \n" % time.ctime()
            f.write(log)
            f.close()
            time.sleep(BEAT_PERIOD)
                       
    def stop(self):
        self.thread_stop = True
        self.s.shutdown(socket.SHUT_RDWR)
        self.s.close()
        print "the connection is closed by user"
        self.connection_state = False
        self.connectserver()

    def send(self):
        while True:
            if self.connection_state == False:
                ip = socket.gethostbyname(socket.gethostname())
                print "No data is sent,please open the bootstrap server firstly"
                print "Local IP :%s >:" % ip ,
            else:
                if not self.username:
                    print "username >", ;self.username = raw_input()           
                    if not self.username:
                        print "there is no username, please input again"
                    else:
                        # addr = self.s.getsockname()
                        addr = self.listening_addr;
                        message = ('CHB', addr, self.username)
                        self.s.sendall(str(message))
                        # FIXME: sending listening_addr to server
                        self.music_info = Music_Info(self.username)
                        # FIXME: parse music song list
                else: 
                    print "Connection Socket : %s >:" % str(self.s.getsockname()), ;
                    data = raw_input()
                    if not data:
                        print "there is no data,please input data";
                    elif data == 'stop':
                        self.stop()
                    elif data == 'terminate':
                        msg = ('terminate',)
                        self.connection_state = False
                        self.s.sendall(str(msg))
                        self.s.close()
                        sys.exit()
                    else: 
                        temp = list(data)
                        msg = ('Debug', temp)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          
                        self.s.sendall(str(msg))
            
    def receive(self):
        while True:
            if self.connection_state:
                infds_c, outfds_c, errfds_c = select.select([self.s, ], [], [])
                if len(infds_c) != 0:
                    try:
                        data = self.s.recv(1024)
                    except:
                        print "socket closed"   
                        self.thread_stop = True
                        self.s.shutdown(socket.SHUT_RDWR)
                        self.s.close()
                        print "the connection is closed by user"
                        self.connection_state = False
                        self.connectserver()
                        
                    if len(data) != 0:
                        #print "\nreceived data : %s \r\n " % data
                        xyz = ast.literal_eval(data)# change it to tuple
                        if xyz[0] == 'UT':
                            self.UT = xyz[1]
                            print "\nreceived message:%s \r" % str(xyz[1])

                            print "in receiving UT"                            
                                                        
                            # contact other clients except myself
                            for ut_item in xyz[1] :
                                # FIXME: assume (ut_item[0], ut_item[1]) is the listening address
                                # add to own music_table

                                key = (ut_item[0], int(ut_item[1]))
                                if key == self.listening_addr :
                                    print "comparison is true"
                                    self.music_table[key] = self.music_info
                                else :    
                                    self.music_table[key] = Music_Info(ut_item[2])
                                                       
                            print self.music_table
                            
                                                        
                            print "first time multicast CHB - this line shouldn't be seen twice"
                            
                            self.multicast_CHB()

                            
                        else:
                            print "\nreceived message:%s \r" % str(xyz[1])



                            

            
                                

                            
                
def main():
    client = Client('CS_HB_Thread')
    #client.start()

    thread_send = threading.Thread(target=client.send)
    thread_send.start()  
    
    thread_receive = threading.Thread(target=client.receive)
    thread_receive.start() 
    
           
if __name__ == '__main__':
    main()
