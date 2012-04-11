'''
Created on Apr 3, 2012

@author: chiz
'''

import os
from mutagen.mp3 import MP3

class Music_Info(object):
    def __init__(self, starting_counter):        
        self.song_dict = {}
        self.repo_path = os.path.abspath("songs/") # FIXME: path should be changed later
        song_files = os.listdir(self.repo_path)
        for song_file in song_files :
            starting_counter[0] += 1;
            self.song_dict[starting_counter[0]] = Song_Info(self.repo_path+'/'+song_file);
            # print song_file
        
        print self.song_dict
    def __repr__(self) :
        # print "inside __repr__"
        return str(self.song_dict)

    # def __str__(self) :
    #     print "inside __str__"
    #     return str(self.song_dict)

        
class Song_Info(object) :
    def __init__(self, filename) :
        # print filename
        audio = MP3(filename)
        self.fname = filename
        self.title = self.try_get_key(audio, 'TIT2')
        self.artist = self.try_get_key(audio, 'TPE1')
        self.album = self.try_get_key(audio, 'TALB')
        self.mtype = self.try_get_key(audio, 'TCON')
        self.year = self.try_get_key(audio, 'TDRC')
        self.length = audio.info.length;
        self.like = 0;

    def try_get_key(self, audio, key) :
        if key in audio.keys() :
            return audio[key]
        else :
            return None;
        
    def __repr__(self) :
        # print "inside song_info __repr"
        # return str((self.fname, self.title, self.artist, self.album, self.mtype, self.year, self.length))
        return str((self.title))




#class Session_Info(dict) :
#    def __init__(self, name = None):
#        self["username"] = name
