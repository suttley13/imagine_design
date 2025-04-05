# Import error logging packages
import logging
import traceback
import sys

# Set up logging to stderr
logging.basicConfig(
    level=logging.DEBUG, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stderr)]
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Log startup info
logger.info("Starting application...")

import base64
import os
import mimetypes
import uuid
import requests
import json
import io
import tempfile
import subprocess
import sys
import time
import random
import re
from pathlib import Path
from PIL import Image
from flask import Flask, request, jsonify, send_from_directory, send_file, current_app, g
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity
from flask_migrate import Migrate
from google import genai
from google.genai import types
from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.exceptions import Unauthorized

try:
    logger.info("Basic imports successful")
    
    # Log each complex import separately
    try:
        from flask_jwt_extended import JWTManager
        logger.info("JWTManager imported successfully")
    except Exception as e:
        logger.error(f"Error importing JWTManager: {str(e)}")
        logger.error(traceback.format_exc())
    
    try:
        from flask_migrate import Migrate
        logger.info("Migrate imported successfully")
    except Exception as e:
        logger.error(f"Error importing Migrate: {str(e)}")
        logger.error(traceback.format_exc())
    
    try:
        from google import genai
        from google.genai import types
        logger.info("Google Genai imports successful")
    except Exception as e:
        logger.error(f"Error importing Google Genai: {str(e)}")
        logger.error(traceback.format_exc())
    
    try:
        from dotenv import load_dotenv
        logger.info("dotenv imported successfully")
    except Exception as e:
        logger.error(f"Error importing dotenv: {str(e)}")
        logger.error(traceback.format_exc())
    
    try:
        from flask_sqlalchemy import SQLAlchemy
        logger.info("SQLAlchemy imported successfully")
    except Exception as e:
        logger.error(f"Error importing SQLAlchemy: {str(e)}")
        logger.error(traceback.format_exc())
    
    try:
        from werkzeug.middleware.proxy_fix import ProxyFix
        from werkzeug.exceptions import Unauthorized
        logger.info("Werkzeug imports successful")
    except Exception as e:
        logger.error(f"Error importing Werkzeug: {str(e)}")
        logger.error(traceback.format_exc())
    
    # Try importing models and auth separately
    try:
        # Import models and authentication
        from models import db
        logger.info("db imported successfully from models")
    except Exception as e:
        logger.error(f"Error importing db from models: {str(e)}")
        logger.error(traceback.format_exc())
    
    try:
        from auth import auth_bp, auth_required, track_redesign, ANONYMOUS_COOKIE_NAME, MAX_ANONYMOUS_USAGE
        logger.info("Auth components imported successfully")
    except Exception as e:
        logger.error(f"Error importing auth components: {str(e)}")
        logger.error(traceback.format_exc())
    
    try:
        from config import config
        logger.info("Config imported successfully")
    except Exception as e:
        logger.error(f"Error importing config: {str(e)}")
        logger.error(traceback.format_exc())
    
    # Load environment variables from .env file
    try:
        load_dotenv()
        logger.info("Environment variables loaded successfully")
    except Exception as e:
        logger.error(f"Error loading environment variables: {str(e)}")
        logger.error(traceback.format_exc())
    
    # Get environment configuration
    config_name = os.environ.get('FLASK_CONFIG') or 'default'
    logger.info(f"Using configuration: {config_name}")
    
    # Create Flask app
    app = Flask(__name__, static_folder='public', static_url_path='')
    logger.info("Flask app created")
    
    # Apply configuration
    try:
        app.config.from_object(config[config_name])
        logger.info(f"Configuration {config_name} applied successfully")
        
        # Log key config values (avoiding secrets)
        safe_config = {k: v for k, v in app.config.items() 
                     if not any(secret in k.lower() for secret in 
                               ['key', 'pass', 'secret', 'token', 'cred'])}
        logger.info(f"Configuration values: {safe_config}")
        
        config[config_name].init_app(app)
        logger.info("init_app called successfully")
    except Exception as e:
        logger.error(f"Error applying configuration: {str(e)}")
        logger.error(traceback.format_exc())
    
    # Configure proxy headers for cloud run
    try:
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
        logger.info("ProxyFix applied to wsgi_app")
    except Exception as e:
        logger.error(f"Error applying ProxyFix: {str(e)}")
        logger.error(traceback.format_exc())
    
    # Initialize extensions
    try:
        jwt = JWTManager(app)
        logger.info("JWTManager initialized")
    except Exception as e:
        logger.error(f"Error initializing JWTManager: {str(e)}")
        logger.error(traceback.format_exc())
    
    try:
        db.init_app(app)
        logger.info("SQLAlchemy initialized")
    except Exception as e:
        logger.error(f"Error initializing SQLAlchemy: {str(e)}")
        logger.error(traceback.format_exc())
    
    try:
        migrate = Migrate(app, db)
        logger.info("Flask-Migrate initialized")
    except Exception as e:
        logger.error(f"Error initializing Flask-Migrate: {str(e)}")
        logger.error(traceback.format_exc())
    
    # Simplify database connection handling
    try:
        with app.app_context():
            try:
                # Log the database URI (removing password)
                db_uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
                if '@' in db_uri and ':' in db_uri:
                    # Mask the password in the connection string for logging
                    parts = db_uri.split('@')
                    user_pass = parts[0].split(':')
                    if len(user_pass) > 2:
                        masked_uri = f"{user_pass[0]}:****@{parts[1]}"
                        logger.info(f"Database URI: {masked_uri}")
                
                # Try to create tables
                db.create_all()
                logger.info("Database tables created successfully")
            except Exception as e:
                logger.error(f"Database initialization error: {str(e)}")
                logger.error(traceback.format_exc())
                # Continue anyway - tables might already exist
    except Exception as e:
        logger.error(f"Error creating app context: {str(e)}")
        logger.error(traceback.format_exc())
    
    # Register blueprints
    try:
        app.register_blueprint(auth_bp, url_prefix='/auth')
        logger.info("Auth blueprint registered successfully")
    except Exception as e:
        logger.error(f"Error registering auth blueprint: {str(e)}")
        logger.error(traceback.format_exc())
    
    # Ensure uploads and generated directories exist
    try:
        os.makedirs('uploads', exist_ok=True)
        os.makedirs('generated', exist_ok=True)
        os.makedirs('logs', exist_ok=True)
        logger.info("Created required directories")
    except Exception as e:
        logger.error(f"Error creating directories: {str(e)}")
        logger.error(traceback.format_exc())
    
    # Make generated directory accessible to static file server
    app.config['GENERATED_FOLDER'] = os.path.abspath('generated')
    logger.info(f"GENERATED_FOLDER set to: {app.config['GENERATED_FOLDER']}")
    
    # Load API keys from environment
    try:
        API_KEY = os.environ.get("GEMINI_API_KEY")
        if not API_KEY:
            logger.warning("GEMINI_API_KEY environment variable not set")
        else:
            logger.info("GEMINI_API_KEY found in environment")
        
        CLAUDE_API_KEY = os.environ.get("CLAUDE_API_KEY")
        if not CLAUDE_API_KEY:
            logger.warning("CLAUDE_API_KEY environment variable not set")
        else:
            logger.info("CLAUDE_API_KEY found in environment")
        
        CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-3-sonnet-20240229")
        logger.info(f"Using CLAUDE_MODEL: {CLAUDE_MODEL}")
    except Exception as e:
        logger.error(f"Error loading API keys: {str(e)}")
        logger.error(traceback.format_exc())
    
    # Initialize the Gemini client
    try:
        client = genai.Client(api_key=API_KEY)
        logger.info("Gemini client initialized")
    except Exception as e:
        logger.error(f"Error initializing Gemini client: {str(e)}")
        logger.error(traceback.format_exc())
    
    # Minimal route for health check
    @app.route('/healthz')
    def healthz():
        return jsonify({"status": "ok"})
    
    # Root route
    @app.route('/')
    def index():
        try:
            return send_from_directory('public', 'index.html')
        except Exception as e:
            logger.error(f"Error serving index.html: {str(e)}")
            logger.error(traceback.format_exc())
            return jsonify({"error": "Error serving index page", "details": str(e)}), 500
            
    @app.route('/api/chat', methods=['POST'])
    def chat():
        try:
            data = request.json
            message = data.get('message', '')
            
            # Text-only request
            model = "gemini-1.5-flash"
            contents = [
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(text=message),
                    ],
                ),
            ]
            
            generate_content_config = types.GenerateContentConfig(
                temperature=1,
                top_p=0.95,
                top_k=40,
                max_output_tokens=8192,
                response_mime_type="text/plain",
            )
            
            response = client.models.generate_content(
                model=model,
                contents=contents,
                config=generate_content_config,
            )
            
            return jsonify({"text": response.text, "images": []})
        
        except Exception as e:
            print(f"Error in text chat: {str(e)}")
            return jsonify({"error": str(e)}), 500

    @app.route('/api/chat-with-image', methods=['POST'])
    def chat_with_image():
        try:
            message = request.form.get('message', '')
            is_preview_processing = message == 'Processing HEIC preview'
            
            # Check for uploaded image
            image_file = request.files.get('image')
            if not image_file:
                return jsonify({"error": "No image provided"}), 400
            
            # Process the uploaded image (handles HEIC conversion)
            try:
                image_path = process_uploaded_image(image_file)
                print(f"Processed image saved to {image_path}")
            except Exception as e:
                return jsonify({"error": f"Error processing image: {str(e)}"}), 400
            
            # For preview processing, just return the processed image path
            if is_preview_processing:
                # Generate a unique filename for the preview image
                preview_name = f"image_preview_{uuid.uuid4()}.jpg"
                preview_path = f"generated/{preview_name}"
                
                # Copy the processed image to a preview location
                import shutil
                shutil.copy(image_path, preview_path)
                
                # Clean up the uploaded file
                os.remove(image_path)
                
                # Return the preview image URL
                preview_url = f"/generated/{preview_name}"
                return jsonify({
                    "text": "Preview processed",
                    "images": [preview_url]
                })
            
            # Regular image generation flow continues below
            # Get mime type
            mime_type = mimetypes.guess_type(image_path)[0] or "image/jpeg"
            
            # Upload file to Gemini
            uploaded_file = client.files.upload(file=image_path)
            
            # Initialize the model
            model = "gemini-2.0-flash-exp-image-generation"
            
            # Create content with image and text
            contents = [
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_uri(
                            file_uri=uploaded_file.uri,
                            mime_type=uploaded_file.mime_type,
                        ),
                        types.Part.from_text(text=message),
                    ],
                ),
            ]
            
            # Configure generation
            generate_content_config = types.GenerateContentConfig(
                temperature=1,
                top_p=0.95,
                top_k=40,
                max_output_tokens=8192,
                response_modalities=["image", "text"],
                response_mime_type="text/plain",
            )
            
            # List to store generated image names
            generated_images = []
            response_text = ""
            
            # Stream response to capture both text and images
            for chunk in client.models.generate_content_stream(
                model=model,
                contents=contents,
                config=generate_content_config,
            ):
                if not chunk.candidates or not chunk.candidates[0].content or not chunk.candidates[0].content.parts:
                    continue
                    
                part = chunk.candidates[0].content.parts[0]
                
                # If chunk contains image data
                if hasattr(part, 'inline_data') and part.inline_data:
                    file_name = f"generated/image_{uuid.uuid4()}"
                    inline_data = part.inline_data
                    file_extension = mimetypes.guess_extension(inline_data.mime_type) or ".png"
                    full_path = f"{file_name}{file_extension}"
                    
                    # Save the image
                    with open(full_path, "wb") as f:
                        f.write(inline_data.data)
                    
                    # Get the filename without the full path
                    filename = os.path.basename(full_path)
                    
                    # Add to list of generated images (web path)
                    # Use a relative URL that can be served by Flask
                    image_web_path = f"/generated/{filename}"
                    generated_images.append(image_web_path)
                    
                    print(f"Generated image saved to: {full_path}")
                    print(f"Image will be served at: {image_web_path}")
                    
                    # Double check file exists
                    if os.path.exists(full_path):
                        print(f"Confirmed file exists at: {full_path}")
                    else:
                        print(f"WARNING: File does not exist at: {full_path}")
                else:
                    # Accumulate text response
                    if hasattr(chunk, 'text'):
                        response_text += chunk.text
            
            # Clean up the uploaded file
            os.remove(image_path)
            
            return jsonify({
                "text": response_text,
                "images": generated_images
            })
        
        except Exception as e:
            print(f"Error in image generation: {str(e)}")
            return jsonify({"error": str(e)}), 500

    def process_uploaded_image(file, prefix=""):
        """Process an uploaded image file, handling various formats including HEIC/HEIF."""
        # Generate a unique filename with optional prefix
        original_filename = file.filename
        extension = os.path.splitext(original_filename)[1].lower()
        
        # Check if this is a HEIC/HEIF image
        is_heic = extension in ['.heic', '.heif'] or (file.content_type and ('heic' in file.content_type.lower() or 'heif' in file.content_type.lower()))
        
        if is_heic:
            print(f"Detected HEIC image: {original_filename}")
            print("Attempting to convert HEIC to JPEG...")
            
        # Save the original file to a temporary location
        with tempfile.NamedTemporaryFile(delete=False, suffix=extension) as temp:
            file.save(temp.name)
            temp_path = temp.name
        
        # Generate output path with standard extension and prefix
        output_path = f"uploads/{prefix}{uuid.uuid4()}.jpg"
        
        # Ensure the uploads directory exists
        os.makedirs("uploads", exist_ok=True)
        
        try:
            # Try opening the image with PIL first
            try:
                with Image.open(temp_path) as img:
                    # Convert to RGB if needed
                    if img.mode in ('RGBA', 'LA'):
                        print(f"Converting image from {img.mode} to RGB")
                        background = Image.new('RGB', img.size, (255, 255, 255))
                        background.paste(img, mask=img.split()[3] if img.mode == 'RGBA' else img.split()[1])
                        img = background
                    elif img.mode != 'RGB':
                        print(f"Converting image from {img.mode} to RGB")
                        img = img.convert('RGB')
                    
                    # Save as JPEG
                    img.save(output_path, format='JPEG', quality=95)
                    print(f"Image processed and saved to {output_path}")
                    
                    # Clean up temp file
                    os.remove(temp_path)
                    return output_path
                    
            except Exception as img_error:
                print(f"Error opening image with PIL: {str(img_error)}")
                
                # If this is a HEIC image, try external conversion tools
                if is_heic:
                    print("Trying external tools for HEIC conversion...")
                    
                    # Try different conversion methods depending on platform
                    conversion_success = False
                    
                    # Try method 1: Use sips (macOS)
                    if not conversion_success and sys.platform == 'darwin':
                        try:
                            print("Trying sips for conversion (macOS)...")
                            subprocess.run(['sips', '-s', 'format', 'jpeg', '-s', 'formatOptions', 'best', 
                                            temp_path, '--out', output_path], 
                                           check=True, capture_output=True)
                            conversion_success = os.path.exists(output_path)
                            if conversion_success:
                                print("HEIC conversion with sips succeeded")
                        except Exception as e:
                            print(f"sips conversion failed: {str(e)}")
                    
                    # Try method 2: Use ImageMagick if available
                    if not conversion_success:
                        try:
                            print("Trying ImageMagick for conversion...")
                            subprocess.run(['convert', temp_path, output_path], 
                                          check=True, capture_output=True)
                            conversion_success = os.path.exists(output_path)
                            if conversion_success:
                                print("HEIC conversion with ImageMagick succeeded")
                        except Exception as e:
                            print(f"ImageMagick conversion failed: {str(e)}")
                    
                    # Try method 3: Use heif-convert if available
                    if not conversion_success:
                        try:
                            print("Trying heif-convert for conversion...")
                            subprocess.run(['heif-convert', temp_path, output_path], 
                                          check=True, capture_output=True)
                            conversion_success = os.path.exists(output_path)
                            if conversion_success:
                                print("HEIC conversion with heif-convert succeeded")
                        except Exception as e:
                            print(f"heif-convert conversion failed: {str(e)}")
                    
                    # If any conversion method worked, return the output path
                    if conversion_success:
                        # Clean up temp file
                        os.remove(temp_path)
                        return output_path
                    else:
                        # If all conversions failed, notify the user but don't hard error
                        print("All HEIC conversion methods failed")
                        os.remove(temp_path)
                        raise ValueError("Unable to convert HEIC image. Please convert it to JPEG before uploading.")
                
                # For non-HEIC images that PIL couldn't open, try a generic approach
                print("Trying to handle as a generic image format...")
                
                # For non-HEIC images, we can try using a different approach or format
                if not is_heic:
                    # Copy the file with a more common extension
                    with open(temp_path, 'rb') as src_file:
                        with open(output_path, 'wb') as dest_file:
                            dest_file.write(src_file.read())
                    print(f"File copied to {output_path} - will attempt to process")
                    
                    # Clean up temp file
                    os.remove(temp_path)
                    return output_path
                else:
                    raise ValueError("Unsupported image format. Please upload JPEG, PNG, or GIF images.")
                
        except Exception as e:
            # Clean up temp file if still exists
            if os.path.exists(temp_path):
                os.remove(temp_path)
            print(f"Error processing uploaded image: {str(e)}")
            raise

    def make_claude_request(url, headers, payload, max_retries=3, initial_delay=1):
        for attempt in range(max_retries):
            try:
                claude_response = requests.post(url, headers=headers, json=payload)
                
                # If successful, return the response
                if claude_response.status_code == 200:
                    return claude_response
                    
                # If overloaded, wait and retry
                if claude_response.status_code == 529:
                    if attempt < max_retries - 1:  # Don't sleep on the last attempt
                        delay = initial_delay * (2 ** attempt) + random.uniform(0, 0.1)  # exponential backoff with jitter
                        print(f"Claude API overloaded, retrying in {delay:.1f} seconds...")
                        time.sleep(delay)
                        continue
                        
                # For other errors, raise immediately
                claude_response.raise_for_status()
                
            except Exception as e:
                if attempt < max_retries - 1:
                    delay = initial_delay * (2 ** attempt) + random.uniform(0, 0.1)
                    print(f"Error making Claude API request: {str(e)}, retrying in {delay:.1f} seconds...")
                    time.sleep(delay)
                    continue
                raise
        
        # If we get here, all retries failed
        raise Exception(f"Claude API still overloaded after {max_retries} retries")

    @app.route('/api/claude-suggestions', methods=['POST'])
    @auth_required
    def claude_suggestions():
        """Get redesign suggestions from Claude"""
        try:
            # Check if required files are in request
            if 'original' not in request.files or 'inspiration' not in request.files:
                return jsonify({"error": "Both original and inspiration images are required"}), 400
            
            # Get files
            original_file = request.files['original']
            inspiration_file = request.files['inspiration']
            
            # Validate files
            for file in [original_file, inspiration_file]:
                if file.filename == '':
                    return jsonify({"error": "No file selected"}), 400
            
            # Save files to temporary locations
            original_path = os.path.join('uploads', f"{uuid.uuid4()}.jpg")
            inspiration_path = os.path.join('uploads', f"{uuid.uuid4()}.jpg")
            
            logger.info(f"Saving original image to {original_path}")
            original_file.save(original_path)
            
            logger.info(f"Saving inspiration image to {inspiration_path}")
            inspiration_file.save(inspiration_path)
            
            # Process with Claude
            try:
                logger.info("Calling Claude API with timeout of 60 seconds")
                
                # Get the anthropic client
                headers = {
                    "x-api-key": CLAUDE_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                }
                
                # Prepare images for Claude
                logger.info("Preparing images for Claude")
                original_b64 = encode_image(original_path)
                inspiration_b64 = encode_image(inspiration_path)
                
                # Create the prompt
                prompt_text = f"""You're the world's greatest interior designer. I'll show you two images:
1. The first is a room I want to redesign
2. The second is an inspiration image with a style I like

Please suggest 3 different ways to redesign my room based on the inspiration image.
For each suggestion, provide:
- A clear, specific title (10 words or less)
- A detailed description with color schemes, furniture placement, etc. (250-350 words)
"""
                
                # Prepare the request
                payload = {
                    "model": CLAUDE_MODEL,
                    "max_tokens": 1500,
                    "temperature": 0.7,
                    "messages": [
                        {
                            "role": "user", 
                            "content": [
                                {"type": "text", "text": prompt_text},
                                {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": original_b64}},
                                {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": inspiration_b64}}
                            ]
                        }
                    ]
                }
                
                logger.info("Sending request to Claude API")
                response = requests.post(
                    "https://api.anthropic.com/v1/messages",
                    headers=headers,
                    json=payload,
                    timeout=60
                )
                
                # Check if response is successful
                if response.status_code != 200:
                    logger.error(f"Claude API error: {response.status_code} - {response.text}")
                    return jsonify({"error": f"Error from Claude API: {response.status_code}"}), 500
                    
                result = response.json()
                logger.info("Received response from Claude")
                
                # Extract suggestions from Claude's response
                suggestions_text = result["content"][0]["text"]
                
                # Parse suggestions (titles and descriptions)
                suggestions = parse_suggestions(suggestions_text)
                
                # Track usage
                if not track_usage(request, original_path, inspiration_path):
                    logger.error("Failed to track usage")
                
                # Return suggestions to client
                return jsonify({"suggestions": suggestions})
                
            except requests.exceptions.Timeout:
                logger.error("Claude API request timed out")
                return jsonify({"error": "The Claude API request timed out. Please try again later."}), 504
            except requests.exceptions.RequestException as e:
                logger.error(f"Claude API request error: {str(e)}")
                return jsonify({"error": f"Error connecting to Claude API: {str(e)}"}), 502
            except Exception as e:
                logger.error(f"Error processing Claude request: {str(e)}")
                return jsonify({"error": f"Error processing suggestion request: {str(e)}"}), 500
            
        except Exception as e:
            logger.exception(f"Error in claude_suggestions: {str(e)}")
            return jsonify({"error": str(e)}), 500
        finally:
            # Clean up temporary files
            try:
                if 'original_path' in locals() and os.path.exists(original_path):
                    os.remove(original_path)
                if 'inspiration_path' in locals() and os.path.exists(inspiration_path):
                    os.remove(inspiration_path)
            except Exception as e:
                logger.error(f"Error cleaning up temporary files: {str(e)}")

    # Helper function to track usage
    def track_usage(request, original_path, inspiration_path):
        """Track usage of the redesign service"""
        try:
            # Get user info
            user_id = None
            anonymous_id = None
            
            # Check if user is authenticated
            auth_header = request.headers.get('Authorization')
            if auth_header and auth_header.startswith('Bearer '):
                try:
                    # Extract user_id from JWT token
                    token = auth_header.split(' ')[1]
                    user_id = get_jwt_identity()
                except:
                    logger.error("Failed to extract user_id from token")
            
            # If not authenticated, use anonymous ID
            if not user_id:
                anonymous_id = request.cookies.get(ANONYMOUS_COOKIE_NAME)
            
            # Track the redesign
            success, _ = track_redesign(
                user_id=user_id,
                anonymous_id=anonymous_id,
                original_path=original_path,
                inspiration_path=inspiration_path
            )
            
            return success
        except Exception as e:
            logger.error(f"Error tracking usage: {str(e)}")
            return False

    # Helper function to encode images for Claude
    def encode_image(image_path):
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    # Helper function to parse suggestions from Claude
    def parse_suggestions(text):
        suggestions = []
        current_suggestion = None
        
        try:
            # Split by suggestion numbers
            parts = re.split(r'\n\s*(?:Suggestion |)\d+[\.:]\s*', text)
            
            # Remove any empty parts and the first part if it's just an intro
            parts = [p.strip() for p in parts if p.strip()]
            if len(parts) > 3 and len(parts[0]) < 100:  # The first part is likely an intro
                parts = parts[1:]
            
            # Take up to 3 suggestions
            parts = parts[:3]
            
            for i, part in enumerate(parts):
                lines = part.split('\n')
                title = None
                description = []
                
                # First non-empty line is the title
                for line in lines:
                    if line.strip() and not title:
                        title = line.strip()
                        # Remove any "Title:" prefix
                        title = re.sub(r'^Title:\s*', '', title)
                        # Remove any numbering
                        title = re.sub(r'^\d+[\.\)]\s*', '', title)
                    elif title:
                        # Everything after the title is the description
                        description.append(line)
                
                # Join description lines
                full_description = '\n'.join(description).strip()
                
                # Clean up the description
                full_description = re.sub(r'^Description:\s*', '', full_description)
                
                # Add to suggestions if we have both title and description
                if title and full_description:
                    suggestions.append({
                        "title": title,
                        "description": full_description
                    })
            
            # If we don't have exactly 3 suggestions, create dummy ones
            while len(suggestions) < 3:
                suggestions.append({
                    "title": f"Redesign Option {len(suggestions) + 1}",
                    "description": "I apologize, but I couldn't generate a detailed suggestion. Please try again or use one of the other redesign options."
                })
            
            return suggestions[:3]  # Ensure we return exactly 3 suggestions
            
        except Exception as e:
            logger.error(f"Error parsing suggestions: {str(e)}")
            # Return default suggestions
            return [
                {
                    "title": "Elegant Transformation",
                    "description": "I apologize, but I couldn't parse the suggestions properly. This is a fallback suggestion. Please try again with your redesign."
                },
                {
                    "title": "Modern Refresh",
                    "description": "I apologize, but I couldn't parse the suggestions properly. This is a fallback suggestion. Please try again with your redesign."
                },
                {
                    "title": "Cozy Makeover",
                    "description": "I apologize, but I couldn't parse the suggestions properly. This is a fallback suggestion. Please try again with your redesign."
                }
            ]

    @app.route('/api/save-results', methods=['POST'])
    def save_results():
        try:
            data = request.json
            result_image_url = data.get('result_image')
            suggestions = data.get('suggestions', [])
            
            # Remove the leading path as we'll be reading from the filesystem
            result_file = result_image_url.replace('/generated/', 'generated/')
            
            # Check if the result file exists
            if not os.path.exists(result_file):
                print(f"Result file not found: {result_file}")
                return jsonify({"error": "Result image not found"}), 404
            
            # Format suggestions for clipboard
            suggestion_text = ""
            for i, suggestion in enumerate(suggestions):
                suggestion_text += f"{i+1}. {suggestion.get('title')}\n"
                suggestion_text += f"{suggestion.get('description')}\n\n"
            
            # Instead of saving to downloads folder, create a download URL
            # Generate a unique filename
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            download_filename = f"room_redesign_{timestamp}.jpg"
            
            # Store the original path and generate a download URL
            # We'll use a temporary mapping to handle the download
            app.config.setdefault('DOWNLOAD_MAPPING', {})
            download_id = str(uuid.uuid4())
            app.config['DOWNLOAD_MAPPING'][download_id] = {
                'file_path': result_file,
                'filename': download_filename,
                'timestamp': datetime.datetime.now()
            }
            
            # Create download URL
            download_url = f"/api/download/{download_id}"
            
            # Get user info for tracking the result
            user_id = None
            anonymous_id = None
            
            # Try to get user ID from token
            try:
                # Check for JWT Authorization header
                auth_header = request.headers.get('Authorization')
                if auth_header and auth_header.startswith('Bearer '):
                    from flask_jwt_extended import decode_token
                    token = auth_header.split(' ')[1]
                    # Extract user ID from token
                    decoded = decode_token(token)
                    user_id = decoded.get('sub')
            except:
                pass
            
            # If no user ID, get anonymous ID from cookie
            if not user_id:
                anonymous_id = request.cookies.get(ANONYMOUS_COOKIE_NAME)
                
            # Update redesign record with result image
            if user_id or anonymous_id:
                from models import Redesign
                
                # Find the most recent redesign by this user
                if user_id:
                    redesign = Redesign.query.filter_by(user_id=user_id).order_by(Redesign.created_at.desc()).first()
                else:
                    redesign = Redesign.query.filter_by(anonymous_id=anonymous_id).order_by(Redesign.created_at.desc()).first()
                    
                # If found, update with result image
                if redesign:
                    redesign.result_image_path = result_file
                    db.session.commit()
            
            # Return success with download URL and clipboard content
            return jsonify({
                "success": True,
                "message": "Image ready for download",
                "clipboard_content": suggestion_text,
                "download_url": download_url
            })
        
        except Exception as e:
            print(f"Error preparing download: {str(e)}")
            return jsonify({"error": str(e)}), 500

    @app.route('/api/download/<download_id>', methods=['GET'])
    def download_file(download_id):
        try:
            # Get the file information from our mapping
            download_mapping = app.config.get('DOWNLOAD_MAPPING', {})
            if download_id not in download_mapping:
                return "Download expired or not found", 404
            
            file_info = download_mapping[download_id]
            file_path = file_info['file_path']
            filename = file_info['filename']
            
            # Check if the file exists
            if not os.path.exists(file_path):
                return "File not found", 404
            
            # Create a high-quality JPEG version of the image
            try:
                img = Image.open(file_path)
                
                # Convert to RGB if needed (required for JPEG)
                if img.mode in ('RGBA', 'LA'):
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    background.paste(img, mask=img.split()[3] if img.mode == 'RGBA' else img.split()[1])
                    img = background
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Create a BytesIO object to hold the image data
                img_io = io.BytesIO()
                img.save(img_io, format='JPEG', quality=95)
                img_io.seek(0)
                
                # Remove the download mapping after use (cleanup)
                download_mapping.pop(download_id, None)
                
                # Set headers to force download
                response = send_file(
                    img_io,
                    as_attachment=True,
                    download_name=filename,
                    mimetype='image/jpeg'
                )
                response.headers["Content-Disposition"] = f"attachment; filename={filename}"
                return response
            except Exception as e:
                print(f"Error processing image for download: {str(e)}")
                return str(e), 500
            
        except Exception as e:
            print(f"Error in download: {str(e)}")
            return str(e), 500

    # Serve static files from public directory
    @app.route('/<path:path>')
    def serve_static(path):
        return send_from_directory('public', path)

    # Serve generated images
    @app.route('/generated/<path:filename>')
    def serve_generated_image(filename):
        print(f"Attempting to serve image: {filename}")
        print(f"From directory: {app.config['GENERATED_FOLDER']}")
        
        file_path = os.path.join(app.config['GENERATED_FOLDER'], filename)
        
        if os.path.exists(file_path):
            print(f"Image file exists at: {file_path}")
            return send_file(file_path)
        else:
            print(f"Image file does not exist at: {file_path}")
            return "Image not found", 404

    @app.route('/api/usage/count', methods=['GET'])
    def get_usage_count():
        """Get the remaining anonymous usage count"""
        anonymous_id = request.cookies.get(ANONYMOUS_COOKIE_NAME)
        
        if not anonymous_id:
            # No anonymous ID yet, so full remaining usage
            response = jsonify({
                "usage_count": 0,
                "remaining": MAX_ANONYMOUS_USAGE,
                "authenticated": False
            })
            
            # Create a new anonymous ID
            new_anonymous_id = str(uuid.uuid4())
            response.set_cookie(ANONYMOUS_COOKIE_NAME, new_anonymous_id, max_age=60*60*24*365, httponly=True, samesite='Strict')
            return response
        
        # Check for JWT Authorization to see if user is logged in
        is_authenticated = False
        try:
            # Check for JWT Authorization header
            auth_header = request.headers.get('Authorization')
            if auth_header and auth_header.startswith('Bearer '):
                # User has a token, they're authenticated
                is_authenticated = True
        except:
            pass
        
        if is_authenticated:
            # Authenticated users have unlimited usage
            return jsonify({
                "usage_count": 0,
                "remaining": "unlimited",
                "authenticated": True
            })
        
        # Get usage count for anonymous ID
        from models import Redesign
        usage_count = Redesign.query.filter_by(anonymous_id=anonymous_id).count()
        
        return jsonify({
            "usage_count": usage_count,
            "remaining": max(0, MAX_ANONYMOUS_USAGE - usage_count),
            "authenticated": False
        })

except Exception as e:
    logger.critical(f"CRITICAL ERROR DURING STARTUP: {str(e)}")
    logger.critical(traceback.format_exc())
    
    # Create a fallback app that just reports the error
    fallback_app = Flask(__name__)
    
    @fallback_app.route('/')
    def error_index():
        return f"""
        <html>
        <head><title>Error Starting Application</title></head>
        <body>
            <h1>Application Error</h1>
            <p>There was an error starting the application:</p>
            <pre>{str(e)}</pre>
            <p>See logs for more details.</p>
        </body>
        </html>
        """, 500
    
    @fallback_app.route('/healthz')
    def healthz():
        return jsonify({"status": "error", "message": str(e)}), 500
    
    app = fallback_app

# Ensure the application listens on the port provided by Cloud Run
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port) 