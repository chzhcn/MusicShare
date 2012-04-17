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
from Client_Message import Client_Like_Message

#Primary Server
CS_Primary_Request_IP = '127.0.0.1'; CS_Primary_Request_Port = 12345;
#Secondary Server
CS_Backup_Request_IP = '127.0.0.1'; CS_Backup_Request_Port = 12347;
#HeartBeat Time
BEAT_PERIOD=15;CHECK_TIMEOUT=30

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
        
        # self.username_init1=False
        # self.username_init2=False
        self.detectlost_lock = threading.Lock()
        self.connection_server=''
        self.connection_state=False
        self.normal_shutdown=False
        self.logical_time=0
        self.poll_event=threading.Event()
        self.hb_event=threading.Event()
        self.received_hb={}
        
        self.connect_server()
        self.open_listener()
        
        

        
        # self.thread_server_receive = threading.Thread(target=self.receive_server)
        # self.thread_server_receive.start() 
        
        self.thread_client_receive = threading.Thread(target=self.receive_client)
        self.thread_client_receive.start()
        
        self.thread_client_HB = threading.Thread(target=self.period_CCHB)
        self.thread_client_HB.start()
        

        self.thread_server_HB = threading.Thread(target=self.send_hb)
        self.thread_server_HB.start()
        
        self.thread_client_DL = threading.Thread(target=self.detectLost)
        self.thread_client_DL.start()
        
        self.thread_poll_server= threading.Thread(target=self.poll_server)
        self.thread_poll_server.start()
           
        self.thread_client_liveness = threading.Thread(target=self.client_liveness_check)
        self.thread_client_liveness.start()

    def connect_server(self):
        # Try Primary Server
        if self.connection_server=='':
            print "Request Primary Server in next 5s, please wait"
            past=time.time();
            self.t=0
            while self.t<5:
                try: 
                        self.s = socket.create_connection((CS_Primary_Request_IP, CS_Primary_Request_Port),10)
                        self.connection_state=True
                        self.connection_server='Primary'   
                        print "Connected to Primary Server!!!"
                        break
                except: 
                        self.connection_state=False
                        
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
                        print "Connected to Secondary Server!!!"
                        self.connection_state=True
                        self.connection_server='Secondary'
                        break
                except: 
                        self.connection_state=False
                self.t=time.time()-past
             
            if self.connection_server=='Secondary' and self.username:
                        self.hb_event.set()
                        self.poll_event.set()
                        self.s.shutdown(socket.SHUT_RDWR)    
                        self.s.close()    
          
                                   
                       
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

    def send_hb(self):
            flag=True
            while True: 
                self.hb_event.wait()    
                if self.connection_state and self.connection_server=='Primary': 
                                try:
                                    self.hb = socket.create_connection((CS_Primary_Request_IP, CS_Primary_Request_Port))
                                    self.hb_enable=True
                                except:
                                    if flag:
                                        print "\n................Primary Server May be down........................"
                                        flag=False
                                    self.hb_enable=False
                                    
                elif self.connection_state and self.connection_server=='Secondary': 
                            try:
                                self.hb = socket.create_connection((CS_Backup_Request_IP, CS_Backup_Request_Port))
                                self.hb_enable=True
                            except:
                                print "\n................Secondary Server May be down........................"
                                self.hb_enable=False
                                
                if self.hb_enable: 
                            try:
                                message=('PyHB',self.username,self.logical_time)
                                self.hb.send(str(message)) 
                                self.logical_time=self.logical_time+1
                            except:
                                print "HB cannot send to server" 
                            print "\nHeartbeat Message is sent to '%s' %s" % (str(self.connection_server), str(time.ctime()) ) 
                            self.received_hb[self.connection_server]=time.time()
                            self.hb_enable=False  
                            self.hb.shutdown(socket.SHUT_RDWR) 
                            self.hb.close() 
                        
                            time.sleep(BEAT_PERIOD)
                            
    def detectLost(self):
        while True:
                limit = time.time() - CHECK_TIMEOUT
                self.detectlost_lock.acquire()
                servername=''
                for servername in self.received_hb.keys():
                    if self.received_hb[servername]<= limit:
    
                        del self.received_hb[servername] 
                        
                        if self.normal_shutdown:
                            print "------------------I gracefully leave the %s Server --------------------" %servername
                            self.normal_shutdown=False
                        else:
                            print "------------------%s Server get lost--------------------" %servername
                            
                            self.connection_state=False
                            self.hb_event.clear()
                            self.connect_server()
                self.detectlost_lock.release()
                #time.sleep(CHECK_TIMEOUT) 
                
    def poll_server(self):
            t=15
            while True:
                self.poll_event.wait()
                print "Primary is being polling"
                if self.connection_state and self.connection_server=='Secondary' : 
                    try:
                        self.poll = socket.create_connection((CS_Primary_Request_IP, CS_Primary_Request_Port))
                        pconn=True                
                    except:
                        pconn=False
                        
                    if pconn:           
                        print "...................Server state exchange is processing...................."
                        self.poll.shutdown(socket.SHUT_RDWR)
                        self.poll.close()
                        self.normal_shutdown=True
                        self.connection_state=True;self.connection_server='Primary'
                        self.poll_event.clear()
                 
                    time.sleep(t)
    #                if t<3600:
    #                    t=t+60
    #                else:
    #                    t=3600            
                

    def init_username(self):
        addr=self.listening_addr;
                
        message=('CHB', addr[0], addr[1], self.username)
        try :
            self.s.sendall(str(message))
        except :
            print "send to server error"
            self.init_username_error()
            
        infds_c,outfds_c,errfds_c = select.select([self.s,],[],[])
        data=''
        if len(infds_c)!= 0:
            print '4'
            try:
                data=self.s.recv(8192)
            except Exception as inst :
                print "receive from server error"
                print type(inst)
                print inst
                self.init_username_error()
            print "the data is ",data        
            if len(data) != 0:
                print '2'
                
                self.s.shutdown(socket.SHUT_RDWR)
                self.s.close()
                self.hb_event.set()
                if self.connection_server=="Secondary":
                    self.poll_event.set()
                
                xyz=ast.literal_eval(data)# change it to tuple
                if xyz[0] == 'UT':
                    print '1'
                    self.session_table_lock.acquire()                                      
                    self.music_table_lock.acquire()    
                    # contact other clients except myself
                    for ut_item in xyz[1] :
                        key = (ut_item[0], int(ut_item[1]))
                    
                        self.session_table[key] = {'username' : ut_item[2], 'app_start_time' : None, 'logical_clk_time' : None, 'last_recv_time' : None}
                        if key == self.listening_addr :
                            self.music_table[key] = self.music_info

                    self.session_table_lock.release()                                           
                    self.music_table_lock.release()

                    print "first time multicast discovery message to clients - this line shouldn't be seen twice"
                
                    self.multicast_CCD()
                else :
                    print 'something is wrong 1'
            else :
                print 'something is wrong 3'

    def init_username_error(self) :
        print "server is down in sending first server discovery"
        try :
            self.s.shutdown(socket.SHUT_RDWR)
            self.s.close()
        except :
            print 'shut down connection to server error'
            
        self.connect_server()
        self.init_username()
                
    def receive_client(self):
        while True :
            peer_socket, peer_address = self.listening_sock.accept()
            peer_socket.settimeout(10)
                    
            data = peer_socket.recv(8192)
            
            peer_socket.close()
            message = pickle.loads(data);
            
            print 'receive new message of type %s, from client %s' % (message.m_type, message.sender_listening_addr) 
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
         
            if message.m_type == 'CCHB' or message.m_type == 'CCD' :
                
                self.music_table_lock.acquire()
                
                self.music_table[message.sender_listening_addr] = message.music_info
                
                self.music_table_lock.release()       
                
                print "client discovery | heartbeat message received"
                print message.m_type, message.sender_listening_addr
                self.dump_table()
                
                if message.m_type == 'CCD'  :
                    # send hb message back right asway
                    print 'message received is discovery; sending back a client heartbeat message as reply'
                    self.send_C_Music(message.sender_listening_addr, 'CCHB') 
                
            elif message.m_type == 'LIKE' :
                if message.receiver_app_start_time == self.app_start_time :
                    self.music_info.song_dict[message.song_seq_no].like = self.music_info.song_dict[message.song_seq_no].like+1
            
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

    def send_like(self, receiver_key, song_seq_num):
        self.logical_clk_lock.acquire()
        self.logical_clk_time += 1
        try :
            self.music_info_lock.acquire()
            self.send_obj(receiver_key, Client_Like_Message('LIKE', self.listening_addr, self.username, self.app_start_time, self.logical_clk_time, self.session_table[receiver_key]['app_start_time'], song_seq_num))
        except Exception as inst:
            print type(inst)
            print inst
            print "send_like() exception"
        finally:
            self.logical_clk_lock.release()
            self.music_info_lock.release()
    
            
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

    def client_liveness_check(self):
        liveness_threshold = 20
        while True:
            # print "presleep"
            time.sleep(15)
            # print "postsleep"
            #Go through session table to check last_recv_time
            # print "prelock"
            self.session_table_lock.acquire()
            # print "post-lock"
            for k in self.session_table.keys() :
                if k != self.listening_addr :
                    if(time.time() - self.session_table[k]['last_recv_time'] > liveness_threshold):
                        self.remove_lost_client(k)
            # print "pre-unlock"
            self.session_table_lock.release()
            # print "post-unlock"
    
    def remove_lost_client(self,key):
        # Delete client from all the tables
        self.remove_session_table(key)
        self.remove_music_table(key)
        
    def remove_session_table(self,key):
        del self.session_table[key]

    def remove_music_table(self, key):
        
        self.music_table_lock.acquire()
        del self.music_table[key]
        self.music_table_lock.release()

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
        
    def run(self):
        
        while (True) :
            command_str = raw_input("> ");
            if command_str == '' : 
                continue
            command = command_str.split(' ');
                
            if command[0] == 'user' :
                self.username = self.music_info.username = command[1]
                print self.listening_addr
                self.init_username()
                # self.send_SD()
                
            elif command[0] == 'SD' :
                self.send_SD()
            
            elif command[0] == 'listen' :
                self.open_listener();
            
            elif command[0] == 'like' :
                self.send_like((command[1], int(command[2])), int(command[3]))
                
            elif command[0] == 'q' :
                sys.exit()
                
            else :
                print "no match"

def main() :
    c = client();
    c.run();

if __name__ == '__main__':
    main()

