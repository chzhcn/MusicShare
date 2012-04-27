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
import shutil
import os


from client_info import Music_Info
from Client_Message import Client_Message
from Client_Message import Client_Music_Message
from Client_Message import Client_Request_Message

from Caching import Caching
from Player import Player

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

        self.music_table = {}
        self.session_table = {}
        self.file_table = {}
        self.music_info_object = Music_Info()
        self.music_info, self.file_table = self.music_info_object.read_repo(self.music_counter)
        
        self.music_table_lock = threading.Lock()
        self.session_table_lock = threading.Lock()
        self.logical_clk_lock = threading.Lock()
        self.music_info_lock = threading.Lock()
        
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
        self.open_stream_port()
        
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
        
        self.player=Player()
        
    def getNetworkIp(self):   
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)        
        s.connect(('google.com', 0))    
        return s.getsockname()[0] 

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
                            # self.hb.shutdown(socket.SHUT_RDWR)
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
            time.sleep(1) 
                
    def poll_server(self):
        t=15
        while True:
            self.poll_event.wait()
            print "Primary is being polled"
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
            
    def print_list(self,data):
        print ".......................User Table is.....................\n"
        num=1;
        userlist=ast.literal_eval(data)
        for i in userlist[1]:
            print num,':',i[0],':',i[1],':',i[2],'\n'
            num=num+1
                        

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
            self.print_list(data)       
            if len(data) != 0:
                print '2'
                
                # self.s.shutdown(socket.SHUT_RDWR)
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
            try:
                message = pickle.loads(data);
            except:
                pass
            
            print 'receive new message of type %s, from client %s' % (message.m_type, message.sender_listening_addr) 

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
         
            if message.m_type == 'CCHB' or message.m_type == 'CCD' :
                
                self.music_table_lock.acquire()
                
                self.music_table[message.sender_listening_addr] = message.music_info
                
                self.music_table_lock.release()       
                
                print "client discovery | heartbeat message received"
                print message.m_type, message.sender_listening_addr

                if message.m_type == 'CCD'  :
                    # send hb message back right asway
                    print 'message received is discovery; sending back a client heartbeat message as reply'
                    self.send_C_Music(message.sender_listening_addr, 'CCHB') 
                
            elif message.m_type == 'LIKE' or message.m_type == 'STREAM'  :
                if message.receiver_app_start_time == self.app_start_time :
                    print 'app_start_times match'
                    if message.m_type == 'LIKE' and message.song_seq_no in self.music_info.keys() :
                        self.music_info_lock.acquire()
                        self.music_info[message.song_seq_no].like = self.music_info[message.song_seq_no].like+1
                        self.music_info_lock.release()
                    elif message.m_type == 'STREAM' :
                        # print 'stream'
                        self.thread_stream = threading.Thread(target=self.stream_music, args=(message,))
                        self.thread_stream.start()
                else :
                    print 'app_start_times don\'t match'
                    self.send_C_Music(message.sender_listening_addr, 'CCHB')

    def stream_music(self, message) :
        ''' This function handles the streaming request message '''
        song_local_seq =  message.song_seq_no

        if song_local_seq in self.file_table.keys() :
            song_local_path = self.file_table[song_local_seq]
            requester_ip = message.sender_listening_addr[0]
            requester_stream_port = message.streaming_port
            print "-----------------------------Stream Info-------------------------------"
            print "request song_num :",song_local_seq
            print "request song path :",song_local_path
            #print requester_stream_port
            print "send stream to ip :",requester_ip
            print "send stream to port :", message.sender_listening_addr[1]
            self.player.sender_init(message.sender_listening_addr[0],message.sender_listening_addr[1],song_local_path)
        else :
            # FIXME: requested song is not there; should reply with rejection
            print "Song is not in current peer now"
            pass
        pass
            
    def dump_table(self):
        print 'dump tables: '
        print self.music_table
        # print self.session_table
        print self.file_table
 
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

    def send_request(self, request_type, receiver_key, song_seq_num):
        self.logical_clk_lock.acquire()
        self.logical_clk_time += 1
        try :
            self.music_info_lock.acquire()
            self.send_obj(receiver_key, Client_Request_Message(request_type, self.listening_addr, self.username, self.app_start_time, self.logical_clk_time, self.session_table[receiver_key]['app_start_time'], song_seq_num, self.streaming_addr[1]))
        except Exception as inst:
            print type(inst)
            print inst
            print "send_request() exception"
        finally:
            self.logical_clk_lock.release()
            self.music_info_lock.release()

    def send_like(self, receiver_key, song_seq_num):
        self.send_request('LIKE', receiver_key, song_seq_num)

    def send_stream(self, receiver_key, song_seq_num):
        self.send_request('STREAM', receiver_key, song_seq_num)
        
        self.stream_ip=receiver_key[0];
        self.stream_port=int(receiver_key[1]);
        self.stream_song_num=int(song_seq_num)     
        self.ip=self.getNetworkIp()  
        
        #print "self.stream_ip",self.stream_ip
        #print "self.stream_port",self.stream_port
        print ".........................Stream Info..................................."
        print "request song num :",self.stream_song_num 
        print "receive stream ip :",self.ip
        print "receive stream port :",self.port
         

        self.player.receiver_init(self.ip,self.port,self.stream_song_num)
            
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
            time.sleep(15)
            self.session_table_lock.acquire()
            for k in self.session_table.keys() :
                if k != self.listening_addr :
                    if(time.time() - self.session_table[k]['last_recv_time'] > liveness_threshold):
                        self.remove_lost_client(k)
            self.session_table_lock.release()
    
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
        #self.listening_addr = (socket.gethostbyname(socket.gethostname()), 0)
        self.listening_addr = (str(self.getNetworkIp()), 0)       
        self.listening_sock.bind(self.listening_addr)
        self.listening_addr = self.listening_sock.getsockname()
        self.port=self.listening_addr[1]
        self.listening_sock.listen(5)

    def open_stream_port(self):
        self.streaming_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.streaming_addr = (socket.gethostbyname(socket.gethostname()), 0)
        self.streaming_sock.bind(self.streaming_addr)
        self.streaming_addr = self.streaming_sock.getsockname()
        self.streaming_sock.listen(5)

    def add_song(self,filepath):
        repo_path = os.path.abspath("songs2/") # FIXME: path should be changed later
        #check if song with same name exists
        self.music_info_lock.acquire()
        if(self.music_info_object.check_song_exists(self.music_info,filepath)==False):
            # copy the file from current location to repo folder
            shutil.copy(filepath,repo_path)
            self.music_counter[0] +=1;
            self.music_info_object.read_song(self.music_info,self.file_table,self.music_counter[0], filepath)
            self.music_info_lock.release()
        else:
            self.music_info_lock.release()
            print 'duplicate song already exists in library'

    def remove_song(self,filepath) :
        #check if song exists
        self.music_info_lock.acquire()
        #Remove song from song_dict/music_info
        self.music_info_object.remove_song(self.music_info,self.file_table,filepath)
        self.music_info_lock.release()

    def run(self):
        
        while (True) :
            command_str = raw_input("> ");
            if command_str == '' : 
                continue
            command = command_str.split(' ');
                
            if command[0] == 'user' :
                self.username = command[1]
                print "the self.listening_address is ,",self.listening_addr
                self.init_username()
                
            elif command[0] == 'SD' :
                self.send_SD()
            
            elif command[0] == 'listen' :
                self.open_listener();
            
            elif command[0] == 'like' :
                self.send_like((command[1], int(command[2])), int(command[3]))

            elif command[0] == 'stream' :
                self.send_stream((command[1], int(command[2])), int(command[3]))

            elif command[0] == 'add':
                self.add_song(command[1])

            elif command[0]=='remove':
                self.remove_song(command[1])

            elif command[0] == 'dump' :
                self.dump_table()
                
            elif command[0] == 'q' :
                sys.exit()
            elif command[0]=='pause':
                self.player.pause()
            elif command[0]=='resume':
                self.player.resume()
            elif command[0]=='stop':
                self.player.stop()  
            elif command[0]=='replay':
                if not self.player.check_cache_dic(self.stream_song_num):
                    self.send_stream((self.stream_ip,self.stream_port),self.stream_song_num)
            elif command[0]== 'play_locally':
                local_song_path=command[1]
                self.player.resume(local_song_path)
            else :
                print "command not recognized"

def main() :
    c = client();
    c.run();

if __name__ == '__main__':
    main()
