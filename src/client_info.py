'''
Created on Apr 3, 2012

@author: chiz
'''

import os
from mutagen.mp3 import MP3

class Music_Info(object):
    def __init__(self):
        self.song_dict = {}
        self.file_dict = {}

    def read_repo(self, starting_counter, repo_path):
        song_files = os.listdir(repo_path)
        for song_file in song_files :
            starting_counter[0] += 1;
            filepath = repo_path+os.sep+song_file
            self.read_song(self.song_dict, self.file_dict, starting_counter[0], filepath)
        
        return self.song_dict, self.file_dict

    def read_song(self, song_dict, file_dict, index, filepath) :
        song_dict[index] = Song_Info(filepath);
        file_dict[index] = filepath;

    def add_cache(self, file_dict, index, filepath) :
        file_dict[index] = filepath;

    def check_song_exists(self,song_dict,filepath):
        new_song_title = Song_Info(filepath).title
        for index, song_info in song_dict.items():
            if(song_info.title == new_song_title):
                return True
        return False

    def remove_song(self,song_dict,file_dict,filepath):
        old_song_title = Song_Info(filepath).title
        for index, song_info in song_dict.items():
            if(song_info.title == old_song_title):
                del song_dict[index]
                del file_dict[index]
                #remove from repo folder
                os.remove(filepath)

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
        self.rep_dict = {}

    def add_rep(self, rep_addr, rep_seq) :
        self.rep_dict[rep_addr]= rep_seq

    def try_get_key(self, audio, key) :
        if key in audio.keys() :
            return audio[key]
        else :
            return None;
        
    def __repr__(self) :
        return str((self.title, self.like, self.rep_dict))
