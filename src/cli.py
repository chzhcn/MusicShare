'''
Created on Mar 22, 2012

@author: chiz
'''

import ast;
import socket;
import pickle;
import time;
import sys;
import threading;
import select;

from client_info import Music_Info
from Client_Message import Client_Music_Message

#Primary Server
CS_Primary_Request_IP = '127.0.0.1'; CS_Primary_Request_Port = 12345;
#Secondary Server
CS_Backup_Request_IP = '127.0.0.1'; CS_Backup_Request_Port = 12347;

class client(object):


    def __init__(self):
        print "in init of client"
        
        self.s = None;
        self.send_socket = None;
        
        # self.username = 'c1'
        self.username = None;        
        self.app_start_time = time.time()
        self.logical_clk_time = 0;
        
        self.music_info = Music_Info()
        self.music_table = {}
        self.session_table = {}
        
        self.music_table_lock = threading.Lock()
        self.session_table_lock = threading.Lock()
        self.logical_clk_lock = threading.Lock()
        self.music_info_lock = threading.Lock()
        
#        self.listening_sock = None;
#        self.listening_addr = None;
        
        self.connect_server()
        self.open_listener()
        
        self.thread_server_receive = threading.Thread(target=self.receive_server)
        self.thread_server_receive.start() 
        
        self.thread_client_receive = threading.Thread(target=self.receive_client)
        self.thread_client_receive.start()
        
        self.thread_client_HB = threading.Thread(target=self.period_CCHB)
        self.thread_client_HB.start()
        
    def connect_server(self):
        
        # re_initialize socket state, so that this function can be reused.
        self.connection_sate = False;
        
        if self.s is socket :
            self.s.shutdown(socket.SHUT_RDWR)
            self.s.close()
        
        # Try Primary Server
        print "Request Primary Server in next 30s, please wait"
        past = time.time();
        t = 0
        while t < 30:
            try: 
                    self.s = socket.create_connection((CS_Primary_Request_IP, CS_Primary_Request_Port), 10)
                    self.connection_state = True
                    print "Connected to Primary Server!!!"
                    break
            except: 
                    self.connection_state = False
                    
            t = time.time() - past

        # Try Secondary server
        if self.connection_state == False:
            print "Primary Server fails,.............." 
            print "Request Secondary Server in next 30s,please wait"
            past = time.time();
            t = 0
            while t < 30:
                try: 
                        self.s = socket.create_connection((CS_Backup_Request_IP, CS_Backup_Request_Port), 10)
                        self.connection_state = True
                        print "Connected to Secondary Server!!!"
                        break
                except: 
                        self.connection_state = False
    
                t = time.time() - past
                
        self.s.settimeout(30)

        # Give user feedback and close the program   
        if self.connection_state == False:
            print "Secondary Server fails,,.............."
            time.sleep(1)
            print "We are sorry for the inconvenience,the program will close in next 10 seconds"
            past = time.time()
            t = 0
            while t < 10:
                t = time.time() - past
            sys.exit()   
            
            
    def receive_server(self):
        while True:
            if not self.connection_state:
                continue
            
            infds_c, outfds_c, errfds_c = select.select([self.s, ], [], [])
            if len(infds_c) == 0:
                continue
            
            try:
                data = self.s.recv(1024)
            except:
                print "server is down in receiving first server discovery reply"
                   
                # self.thread_stop = True
                self.connect_server()
                self.send_SD()
                
            if len(data) == 0:
                continue
            
            #print "\nreceived data : %s \r\n " % data
            xyz = ast.literal_eval(data)# change it to tuple
            
            print "\nreceived message:%s \r" % str(xyz[1])
            

            if xyz[0] == 'UT':
                # self.UT = xyz[1]
                    
                print "in receiving UT"                            
                self.music_table_lock.acquire()    
                self.session_table_lock.acquire()                                      
                # contact other clients except myself
                for ut_item in xyz[1] :
                    
        
                    key = (ut_item[0], int(ut_item[1]))
                    
                    self.session_table[key] = {'username' : ut_item[2], 'app_start_time' : None, 'logical_clk_time' : None, 'last_recv_time' : None}
                    # self.session_table[key] = Session_Info(ut_item[2])

                    if key == self.listening_addr :
                        print "find self"
                        self.music_table[key] = self.music_info
                    # else :    
                    #    self.music_table[key] = Music_Info(ut_item[2])
                
                self.music_table_lock.release()
                self.session_table_lock.release()                           
                print self.music_table
                
                                            
                print "first time multicast CHB - this line shouldn't be seen twice"
                
                self.multicast_CCD()
                
    def receive_client(self):
        while True :
            peer_socket, peer_address = self.listening_sock.accept()
            peer_socket.settimeout(10)
        
            
            data = peer_socket.recv(8192)
            
            peer_socket.close()
            message = pickle.loads(data);
            
            print 'receive_client : new message'
            # self.dump_table()
            
            self.session_table_lock.acquire()       
            
            # check logical_clk_time
            if message.sender_listening_addr in self.session_table.keys() and message.logical_clk_time <= self.session_table[message.sender_listening_addr]['logical_clk_time'] :
                continue
            
            self.session_table[message.sender_listening_addr] = {}
            self.session_table[message.sender_listening_addr]['logical_clk_time'] = message.logical_clk_time
            
            # record last_recv_time
            self.session_table[message.sender_listening_addr]['last_recv_time'] = time.time()
            self.session_table[message.sender_listening_addr]['username'] = message.username
            self.session_table[message.sender_listening_addr]['app_start_time'] = message.app_start_time
            
            self.session_table_lock.release()       
                

#            target_music_info = self.music_table[peer_address];
#            message_music_info = message[1];          
#            
#            print message    
#              
#            # check delayed message        
#            if target_music_info.logical_clk_time >= message_music_info.logical_clk_time :
#                continue
#            
#            message_music_info.last_recv_time = time.time()
         
            if message.type == 'CCHB' or message.type == 'CCD' :
                
                self.music_table_lock.acquire()
                
                self.music_table[message.sender_listening_addr] = message.music_info
                
                self.music_table_lock.release()       
                
                print "D/HB received"
                print message.type, message.sender_listening_addr
                # self.dump_table()
                
                if message.type == 'CCD'  :
                    # send hb message back right asway
                    print 'sending back CCHB'
                    self.send_C_Music(message.sender_listening_addr, 'CCHB') 
                
            elif message.type == 'LIKE' :
                pass
            
            
        
    def dump_table(self):
        print 'dump tables'
        print self.music_table
        print self.session_table
 
    def send_obj(self, addr, obj):  
        try :
            self.send_socket = socket.create_connection(addr, 10)    
            data = pickle.dumps(obj)
            self.send_socket.send(data); 
        except Exception as inst:
            print type(inst)
            print inst
            print "send_obj() exception. addr: %s obj: %s" % (addr, str(obj))
            raise

            

    def send_C_Music(self, address, m_type):
        self.logical_clk_lock.acquire()
        self.logical_clk_time += 1
        try :
            self.music_info_lock.acquire()
            self.send_obj(address, Client_Music_Message(m_type, self.listening_addr, self.username, self.app_start_time, self.logical_clk_time, self.music_info))
        except Exception as inst:
            print type(inst)
            print inst
            print "send_C_Music() exception addr %s obj: %s" % (address, self.music_info)
        finally:
            self.logical_clk_lock.release()
            self.music_info_lock.release()
            
    

                           
    def multicast_C_Music(self, m_type):
        print "multicast_C"
        self.session_table_lock.acquire()
        for k in self.session_table.keys() :
            # print (k, v)
            if k != self.listening_addr :
                self.send_C_Music(k, m_type)
            else :
                print "comparison is true"   
        self.session_table_lock.release() 
                
                
    def multicast_CCD(self):
        self.multicast_C_Music('CCD')
        
    def multicast_CCHB(self):
        self.multicast_C_Music('CCHB') 
        
    def period_CCHB(self):
        while True :
            time.sleep(10)
            self.multicast_CCHB()

    def open_listener(self):
            self.listening_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.listening_addr = (socket.gethostbyname(socket.gethostname()), 0)
            self.listening_sock.bind(self.listening_addr)
            self.listening_addr = self.listening_sock.getsockname()
            self.listening_sock.listen(5)           
                    
                  
    def send_SD(self):     
        
        addr = self.listening_addr;
        message = ('CHB', addr, self.username)
        try :
            self.send_server_String(str(message))
        except :
            print "server is down in sending first server discovery"
            
            self.s.shutdown(socket.SHUT_RDWR)
            self.s.close()
            
            self.connect_server()
            self.send_SD()
            
    # FIXME : assuming long-live connections to servers    
    def send_server_String(self, message):
        try :
            self.s.sendall(message)
        except Exception as inst :
            print type(inst)
            print inst
            raise
        
    def run(self):
        
        while (True) :
            command_str = raw_input("> ");
            if command_str == '' : 
                continue
            command = command_str.split(' ');
                
            if command[0] == 'user' :
                self.username = self.music_info.username = command[1]
                
                self.send_SD()
                
            elif command[0] == 'SD' :
                self.send_SD()
            
            elif command[0] == 'listen' :
                self.open_listener();
                
            elif command[0] == 'q' :
                sys.exit()
                
            else :
                print "no match"





def main() :
    c = client();
    c.run();

if __name__ == '__main__':
    main()

