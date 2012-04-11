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
        self.s = None;
        self.send_socket = None;
        
        self.username = None;        
        self.app_start_time = time.time()
        self.logical_clk_time = 0;

        self.music_counter = [0, ];
        
        self.music_info = Music_Info(self.music_counter)
        self.music_table = {}
        self.session_table = {}
        
        self.music_table_lock = threading.Lock()
        self.session_table_lock = threading.Lock()
        self.logical_clk_lock = threading.Lock()
        self.music_info_lock = threading.Lock()

        self.username_init1=False
        self.username_init2=False
        
        self.connect_server()
        self.open_listener()
        
        # self.thread_server_receive = threading.Thread(target=self.receive_server)
        # self.thread_server_receive.start() 
        
        self.thread_client_receive = threading.Thread(target=self.receive_client)
        self.thread_client_receive.start()
        
        self.thread_client_HB = threading.Thread(target=self.period_CCHB)
        self.thread_client_HB.start()

        # self.thread_server_HB = threading.Thread(target=self.send_HB)
        # self.thread_server_HB.start()
        
#    def connect_server(self):
#        
#        # re_initialize socket state, so that this function can be reused.
#        self.connection_sate = False;
#        
#        if self.s is socket :
#            self.s.shutdown(socket.SHUT_RDWR)
#            self.s.close()
#        
#        # Try Primary Server
#        print "Request Primary Server in next 30s, please wait"
#        past = time.time();
#        t = 0
#        while t < 30:
#            try: 
#                    self.s = socket.create_connection((CS_Primary_Request_IP, CS_Primary_Request_Port), 10)
#                    self.connection_state = True
#                    print "Connected to Primary Server!!!"
#                    break
#            except: 
#                    self.connection_state = False
#                    
#            t = time.time() - past
#
#        # Try Secondary server
#        if self.connection_state == False:
#            print "Primary Server fails,.............." 
#            print "Request Secondary Server in next 30s,please wait"
#            past = time.time();
#            t = 0
#            while t < 30:
#                try: 
#                        self.s = socket.create_connection((CS_Backup_Request_IP, CS_Backup_Request_Port), 10)
#                        self.connection_state = True
#                        print "Connected to Secondary Server!!!"
#                        break
#                except: 
#                        self.connection_state = False
#    
#                t = time.time() - past
#                
#        self.s.settimeout(30)
#
#        # Give user feedback and close the program   
#        if self.connection_state == False:
#            print "Secondary Server fails,,.............."
#            time.sleep(1)
#            print "We are sorry for the inconvenience,the program will close in next 10 seconds"
#            past = time.time()
#            t = 0
#            while t < 10:
#                t = time.time() - past
#            sys.exit()   

    def connect_server(self):
        # Try Primary Server
        print "Request Primary Server in next 5s, please wait"
        past=time.time();
        self.t=0
        while self.t<5:
            try: 
                self.s = socket.create_connection((CS_Primary_Request_IP, CS_Primary_Request_Port),10)
                self.connection_state=True
                self.connection_server='Primary'
                self.prevous_server=self.connection_server
                self.judge=True
                
                print "Connected to Primary Server!!!"
                break
            except: 
                self.connection_state=False
                self.connection_pserver_fail=True
                        
                #self.prevous_server=''
                        
            self.t=time.time()-past

        # Try Secondary server
        if self.connection_state==False:
            print "Primary Server fails,.............." 
            print "Request Secondary Server in next 10s,please wait"
            past=time.time();
            self.t=0
            while self.t<10:
                try: 
                        self.s = socket.create_connection((CS_Backup_Request_IP, CS_Backup_Request_Port),10)
                        self.connection_state=True
                        self.connection_server='Secondary'
                        self.connection_Sserver=True
                        print "Connected to Secondary Server!!!"
                        self.judge=True
                        self.connection_state=True
                        break
                except: 
                        self.connection_state=False
    
                self.t=time.time()-past

        # Give user feedback and close the program   
        if self.connection_state==False:
            print "Secondary Server fails,,.............."
            time.sleep(1)
            print "We are sorry for that, you cannot update your userlist currently"
            past=time.time()
            self.t=0
            while self.t<10:
                self.t=time.time()-past
            sys.exit()

    def init_username(self):
        addr=self.listening_addr;
                
        message=('CHB', addr[0], addr[1], self.username)
        try :
            self.s.sendall(str(message))
        except :
            print "send to server error"
            self.init_username_error()
            
        infds_c,outfds_c,errfds_c = select.select([self.s,],[],[])
        if len(infds_c)!= 0:    
            try:
                data=self.s.recv(8192)
            except:
                print "receive from server error"
                self.init_username_error()
                    
        if len(data) != 0:
            xyz=ast.literal_eval(data)# change it to tuple
            if xyz[0] == 'UT':
                self.music_table_lock.acquire()    
                self.session_table_lock.acquire()                                      
                 # contact other clients except myself
                for ut_item in xyz[1] :
                    key = (ut_item[0], int(ut_item[1]))
                    
                    self.session_table[key] = {'username' : ut_item[2], 'app_start_time' : None, 'logical_clk_time' : None, 'last_recv_time' : None}
                    if key == self.listening_addr :
                        self.music_table[key] = self.music_info
                
                self.music_table_lock.release()
                self.session_table_lock.release()                           
                                            
                print "first time multicast discovery message to clients - this line shouldn't be seen twice"
                
                self.multicast_CCD()

            if xyz[0]=='UT':
                self.UT=xyz[1]
                print "First Received message: %s \r\n" % str(xyz[1])
            else:
                print "Error First Received message:%s \r\n" %str(xyz[1])  
                
                self.s.shutdown(socket.SHUT_RDWR)    
                self.s.close()
                self.username_init2=True

    def init_username_error(self) :
        print "server is down in sending first server discovery"
            
        self.s.shutdown(socket.SHUT_RDWR)
        self.s.close()
            
        self.connect_server()
        self.init_username()

            
    # def receive_server(self):
    #     while True:
    #         if not self.connection_state:
    #             continue
            
    #         infds_c, outfds_c, errfds_c = select.select([self.s, ], [], [])
    #         if len(infds_c) == 0:
    #             continue
            
    #         try:
    #             data = self.s.recv(1024)
    #         except:
    #             # print "server is down in receiving first server discovery reply"
                   
    #             # self.thread_stop = True
    #             self.connect_server()
    #             self.send_SD()
                
    #         if len(data) == 0:
    #             continue
            
    #         #print "\nreceived data : %s \r\n " % data
    #         xyz = ast.literal_eval(data)# change it to tuple
            
    #         print "\nreceived U.T. from server:%s \r" % str(xyz[1])
            

    #         if xyz[0] == 'UT':
                        
    #             self.music_table_lock.acquire()    
    #             self.session_table_lock.acquire()                                      
    #             # contact other clients except myself
    #             for ut_item in xyz[1] :
                    
        
    #                 key = (ut_item[0], int(ut_item[1]))
                    
    #                 self.session_table[key] = {'username' : ut_item[2], 'app_start_time' : None, 'logical_clk_time' : None, 'last_recv_time' : None}
    #                 # self.session_table[key] = Session_Info(ut_item[2])

    #                 if key == self.listening_addr :
    #                     # print "find self"
    #                     self.music_table[key] = self.music_info
    #                 # else :    
    #                 #    self.music_table[key] = Music_Info(ut_item[2])
                
    #             self.music_table_lock.release()
    #             self.session_table_lock.release()                           
    #             # print self.music_table
                
                                            
    #             print "first time multicast discovery message to clients - this line shouldn't be seen twice"
                
    #             self.multicast_CCD()
                
    def receive_client(self):
        while True :
            peer_socket, peer_address = self.listening_sock.accept()
            peer_socket.settimeout(10)
                    
            data = peer_socket.recv(8192)
            
            peer_socket.close()
            message = pickle.loads(data);
            
            print 'receive new message of type %s, from client %s' % (message.type, message.sender_listening_addr) 
            # self.dump_table()
            
            self.session_table_lock.acquire()   
            
            session_table_entry = {};       
            
            # check logical_clk_time
            if message.sender_listening_addr in self.session_table.keys() and message.logical_clk_time <= self.session_table[message.sender_listening_addr]['logical_clk_time'] :
                self.session_table_lock.release()
                continue
                    
            session_table_entry['logical_clk_time'] = message.logical_clk_time            
            # record last_recv_time
            session_table_entry['last_recv_time'] = time.time()
            session_table_entry['username'] = message.username
            session_table_entry['app_start_time'] = message.app_start_time
            
            self.session_table[message.sender_listening_addr] = session_table_entry
            
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
                
                print "client discovery | heartbeat message received"
                print message.type, message.sender_listening_addr
                self.dump_table()
                
                if message.type == 'CCD'  :
                    # send hb message back right asway
                    print 'message received is discovery; sending back a client heartbeat message as reply'
                    self.send_C_Music(message.sender_listening_addr, 'CCHB') 
                
            elif message.type == 'LIKE' :
                pass
            
            
        
    def dump_table(self):
        print 'dump tables2'
        # for mi in self.music_table.values() :
        #     print mi.song_dict
        print self.music_table
        # print self.session_table
 
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
        print "multicasting music info to clients"
        self.session_table_lock.acquire()
        for k in self.session_table.keys() :
            # print (k, v)
            if k != self.listening_addr :
                self.send_C_Music(k, m_type)
            #else :
            #    print "comparison is true"   
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
                    
    # def send_hb(self):
    #     #print ('Sending Heartbeat to IP %s , port %d\n') % (CS_Primary_Request_IP, CS_Primary_Request_Port)       
    #         while True: 
    #           if self.connection_state and self.connection_server=='Primary':
    #             if self.username_init2 or self.connection_switch_to_p:            
    #                      if self.fist_hearthb:     
    #                         time.sleep(1)
    #                         self.fist_hearthb=False

    #                      if not self.connection_switch_to_p:
    #                         try:
    #                             self.hb = socket.create_connection((CS_Primary_Request_IP, CS_Primary_Request_Port))
    #                             self.hb_enable=True
    #                         except:
    #                             if not self.alter:
    #                                 print "\n................Primary Server May be down........................"
    #                                 self.alter=True
    #                             else:
    #                                 self.connectserver()
    #                             self.hb_enable=False
                                 
    #                             time.sleep(BEAT_PERIOD)
 
    #           elif self.connection_state and self.connection_server=='Secondary': 
    #                     if self.connection_lost or self.username_init2: 
    #                         if self.fist_hearthb:     
    #                             time.sleep(1)
    #                             self.fist_hearthb=False

    #                         try:
    #                             self.hb = socket.create_connection((CS_Backup_Request_IP, CS_Backup_Request_Port))
    #                             #print "Oh yeah you are on the backup"
    #                             self.hb_enable=True
    #                         except:
    #                             print "Secondary Server May be down"
    #                             self.hb_enable=False
                                
    #           if self.hb_enable: 
    #                          if os.path.isfile('CS_HB_Sentout.log.txt'):
    #                             f=file('CS_HB_Sentout.log','a')
    #                          else:
    #                             f=file('CS_HB_Sentout.log','w')    
    #                          try:
    #                             message=('PyHB',self.username)
    #                             self.hb.send(str(message)) 
    #                          except:
    #                             print "HB cannot send to server" 
    #                          print "\nHeartbeat Message is sent to %s %s" % (str(self.connection_server), str(time.ctime()) ) 
    #                          #self.hb.shutdown(socket.SHUT_RDWR)   
    #                          self.hb.close() 
    #                          self.received_hb[self.connection_server]=time.time()
    #                          log= "Heartbeat is sent out, Time: %s \n" % time.ctime()
    #                          f.write(log)
    #                          f.close()
    #                          time.sleep(BEAT_PERIOD)              
                            
                                               
      
                             
                             
 
    #           """""   // send_hb timer
    #          if self.connection_server=='Primary':
    #                     if not self.connection_switch:
    #                         try:
    #                             self.hb = socket.create_connection((CS_Primary_Request_IP, CS_Primary_Request_Port))
    #                         except:
    #                             print "Primary Server May be down"
    #                             self.connectserver()
    #                     else:
    #                         pass      
    #          elif self.connection_server=='Secondary':
    #              try:
    #                 self.hb = socket.create_connection((CS_Backup_Request_IP, CS_Backup_Request_Port))
    #              except:
    #                 print "Secondary Server May be down"
    #                 self.connectserver()
    #          else:
    #             print "error"
                
    #          """                       
                  
    # def send_SD(self):     
        
    #     addr = self.listening_addr;
    #     message = ('CHB', addr, self.username)
    #     try :
    #         self.send_server_String(str(message))
    #     except :
    #         print "server is down in sending first server discovery"
            
    #         self.s.shutdown(socket.SHUT_RDWR)
    #         self.s.close()
            
    #         self.connect_server()
    #         self.send_SD()
            
    # FIXME : assuming long-live connections to servers    
    # def send_server_String(self, message):
    #     try :
    #         self.s.sendall(message)
    #     except Exception as inst :
    #         print type(inst)
    #         print inst
    #         raise
        
    def run(self):
        
        while (True) :
            command_str = raw_input("> ");
            if command_str == '' : 
                continue
            command = command_str.split(' ');
                
            if command[0] == 'user' :
                self.username = self.music_info.username = command[1]
                
                self.init_username()
                # self.send_SD()
                
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

