from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import (
    create_access_token, 
    create_refresh_token, 
    jwt_required, 
    get_jwt_identity,
    set_access_cookies, 
    set_refresh_cookies,
    unset_jwt_cookies
)
from werkzeug.security import generate_password_hash, check_password_hash
import datetime
import json
from functools import wraps
import re
import uuid

from models import db, User, Redesign

# Create a Blueprint for auth routes
auth_bp = Blueprint('auth', __name__)

# Constants for anonymous usage
MAX_ANONYMOUS_USAGE = 3
ANONYMOUS_COOKIE_NAME = 'redesign_anonymous_id'

# Helper function to validate email
def is_valid_email(email):
    # Basic email validation regex
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(pattern, email) is not None

# Helper function to validate password strength
def is_strong_password(password):
    """
    Validate password strength
    - At least 8 characters
    - Contains at least one digit
    - Contains at least one uppercase letter
    """
    if len(password) < 8:
        return False
    if not any(char.isdigit() for char in password):
        return False
    if not any(char.isupper() for char in password):
        return False
    return True

# Decorator to check if user is authenticated or has anonymous uses left
def auth_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # First, check for JWT token
        try:
            # Check for Authorization header
            auth_header = request.headers.get('Authorization')
            if auth_header and auth_header.startswith('Bearer '):
                # User has a token, let them proceed
                return f(*args, **kwargs)
        except:
            pass
            
        # If no valid token, check for anonymous ID in cookies
        anonymous_id = request.cookies.get(ANONYMOUS_COOKIE_NAME)
        
        # If anonymous ID exists, check usage count
        if anonymous_id:
            usage_count = Redesign.query.filter_by(anonymous_id=anonymous_id).count()
            
            # If under limit, allow request
            if usage_count < MAX_ANONYMOUS_USAGE:
                return f(*args, **kwargs)
            else:
                # User has exceeded anonymous usage limit
                return jsonify({
                    'error': 'ANONYMOUS_USAGE_LIMIT',
                    'message': f'You have used all your {MAX_ANONYMOUS_USAGE} anonymous redesigns. Please sign in or register to continue.',
                    'code': 'AUTH_REQUIRED'
                }), 401
        
        # If user has no ID at all, create one and allow first access
        new_anonymous_id = str(uuid.uuid4())
        response = f(*args, **kwargs)
        
        # If response is a tuple, get the response object
        if isinstance(response, tuple):
            resp_obj = response[0]
        else:
            resp_obj = response
            
        # Set the cookie if response is a Response object
        if hasattr(resp_obj, 'set_cookie'):
            resp_obj.set_cookie(ANONYMOUS_COOKIE_NAME, new_anonymous_id, max_age=60*60*24*365, httponly=True, samesite='Strict')
            
        return response
    
    return decorated_function

@auth_bp.route('/register', methods=['POST'])
def register():
    """Register a new user"""
    try:
        data = request.get_json()
        
        # Validate input
        if not data or not data.get('email') or not data.get('password'):
            return jsonify({'error': 'Email and password are required'}), 400
        
        email = data.get('email')
        password = data.get('password')
        
        # Validate email format
        if not is_valid_email(email):
            return jsonify({'error': 'Invalid email format'}), 400
        
        # Validate password strength
        if not is_strong_password(password):
            return jsonify({
                'error': 'Password is too weak. It must be at least 8 characters and contain at least one digit and one uppercase letter.'
            }), 400
        
        # Check if user already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            return jsonify({'error': 'Email already registered'}), 409
        
        # Create new user
        new_user = User(email=email)
        new_user.password = password  # This uses the password setter which hashes the password
        
        # Add user to database
        db.session.add(new_user)
        db.session.commit()
        
        # Create tokens
        access_token = create_access_token(identity=new_user.id)
        refresh_token = create_refresh_token(identity=new_user.id)
        
        # Create response
        response = jsonify({
            'message': 'User registered successfully',
            'user': {'id': new_user.id, 'email': new_user.email},
            'access_token': access_token
        })
        
        # Set cookies
        set_access_cookies(response, access_token)
        set_refresh_cookies(response, refresh_token)
        
        # If user had anonymous redesigns, associate them with the new account
        anonymous_id = request.cookies.get(ANONYMOUS_COOKIE_NAME)
        if anonymous_id:
            anonymous_redesigns = Redesign.query.filter_by(anonymous_id=anonymous_id).all()
            for redesign in anonymous_redesigns:
                redesign.user_id = new_user.id
                redesign.anonymous_id = None
            db.session.commit()
        
        return response, 201
    
    except Exception as e:
        current_app.logger.error(f"Error in register: {str(e)}")
        return jsonify({'error': 'Registration failed', 'details': str(e)}), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    """Login an existing user"""
    try:
        data = request.get_json()
        
        # Validate input
        if not data or not data.get('email') or not data.get('password'):
            return jsonify({'error': 'Email and password are required'}), 400
        
        email = data.get('email')
        password = data.get('password')
        
        # Find the user
        user = User.query.filter_by(email=email).first()
        
        # Check if user exists and password is correct
        if not user or not user.verify_password(password):
            return jsonify({'error': 'Invalid email or password'}), 401
        
        # Update last login time
        user.last_login = datetime.datetime.utcnow()
        db.session.commit()
        
        # Create tokens
        access_token = create_access_token(identity=user.id)
        refresh_token = create_refresh_token(identity=user.id)
        
        # Create response
        response = jsonify({
            'message': 'Login successful',
            'user': {'id': user.id, 'email': user.email},
            'access_token': access_token
        })
        
        # Set cookies
        set_access_cookies(response, access_token)
        set_refresh_cookies(response, refresh_token)
        
        # If user had anonymous redesigns, associate them with the account
        anonymous_id = request.cookies.get(ANONYMOUS_COOKIE_NAME)
        if anonymous_id:
            anonymous_redesigns = Redesign.query.filter_by(anonymous_id=anonymous_id).all()
            for redesign in anonymous_redesigns:
                redesign.user_id = user.id
                redesign.anonymous_id = None
            db.session.commit()
        
        return response, 200
    
    except Exception as e:
        current_app.logger.error(f"Error in login: {str(e)}")
        return jsonify({'error': 'Login failed', 'details': str(e)}), 500

@auth_bp.route('/logout', methods=['POST'])
def logout():
    """Logout the current user"""
    response = jsonify({'message': 'Logout successful'})
    unset_jwt_cookies(response)
    return response, 200

@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """Refresh the access token"""
    current_user_id = get_jwt_identity()
    access_token = create_access_token(identity=current_user_id)
    
    response = jsonify({'access_token': access_token})
    set_access_cookies(response, access_token)
    
    return response, 200

@auth_bp.route('/user', methods=['GET'])
@jwt_required()
def get_user():
    """Get the current user's information"""
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Get usage count
    usage_count = Redesign.query.filter_by(user_id=current_user_id).count()
    
    return jsonify({
        'user': {
            'id': user.id,
            'email': user.email,
            'created_at': user.created_at.isoformat() if user.created_at else None,
            'last_login': user.last_login.isoformat() if user.last_login else None
        },
        'usage_count': usage_count
    }), 200

@auth_bp.route('/check-anonymous', methods=['GET'])
def check_anonymous():
    """Check anonymous usage status"""
    anonymous_id = request.cookies.get(ANONYMOUS_COOKIE_NAME)
    
    if not anonymous_id:
        # Generate a new anonymous ID
        anonymous_id = str(uuid.uuid4())
        response = jsonify({
            'anonymous_id': anonymous_id,
            'usage_count': 0,
            'remaining': MAX_ANONYMOUS_USAGE
        })
        response.set_cookie(ANONYMOUS_COOKIE_NAME, anonymous_id, max_age=60*60*24*365, httponly=True, samesite='Strict')
        return response, 200
    
    # Get usage count
    usage_count = Redesign.query.filter_by(anonymous_id=anonymous_id).count()
    
    return jsonify({
        'anonymous_id': anonymous_id,
        'usage_count': usage_count,
        'remaining': max(0, MAX_ANONYMOUS_USAGE - usage_count)
    }), 200

# Function to track a redesign
def track_redesign(user_id=None, anonymous_id=None, original_path=None, inspiration_path=None, result_path=None, suggestions_data=None):
    """
    Track a redesign in the database
    """
    try:
        # Create a new redesign record
        redesign = Redesign(
            user_id=user_id,
            anonymous_id=anonymous_id,
            original_image_path=original_path,
            inspiration_image_path=inspiration_path,
            result_image_path=result_path,
            suggestions=json.dumps(suggestions_data) if suggestions_data else None
        )
        
        db.session.add(redesign)
        db.session.commit()
        
        return True, redesign.id
    except Exception as e:
        current_app.logger.error(f"Error tracking redesign: {str(e)}")
        return False, None 