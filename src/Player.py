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
    def __init__(self):
        self.cache_dic={}
        self.cache=Caching()
        self.cache_filepath=''
        pass
    def receiver_init(self,ip,port,song_seq_num):
        
        self.cache_filepath=self.get_plain_cachefilepath(song_seq_num)
        #print "cache location is " ,self.cache_filepath
        
        self.pipeline = gst.Pipeline("server")
        self.tcpsrc = gst.element_factory_make("tcpserversrc", "source")
        self.tcpsrc.set_property("host", str(ip))
        self.tcpsrc.set_property("port", int(port)+10)
        self.decode = gst.element_factory_make("decodebin", "decode")
        self.decode.connect("new-decoded-pad", self.new_decode_pad)
        self.convert = gst.element_factory_make("audioconvert", "convert")
        self.sink = gst.element_factory_make("alsasink", "sink")
        self.pipeline.add(self.tcpsrc,self.decode,self.convert,self.sink)
        gst.element_link_many(self.tcpsrc,self.decode)
        gst.element_link_many(self.convert,self.sink) 
        
        
        self.filepipeline = gst.Pipeline("fileserver")
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
        

        self.song_playing=True
        self.pipeline.set_state(gst.STATE_PLAYING) 
        self.filepipeline.set_state(gst.STATE_PLAYING)

       
        
        self.thread_song_play=threading.Thread(target=self.song_loop)
        self.thread_song_play.start()
        
        
        self.thread_caching_song=threading.Thread(target=self.cache_song,args=(self.cache_filepath,song_seq_num,))
        self.thread_caching_song.start()
   
   
        self.bus = self.pipeline.get_bus()
        self.bus.enable_sync_message_emission()
        self.bus.add_signal_watch()
        self.bus.connect('message::tag', self.on_tag)
        

    def sender_init(self,ip,port,filepath):

        
        self.pipeline = gst.Pipeline("client")
        self.src = gst.element_factory_make("filesrc", "source")
        self.src.set_property("location", filepath)
        self.pipeline.add(self.src)
        self.client = gst.element_factory_make("tcpclientsink", "client")
        self.pipeline.add(self.client)
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

        
        time.sleep(2)
        self.pipeline.set_state(gst.STATE_PLAYING)
        self.pipeline1.set_state(gst.STATE_PLAYING)
        
        

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
        while self.song_playing:
            time.sleep(1)
            
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
        self.song_playing=True
        self.thread_song_play=threading.Thread(target=self.song_loop)
        self.thread_song_play.start()   
        
    def runloop(self):
        print "I am running" 
        d = IODriver(self.run)
        print "I am running too" 
        self.loop.run()
        
    def on_message(self, bus, message): 
        if message.type == gst.MESSAGE_EOS: 
            # End of Stream 
            self.player.set_state(gst.STATE_NULL) 
        elif message.type == gst.MESSAGE_ERROR: 
            self.player.set_state(gst.STATE_NULL) 
            (err, debug) = message.parse_error() 
            print "Error: %s" % err, debug
            
    def on_tag(self,bus, msg):
        taglist = msg.parse_tag()
        print 'on_tag:'
        for key in taglist.keys():
            print '\t%s = %s' % (key, taglist[key])
            
    def resume(self):
        self.pipeline.set_state(gst.STATE_PLAYING) 
           
    def stop(self):
        self.pipeline.set_state(gst.STATE_NULL)
        self.song_playing=False
        
    def pause(self):
        self.pipeline.set_state(gst.STATE_PAUSED)
        
    def replay(self):
        pass
             
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
   
    def new_decode_pad(self,dbin, pad, islast):
            pad.link(self.convert.get_pad("sink")) 
            
    def new_decode_pad_file(self,dbin, pad, islast):
            pad.link(self.convert.get_pad("sink"))        
            






    