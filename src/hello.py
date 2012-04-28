from flask import Flask,url_for,render_template,request
from werkzeug import secure_filename
import cli
import threading
import os
app = Flask(__name__)
c = cli.client()

def template() :
    return render_template("welcome.html",name=c.username,music_table=c.music_table, listening_addr = c.listening_addr)

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
    name = None
    music_table={}
    if request.method == 'POST':
        print request.form['username']
        name = request.form['username']
        c.username = name
        c.init_username()

    return template()


@app.route('/login/<receiver_ip>&<int:receiver_port>&<int:song_seq_num>', methods=['POST', 'GET'])
def stream(receiver_ip, receiver_port, song_seq_num) :
    print type(receiver_ip), type(receiver_port), type(song_seq_num)
    print receiver_ip, receiver_port, song_seq_num
    if c.player.song_playing == False :
        c.send_stream((receiver_ip, receiver_port), song_seq_num)
        print 'called stream'
        # c.in_play = True

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
    app.debug = True
    app.run('127.0.0.1', 1235)
