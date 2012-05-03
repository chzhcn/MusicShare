from flask import Flask,url_for,render_template,request
from werkzeug import secure_filename
import cli
import threading
import os
import sys

app = Flask(__name__)
c = None

def template() :
    return render_template("welcome.html",name=c.username,music_table=c.music_table, listening_addr = c.listening_addr, is_paused = c.player.is_paused)

@app.route('/')
def index():
    return render_template('hello.html')

@app.route('/like/<int:seqno>&<ip>&<int:port>')
def like(seqno,ip,port):
    c.send_like((ip,port),seqno)
    return template()

@app.route('/remove/<int:seqno>')
def remove(seqno):
    c.remove_song(c.file_table[seqno])
    return template()

@app.route('/login', methods=['POST', 'GET'])
def login():
    print 'in login'
    name = None
    music_table={}
    print c.username
    if request.method == 'POST' and c.username == None :
        print request.form['username']
        name = request.form['username']
        c.username = name
        c.init_username()

    return template()

def dump_flags(func) :
    print func
    print 'is_playing: ', c.player.is_playing
    print 'is_paused: ', c.player.is_paused

@app.route('/login/<receiver_ip>&<int:receiver_port>&<int:song_seq_num>', methods=['POST', 'GET'])
def stream(receiver_ip, receiver_port, song_seq_num) :
    print type(receiver_ip), type(receiver_port), type(song_seq_num)
    print receiver_ip, receiver_port, song_seq_num
    # if c.player.is_playing == False :
    recv_addr = (receiver_ip, receiver_port)
    c.try_play(recv_addr, song_seq_num)
    print 'called stream'

    return template()

@app.route('/resume', methods=['POST', 'GET']) 
def resume() :
    # dump_flags('resume')
    if c.player.is_paused == True :
       c.player.resume()

    # dump_flags('resume')
    return template()

@app.route('/pause', methods=['POST', 'GET'])
def pause() :
    # dump_flags('pause')
    c.player.pause()
    # dump_flags('pause');
    return template()

@app.route('/stop', methods=['POST', 'GET'])
def stop() :
    # dump_flags('stop')
    c.player.stop()
    # dump_flags('stop')
    return template()

def refresh1():
    return template()

def refresh2():
    while True:
        refresh1()
        time.sleep(10)
        
@app.route('/refresh',methods=['POST', 'GET'])
def refresh():
    music_table={}
    if request.method == 'POST':
        f = request.files['newsong']
        print 'filename: ' + f.filename
        if f.filename != None :
            path = c.repo_path+os.sep+secure_filename(f.filename)
            f.save(path)
            c.add_song_server(path)

    return template()

@app.route('/user/<username>')
def show_user_profile(username):
    # show the user profile for that user
    return '<b>Hello %s </b>' % username
    
with app.test_request_context('/hello', method='POST'):
    # now you can do something with the request until the
    # end of the with block, such as basic assertions:
    assert request.path == '/hello'
    assert request.method == 'POST'

if __name__ == '__main__':
    global c;
    if c==None :
        c = cli.client(sys.argv[2])
    port = int(sys.argv[1])
    app.debug = True
    app.run('127.0.0.1', port)
