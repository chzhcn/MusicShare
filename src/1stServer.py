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
CHECK_TIMEOUT=15
address = ('127.0.0.1', 12345) # let the kernel give us a port
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
    
    def __init__(self, address,v,client):
        self.v=v
        self.client=client
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
        EchoHandler(sock=client_info[0],vector=self.v,client=self.client)
        return
    
    def handle_close(self):
        self.logger.debug('handle_close()')
        self.close()
        return

class EchoHandler(asyncore.dispatcher):
    """Handles echoing messages from a single client.
    """
    
    def __init__(self, sock, vector,client):
       
        self.chunk_size = 8192
        self.v=vector   # vector object
        self.client=client
#        self.v=vector
#        print "My vector from Echohandler is :", self.v.toString
        self.logger = logging.getLogger('EchoHandler%s' % str(sock.getsockname()))
        asyncore.dispatcher.__init__(self, sock=sock)
        self.data_to_write = []
        self.vector=[0,0]
        self.UT_enable=False
        self.v=VectorClock(2,0)

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
#
#    def selfv(self,vector):
#        self.v=vector
        print self.v.toString
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

                                                        if self.client.connected:                           
                                                            self.client.express_send()
                                                       
                                                        self.remoteUT=[]
                                                        for y in UTM:
                                                            self.remoteUT.append((y[0],y[1],y[2]))
                  
                                                        print "%s is added into our system" % newdata[3] 
                                                        tosend=str(('UT',self.remoteUT))
                                                        self.data_to_write.append(tosend)
                                                       
                                                        
                                                        
     
            elif newdata[0] =='PyHB':
    #                                                    if newdata[2]>=self.llogical_time:
    #                                                        self.llogical_time=newdata[2]
                                                            
                                                        heartbeats_test[newdata[1]]=time.time()
                                                            
                                                    
    #                                                    for s in UTM:
    #                                                        if s[2]==newdata[1]:
    #                                                            s[3]=time.time()
                                                
                                                        print "HB Connected from" , self.addr
                                                        print "Recevied PyHB",time.ctime() 
                                                        print "HB Disconnected from", self.addr,'\n'
                                                        self.close()
            #......................................Server Part.................................................                                             
            elif newdata[0] =='SPyHB':
                                                        heartbeats_test[newdata[1]]=time.time()
                                                        
                                                        for j in UTM:
                                                                if j not in newdata[2]:
                                                                    UTM.remove(j)
                                                                    del heartbeats_test[j[2]] 
                                                                    
                                                        for k in newdata[2]:
                                                                if k not in UTM:
                                                                    UTM.append(k)
    
                                                        for i in newdata[2]:
                                                            for x in UTM:
                                                                if i[2]==x[2]:
                                                                    heartbeats_test[i[2]]=time.time() 
                                                                    for n in range(2):
                                                                        if i[4][n]>v[n]:
                                                                            v[n]=i[4][n] #vector clock is updated
                                                                            x=i # item is updated
                                                                        else:
                                                                            pass
                                                        v[0]=v[0]+1   
                                                                       
                                                        print self.v.toString()
                                                        print "SHB Connected from" , self.addr
                                                        print "Recevied SPyHB",time.ctime() 
                                                        print "SHB Disconnected from", self.addr,'\n'
                                                        #UTM=newdata[1] 
                                                        print "received peer update now",UTM 
                                                        #self.close()
            elif newdata[0] =='SSR':                    #Server Synchronization Request
                                                        tosend=str(('RSSR',UTM))
                                                        self.data_to_write.append(tosend)
            elif newdata[0] =='RSSR':                    #Reply Server Synchronization Request
                                                        UTM=newdata[1]  
                                                        print "received first update now",UTM                                         
            #self.logger.debug('handle_read() -> (%d) "%s"', len(data), data)
            #self.data_to_write.insert(0, data)
        
    def handle_close(self):
        self.logger.debug('handle_close()')
        self.close()

class Monitor():
    def __init__(self,vector):
        self.v=vector
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
                                    
                            if self.client.connected:                           
                                    self.client.express_send()
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
    
    def __init__(self,v):
        global UTM
        self.chunk_size=8192
        self.message=str(('SSR',UTM))
        self.host='127.0.0.1'
        self.port=12347
        self.connection_state=False
        self.fail_num=0
        self.connection_state=False
#        self.v=VectorClock(2,0)
        self.v=v
        #print "My vector from EchoClient is ",self.v.toString()
        
#        self.message = message
#        self.to_send = message
        self.received_data = []
        #elf.chunk_size = chunk_size
        self.logger = logging.getLogger('EchoClient')
        self.data_to_write=[]
        
        self.hb_event=threading.Event()
        self.thread_server_HB = threading.Thread(target=self.send_hb)
        self.thread_server_HB.start()
        
        asyncore.dispatcher.__init__(self)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connect((self.host, self.port))
        self.data_to_write.append(self.message)
        #self.v.sendAction()
        return

    def handle_expt(self):
        print "My God"
        
#    def handle_connect_event(self):
#        self.data_to_write.append(self.message)
##        msg=str(('SPyHB','Server',UTM))
##        self.send(msg)
##        time.sleep(30)
        
#        pass
    def express_send(self):
        msg=str(('express',UTM))
        self.send(msg)


    def send_hb(self):
        global UTM
        while True:
            self.hb_event.wait()
            print "SPyHB is sent",time.ctime()
            msg=str(('SPyHB','Server',UTM))
            #print "current v is :",v
            self.send(msg)
            if self.connected:
                heartbeats_test['Server']=time.time()
            time.sleep(10)
            
    def handle_connect(self):
        print "client connected"
        self.logger.debug('client_handle_connect()')

        
    
    def handle_close(self):
        if self.connected:
            print "self.connected",self.connected
            self.logger.debug('client_handle_close()')
            self.logger.debug('Network Error')
            self.close()
#            print "self.connected",self.connected
#            self.hb_event.clear()
#            while not self.connected:
#                try:   
#                    self.connect((self.host, self.port))
#                except:
#                    print "I lost peer ",time.ctime()
#                time.sleep(2)    
#          
        else:
            self.fail_num=self.fail_num+1
            try:
                self.connect((self.host, self.port))
            except:
                print "I lost",time.ctime()
                #self.hb_event.clear()
            #time.sleep(2)   
                
        return


    
#    def writable(self):
#        self.logger.debug('writable() -> %s', bool(self.to_send))
#        return bool(self.to_send)
    def writable(self):
        """We want to write if we have received data."""
        response = bool(self.data_to_write)
        #self.logger.debug('writable() -> %s', response)
        return response

    
    def handle_write(self):
        data = self.data_to_write.pop()
        sent = self.send(data[:self.chunk_size])
        if sent < len(data):
            remaining = data[sent:]
            self.data.to_write.append(remaining)
        self.logger.debug('handle_write() -> (%d) "%s"', sent, data[:sent])
        return
#        if not self.writable():
#            self.handle_close()
#            self.logger.debug('handle_write() -> (%d) "%s"', sent, self.to_send[:sent])
#            self.to_send = self.to_send[sent:]

#    def readable(self):        
#        read_enable=bool(self.recv(self.chunk_size))  
#        self.logger.debug('readable() -> %s'% read_enable) 
#        return read_enable
    def handle_read(self):
        global UTM
        newdata=''
        data = self.recv(self.chunk_size)
        if data:
            print "xreceived data" , data
            
            try:
                                                        newdata=ast.literal_eval(data)
            except:
                                                        pass
            if newdata[0] =='SPyHB':
                                                        heartbeats_test[newdata[1]]=time.time()
                                                        print "SHB Connected from" , self.addr
                                                        print "Recevied SPyHB",time.ctime() 
                                                        print "SHB Disconnected from", self.addr,'\n'
                                                        UTM=newdata[2] 
                                                        print "SHB received peer update now",UTM 
                                                        #self.close()
            elif newdata[0] =='SSR':                    #Server Synchronization Request
                                                        tosend=str(('RSSR',UTM))
                                                        self.data_to_write.append(tosend)
                                                        
            elif newdata[0] =='RSSR':                    #Reply Server Synchronization Request
                       
                                                        if UTM==[] and newdata[1]==[]:
                                                            print "Both UT are empty,do nothing"       
                                                        elif UTM!=[] and newdata[1]==[]:
                                                            print "Local UT is not empty, the update UT is empty,do nothing"                                                    
                                                        elif UTM==[] and newdata[1]!=[] :
                                                            UTM=newdata[1]
                                                            for i in newdata[1]:
                                                                print i[2],'is added into heartbeats_test'
                                                                heartbeats_test[i[2]]=time.time()
                                                            print "RSSR is",newdata
                                                            print "UT after RSSR is ", UTM
                                                        elif UTM!=[] and newdata[1]!=[]:
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
                                                                v[0]=v[0]+1  

                                                            
                                                        #print "received first update now",UTM  
                                                        self.hb_event.set()  
                                             
        return                                               
        #self.logger.debug('handle_read() -> (%d) "%s"', len(data), data)
        #self.received_data.append(data)

            
    
def main():
    vector=VectorClock(2,0)
    vector.init()
    client = EchoClient(vector)

    server = EchoServer(address,vector,client)
    monitor=Monitor(vector)
    
    asyncore.loop()

        

if __name__ == '__main__':
    main()