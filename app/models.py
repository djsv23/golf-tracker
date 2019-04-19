from app import db
from datetime import date, datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app import login
from hashlib import md5

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    gender_cd = db.Column(db.String(1))
    hdcp_index = db.Column(db.Numeric)
    about_me = db.Column(db.String(140))
#    rounds = db.Relationship('User', backref='round', lazy='dynamic')

    def __repr__(self):
        return '<User {}>'.format(self.username)
        
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
        
    def avatar(self, size):
        digest = md5(self.email.lower().encode('utf-8')).hexdigest()
        return 'https://www.gravatar.com/avatar/{}?d=identicon&s={}'.format(
            digest, size)

#class Round(db.Model):
#    id = db.Column(db.Integer, primary_key = True)
#    out_score = db.Column(db.Integer)
#    in_score = db.Column(db.Integer)
#    gross_score = db.Column(db.Integer, index=True)
#    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), index=True)
#    net_score = db.Column(db.Integer, index=True)
#    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), index=True)
#    played_date = db.Column(db.Date, index=True, default=datetime.today)
#    
#class Course(db.Model):
#    id = db.Column(db.Integer, primary_key = True)
#    name = db.Column(db.String(128), unique=True)
#    addr_id = db.Column(db.Integer, db.ForeignKey('address.id'))
#    course_address = db.Relationship('Course Adddress', backref='address', lazy='dynamic')
#    par = db.Column(db.Integer)
#    round = db.Relationship('Course', backref='round', lazy='dynamic')
#        
#class Address(db.Model):
#    id = db.Column(db.Integer, primary_key = True)
#    street = db.Column(db.String(64))
#    city = db.Column(db.String(25))
#    state = db.Column(db.String(2))
#    zip_cd = db.Column(db.String(5))
#
#class Tee(db.Model):
#    id = db.Column(db.Integer, primary_key = True)
#    position = db.Column(db.Integer)
#    color = db.Column(db.String(16))
#    women_rating = db.Column(db.Numeric)
#    women_slope = db.Column(db.Numeric)
#    men_rating = db.Column(db.Numeric)
#    men_slope = db.Column(db.Numeric)
#    course_id = (db.Integer, db.ForeignKey('course.id'))
#    course = db.relationship('Course', backref='course', lazy='dynamic')
    
@login.user_loader
def load_user(id):
    return User.query.get(int(id))