from flask import Flask,url_for,render_template,request
import cli
import threading
app = Flask(__name__)
c = cli.client()
@app.route('/')
def index():
    return render_template('hello.html')

@app.route('/login', methods=['POST', 'GET'])
def login():
    name = None
    music_table={}
    if request.method == 'POST':
        print request.form['username']
        name = request.form['username']
        c.username = name
        c.init_username()

    return render_template("welcome.html",name=c.username,music_table=c.music_table)

def refresh1():
    return render_template("welcome.html",name=c.username,music_table=c.music_table)

def refresh2():
    while True:
        refresh1()
        time.sleep(10)
        
@app.route('/refresh',methods=['POST', 'GET'])
def refresh():
    music_table={}
    if request.method == 'POST':
        return render_template("welcome.html",name=c.username,music_table=c.music_table)
    else:
        return render_template("welcome.html",name=c.username,music_table=c.music_table)
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
    app.run('127.0.0.1',1234)
