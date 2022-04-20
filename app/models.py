from datetime import datetime
from email.policy import default
from app import db, login
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from time import time
from app import app
import jwt
import json

followers = db.Table('followers', 
        db.Column('follower_id', db.Integer, db.ForeignKey('user.id')),
        db.Column('followed_id', db.Integer, db.ForeignKey('user.id'))
)

voted_by = db.Table('voted_by',
        db.Column('user_id', db.Integer, db.ForeignKey('post.id')),
        db.Column('post_id', db.Integer, db.ForeignKey('user.id'))
)

voted_by_comm = db.Table('voted_by_comm',
        db.Column('user_id', db.Integer, db.ForeignKey('comments.id')),
        db.Column('comments_id', db.Integer, db.ForeignKey('user.id'))
)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(32), index=True, unique=True)
    email = db.Column(db.String(64), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    posts = db.relationship('Post', backref='author', lazy='dynamic')
    about_me = db.Column(db.String(128))
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    karma = db.Column(db.Integer, default=0)
    followed = db.relationship(
        'User', secondary=followers,
        primaryjoin=(followers.c.follower_id == id),
        secondaryjoin=(followers.c.followed_id == id),
        backref=db.backref('followers', lazy='dynamic'), lazy='dynamic')
    messages_sent = db.relationship('Message', foreign_keys='Message.sender_id', backref='author', lazy='dynamic')
    messages_received =  db.relationship('Message', foreign_keys='Message.recipient_id', backref='recipient', lazy='dynamic')
    last_message_read_time = db.Column(db.DateTime)
    notifications = db.relationship('Notification', backref='author', lazy='dynamic')



    def _repr_(self):
        return '<User {}>'.format(self.username)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def follow(self, user):
        if not self.is_following(user):
            self.followed.append(user)

    def unfollow(self, user):
        if self.is_following(user):
            self.followed.remove(user)

    def is_following(self, user):
        return self.followed.filter(followers.c.followed_id == user.id).count() > 0

    def followed_posts(self):
        followed = Post.query.join(
            followers, (followers.c.followed_id == Post.user_id)).filter(
                followers.c.follower_id == self.id)
        own = Post.query.filter_by(user_id=self.id)
        return followed.union(own).order_by(Post.timestamp.desc())
        
    def get_reset_password_token(self, expires_in=600):
        return jwt.encode({'reset_password': self.id, 'exp': time() + expires_in}, app.config['SECRET_KEY'], algorithm='HS256')

    @staticmethod
    def verify_reset_password_token(token):
        try:
            id = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])['reset_password']
        except: 
            return
        return User.query.get(id)  

    def new_messages(self):
        last_read_time = self.last_message_read_time or datetime(1900, 1, 1)
        return Message.query.filter_by(recipient=self).filter(Message.timestamp > last_read_time).count()

    def add_notification(self, name, data):
        self.notifications.filter_by(name=name).delete()
        n = Notification(name=name, payload_json=json.dumps(data), user_id=self.id)
        db.session.add(n)
        return n

@login.user_loader
def load_user(id):
    return User.query.get(int(id))
      
    
class Post(db.Model):
    __searchable__ = ['body']
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.String(140))
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    karma = db.Column(db.Integer, default=0)
    voted_on = db.relationship('User', secondary=voted_by, 
        primaryjoin=(voted_by.c.post_id == id),
        secondaryjoin=(voted_by.c.user_id == User.id),
        backref=db.backref('voted_by', lazy='dynamic'), lazy='dynamic')
    comments = db.relationship('Comment', backref='post', lazy='dynamic')

    def __repr__(self):
        return '<Post {}>'.format(self.body)

    def is_voted(self, user):
        return self.voted_on.filter(voted_by.c.user_id == user.id).count() > 0
  
    def karmachange(self, user, change, postauthor):
        if not self.is_voted(user):
            self.voted_on.append(user)
            if change == '+':
                self.karma = self.karma + 1
                postauthor.karma = postauthor.karma + 1
                db.session.commit()
                return True
            elif change == '-':
                self.karma = self.karma - 1
                postauthor.karma = postauthor.karma - 1
                db.session.commit()
                return True
        return False

        
        
class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    body = db.Column(db.String(140))
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    karma = None
    def __repr__(self):
        return '<Message {}>'.format(self.body)
        
class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    timestamp = db.Column(db.Float, index=True, default=time)
    payload_json = db.Column(db.Text)

    def get_data(self):
        return json.loads(str(self.payload_json))

class Comment(db.Model):
    __tablename__ = 'comments'
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text)
    body_html = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'))
    karma = db.Column(db.Integer, default=0)
    voted_on_comm = db.relationship('User', secondary=voted_by_comm, 
        primaryjoin=(voted_by_comm.c.comments_id == id),
        secondaryjoin=(voted_by_comm.c.user_id == User.id),
        backref=db.backref('voted_by_comm', lazy='dynamic'), lazy='dynamic')

    def __repr__(self):
        return '<Post {}>'.format(self.body)

    def username(self):
        username = User.query.filter_by(id=self.author_id).first_or_404()
        return username.username

    def is_voted_on(self, user):
        return self.voted_on_comm.filter(voted_by_comm.c.user_id == user.id).count() > 0

    def karmachangecomm(self, user, change, commauthor):
        if not self.is_voted_on(user):
            self.voted_on_comm.append(user)
            if change == '+':
                self.karma = self.karma + 1
                commauthor.karma = commauthor.karma + 1
                db.session.commit()
                return True
            elif change == '-':
                self.karma = self.karma - 1
                commauthor.karma = commauthor.karma - 1
                db.session.commit()
                return True
        return False

