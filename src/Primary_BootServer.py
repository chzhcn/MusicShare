#-*- encoding: utf-8 -*-
'''
Created on Mar 25, 2012

@author: Yong
'''


import socket, threading, time, select, sys, os, cPickle, ast
from threading import Timer  
# For Client Server
CS_Primary_Request_IP = '127.0.0.1';CS_Primary_Request_Port = 12345; cs = (CS_Primary_Request_IP, CS_Primary_Request_Port)
# For Local Server 
SS_Listen_IP = '127.0.0.1';SS_Listen_Port = 12346; ss = (SS_Listen_IP, SS_Listen_Port)
# For Peer Server
SS_Target_IP = '127.0.0.1';SS_Target_Port = 12348; ss_target = (SS_Target_IP, SS_Target_Port)
CHECK_PERIOD = 20; CHECK_TIMEOUT = 10;BUFFER_SIZE = 1024
BEAT_PERIOD = 5;MESSAGE = 'PyHB';judge = 1
MESSAGE = "This is message from server"

class requestor(threading.Thread):
    def __init__(self, threadname):
        threading.Thread.__init__(self, name=threadname) 
        self.thread_stop = False
        self.connection_state = False
        self.UT = []
        self.fileopen = False


    def get_local_conn_info(self):
        addr = self.s.getsockname()   
        return addr
        
    def request_conn(self):  
        global s
        address = ss_target
        #s=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        while self.connection_state == False:
            try: 
                    #socket.create_connection(address, timeout, source_address)
                    #print "We are trying connection......."
                    s = socket.create_connection(address) 
                    print "Connection to Backup Server is established \n"
                    
                    #s.connect(Server);
                    self.connection_state = True
            except: 
                    #print "please open the peer server firstly";
                    self.connection_state = False
    def getsock(self):
        if self.connection_state == True:
            return s
        else:
            return None
    def setUT(self, UT):
        self.UT = UT
       

    def send(self):  
        print ('Sending Heartbeat to IP %s , port %d\n') % (SS_Target_IP, SS_Target_Port)   
        while True:
            if self.connection_state and (not self.thread_stop):  
                if os.path.isfile('SHB_sendout_log.txt'):
                    f = file('SHB_sendout_log.txt', 'a')
                else:
                    f = file('SHB_sendout_log.txt', 'w') 
                try:
                    msg = ('SS', self.UT)
                    s.sendall(str(msg))
                except:
                    print "error"
                    time.sleep(10)
                log = "Heartbeat is sent out, Time: %s \n" % time.ctime()
                f.write(log)
                f.close()
                time.sleep(BEAT_PERIOD)
            
    def stop(self):
        self.thread_stop = True
        s.shutdown(socket.SHUT_RDWR)
        s.close()
        print "the connection is closed by user"
        self.connection_state = False
        #self.connectserver()
  
class listener():
    def __init__(self):
        pass
    def socket_init(self):
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.settimeout(CHECK_TIMEOUT)
        try:
            self.s.bind((CS_Primary_Request_IP, CS_Primary_Request_Port))
        except:
            print "Sorry,socket is occupied by another program,pleas close it firstly"
            sys.exit()

        
    def listen(self):
        self.s.listen(5)
        self.ins = [self.s];self.ous = [];self.data = {};self.adrs = {} 


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

    def getSilent(self, sock):
        """Return a list of clients with heartbeat older than CHECK_TIMEOUT"""
        limit = time.time() - CHECK_TIMEOUT
        self._lock.acquire()
        silent = [ip for (ip, ipTime) in self.items() if ipTime < limit]  
        #print dict
        #print self        
        self._lock. release()
        #print silent
        for x in silent:
            if x == sock:
                silent.remove(x)
                print "There is a mistake you know everything is fine now"
                for (ip, ipTime) in self.items():
                    if ipTime < limit:
                        self.pop(ip)
                        
                #print silent
            else:pass
        return silent
       

class Receiver(threading.Thread):
      
    def __init__(self, goOnEvent, heartbeats, requestor):
        self.UT = []
        self.TT = []
        self.vector = [0, 0]
        super(Receiver, self).__init__()
        self.goOnEvent = goOnEvent
        self.heartbeats = heartbeats
        self.connetcion_state = None
        self.count = 0
        self.i = 0
        self.sockx = [] 
        self.requestor = requestor
        self.closed_state = False
        
    def getUT(self):
        return self.UT
        
        
    def socket_init(self, address):
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.settimeout(CHECK_TIMEOUT)
        try:
            print address
            self.s.bind(address)
            print "done"
        except:
            print "Sorry,socket is occupied by another program,pleas close it firstly"
            sys.exit()

        
    def listen(self):
        self.s.listen(5)
        self.ins = [self.s, ];self.ous = [];self.error = [];self.data = {};self.adrs = {};self.sock_ut = {}  
        
    def set_connection_state(self, key, value):
        if key == 1:
            self.connetcion_state = value
        elif key == 0:
            self.connetcion_state = None
    def get_connection_state(self):
        return  self.connetcion_state 
    
    def sendback(self): 
        while 1:
            self.s.send(MESSAGE + ' ' + str(self.i))
            self.i = self.i + 1
        
      
    def run(self):  
        try:
            while self.goOnEvent.isSet():
                try:
                    i, o, e = select.select(self.ins, self.ous, [])
                except: 
                    self.set_connection_state(0, None)
                    self.listen()
               
                for x in i:
                                        if x is self.s:
                                            newSocket, address = self.s.accept()                               
                                            self.set_connection_state(1, address[0])
                                            print "local %s is connected from %s" % (self.s.getsockname(), address)
                                            self.ins.append(newSocket)
 
                                            self.adrs[newSocket] = address
                                        else:
                                            try:data = x.recv(8192)
                                            except:
                                                if not self.closed_state:
                                                    print "Network Error,disconnected from %s,please check your network" % str(self.adrs[x])
                                                    self.set_connection_state(0, None)
                                                    
                                                    del self.adrs[x]
                                                    try:self.ous.remove(x)
                                                    except ValueError:pass
     
                                                    data = None
                                                    a = time.time()
                                                    n = 0
                                                    while n < 60:
                                                        self.listen()
                                                        n = time.time() - a
                                                    print "Client cannot recovery from network failure"    
                                                    #self.listen()
                                                    x.close()
                                                    break;break
                                                else:
                                                    break;break
                                                #x.close();sys.exit() 
                                                               
                                            if data:
                                                #newdata=data
                                                #newdata=eval(data)
                                                try:
                                                    newdata = ast.literal_eval(data)
                                                except:
                                                    pass
                                                if newdata[0] == 'CHB':
                                                    ip = newdata[1][0]
                                                    port = newdata[1][1]
                                                    username = newdata[2]
                                                    
                                                    host_id = [ip, str(port), username]
                                                    self.sock_ut[x] = host_id
                                                    
                                                    tt = [ip, port, time.ctime(), self.vector]
                                                    
                                                    self.UT.append(host_id)
                                                    self.TT.append(tt)
                                                    
                                                    self.requestor.setUT(self.UT)

                                                    print "%s is added into our system" % username
                                                    
                                                    self.sockx.append(x) 
                                                    
                                                    for n in self.sockx:
                                                        self.ous.append(n)
                                                        
                                                    # FIXME:
                                                    self.sockx.remove(x)
 
                                                    self.data[x] = self.data.get(x, '') + str(self.UT)

                                                        
                                                elif newdata[0] == 'Debug':
                                                    message = ''.join(newdata[1])
                                                    print "received message from %s : %s" % self.adrs[x], message
                                                    #self.data[x]=self.data.get(x,'')+newdata
                                                    #if x not in self.ous:self.ous.append(x)
                                                elif newdata[0] == 'terminate' :
                                                    print "%s leaves the group" % str(self.adrs[x])
                                                    self.closed_state = True
                                                    self.sockx.remove(x)
                                                    id = self.sock_ut.get(x)
                                                    self.UT.remove(id)
                                                    self.requestor.setUT(self.UT)
                                                    for n in self.sockx:
                                                        self.ous.append(n)
                                                elif newdata[0] == 'PyHB':
                                                    if os.path.isfile('server_receive_hb_log.txt'):
                                                        f = file('server_receive_hb_log.txt', 'a')
                                                    else:
                                                        f = file('server_receive_hb_log.txt', 'w')
                                                    log = "received data : PyHB  Time: %s \n" % time.ctime()
                                                    f.write(log)
                                                    f.close()
                                                    
                                                    self.heartbeats[address[0]] = time.time() 
                                                elif newdata != 'PyHB':
                                                    print "%d bytes from %s,the content is %s" % (len(newdata), self.adrs[x], newdata)
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
                            tosend = ('UT', self.UT)
                            try: 
                                x.sendall(str(tosend))
                            except: 
                                print "I cannot send data to %s" % str(self.adrs[x])
                            
                            print "UT has been sent to %s" % str(self.adrs[x])
                            self.ous.remove(x)
                    else:
                        msg = 'there is no user currently'
                        x.sendall(msg)
                        self.ous.remove(x)
                        


        finally:
            self.s.close()  
    
       
               
def main():
    receiverEvent = threading.Event()
    receiverEvent.set()

    heartbeats = Heartbeats()
    
    ss_requestor = requestor('hbtor')
    thread1 = threading.Thread(target=ss_requestor.request_conn)  
    thread1.start()
    #ss_requestor.request_conn(ss_target)
    
    thread2 = threading.Thread(target=ss_requestor.send)  
    thread2.start()
    

    cs_receiver = Receiver(goOnEvent=receiverEvent, heartbeats=heartbeats, requestor=ss_requestor)  
    cs_receiver.socket_init(cs)
    cs_receiver.listen()
    cs_receiver.start()

    ss_receiver = Receiver(goOnEvent=receiverEvent, heartbeats=heartbeats, requestor=ss_requestor)  
    ss_receiver.socket_init(ss)
    ss_receiver.listen()
    ss_receiver.start()
  
    print ('Threaded heartbeat server for Client is listening on port %d') % CS_Primary_Request_Port
    print ('Threaded heartbeat server for PeerServer is listening on port %d\n') % SS_Listen_Port
    
    
    
    try:
        while True:
            silent = heartbeats.getSilent(cs_receiver.get_connection_state())
            if len(silent) != 0:
                print 'Lost clients: %s' % silent             
            else: 
                pass
            time.sleep(CHECK_PERIOD)
    except KeyboardInterrupt:
        print 'Exiting, please wait...'
        receiverEvent.clear()
        cs_receiver.join()
        print 'Finished.'
        sys.exit()
    
if __name__ == '__main__':
    main()


