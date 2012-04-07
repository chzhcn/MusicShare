#-*- encoding: utf-8 -*-
'''
Created on Mar 25, 2012

@author: Yong
'''


import socket, threading, time, select, sys, os, cPickle, ast
from threading import Timer  
# For Client Server
CS_Primary_Request_IP = '127.0.0.3';CS_Primary_Request_Port = 60000; cs=(CS_Primary_Request_IP, CS_Primary_Request_Port)
# For Local Server 
SS_Listen_IP = '127.0.0.3';SS_Listen_Port = 60002; ss=(SS_Listen_IP, SS_Listen_Port)
# For Peer Server
SS_Target_IP = '127.0.0.2';SS_Target_Port = 60001; ss_target=(SS_Target_IP,SS_Target_Port)
CHECK_PERIOD = 120; CHECK_TIMEOUT = 120;BUFFER_SIZE=1024
BEAT_PERIOD = 5;MESSAGE='PyHB';judge=1
MESSAGE="This is message from server"

class requestor(threading.Thread):
    def __init__(self,threadname):
        threading.Thread.__init__(self, name = threadname) 
        self.thread_stop= False
        self.connection_state=False
        self.UT=[]
        self.fileopen=False
        self.s=None
        self.i=0
        self.judge=False


    def get_local_conn_info(self):
        addr=self.s.getsockname()   
        print addr
        
    def request_conn(self):  
        #s=socket.socket(socket.AF_INET,socket.SOCK_STREAM) 
        while self.connection_state==False:
            try: 
                    #socket.create_connection(address, timeout, source_address)
                    #print "We are trying connection......."
                    self.s = socket.create_connection(ss_target) 
                    print "Connection to Primary Server is established \n"
                    #s.connect(Server);
                    self.connection_state=True
            except: 
                    #print "please open the peer server firstly";
                    self.connection_state=False
    def getsock(self):
        if self.connection_state==True:
            return self.s
        else:
            return None
    def setUT(self,UT):
        self.UT=UT
       

    def send(self):          
        print ('Sending Heartbeat to IP %s , port %d\n') % (SS_Target_IP, SS_Target_Port)   
        while True:
            if self.connection_state and (not self.thread_stop):  
                if os.path.isfile('SHB_sendout_log.txt'):
                    f=file('SHB_sendout_log.txt','a')
                else:
                    f=file('SHB_sendout_log.txt','w') 
                try:
                    msg=('SS',self.UT)
                    self.s.sendall(str(msg))
                except:      
                   if not self.judge:
                        if self.i < 2:  
                            time.sleep(10)
                            self.i=self.i+1
                        print "Primary Server is down"
                        self.judge=True
                log= "Heartbeat is sent out, Time: %s \n" % time.ctime()
                f.write(log)
                f.close()
                time.sleep(BEAT_PERIOD)
            
    def stop(self):
        self.thread_stop=True
        self.s.shutdown(socket.SHUT_RDWR)
        self.s.close()
        print "the connection is closed by user"
        self.connection_state=False
        #self.connectserver()
    def express_send(self,x):
            #print ('Sending Heartbeat to IP %s , port %d\n') % (SS_Target_IP, SS_Target_Port)   
            if self.connection_state and (not self.thread_stop):  
                if os.path.isfile('SHB_sendout_log.txt'):
                    f=file('Express_SHB_sendout_log.txt','a')
                else:
                    f=file('Express_SHB_sendout_log.txt','w') 
                try:
                    msg=('express_SS',x)
                    self.s.sendall(str(msg))
                except:
                    print "error"
                log= "expressUT is sent out, Time: %s \n" % time.ctime()
                f.write(log)
                f.close()
        

class Heartbeats(dict):
    """Manage shared heartbeats dictionary with thread locking"""

    def __init__(self):
        super(Heartbeats, self).__init__()
        self._lock = threading.Lock()

    def __setitem__(self, key, value):
        """Create or update the dictionary entry for a client"""
        self._lock.acquire()
        super(Heartbeats, self).__setitem__(key, value)
        self._lock.release()

    def getSilent(self,sock):
        """Return a list of clients with heartbeat older than CHECK_TIMEOUT"""
        limit = time.time() - CHECK_TIMEOUT
        self._lock.acquire()
        silent = [ip for (ip, ipTime) in self.items() if ipTime < limit]  
        #print dict
        #print self        
        self._lock. release()
        #print silent
        for x in silent:
            if x==sock:
                silent.remove(x)
                print "There is a mistake you know everything is fine now"
                for (ip,ipTime) in self.items():
                    if ipTime<limit:
                        self.pop(ip)
                        
                #print silent
            else:pass
        return silent
       

class Receiver(threading.Thread):
      
    def __init__(self, goOnEvent, heartbeats,requestor):
        self.UT=[]
        self.TT=[]
        self.SS_UT=[]
        self.vector=[0,0]
        super(Receiver, self).__init__()
        self.goOnEvent = goOnEvent
        self.heartbeats = heartbeats
        self.connetcion_state=None
        self.count=0
        self.i=0
        self.sockx=[] 
        self.requestor=requestor
        self.closed_state=False
        self.remoteUT=[]
        self._lock = threading.Lock()
        self.server=''
        self.client=None
        self.server=None
        
    def passUT(self,receiver):
        self.client=receiver
        
    def getUT(self):
        return self.UT
    def setUT(self,UT):
        self.UT=UT
        
    def socket_init(self,address):
        if address==(SS_Listen_IP, SS_Listen_Port):      
            self.server='ss'
        elif address==(CS_Primary_Request_IP, CS_Primary_Request_Port):
            self.server='cs'
            
        self.s=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self.s.settimeout(CHECK_TIMEOUT)
        try:
            self.s.bind(address)
        except:
            print "Sorry,socket is occupied by another program,pleas close it firstly"
            sys.exit()

        
    def listen(self):
        self.s.listen(5)
        self.ins=[self.s,];self.ous=[];self.error=[];self.data={};self.adrs={};self.sock_ut={}  
        
    def set_connection_state(self,key,value):
        if key==1:
            self.connetcion_state=value
        elif key==0:
            self.connetcion_state=None
    def get_connection_state(self):
        return  self.connetcion_state 
    
    def sendback(self): 
        while 1:
            self.s.send(MESSAGE+' '+str(self.i))
            self.i=self.i+1
    def getremoteUT(self):
        return self.remoteUT
      
    def run(self): 
        global UTT 
        try:
            while self.goOnEvent.isSet():
                
                try:
                    i,o,e=select.select(self.ins,self.ous,[])
                except: 
                    self.set_connection_state(0,None)
                    self.listen()
               
                for x in i:
                                        if x is self.s:
                                            newSocket,address=self.s.accept()                               
                                            self.set_connection_state(1,address[0])
                                            print "local %s is connected from %s" % (self.s.getsockname(),address)
                                            self.ins.append(newSocket)
                                            self.adrs[newSocket]=address
                                                
                                        else:
                                            try:data=x.recv(8192)
                                            except:
                                                if not self.closed_state:
                                                    #print "Network Error,disconnected from %s,please check your network" % str(self.adrs[x])
                                                    self.set_connection_state(0,None)
                                                    
#                                                    del self.adrs[x]
#                                                    try:self.ous.remove(x)
#                                                    except ValueError:pass
                                                    data=None
                                                    #print "Client cannot recovery from network failure"    
                                                    #self.listen()
                                                    #x.close()
                                                    break;break
                                                else:
                                                    break;break
                                                #x.close();sys.exit() 
                                                               
                                            if data:
                                                #newdata=data
                                                #newdata=eval(data)
                                                try:
                                                    newdata=ast.literal_eval(data)
                                                except:
                                                    pass
                                                if newdata[0]=='CHB':
                                                    client_info=[newdata[1][0],newdata[1][1],newdata[2],time.ctime(),self.vector]
                                                    #self.sock_ut[x]=client_info
                                                    self.UT.append(client_info)
                                                    
                                                    if x not in self.ous: 
                                                        self.ous.append(x)
                                                        
                                                    print "%s is added into our system" % newdata[2]                              
                                                    #self.sockx.append(x) 
                                                    
                                                    #self.requestor.setUT(self.UT)
                                                    #self.requestor.express_send(self.UT)
                                                    #for n in self.sockx:
                                                        #self.ous.append(n)

                                                    #self.data[x]=self.data.get(x,'')+str(self.UT)      
                                                elif newdata[0]=='SS':
                                                    self.SS_UT=newdata[1]
                                                    if self.SS_UT:
                                                        print "UT Updata : %s :%s " %(str(self.SS_UT),str(time.ctime()))
#                                                        if self.server=='ss':
#                                                            self.client.setUT(self.SS_UT)
                                                        UTT=self.SS_UT
                                                        self.UT=self.SS_UT 
                                                    else:
                                                        print "UT Updata is empty %s" % str(time.ctime())
                                                elif newdata[0]=='SSR':
                                                    #print "I have no data to synchronization"
                                                    #print self.UT
#                                                    if self.server=='ss':
#                                                        self.client.setUT(self.UT)
#                                                    print self.UT  
                                                     
                                                    if self.UT:
                                                        msg=('rSSR',self.UT)
                                                        x.sendall(str(msg))
                                                    else:
                                                        pass
        
                                                elif newdata[0]=='express_SS':
                                                    self.SS_UT=newdata[1]
                                                    if self.SS_UT:
                                                        print "Express UT Updata : " ,self.SS_UT 
#                                                        if self.server=='ss':
#                                                            self.client.setUT(self.SS_UT)
                                                        UTT=self.SS_UT
                                                        self.UT=self.SS_UT 
                                                    else:
                                                        print "UT Updata is empty" 
                                                elif newdata[0] =='Debug':
                                                    message=''.join(newdata[1])
                                                    print "received message from %s : %s" % self.adrs[x],message
                                                    #self.data[x]=self.data.get(x,'')+newdata
                                                    #if x not in self.ous:self.ous.append(x)
                            
                                        
                                                elif newdata[0] =='terminate' :
                                                    print "%s leaves the group" % str(self.adrs[x])
                                                    self.closed_state=True
                                                    self.sockx.remove(x)
                                                    id=self.sock_ut.get(x)
                                                    self.UT.remove(id)
#                                                    self.requestor.setUT(self.UT)
#                                                    self.requestor.express_send(self.UT)
                                                    for n in self.sockx:
                                                        self.ous.append(n)
                                                elif newdata[0] =='PyHB':
                                                    print "Recevied PyHB",time.ctime()
                                                    if os.path.isfile('server_receive_hb_log.txt'):
                                                        f=file('server_receive_hb_log.txt','a')
                                                    else:
                                                        f=file('server_receive_hb_log.txt','w')
                                                    log= "received data : PyHB  Time: %s \n" % time.ctime()
                                                    f.write(log)
                                                    f.close()
#                                                    if self.server=='ss':
#                                                        self.client.setUT(self.UT)
#                                                    elif self.server=='cs':
#                                                        y=self.client.getUT()
#                                                        print x
                                                            
#                                                    self.heartbeats[address[0]] = time.time() 
#                                                    self.UT=UTT
#                                                    tosendx=('UT',self.UT)
#                                                    x.sendall(str(tosendx))
                                                    
                                                    
                                                elif newdata != 'PyHB':
                                                    print "%d bytes from %s,the content is %s" % (len(newdata),self.adrs[x],newdata)
                                                    #self.data[x]=self.data.get(x,'')+str(newdata)
                                                    print x
                                                    print self.ous
                                                    
                                                    for n in self.sockx:
                                                        self.ous.append(n)
                                                    print self.ous
                                           
                                            else:
                                                print "Disconnected from", self.adrs[x]
                                                del self.adrs[x]
                                                
                                                if x is  self.sockx:
                                                    self.sockx.remove(x)
                                                    
                                                try:self.ous.remove(x)
                                                except ValueError:pass
                                                x.close()                
                for x in o:
                    
                    if self.UT:
                        self.remoteUT=[]
                        for i in self.UT:     
                            self.remoteUT.append((i[0],i[1],i[2]))
                        
                        tosend=('UT',self.remoteUT)
                        try: 
                            x.sendall(str(tosend))
                        except: 
                            print "I cannot send data to %s" % str(self.adrs[x])
                            
                        print "UT has been sent to %s" % str(self.adrs[x])
                        self.ous.remove(x)
     
                    else:
                        msg='there is no user currently'
                        x.sendall(msg)
                        self.ous.remove(x)

               
        finally:
            self.s.close()  
    
       
               
def main():
    receiverEvent = threading.Event()
    receiverEvent.set()

    heartbeats = Heartbeats()
    
    ss_requestor= requestor('hbtor')
    # For connection to Backup Server
    
    thread1 = threading.Thread(target = ss_requestor.request_conn)  
    thread1.start()
    
    #ss_requestor.request_conn(ss_target)
    # For sending hb to Backup Server
    
    thread2 = threading.Thread(target = ss_requestor.send)  
    thread2.start()
    
    #ss_requestor.get_local_conn_info()
    

    cs_receiver = Receiver(goOnEvent = receiverEvent, heartbeats = heartbeats,requestor= ss_requestor)  
    ss_receiver = Receiver(goOnEvent = receiverEvent, heartbeats = heartbeats,requestor= ss_requestor)  
    
    
    cs_receiver.socket_init(cs)
    #cs_receiver.passUT(ss_receiver)
    cs_receiver.listen()
    cs_receiver.start()


    ss_receiver.socket_init(ss)
    #ss_receiver.passUT(cs_receiver)
    ss_receiver.listen()
    ss_receiver.start()
  
    print ('Threaded heartbeat server for Client is listening on port %d') % CS_Primary_Request_Port
    print ('Threaded heartbeat server for PeerServer is listening on port %d\n') % SS_Listen_Port
    
    
    
    try:
        while True:
            silent=heartbeats.getSilent(cs_receiver.get_connection_state())
            if len(silent)!=0:
                print 'Lost clients: %s' % silent             
            else: 
                pass
            time.sleep(CHECK_PERIOD)
    except KeyboardInterrupt:
        print 'Exiting, please wait...'
        receiverEvent.clear()
        cs_receiver.join()
        print 'Finished.'
    
if __name__ == '__main__':
    main()


