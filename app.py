import os
from flask import Flask, redirect,request, url_for
from flask import render_template
from flask_sqlalchemy import SQLAlchemy
from flask import flash
from sqlalchemy.sql import func
from flask_login import UserMixin
from flask_login import current_user,login_user,logout_user
from flask_login import LoginManager,login_required
from werkzeug.security import generate_password_hash,check_password_hash
#
from flask_socketio import SocketIO,emit
#
app = Flask(__name__)
socketio = SocketIO(app)  

uri = os.getenv("DATABASE_URL")  # or other relevant config var
if uri.startswith("postgres://"):
    uri = uri.replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_DATABASE_URI'] = uri

# app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///posts.db'

app.config['SECRET_KEY'] = 'remind me to change this later'

db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))

# Models
class User(db.Model,UserMixin):
    id = db.Column(db.Integer,primary_key=True)
    username = db.Column(db.String(150),nullable=False,unique=True)
    password = db.Column(db.String(150),nullable=False)
    date_created = db.Column(db.DateTime(timezone=True),default=func.now())
    posts = db.relationship('blog_post',backref='user',passive_deletes=True)
    comments = db.relationship('comment',backref='user',passive_deletes=True)

class blog_post(db.Model):
    id = db.Column(db.Integer,primary_key=True)
    title = db.Column(db.String(100),nullable=False)
    content = db.Column(db.Text,nullable=False)
    posted_by = db.Column(db.String(20),nullable=True) #,default='N/A'
    posted_on = db.Column(db.DateTime(timezone=True),nullable=False,default=func.now())
    author_id = db.Column(db.Integer,db.ForeignKey('user.id',ondelete='CASCADE')
    ,nullable=False) 
    comments = db.relationship('comment',backref='blog_post',passive_deletes=True)

class comment(db.Model):
    id = db.Column(db.Integer,primary_key=True)
    text = db.Column(db.Text,nullable=False)
    created_time = db.Column(db.DateTime(timezone=True),nullable=False,default=func.now())
    blog_id = db.Column(db.Integer,db.ForeignKey('blog_post.id',ondelete='CASCADE'),
    nullable=False)
    author_id = db.Column(db.Integer,db.ForeignKey('user.id',ondelete='CASCADE'),
    nullable=False) 

#
@app.route('/door',methods=['GET','POST'])
@login_required
def door():
    if request.method == 'POST':
        face = request.form.get('face')
        if not face:
            flash('Please choose a emoji',category='error')
            return redirect('/door')
        else:
            return redirect('/room/'+face)
    else:
        global total_users
        return render_template('door.html',user=current_user,total_online=total_users)

@app.route('/room/<face>')
def room(face):
    return render_template('room2.html',user=current_user,face=face)

@socketio.on("message")
def handleMessage(data):
    emit('new_message',data,broadcast=True)

total_users = 0

@socketio.on('connect')
def test_connect():
    global total_users 
    total_users += 1

@socketio.on('disconnect')
def test_disconnect():
    global total_users
    total_users -= 1
#

@app.route('/')
def welcome():
    return redirect('/posts')

@app.route('/login',methods=['GET','POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('Password')
        
        user = User.query.filter_by(username=username).first()
        
        if user:
            pass_hash = user.password
            if check_password_hash(pass_hash,password):
                login_user(user,remember=True)
                flash('logged in',category='success')
                return redirect('/posts')
            else:
                flash('Password is wrong',category='error')
        else:
            flash('Account does not exists',category='error')
    return render_template('login.html',user=current_user)

@app.route('/register',methods=['GET','POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password1 = request.form.get('Password1')
        password2 = request.form.get('Password2')
        user_exists = User.query.filter_by(username=username).first()
        if user_exists:
            flash('Username already exists',category='error')
        elif password1!=password2:
            flash('Passwords do not match',category='error')
        elif len(password1)<4:
            flash('Password too short',category='error')
        else:
            new_user = User(username=username,
                password=generate_password_hash(password1))
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user,remember=True)
            flash('user created',category='success')
            return redirect('/posts')
    return render_template('registration.html',user=current_user)

@app.route('/posts/new',methods=['GET','POST'])
@login_required
def new_post():
    if request.method == 'POST':
        post_title = request.form['title']
        post_content = request.form['post']
        post_author = current_user.username
        anonym =  request.form.get('anonymous')

        if post_content == '':
            flash('Post Content is empty',category='error')
            return redirect(url_for('new_post'))
        elif post_title == '':
            flash('Post Title is empty',category='error')
            return redirect(url_for('new_post'))
        else:
            if anonym:
                post_author=''
            new_post = blog_post(title=post_title,content=post_content,
            posted_by=post_author,author_id=current_user.id)
            
            db.session.add(new_post)
            db.session.commit()
            return redirect('/posts')
    else:
        return render_template('new_post.html',user=current_user)

@app.route('/posts',methods=['GET','POST'])
@login_required
def posts():
    if request.method == 'POST':
        post_title = request.form['title']
        post_content = request.form['post']
        post_author = current_user.username
        anonym =  request.form.get('anonymous')

        if post_content == '':
            flash('Post Content is empty',category='error')
            return redirect(url_for('new_post'))
        elif post_title == '':
            flash('Post Title is empty',category='error')
            return redirect(url_for('new_post'))
        else:
            if anonym:
                post_author=''
            new_post = blog_post(title=post_title,content=post_content,
            posted_by=post_author,author_id=current_user.id)
            
            db.session.add(new_post)
            db.session.commit()
            return redirect('/posts')
    else:
        all_posts = blog_post.query.order_by(blog_post.posted_on.desc()).all()
        return render_template('posts.html',posts=all_posts,user=current_user)

@app.route('/admin')
def admin():
    all_posts = blog_post.query.order_by(blog_post.posted_on.desc()).all()
    return render_template('admin.html',posts=all_posts,user=current_user)

@app.route('/posts/edit/<int:id>',methods=['GET','POST'])
@login_required
def edit(id):
    to_edit = blog_post.query.get_or_404(id)
    if request.method == 'POST':
        to_edit.title = request.form['title']
        anonym = request.form.get('anonymous')
        if not anonym:
            to_edit.posted_by = current_user.username
        else:
            to_edit.posted_by = ''
        to_edit.content = request.form['post']
        db.session.commit()
        return redirect('/posts')
    else:
        return render_template('edit.html',post=to_edit,user=current_user)

@app.route('/posts/delete/<int:id>')
def delete(id):
    to_delete = blog_post.query.get_or_404(id)
    db.session.delete(to_delete)
    db.session.commit()
    return redirect('/posts')

@app.route('/read_post/<id>')
@login_required
def read_post(id):
    post = blog_post.query.filter_by(id=id).first()
    return render_template('read_post.html',post=post,user=current_user)

@app.route('/create-comment/<id>',methods=['GET','POST'])
@login_required
def create_comment(id):
    text = request.form.get('text')
    com = comment(blog_id=id,text=text,author_id=current_user.id) 
    db.session.add(com)
    db.session.commit()
    return redirect('/read_post/{}'.format(id))

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('welcome'))


@app.route('/room_invite')
@login_required
def room_invite():
    invite = blog_post(title='Join me on Room',content='see you at time ?\nMy face is 🎅',
    posted_by=current_user.username)
    return render_template('room_invite.html',post=invite,user=current_user)


if __name__ == "__main__":
    socketio.run(app)
