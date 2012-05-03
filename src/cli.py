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
import random
import operator

import urllib 
import re

from client_info import Music_Info
from Client_Message import Client_Message
from Client_Message import Client_Music_Message
from Client_Message import Client_Request_Message

from Caching import Caching
from Player import Player

def getNetworkIp():   
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)        
        s.connect(('google.com', 0))    
        return s.getsockname()[0] 

#Primary Server
CS_Primary_Request_IP = str(getNetworkIp()); CS_Primary_Request_Port = 12345;
#Secondary Server
CS_Backup_Request_IP = CS_Primary_Request_IP; CS_Backup_Request_Port = 12347;
#HeartBeat Time
BEAT_PERIOD=15;CHECK_TIMEOUT=30

class client(object):

    def __init__(self, repo_path):
        
        self.open_portforward(False)
       

        self.s = None;
        self.is_connected=False
        self.send_socket = None;

        self.repo_path = repo_path
        
        self.username = None;        
        self.app_start_time = time.time()
        self.logical_clk_time = 0;

        self.music_counter = [0, ];

        self.music_table = {}
        self.session_table = {}
        self.file_table = {}
        self.music_info_object = Music_Info()
        self.music_info, self.file_table = self.music_info_object.read_repo(self.music_counter, self.repo_path)
        
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
        
        self.player=Player(self,)
    def open_portforward(self,value):
        if value:
            
            self.unified_port=False
            
            #................For telling bootstrap server...................
            self.public_ip=str(self.get_real_ip())
            self.public_map_port=50001  #remote map listen port        
            self.real_ip_address=(self.public_ip,self.public_map_port)
        
            #................For local listening...................
            self.ip=str(self.getNetworkIp()) 
            self.port=self.public_map_port    #local listen port
            self.listening_addr=(self.ip,self.port)
            
            #................For test in local Lan, if self.unified_port=True,it can be tested in Lan,otherwise it must be tested in WAN
            if self.unified_port:
                self.public_ip=self.ip
                self.public_map_port=self.port
                self.real_ip_address=self.listening_addr
            self.open_listener()
        else:
            
            self.open_local_listener()
            
            self.ip=self.listening_addr[0]
            self.port=self.listening_addr[1]     #local listen port
            
            self.public_ip=self.ip
            self.public_map_port=self.port
            self.real_ip_address=self.listening_addr
        
    def getNetworkIp(self):   
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)        
        s.connect(('google.com', 0))    
        return s.getsockname()[0] 

    def get_real_ip(self):
#        group = re.compile(u'(?P<ip>\d+\.\d+\.\d+\.\d+)').search(urllib.URLopener().open('http://jsonip.com/').read()).groupdict() 
#        return group['ip'] 
         ip = urllib.urlopen('http://ip.42.pl/raw').read() 
         print ip
         return ip
        

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

        message=('CHB', self.public_ip, self.public_map_port, self.username)
        try :
            self.s.sendall(str(message))
        except Exception as inst :
            print type(inst)
            print inst
            # print "send to server error"
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
                    
                        self.session_table[key] = {'username' : ut_item[2], 'app_start_time' : None, 'logical_clk_time' : None, 'last_recv_time' : time.time()}
                        if key == self.real_ip_address :
                            self.music_table[key] = self.music_info
                            self.session_table[key]['app_start_time'] = self.app_start_time

                    self.music_table_lock.release()
                    self.session_table_lock.release()

                    print "first time multicasting discovery message to clients - this line shouldn't be seen twice"
                
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
            #message=Client_Message(None,None,None,None,None)
            peer_socket.close()
            try:
                message = pickle.loads(data);
            except Exception as inst:
		    print type(inst)
		    print inst
		    message.m_type=None
		    message.sender_listening_addr=None
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
                
            elif message.m_type == 'LIKE' or message.m_type == 'STREAM' or message.m_type == 'REP'  :
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
		    elif message.m_type == 'REP' :
			self.patch_music_table_rep(self.listening_addr, message.song_seq_no, message.sender_listening_addr, message.cache_seq)
			self.multicast_C_Music('CCHB')
                else :
                    print 'app_start_times don\'t match'
                    # print message.receiver_app_start_time, self.app_start_time
                    self.send_C_Music(message.sender_listening_addr, 'CCHB')

    def stream_music(self, message) :
        ''' This function handles the streaming request message '''
        song_local_seq =  message.song_seq_no

        if song_local_seq in self.file_table.keys() :
            song_local_path = self.file_table[song_local_seq]
            print "-----------------------------Stream Info-------------------------------"
            print "request song_num :",song_local_seq
            print "request song path :",song_local_path
            print "send stream to ip :",message.sender_listening_addr[0]
            print "send stream to port :", message.sender_listening_addr[1]
            self.player.sender_init(message.sender_listening_addr[0],message.sender_listening_addr[1],song_local_path)
        else :
            # FIXME: requested song is not there; should reply with rejection
            print "Song is not in current peer now"
            pass
        pass
            
    def dump_table(self):
        print 'dump tables: '
        print '..............................Music Table...........................'
        for key in self.music_table.keys():
            print "..............." ,key
            for i in self.music_table[key].keys():
                print i,":",self.music_table[key][i],'\n'            
        # print self.session_table
        print '..............................File Table...........................'
        for key in self.file_table:
            print key,":",self.file_table[key],'\n'
        print "..............................Self Music INfo............................"
        print self.music_info
 
    def send_obj(self, addr, obj):  
        try :
            try:
                self.send_socket = socket.create_connection(addr, 10)
                self.is_connected=True
            except:
                self.is_connected=False
                print "+++++++++++++++++++++++Connection Problem++++++++++++++++++++++"   
            if self.is_connected: 
                data = pickle.dumps(obj)
                self.send_socket.sendall(data);  
        except Exception as inst:
            print type(inst)
            print inst
            print "send_obj() exception. addr: %s obj: %s" % (addr, str(obj))
            raise

    def send_request(self, request_type, receiver_key, song_seq_num, cache_seq=-1):
        self.logical_clk_lock.acquire()
        self.logical_clk_time += 1
        try :
            self.streaming_addr=receiver_key
            self.send_obj(receiver_key, Client_Request_Message(request_type, self.real_ip_address, self.username, self.app_start_time, self.logical_clk_time, self.session_table[receiver_key]['app_start_time'], song_seq_num, self.streaming_addr[1], cache_seq))
        except Exception as inst:
            print type(inst)
            print inst
            print "send_request() exception"
        finally:
            self.logical_clk_lock.release()

    def send_rep(self, receiver_key, receiver_song_seq_num, cache_seq) :
	    self.send_request('REP', receiver_key, receiver_song_seq_num, cache_seq)

    def send_like(self, receiver_key, song_seq_num):
        self.send_request('LIKE', receiver_key, song_seq_num)

    def send_stream(self, receiver_key, song_seq_num, owner_key, owner_song_seq_num):
        self.send_request('STREAM', receiver_key, song_seq_num)
        
        self.stream_ip=receiver_key[0];
        self.stream_port=int(receiver_key[1]);
        self.stream_song_num=int(song_seq_num)     
 
        
        #print "self.stream_ip",self.stream_ip
        #print "self.stream_port",self.stream_port
        print ".........................Stream Info..................................."
        print "request song num :",self.stream_song_num 
        print "receive stream ip :",self.ip
        print "receive stream port :",self.port

        self.player.receiver_init(self.ip,self.port, self.stream_song_num, owner_key, owner_song_seq_num)
            
    def send_C_Music(self, address, m_type):
        self.logical_clk_lock.acquire()
        self.logical_clk_time += 1
        try :
            self.music_info_lock.acquire()
            self.send_obj(address, Client_Music_Message(m_type, self.real_ip_address, self.username, self.app_start_time, self.logical_clk_time, self.music_info))
        except Exception as inst:
            print type(inst)
            print inst
            print "send_C_Music() exception addr %s obj: %s" % (address, self.music_info)
        finally:
            self.music_info_lock.release()
            self.logical_clk_lock.release()
    
    def multicast_C_Music(self, m_type):
        print "multicasting music info to clients"
        self.session_table_lock.acquire()
        for k in self.session_table.keys() :
		if k!=self.real_ip_address and k!=0 and k!=None :
			self.send_C_Music(k, m_type)
	self.session_table_lock.release()
                
    def multicast_CCD(self):
        self.multicast_C_Music('CCD')
        
    def multicast_CCHB(self):
        self.multicast_C_Music('CCHB') 
        
    def period_CCHB(self):
        while True :
            time.sleep(20)
            self.multicast_CCHB()

    def client_liveness_check(self):
        liveness_threshold = 20
        while True:
            time.sleep(15)
            self.session_table_lock.acquire()
            for k in self.session_table.keys() :
                if k != self.real_ip_address :
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
        if key in self.music_table.keys():
            del self.music_table[key]
        self.music_table_lock.release()

    def close_listen_port(self,port):
        while True:
            try:
                command1="netstat -nltp |grep %s" % port
                a=os.popen(command1).read()
                if len(a)!=0:
                    try:
                        command1="kill -9 $(netstat -tlnp|grep %s | awk \'{ print $7 }\' |awk -F \'/\' \'{print $1 }\')" % port
                        os.system(command1)
                    except:
                        pass
                else:
                    break
            except:
                pass

    def look_up_cache(self, receiver_key, song_seq_num):
	    local_seq = -1
	    no_rep = True
	    rep = None

	    print 'look_up_cache: receiver_key: %s, song_seq_num: %s' % (receiver_key, song_seq_num) 

	    if receiver_key not in self.music_table.keys() or song_seq_num not in self.music_table[receiver_key].keys():
		    print 'receiver_key: %s, song_seq_num: %s, not in table' % (receiver_key, song_seq_num) 
		    return (local_seq, no_rep, rep)

	    print self.music_table
	    print 'in look_up: ', self.music_table[receiver_key][song_seq_num].rep_dict

	    if self.listening_addr in self.music_table[receiver_key][song_seq_num].rep_dict.keys() :
		    local_seq = self.music_table[receiver_key][song_seq_num].rep_dict[self.listening_addr]
		    print 'receiver_key: %s, song_seq_num: %s, in table with hit' % (receiver_key, song_seq_num) 
		    no_rep = False
	    else :
		    rep_len = len(self.music_table[receiver_key][song_seq_num].rep_dict.items())
		    if rep_len == 0 :
			    print 'receiver_key: %s, song_seq_num: %s, in table without cache ' % (receiver_key, song_seq_num) 
			    no_rep = True
		    else :
			    rep_items = self.music_table[receiver_key][song_seq_num].rep_dict.items()
			    rep_items.append((receiver_key, song_seq_num))
			    no_rep = False
			    rep = rep_items[random.randint(0, rep_len)]
			    print 'receiver_key: %s, song_seq_num: %s, in table with multiple cache ' % (receiver_key, song_seq_num) 

	    return (local_seq, no_rep, rep)

    def try_play(self, owner_key, owner_song_seq_num) :
	    if self.player.is_playing :
		    print "It is playing now"
		    self.player.pause()
		    self.player.stop()
	    if self.listening_addr == owner_key and owner_song_seq_num in self.file_table.keys():
		    print 'playing from local repo'
		    self.player.play(self.file_table[owner_song_seq_num])
	    else :
		    local_seq, no_rep, rep = self.look_up_cache(owner_key, owner_song_seq_num)
		    if no_rep == True :
			    print 'no cache; send request to owner: %s %s' % (owner_key, owner_song_seq_num)
			    self.send_stream(owner_key, owner_song_seq_num, owner_key, owner_song_seq_num)
		    elif rep != None :
			    print 'multiple cache; send request to one of them: %s %s, owner: %s %s' % (rep[0], rep[1], owner_key, owner_song_seq_num)
			    self.send_stream(rep[0], rep[1], owner_key, owner_song_seq_num)
		    else :
			    print 'play from local cache'
			    self.player.play(self.file_table[local_seq])

    def open_listener(self):
        self.listening_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)        
#        self.close_listen_port(self.port)
#        self.close_listen_port(int(self.port+11))
#        self.close_listen_port(int(self.port+12))
        print "self.listening_addr ",self.listening_addr
        try:    
            self.listening_sock.bind(self.listening_addr)
        except:
            pass
            #self.listening_sock.bind(self.listening_addr)
            
        self.listening_sock.listen(5)
        
    def open_local_listener(self):
        self.listening_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listening_addr = (socket.gethostbyname(socket.gethostname()), 0)
        self.listening_addr = (str(self.getNetworkIp()), 0)       
        self.listening_sock.bind(self.listening_addr)
        self.listening_addr = self.listening_sock.getsockname()
        self.listening_sock.listen(5)
        return self.listening_addr
    

    def add_song(self,filepath):
        repo_path = os.path.abspath(self.repo_path) # FIXME: path should be changed later
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

    def add_cache(self, cache_path) :
	self.music_info_lock.acquire()
	self.music_counter[0] +=1;
	seq = self.music_counter[0]
	self.music_info_object.add_cache(self.file_table,self.music_counter[0], cache_path)
	self.music_info_lock.release()
	return seq

    def add_song_server(self, filepath):
        self.music_info_lock.acquire()
        self.music_counter[0] +=1;
        self.music_info_object.read_song(self.music_info,self.file_table,self.music_counter[0], filepath)
        self.music_info_lock.release()

    def remove_song(self,filepath) :
        #check if song exists
        self.music_info_lock.acquire()
        #Remove song from song_dict/music_info
        self.music_info_object.remove_song(self.music_info,self.file_table,filepath)
        self.music_info_lock.release()
    
    def top_ten(self):
        song_list=[]
        # print '-----------------------------------top 10--------------------------------------'
        for user,song_info in self.music_table.items():
    	    for seq,song in song_info.items():
	        user_info=(user,seq)
		song_list.append((user_info,song))
		# print 'song: ',
		# print song
        sorted_list = sorted(song_list,key=lambda x:x[1].like,reverse=True)
        # print sorted_list
        return sorted_list

    def patch_music_table_rep(self, holder_key, holder_song_seq_num, rep_listening_addr, cache_seq_num) :
	self.music_table_lock.acquire()
	if holder_key in self.music_table.keys() and holder_song_seq_num in self.music_table[holder_key].keys() :
		self.music_table[holder_key][holder_song_seq_num].add_rep(rep_listening_addr, cache_seq_num)
		print 'in patch: ', self.music_table[holder_key][holder_song_seq_num].rep_dict
		print self.music_table
	else :
		print 'not in table (%s, %s)' % (holder_key, holder_song_seq_num)
	
	self.music_table_lock.release()

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
                if self.player.is_playing:
                    print "It is playing now"
                    self.player.pause() 
                    self.player.stop() 
                else:
                    print "I am lucky"
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
            elif command[0]=='play':
                song_playing_flag=False
                song_num=int(command[1])
                for key in self.file_table.keys():
                    if key==song_num:
                        songpath=self.file_table[key]
                        self.player.play(songpath)
                        song_playing_flag=True
                  
                if song_playing_flag==False:
                    cachepath=self.player.traverse_cache_dic(song_num)
                    if len(cachepath)!=0:
                        self.player.play(cachepath)
                    else:
                        print "Sorry there is no that song in the repo"
                                              
            else :
                print "command not recognized"

def main() :
    c = client();
    c.run();

if __name__ == '__main__':
    main()
