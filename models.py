from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import datetime

db = SQLAlchemy()

class User(db.Model):
    """User model for authentication"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)
    
    # Relationship with redesigns
    redesigns = db.relationship('Redesign', backref='user', lazy=True, cascade="all, delete-orphan")
    
    @property
    def password(self):
        """Prevent password from being accessed"""
        raise AttributeError('Password is not a readable attribute')
    
    @password.setter
    def password(self, password):
        """Set password to a hashed password"""
        self.password_hash = generate_password_hash(password)
    
    def verify_password(self, password):
        """Check if password matches the hashed password"""
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.email}>'


class Redesign(db.Model):
    """Model to track user redesigns"""
    __tablename__ = 'redesigns'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # Nullable for anonymous users
    anonymous_id = db.Column(db.String(255), nullable=True)  # For tracking anonymous users
    original_image_path = db.Column(db.String(255), nullable=True)
    inspiration_image_path = db.Column(db.String(255), nullable=True)
    result_image_path = db.Column(db.String(255), nullable=True)
    suggestions = db.Column(db.Text, nullable=True)  # JSON string of suggestions
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    
    def __repr__(self):
        if self.user_id:
            return f'<Redesign {self.id} by User {self.user_id}>'
        else:
            return f'<Redesign {self.id} by Anonymous {self.anonymous_id}>' 