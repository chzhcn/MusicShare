from flask import Flask,url_for,render_template
import cli
app = Flask(__name__)

@app.route('/')
def index():
    return 'Index Page'
    
@app.route('/hello/')
@app.route('/hello/<name>')
def hello(name=None):
    cli.main()
    return render_template('hello.html', name=name)
    
@app.route('/user/<username>')
def show_user_profile(username):
    # show the user profile for that user
    return '<b>Hello %s </b>' % username
    
#with app.test_request_context():
#   print url_for('show_user_profile', username='Kanchan Matkar')

if __name__ == '__main__':
    app.run(debug=True)
    
    