'''
Created on Apr 3, 2012

@author: chiz
'''

import os
from mutagen.mp3 import MP3

class Music_Info(object):
    def __init__(self, starting_counter):        
        self.song_dict = {}
        self.file_dict = {}

    def read_repo(self, starting_counter):
        repo_path = os.path.abspath("songs2/") # FIXME: path should be changed later
        song_files = os.listdir(repo_path)
        for song_file in song_files :
            starting_counter[0] += 1;
            filepath = repo_path+os.sep+song_file
            self.read_song(starting_counter[0], filepath)
        
        return self.song_dict, self.file_dict

    def read_song(self, index, filepath)
            self.file_dict[index] = filepath;
            self.song_dict[index] = Song_Info(filepath);

    def __repr__(self) :
        return str(self.song_dict)

class Song_Info(object) :
    def __init__(self, filepath) :
        # print filepath
        audio = MP3(filepath)
        self.fname = filepath
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
        return str((self.title, self.like))
