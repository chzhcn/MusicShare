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
#Primary Server
CS_Primary_Request_IP = '127.0.0.2'; CS_Primary_Request_Port = 60000;
#Secondary Server
CS_Backup_Request_IP  = '127.0.0.3'; CS_Backup_Request_Port  = 60000;
#Local Server
Self_Server_Ip   = '127.0.0.1'; Self_Server_Port =50000 ;
CHECK_TIMEOUT=30
BEAT_PERIOD =15;BUFFER_SIZE=1024;MESSAGE='PyHB'

class Client(threading.Thread):
    def __init__(self,threadname):
        threading.Thread.__init__(self, name = threadname)

        self.thread_stop= False
        self.connection_state=False
        self.connection_server=None  
        self.username=None
        self.log_open=False
        self.UT=[]
        self.s=None
        self.hb=None
        self.username_init1=False
        self.username_init2=False
        self.fist_hearthb=True
        self.connection_switch_to_p=False  
        self.received_hb={}
        self._lock = threading.Lock()
        self.hb_enable=False
        self.prevous_server=''
        self.connection_lost=False
        self.connectserver()
        self.port=12345
        self.alter=False
        self.judge=False
                     
    def connectserver(self):
        # Try Primary Server
        if not self.connection_lost:
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
        
    def send_hb(self):
        #print ('Sending Heartbeat to IP %s , port %d\n') % (CS_Primary_Request_IP, CS_Primary_Request_Port)       
            while True: 
              if self.connection_state and self.connection_server=='Primary':
                if self.username_init2 or self.connection_switch_to_p:            
                         if self.fist_hearthb:     
                            time.sleep(1)
                            self.fist_hearthb=False

                         if not self.connection_switch_to_p:
                            try:
                                self.hb = socket.create_connection((CS_Primary_Request_IP, CS_Primary_Request_Port))
                                self.hb_enable=True
                            except:
                                if not self.alter:
                                    print "\n................Primary Server May be down........................"
                                    self.alter=True
                                else:
                                    self.connectserver()
                                self.hb_enable=False
                                 
                                time.sleep(BEAT_PERIOD)
 
              elif self.connection_state and self.connection_server=='Secondary': 
                        if self.connection_lost or self.username_init2: 
                            if self.fist_hearthb:     
                                time.sleep(1)
                                self.fist_hearthb=False

                            try:
                                self.hb = socket.create_connection((CS_Backup_Request_IP, CS_Backup_Request_Port))
                                #print "Oh yeah you are on the backup"
                                self.hb_enable=True
                            except:
                                print "Secondary Server May be down"
                                self.hb_enable=False
                                
              if self.hb_enable: 
                             if os.path.isfile('CS_HB_Sentout.log.txt'):
                                f=file('CS_HB_Sentout.log','a')
                             else:
                                f=file('CS_HB_Sentout.log','w')    
                             try:
                                message=('PyHB',self.username)
                                self.hb.send(str(message)) 
                             except:
                                print "HB cannot send to server" 
                             print "\nHeartbeat Message is sent to %s %s" % (str(self.connection_server), str(time.ctime()) ) 
                             #self.hb.shutdown(socket.SHUT_RDWR)   
                             self.hb.close() 
                             self.received_hb[self.connection_server]=time.time()
                             log= "Heartbeat is sent out, Time: %s \n" % time.ctime()
                             f.write(log)
                             f.close()
                             time.sleep(BEAT_PERIOD)              
                            
                                               
      
                             
                             
 
              """""   // send_hb timer
             if self.connection_server=='Primary':
                        if not self.connection_switch:
                            try:
                                self.hb = socket.create_connection((CS_Primary_Request_IP, CS_Primary_Request_Port))
                            except:
                                print "Primary Server May be down"
                                self.connectserver()
                        else:
                            pass      
             elif self.connection_server=='Secondary':
                 try:
                    self.hb = socket.create_connection((CS_Backup_Request_IP, CS_Backup_Request_Port))
                 except:
                    print "Secondary Server May be down"
                    self.connectserver()
             else:
                print "error"
                
             """                       
                                        
    def poll_server(self):
        t=30
        while True:
            if self.connection_server=='Secondary' : 
                #print "\nPrimary Server is monitored",time.ctime()
                try:
                    self.poll = socket.create_connection((CS_Primary_Request_IP, CS_Primary_Request_Port))
                    pconn=True                
                except:
                    pconn=False
                    
                if pconn:           
                    print "...................Server state exchange is finished...................."
                    try:
                        self.poll=None
                    except:
                        pass
                    self.s.close()
                    self.hb.close()
                    self.hb_enable=False
                    self.connection_state=False
                    self.connection_lost=False
                    self.connectserver()
                    
#                    self.connection_server='Primary'
#                    self.connection_switch_to_p=True
#                    self.connection_state=True 
                    break                  
                time.sleep(t)
#                if t<3600:
#                    t=t+60
#                else:
#                    t=3600
                                                                                        
    def stop(self):
        self.thread_stop=True
        self.s.shutdown(socket.SHUT_RDWR)
        self.s.close()
        print "the connection is closed by user"
        self.connection_state=False 
        self.connectserver()
        
    def init_username(self):
            if not self.username:
                self.username=raw_input("username >") 
                  
            if not self.username:
                print "there is no username, please input again"
            #elif not self.connection_lost:
            else:
                addr=self.s.getsockname()
                #print addr
                #print "sencond time"
                
                message=('CHB',addr[0],self.port,self.username)
                self.s.sendall(str(message))
                #self.s.sendall(self.username) 
                #print "usranme message is sent"
                self.username_init1=True 
                
            if self.username_init1:
                #data_received=False
                #while not data_received:
                    infds_c,outfds_c,errfds_c = select.select([self.s,],[],[])
                    if len(infds_c)!= 0:    
                        try:
                            data=self.s.recv(8192)
                            data_received=True
                            #print "received"
                        except:
                            #print "socket closed" 
                            data_received=False  
              
                    if data_received and len(data) != 0:
                         #print "\nreceived data : %s \r\n " % data
                         #print "Received message : ",data
                         
                         xyz=ast.literal_eval(data)# change it to tuple                       
                         if xyz[0]=='UT':
                            self.UT=xyz[1]
                            print "First Received message: %s \r\n" % str(xyz[1])
                         else:
                            print "Error First Received message:%s \r\n" %str(xyz[1])  
                             
                         self.s.shutdown(socket.SHUT_RDWR)    
                         self.s.close()
                         self.username_init2=True
                         #print "username has been set"                           
    def init_shell(self):
        print ">:" ,;data=raw_input()
        if not data:
            #print "there is no data,please input data";
           print ">:" ,;data=raw_input()
        elif data=='stop':
            self.stop()
        elif data=='terminate':
            sys.exit()
            os.abort()      
            
    def run_shell(self):
        while self.connection_state:
              if not self.username_init2:
                  self.init_username()
              else:  
                  self.init_shell()  
                  
    def getSilent(self):
       while True:
            limit = time.time() - CHECK_TIMEOUT
            self._lock.acquire()
            servername=''
            for servername in self.received_hb.keys():
                if self.received_hb[servername]<= limit:
                    print "------------------%s Server get lost--------------------" %servername
                    del self.received_hb[servername] 
                    self.connection_server=''
                    self.connection_lost=True
                    self.username_init2=False
                    self.connection_state=False
                    self.connectserver()
            self._lock. release()                             
                                                                           
    def receive(self):
        while True:

            if self.username_init2:
                    #print "I am receiving"
#                infds_c,outfds_c,errfds_c = select.select([self.s,],[],[])
#                if len(infds_c)!= 0:
                    try:
                        data=self.hb.recv(1024)
                        data_received=True
                    except:
                        #print "socket closed" 
                        data_received=False  
#                       self.thread_stop=True
#                        self.s.shutdown(socket.SHUT_RDWR)
#                        self.s.close()
#                        print "the connection is closed by user"
#                        self.connection_state=False
#                        self.connectserver()
                        
                    if data_received and len(data) != 0:
                        #print "\nreceived data : %s \r\n " % data
                        #print data
                        self.received_hb[self.connection_server]=time.time()
                        
                        xyz=ast.literal_eval(data)# change it to tuple
                        if xyz[0]=='UT':
                            self.UT=xyz[1]
                            print "HB Received message:%s \r\n" %str(xyz[1])
                        else:
                            print "Error Received message:%s \r\n" %str(xyz[1])
                            
                        self.hb.shutdown(socket.SHUT_RDWR)    
                        self.hb.close() 
                        
                
def main():
    client=Client('CS_HB_Thread')
    
    thread_send= threading.Thread(target =client.run_shell)
    thread_send.start()  
    
#    thread_receive = threading.Thread(target= client.receive)
#    thread_receive.start() 

    
    thread_hb= threading.Thread(target =client.send_hb)
    thread_hb.start()
    
    thread_ms= threading.Thread(target =client.getSilent)
    thread_ms.start()
#    
#        
    thread_poll_server= threading.Thread(target =client.poll_server)
    thread_poll_server.start()
    
    
    
           
if __name__ == '__main__':
    main()
