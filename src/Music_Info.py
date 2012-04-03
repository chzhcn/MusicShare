'''
Created on Apr 3, 2012

@author: chiz
'''

import time

class Music_Info:
    def __init__(self, username):
        self.username = username
        # last_recv_time for self is meaningless
        self.app_start_time = self.last_recv_time = time.time()
        self.logical_clk_time = 0;
        self.song_list = []
        # FIXME: parse music song list
    
