'''
Created on Apr 22, 2012

@author: yong
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


import gobject
gobject.threads_init()
import pygst
pygst.require('0.10')
import gst
import thread

from Caching import Caching


class Player():
    def __init__(self,client):
        self.client=client
        self.cache_dic={}
        self.cache=Caching()
        self.cache_filepath=''
        self.is_playing=False
        self.is_sending=False
        self.port_list=[]
        pass
    def receiver_init(self,ip,port,song_seq_num):
        
        self.cache_filepath=self.get_plain_cachefilepath(song_seq_num)
        #print "cache location is " ,self.cache_filepath
        
        self.pipeline = gst.Pipeline("server")
        self.tcpsrc = gst.element_factory_make("tcpserversrc", "source")
        self.tcpsrc.set_property("host", str(ip))
        self.tcpsrc.set_property("port", int(port)+10)  #50001+10=50011
        self.decode = gst.element_factory_make("decodebin", "decode")
        self.decode.connect("new-decoded-pad", self.new_decode_pad)
        self.convert = gst.element_factory_make("audioconvert", "convert")
        self.sink = gst.element_factory_make("alsasink", "sink")
        self.pipeline.add(self.tcpsrc,self.decode,self.convert,self.sink)
        gst.element_link_many(self.tcpsrc,self.decode)
        gst.element_link_many(self.convert,self.sink) 
        


        
        self.filepipeline = gst.Pipeline("fileserver") #50001+11=50012
        self.tcpsrc1 = gst.element_factory_make("tcpserversrc", "source1")
        self.tcpsrc1.set_property("host", str(ip))
        self.tcpsrc1.set_property("port", int(port)+11)  
        self.decode1 = gst.element_factory_make("decodebin", "decode1")
        self.decode1.connect("new-decoded-pad", self.new_decode_pad_file)
        self.convert1 = gst.element_factory_make("audioconvert", "convert1")
        self.filesink = gst.element_factory_make("filesink")
        self.filesink.set_property("location", self.cache_filepath) 
        self.filepipeline.add(self.tcpsrc1,self.filesink)         
        gst.element_link_many(self.tcpsrc1,self.filesink)
        print "receive filesink address is ",str(ip),':',int(port)+11
        
        
       
        
        self.pipeline.set_state(gst.STATE_PLAYING) 
        self.filepipeline.set_state(gst.STATE_PLAYING)
        self.is_playing = True
        
        gobject.threads_init()
        
        self.bus = self.pipeline.get_bus()
        self.bus.add_signal_watch()
        self.bus.connect("message", self.message_handler)
        
        print "I am prepare to play"
        thread.start_new_thread(self.song_loop, ())
#        self.thread_song_play=threading.Thread(target=self.song_loop)
#        self.thread_song_play.start()
        
        self.thread_caching_song=threading.Thread(target=self.cache_song,args=(self.cache_filepath,song_seq_num,))
        self.thread_caching_song.start()
        
    def message_handler(self, bus, message):
        msgType = message.type
#        print "+++++++++++++++++msg is forever",msgType
#        print self.pipeline.get_state()
#        print self.pipeline.continue_state()
#        print "self.pipeline.is_locked_state()",self.pipeline.is_locked_state()
#        print "self.pipeline.is_locked_state()",self.sink.is_locked_state()
#        print "self.pipeline.is_locked_state()",self.tcpsrc.is_locked_state()
#        print self.pipeline.freeze_notify()
        if msgType == gst.MESSAGE_ERROR:
            self.pipeline.set_state(gst.STATE_NULL)
            self.filepipeline.set_state(gst.STATE_NULL)
            self.is_playing = False
            self.evt_loop.quit()
            print "\n Unable to play audio. Error: ", message.parse_error()
        elif msgType == gst.MESSAGE_EOS:
            self.evt_loop.quit()
            self.pipeline.set_state(gst.STATE_NULL)
            self.filepipeline.set_state(gst.STATE_NULL)
            self.is_playing = False
            print "the audio is over"
            
#        elif msgType == gst.MESSAGE_STATE_CHANGED:
#                oldstate, newstate, pending = message.parse_state_changed()             
#                print("MESSAGE_STATE_CHANGED: %s --> %s" % (oldstate.value_nick, newstate.value_nick))
                

    def sender_init(self,ip,port,filepath):
        
        self.check_sending()
#        
#        print "I want to send something"
#        
#        print self.port_list
#        if port in self.port_list:
#            self.port_list.remove(port)
#
#        else:
#            self.port_list.append(port)

        
        self.sender_pipeline = gst.Pipeline("client")
        self.src = gst.element_factory_make("filesrc", "source")
        self.src.set_property("location", filepath)
        self.sender_pipeline.add(self.src)
        self.client = gst.element_factory_make("tcpclientsink", "client")
        self.sender_pipeline.add(self.client)
        self.client.set_property("host", str(ip))
        self.client.set_property("port", int(port)+10)
        self.src.link(self.client)
        
        self.pipeline1 = gst.Pipeline("fileclient")
        self.src1 = gst.element_factory_make("filesrc", "source1")
        self.src1.set_property("location", filepath)
        self.pipeline1.add(self.src1)
        self.client1 = gst.element_factory_make("tcpclientsink", "client1")
        self.pipeline1.add(self.client1)
        self.client1.set_property("host", str(ip))
        self.client1.set_property("port", int(port)+11)
        self.src1.link(self.client1)
        print "send filesink address is ",str(ip),':',int(port)+11
        
        bus = self.sender_pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self.sender_message_handler)
         
        print "I am beginning to send now"
        time.sleep(1)
        
        self.sender_pipeline.set_state(gst.STATE_PLAYING) 
        self.is_sending=True
        print self.sender_pipeline.get_state();
        self.pipeline1.set_state(gst.STATE_PLAYING)
        thread.start_new_thread(self.song_loop, ())
        
    def sender_message_handler(self, bus, message):
        msgType = message.type
        #print "msg is forever",msgType
        if msgType == gst.MESSAGE_ERROR:
            self.sender_pipeline.set_state(gst.STATE_NULL)
            print "\n Unable to send audio for streaming. Error: ", message.parse_error()
        elif msgType == gst.MESSAGE_EOS:
            self.sender_pipeline.set_state(gst.STATE_NULL)
            self.evt_loop.quit()
            
    def stop_send(self):
        self.sender_pipeline.set_state(gst.STATE_NULL)
        self.evt_loop.quit()
        
    def check_sending(self):
        if self.is_sending:
            self.stop_send()
            self.is_sending=False
        else:
            print "You pass the check"
        
        

    def check_cache_dic(self,song_num):
        if song_num in self.cache_dic.keys():
            self.play_locally(song_num)
            return True
        else:
            return False
        
    def play_locally(self,song_num):
         filepath=self.traverse_cache_dic(song_num)
         #play_path=self.cache.decrypt_file(filepath)
         self.play(filepath)
        
    def traverse_cache_dic(self,song_num):
          for key in self.cache_dic.keys():
              if key==song_num:
                  return self.cache_dic[key]
  
    def song_loop(self): 
            self.evt_loop = gobject.MainLoop()
            self.evt_loop.run()
            #print "loop finished"
           
    def get_plain_cachefilepath(self,song_seq_num):
        path='/tmp/'    
        if os.path.exists(path):
            filepath=path+str(song_seq_num)
        else:
            try:
                os.makedirs(path)
            except:
                print "Directories cannot be created"
            filepath=path+str(song_seq_num)
        return filepath
    
    def new_decode_pad(self,dbin, pad, islast):
            pad.link(self.convert.get_pad("sink")) 
            
    def new_decode_pad_file(self,dbin, pad, islast):
            pad.link(self.convert.get_pad("sink"))   
        
        
    def cache_song(self,filepath,song_seq_num):
        compare_size=0
        size=0
        self.file_stream=False
        while True: 
            #print "I am checking cache now"   
            compare_size=size
            try:
                size=os.path.getsize(filepath)
            except:
                pass
                
            if size-compare_size==0 and size!=0:        
                self.file_stream=True
            else:
                pass
            
            if self.file_stream:
                 #............For temp file...............
                temp_filepath=self.cache.temp_file(filepath)
                self.file_stream=False
                self.cache_dic[song_seq_num]=temp_filepath
                print "Caching is finished :",self.cache_dic
                os.remove(filepath)
                break
            time.sleep(1)
            
                #............For encrypted file...............
                
#                self.cache.encrypt_file(filepath)
#                print "Caching is finished"
#                self.file_stream=False
#                self.cache_dic[song_seq_num]=os.path.splitext(filepath)[0]+'.enc'
#                print self.cache_dic
#                os.remove(filepath)
#                break          
                #decrypt_file(key,en_filepath)
                #print "dencryption is finished"

           
            
    def play(self,filepath):
        commandpath="filesrc location=\"%s\" ! mad ! audioconvert ! alsasink"%filepath
        self.pipeline = gst.parse_launch(commandpath)   
        self.pipeline.set_state(gst.STATE_PLAYING)
        print "Play the song locally" 
        self.is_playing=True
        self.thread_song_play=threading.Thread(target=self.song_loop)
        self.thread_song_play.start()   
                    
    def resume(self):
        self.pipeline.set_state(gst.STATE_PLAYING) 
           
    def stop(self):
        self.pipeline.set_state(gst.STATE_NULL)
        self.evt_loop.quit()
        
    def pause(self):
        self.pipeline.set_state(gst.STATE_PAUSED)
        
    def replay(self):
        pass
 #.........................For test only..........................            
    def seek(self):
        self.position = (self.pipeline.query_position(gst.FORMAT_TIME,None)[0])/gst.SECOND
        dur_int = self.pipeline.query_duration(gst.FORMAT_TIME, None)[0]
        print "dur_time",dur_int
        print "pos is ",self.position
        print "last time",self.pipeline.get_last_stream_time()
        print "last time",self.pipeline.get_last_stream_time()
        self.pipeline.seek_simple(gst.FORMAT_TIME,gst.SEEK_FLAG_FLUSH,(self.position-5))
        self.pipeline.set_state(gst.STATE_PAUSED)
        self.pipeline.set_new_stream_time(self.position-5)
        print "\n starting playback in 2 seconds.."
        time.sleep(2)
        self.pipeline.set_state(gst.STATE_PLAYING)
   

    def runloop(self):
        print "I am running" 
        d = IODriver(self.run)
        print "I am running too" 
        self.loop.run()
        
    def play_loop(self):
        while self.is_playing:
                time.sleep(1)
        print "loop leaves"    
        self.evt_loop.quit()  
            
    def on_tag(self,bus, msg):
        taglist = msg.parse_tag()
        print 'on_tag:'
        for key in taglist.keys():
            print '\t%s = %s' % (key, taglist[key])     
            






    