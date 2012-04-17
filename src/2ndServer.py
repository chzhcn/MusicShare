#-*- encoding: utf-8 -*-
'''
Created on Apr 11, 2012

@author: Yong
'''
import asyncore
import logging
import socket
import time
import ast
import threading,sys, os, cPickle,string

logging.basicConfig(level=logging.DEBUG,
                        format='%(name)s: %(message)s',
                        )
CHECK_TIMEOUT=30
address = ('127.0.0.1',12347) # let the kernel give us a port
UTM=[]
heartbeats_test={}
v=[]

class VectorClock():
    def __init__(self,num,vid):
        self.num=num
        self.id=vid
        self.v=v
    def init(self):
        for i in range(self.num):
            v.append(0)
        v[self.id]=0    
    def tick(self):
        v[self.id]=self.v[self.id]+1
    def sendAction(self):
        v[self.id]=self.v[self.id]+1
    def receiveAcdtion(self,receivedv):
        for i in range(self.num):
            v[i]=max(self.v[i],receivedv[i])
        v[self.id]=self.v[self.id]+1
    def getValue(self,i):
        return v[i]
    def toString(self):
        return str(v)

class EchoServer(asyncore.dispatcher):
    """Receives connections and establishes handlers for each client.
    """
    
    def __init__(self, address,v):
        self.v=v
        #print "My vector from EchoServer is ",self.v.toString()
        self.logger = logging.getLogger('EchoServer')
        asyncore.dispatcher.__init__(self)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.bind(address)
        self.address = self.socket.getsockname()
        self.logger.debug('binding to %s', self.address)
        self.listen(1)
        return

    def handle_accept(self):
        # Called when a client connects to our socket
        client_info = self.accept()
        self.logger.debug('handle_accept() -> %s', client_info[1])
        EchoHandler(sock=client_info[0],vector=self.v)
        return
    
    def handle_close(self):
        self.logger.debug('handle_close()')
        self.close()
        return

class EchoHandler(asyncore.dispatcher):
    """Handles echoing messages from a single client.
    """
    
    def __init__(self, sock, vector):
       
        self.chunk_size = 8192
        self.v=vector   # vector object
#        self.v=vector
#        print "My vector from Echohandler is :", self.v.toString
        self.logger = logging.getLogger('EchoHandler%s' % str(sock.getsockname()))
        asyncore.dispatcher.__init__(self, sock=sock)
        self.data_to_write = []
       
        self.UT_enable=False
        self.llogical_time=0

        self.user_lost=False
        self.lock=threading.Lock()

        return
#    def handle_read_event( self ): 
#            print "received message event" 
#
#
#    def handle_write_event( self ): 
#            print "Asking for a write" 

        
    def writable(self):
        """We want to write if we have received data."""
        response = bool(self.data_to_write)
        #self.logger.debug('writable() -> %s', response)
        return response
    def readable(self):        
        #self.logger.debug('readable() -> True')        
        return True
        
    def handle_write(self):
        """Write as much as possible of the most recent message we have received."""
        data = self.data_to_write.pop()
        sent = self.send(data[:self.chunk_size])
        if sent < len(data):
            remaining = data[sent:]
            self.data.to_write.append(remaining)
        self.logger.debug('handle_write() -> (%d) "%s"', sent, data[:sent])
        if not self.writable():
            self.handle_close()

            
    def handle_expt(self):
        print "Disconned from :",self.addr
        self.close() # connection failed, shutdown

    def handle_read(self):
        global UTM
        global v
        newdata=''
#        print self.connected
#        print self.accepting
#        print self.closing
#        print self.addr
#        print self.debug
        
        """Read an incoming message from the client and put it into our outgoing queue."""
        try:
            data = self.recv(self.chunk_size)
        except:
            print "connection lost "
			
        print "yreceived data" , data,self.addr
        if data:
            try:
                                                        newdata=ast.literal_eval(data)
            except:
                                                        pass
            if newdata[0]=='CHB':
                                                        print "First Connected from" ,self.addr
                                                        ip=newdata[1]
                                                        port=newdata[2]
                                                        username=newdata[3]
                                                        recv_time=time.time()
                                                        
                                                        client_info=[ip,port,username,recv_time,v]
                                                        
                                                        print "client_info", client_info
                                                        
                                                        self.lock.acquire()     
                                                        UTM.append(client_info)
                                                        self.lock.release()
                                                        
                                                        self.v.tick()
                                                        
                                                        
                                                       
                                                        self.remoteUT=[]
                                                        for y in UTM:
                                                            self.remoteUT.append((y[0],y[1],y[2]))
                  
                                                        print "%s is added into our system" % newdata[3] 
                                                        tosend=str(('UT',self.remoteUT))
                                                        self.data_to_write.append(tosend)
     
            elif newdata[0] =='PyHB':
                                                        #print "HB is ",newdata[0]
                                                        if newdata[2]>=self.llogical_time:
                                                            self.llogical_time=newdata[2]
                                                            heartbeats_test[newdata[1]]=time.time()
        
                                                        
                                                        print "HB Connected from" , self.addr
                                                        print "Recevied PyHB",time.ctime() 
                                                        print "HB Disconnected from", self.addr,'\n'
                                                        self.close()
            #......................................Server Part.................................................                                             
            elif newdata[0] =='SPyHB':
                                                        heartbeats_test[newdata[1]]=time.time()
                                                        #newdata[2] is a UTM
                                                        #client_info=[ip,port,username,recv_time,self.vector]
    
                                                        #msg=str(('SPyHB','Server',UTM))
                                                        print "SHB Connected from" , self.addr
                                                        print "Recevied SPyHB",time.ctime() 
                                                        #print "SHB Disconnected from", self.addr,'\n'
                                                        
    #                                                    if newdata[1]!=[] and UTM!=[]:
    #                                                        for x in newdata[1]:
                                                        #print "UT is ",UTM 
                                                        
                                                        for i in newdata[2]:
                                                                    heartbeats_test[i[2]]=time.time()
                                                        #print "UT is ",UTM                 
                                                        UTM=newdata[2]   
                                                        #print "UT is ",UTM         
    #                                                    for j in UTM:
    #                                                            if j not in newdata[2]:
    #                                                                UTM.remove(j)
    #                                                                del heartbeats_test[j[2]] 
    #                                                    
                                                     
                                                        print "received peer update now",UTM,'\n'
    #                                                    for j in UTM:
    #                                                            if j not in newdata[2]:
    #                                                                UTM.remove(j)
    #                                                                del heartbeats_test[j[2]] 
    
          #------------------------------------------------------------------------------
                                                        '''
                                                        print "UT is ",UTM            
                                                        for k in newdata[2]:
                                                            for m in UTM:
                                                                
                                                                if k not in UTM:
                                                                    UTM.append(k)
                                                        print "UT is ",UTM            
                                                        for i in newdata[2]:
                                                            for x in UTM:
                                                                if i[2]==x[2]:
                                                                   heartbeats_test[i[2]]=time.time() 
                                                                   print i[2],'is added to the same' 
                                                                   for n in range(2):
                                                                       if i[4][n]>v[n]:
                                                                           v[n]=i[4][n] #vector clock is updated
                                                                           x=i # item is updated
                                                                       else:
                                                                            pass
                                                        v[1]=v[1]+1 
                                                        print "UT is ",UTM  
                                                                           
                                                        '''
                                                                    
                                                        
                                                                    
              #------------------------------------------------------------------------------
                                                         
                                            
                                                        #self.close()
            elif newdata[0] =='SSR':                    #Server Synchronization Request
                                                        print "received SSR",time.ctime()
                                                        print "SSR update is ",UTM
                                                    
    #------------------------------------------------------------------------------    
                                                        '''
                                                        for j in UTM:
                                                                if j not in newdata[1]:
                                                                    UTM.remove(j)
                                                                    del heartbeats_test[j[2]] 
                                                                    
                                                        for k in newdata[1]:
                                                                if k not in UTM:
                                                                    UTM.append(k)
    
                                                        for i in newdata[1]:
                                                            for x in UTM:
                                                                if i[2]==x[2]:
                                                                   heartbeats_test[i[2]]=time.time() 
                                                                   for n in range(2):
                                                                       if i[4][n]>v[n]:
                                                                           v[n]=i[4][n] #vector clock is updated
                                                                           x=i # item is updated
                                                                       else:
                                                                            pass
                                                        v[1]=v[1]+1   
                                                        '''
                                                        if newdata[1]!=[] and UTM==[]:
                                                            UTM=newdata[1]
                                                        else:
                                                            pass
                                                        
                                                        tosend=str(('RSSR',UTM))
                                                        print "reply the s_RSSR is" ,UTM,tosend
                                                        sent = self.send(tosend)
            elif newdata[0] =='RSSR':                    #Reply Server Synchronization Request
                                                        UTM=newdata[1]  
                                                        print "received first update now",UTM  
            elif newdata[0] =='express':                    #Reply Server Synchronization Request
                                                        UTM=newdata[1]  
                                                        print "express UT is ",UTM                                                                                        
            #self.logger.debug('handle_read() -> (%d) "%s"', len(data), data)
            #self.data_to_write.insert(0, data)
    
    def handle_close(self):
        self.logger.debug('handle_close()')
        self.close()

class Monitor():
    def __init__(self,vector):
        self.lock=threading.Lock()
        self.user_lost=False
        thread_ms= threading.Thread(target=self.getSilent)
        thread_ms.start()
       
    def getSilent(self):
        global UTM
        #print "getsilent starts"
        while True:
            lusername=''
            susername=''
            limit = time.time() - CHECK_TIMEOUT
            self.lock.acquire()
            for lusername in heartbeats_test.keys():
                if heartbeats_test[lusername]<= limit:
                    print "---------------%s get lost--------------------" %lusername
                    del heartbeats_test[lusername] 
                    self.user_lost=True  
                    susername=lusername
                    
                    if self.user_lost and susername!='':
                        #print "suername is ",susername
                        if susername!='Server':
                            #print "I am removing the UT for ",susername
                            for n in UTM:
                                if n[2]==susername:
                                    print "Lost user '%s' has been removed from UT" %n[2]
                                    UTM.remove(n)
                                    #self.v.tick()
                
                            print "Current UT is :",UTM      
                            self.remoteUT=[]      
                            for i in UTM:
                                self.remoteUT.append((i[0],i[1],i[2]))
                            self.user_lost=False
                            #print "user_lost is ",self.user_lost
                                                                
                        else:
                            pass
            self.lock. release()
         
            
            
            #print "I am checing now with lost client",time.ctime()
            time.sleep(30)
    
class EchoClient(asyncore.dispatcher):
    """Sends messages to the server and receives responses.
    """
    
    def __init__(self,):
        chunk_size=8192
        message=str('SSR',)
        self.host='127.0.0.2'
        self.port='60000'
        self.connection_state=False
        self.message = message
        self.to_send = message
        self.received_data = []
        self.chunk_size = chunk_size
        self.logger = logging.getLogger('EchoClient')
        asyncore.dispatcher.__init__(self)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connect((self.host, self.port))
        return
        
    def handle_connect(self):
        if self.connected:
            print "you are connected"
        else:
            print "you are not connected"
#         if not self.connected:
#            try: 
#                    #socket.create_connection(address, timeout, source_address)
#                    #print "We are trying connection......."
#                    self.connect((self.host, self.port))
#                    print "Connection to Backup Server is established \n"
#                    self.logger.debug('connecting to %s', (self.host, self.port))
#                    #s.connect(Server);
#                    self.connection_state=True
#            except: 
#                    print "please open the peer server firstly";
#                    self.connection_state=False
#        self.logger.debug('client_handle_connect()')
    
    def handle_close(self):
        pass
#        self.logger.debug('client_handle_close()')
#        self.close()
#        received_message = ''.join(self.received_data)
#        if received_message == self.message:
#            self.logger.debug('RECEIVED COPY OF MESSAGE')
#        else:
#            self.logger.debug('ERROR IN TRANSMISSION')
#            self.logger.debug('EXPECTED "%s"', self.message)
#            self.logger.debug('RECEIVED "%s"', received_message)
#        return
    
#    def writable(self):
#        self.logger.debug('writable() -> %s', bool(self.to_send))
#        return bool(self.to_send)

    def handle_write(self):
        if self.connected:
            self.send(self.message)
#            self.logger.debug('handle_write() -> (%d) "%s"', sent, self.to_send[:sent])
#            self.to_send = self.to_send[sent:]

    def handle_read(self):
        newdata=''
        data = self.recv(self.chunk_size)
        print "received data" , data
        try:
                                                    newdata=ast.literal_eval(data)
        except:
                                                    pass
        if newdata[0] =='SPyHB':
                                                    heartbeats_test[newdata[1]]=time.time()
                                                    print "SHB Connected from" , self.addr
                                                    print "Recevied SPyHB",time.ctime() 
                                                    print "SHB Disconnected from", self.addr,'\n'
                                                    UTM=newdata[1] 
                                                    print "received peer update now",UTM 
                                                    #self.close()
        elif newdata[0] =='SSR':                    #Server Synchronization Request
                                                    tosend=str(('RSSR',UTM))
                                                    self.data_to_write.append(tosend)
        elif newdata[0] =='RSSR':                    #Reply Server Synchronization Request
                                                    UTM=newdata[1]  
                                                    print "received first update now",UTM                                                     
        #self.logger.debug('handle_read() -> (%d) "%s"', len(data), data)
        #self.received_data.append(data)
            
    
def main():
    vector=VectorClock(2,1)
    vector.init()
    server = EchoServer(address,vector)
    monitor=Monitor(vector)
    #client = EchoClient('127.0.0.3', 60000)
    asyncore.loop()

        

if __name__ == '__main__':
    main()