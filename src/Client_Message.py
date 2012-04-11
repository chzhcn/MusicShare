'''
Created on Apr 5, 2012

@author: chiz
'''

class Client_Message(object) :
    def __init__(self, m_type, sender_listening_addr, username, app_start_time, logical_clk_time):
        self.m_type = m_type
        self.sender_listening_addr = sender_listening_addr
        self.username = username
        self.app_start_time = app_start_time
        self.logical_clk_time = logical_clk_time

class Client_Music_Message(Client_Message) :

    def __init__(self, m_type, sender_listening_addr, username, app_start_time, logical_clk_time, music_info):
        super(Client_Music_Message, self).__init__(m_type, sender_listening_addr, username, app_start_time, logical_clk_time)
        self.music_info = music_info

class Client_Like_Message(Client_Message):
    def __init__(self,m_type,sender_listening_addr,username,app_start_time,logical_clk_time, receiver_app_start_time,song_seq_no ):
        super(Client_Like_Message,self).__init__(m_type,sender_listening_addr,username,app_start_time,logical_clk_time)
        self.receiver_app_start_time = receiver_app_start_time
        self.song_seq_no = song_seq_no
