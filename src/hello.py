from flask import Flask,url_for,render_template,request
from werkzeug import secure_filename
import cli
import threading
import os
app = Flask(__name__)
c = cli.client()

def template(top="False",sorted_list=[]) :
    return render_template("welcome.html",name=c.username,music_table=c.music_table, listening_addr = c.listening_addr,sorted_list=sorted_list,top_ten=top)

@app.route('/')
def index():
    return render_template('hello.html')

@app.route('/like/<int:seqno>&<ip>&<int:port>&<top>')
def like(seqno,ip,port,top):
    c.send_like((ip,port),seqno)
    if(top=="True"):
	sorted_list = c.top_ten()
    	return template(top,sorted_list)
    else:
        return template()

@app.route('/remove/<int:seqno>&<top>')
def remove(seqno,top):
    c.remove_song(c.file_table[seqno])
    if(top=="True"):
	sorted_list = c.top_ten()
    	return template(top,sorted_list)
    else:
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

@app.route('/stream/<receiver_ip>&<int:receiver_port>&<int:song_seq_num>&<top>', methods=['POST', 'GET'])
def stream(receiver_ip, receiver_port, song_seq_num,top) :
    print type(receiver_ip), type(receiver_port), type(song_seq_num)
    print receiver_ip, receiver_port, song_seq_num
    if c.player.is_playing == False :
        recv_addr = (receiver_ip, receiver_port)
        c.try_stream(recv_addr, song_seq_num)
        print 'called stream'
        # c.in_play = True
    if(top=="True"):
	sorted_list = c.top_ten()
    	return template(top,sorted_list)
    else:
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


@app.route('/top10')
def top10():
    sorted_list=[]
    sorted_list=c.top_ten()
    return render_template("welcome.html",name=c.username,music_table=c.music_table, listening_addr = c.listening_addr,sorted_list=sorted_list,top_ten="True")

with app.test_request_context('/hello', method='POST'):
    # now you can do something with the request until the
    # end of the with block, such as basic assertions:
    assert request.path == '/hello'
    assert request.method == 'POST'

if __name__ == '__main__':
    app.debug = True
    app.run('127.0.0.1', 1234)
