from flask import Flask, render_template, request, jsonify, send_file, send_from_directory
import os
import asyncio
import edge_tts
import uuid
import json
from datetime import datetime
import logging
import time
from pathlib import Path
import subprocess
import platform

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here-change-in-production'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Create necessary directories
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / 'static'
OUTPUT_DIR = STATIC_DIR / 'outputs'
CACHE_DIR = STATIC_DIR / 'cache'
CAMERA_DIR = BASE_DIR / 'camera'
PLAYER_DIR = BASE_DIR / 'player'

for directory in [OUTPUT_DIR, CACHE_DIR, CAMERA_DIR, PLAYER_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# Available voices with metadata
VOICES = {
    'en-US-AriaNeural': {'gender': 'Female', 'locale': 'en-US', 'name': 'Aria (US)'},
    'en-US-JennyNeural': {'gender': 'Female', 'locale': 'en-US', 'name': 'Jenny (US)'},
    'en-US-GuyNeural': {'gender': 'Male', 'locale': 'en-US', 'name': 'Guy (US)'},
    'en-GB-SoniaNeural': {'gender': 'Female', 'locale': 'en-GB', 'name': 'Sonia (UK)'},
    'en-GB-RyanNeural': {'gender': 'Male', 'locale': 'en-GB', 'name': 'Ryan (UK)'},
    'en-IN-NeerjaNeural': {'gender': 'Female', 'locale': 'en-IN', 'name': 'Neerja (India)'},
    'en-IN-PrabhatNeural': {'gender': 'Male', 'locale': 'en-IN', 'name': 'Prabhat (India)'},
    'en-AU-NatashaNeural': {'gender': 'Female', 'locale': 'en-AU', 'name': 'Natasha (Australia)'},
    'en-AU-WilliamNeural': {'gender': 'Male', 'locale': 'en-AU', 'name': 'William (Australia)'},
}

# Voice styles for emotional speech
VOICE_STYLES = {
    'default': 'Default',
    'cheerful': 'Cheerful',
    'sad': 'Sad',
    'angry': 'Angry',
    'fearful': 'Fearful',
    'excited': 'Excited',
    'gentle': 'Gentle',
    'hopeful': 'Hopeful'
}

# Audio quality presets
AUDIO_QUALITY = {
    'low': {'bitrate': '16k', 'sample_rate': 16000},
    'medium': {'bitrate': '24k', 'sample_rate': 24000},
    'high': {'bitrate': '48k', 'sample_rate': 48000},
    'studio': {'bitrate': '192k', 'sample_rate': 48000}
}

# Rate and pitch ranges
RATE_RANGES = {'min': -50, 'max': 50, 'default': 0}
PITCH_RANGES = {'min': -50, 'max': 50, 'default': 0}

class TTSService:
    """Singleton TTS service with caching and error handling"""
    
    _instance = None
    _cache = {}
    _cache_max_size = 100
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    async def generate_tts(self, text, voice="en-US-AriaNeural", rate=0, pitch=0, 
                           volume=100, style="default", quality="medium"):
        """Generate TTS with advanced parameters"""
        
        # Create cache key
        cache_key = f"{text}_{voice}_{rate}_{pitch}_{volume}_{style}_{quality}"
        
        # Check cache
        if cache_key in self._cache:
            logger.info(f"Returning cached TTS for: {text[:50]}...")
            return self._cache[cache_key]
        
        try:
            # Generate unique filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_id = str(uuid.uuid4())[:8]
            filename = f"tts_{timestamp}_{unique_id}.mp3"
            output_path = OUTPUT_DIR / filename
            
            # Build voice parameters
            voice_params = self._build_voice_params(voice, rate, pitch, style, quality)
            
            # Generate TTS
            communicate = edge_tts.Communicate(text, voice_params['voice'])
            
            # Save with quality settings
            await communicate.save(str(output_path))
            
            # Verify file exists
            if not output_path.exists():
                raise Exception("TTS generation failed - file not created")
            
            # Get file size
            file_size = output_path.stat().st_size
            
            # Cache result
            result = {
                'filename': filename,
                'path': str(output_path),
                'url': f'/static/outputs/{filename}',
                'size': file_size,
                'duration': self._estimate_duration(text),
                'parameters': {
                    'voice': voice,
                    'rate': rate,
                    'pitch': pitch,
                    'volume': volume,
                    'style': style,
                    'quality': quality
                }
            }
            
            # Manage cache size
            if len(self._cache) >= self._cache_max_size:
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
            
            self._cache[cache_key] = result
            logger.info(f"TTS generated successfully: {filename}")
            
            return result
            
        except Exception as e:
            logger.error(f"TTS generation error: {str(e)}")
            raise
    
    def _build_voice_params(self, voice, rate, pitch, style, quality):
        """Build voice parameters with proper formatting"""
        
        # Base voice
        voice_data = {
            'voice': voice,
            'rate': f"{rate}%",
            'pitch': f"{pitch}Hz",
            'volume': f"{volume}%",
        }
        
        # Add style if not default
        if style != 'default':
            voice_data['style'] = style
        
        return voice_data
    
    def _estimate_duration(self, text):
        """Estimate audio duration based on text length (rough estimate)"""
        words = len(text.split())
        # Average reading speed: ~150 words per minute
        duration_seconds = (words / 150) * 60
        return max(0.5, round(duration_seconds, 1))
    
    def cleanup_old_files(self, max_age_seconds=3600):
        """Clean up old audio files to prevent disk space issues"""
        try:
            current_time = time.time()
            for file in OUTPUT_DIR.glob("*.mp3"):
                file_age = current_time - file.stat().st_mtime
                if file_age > max_age_seconds:
                    file.unlink()
                    logger.info(f"Deleted old file: {file.name}")
        except Exception as e:
            logger.error(f"Cleanup error: {str(e)}")

# Initialize TTS service
tts_service = TTSService()

@app.route('/')
def home():
    """Main page with enhanced UI and camera info"""
    return render_template('index.html', 
                         voices=VOICES,
                         styles=VOICE_STYLES)

@app.route('/api/voices')
def get_voices():
    """Get available voices with metadata"""
    return jsonify(VOICES)

@app.route('/api/generate-tts', methods=['POST'])
def generate_tts():
    """Enhanced TTS generation endpoint"""
    try:
        # Get request data
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Invalid request data'}), 400
        
        text = data.get('text', '').strip()
        if not text:
            return jsonify({'error': 'Text is required'}), 400
        
        # Validate text length
        if len(text) > 5000:
            return jsonify({'error': 'Text too long (max 5000 characters)'}), 400
        
        # Get parameters with defaults
        voice = data.get('voice', 'en-US-AriaNeural')
        if voice not in VOICES:
            return jsonify({'error': f'Invalid voice: {voice}'}), 400
        
        rate = int(data.get('rate', 0))
        pitch = int(data.get('pitch', 0))
        volume = int(data.get('volume', 100))
        style = data.get('style', 'default')
        quality = data.get('quality', 'medium')
        
        # Validate ranges
        rate = max(RATE_RANGES['min'], min(RATE_RANGES['max'], rate))
        pitch = max(PITCH_RANGES['min'], min(PITCH_RANGES['max'], pitch))
        volume = max(0, min(100, volume))
        
        # Generate TTS
        result = asyncio.run(
            tts_service.generate_tts(
                text=text,
                voice=voice,
                rate=rate,
                pitch=pitch,
                volume=volume,
                style=style,
                quality=quality
            )
        )
        
        # Cleanup old files periodically
        tts_service.cleanup_old_files(max_age_seconds=3600)
        
        return jsonify({
            'success': True,
            'message': 'TTS generated successfully',
            'data': result
        })
        
    except Exception as e:
        logger.error(f"Error in generate_tts: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/download/<filename>')
def download_audio(filename):
    """Download generated audio file"""
    try:
        file_path = OUTPUT_DIR / filename
        if not file_path.exists():
            return jsonify({'error': 'File not found'}), 404
        
        return send_file(
            file_path,
            as_attachment=True,
            download_name=filename,
            mimetype='audio/mpeg'
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/delete/<filename>', methods=['DELETE'])
def delete_audio(filename):
    """Delete audio file"""
    try:
        file_path = OUTPUT_DIR / filename
        if file_path.exists():
            file_path.unlink()
            return jsonify({'success': True, 'message': 'File deleted'})
        return jsonify({'error': 'File not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/clear-all', methods=['DELETE'])
def clear_all_audio():
    """Clear all generated audio files"""
    try:
        files_deleted = 0
        for file in OUTPUT_DIR.glob("*.mp3"):
            file.unlink()
            files_deleted += 1
        return jsonify({
            'success': True,
            'message': f'Cleared {files_deleted} audio files'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============= UNITY CAMERA SCRIPT ROUTES =============

@app.route('/api/camera-scripts')
def get_camera_scripts():
    """Get all camera scripts content"""
    try:
        scripts = {}
        camera_file = CAMERA_DIR / 'PubgCamera.cs'
        player_file = PLAYER_DIR / 'PlayerRotate.cs'
        
        if camera_file.exists():
            with open(camera_file, 'r', encoding='utf-8') as f:
                scripts['pubg_camera'] = f.read()
        
        if player_file.exists():
            with open(player_file, 'r', encoding='utf-8') as f:
                scripts['player_rotate'] = f.read()
        
        return jsonify({
            'success': True,
            'scripts': scripts,
            'files': {
                'camera': str(camera_file),
                'player': str(player_file)
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/save-camera-script', methods=['POST'])
def save_camera_script():
    """Save camera script to file"""
    try:
        data = request.get_json()
        script_type = data.get('type', 'camera')  # 'camera' or 'player'
        content = data.get('content', '')
        
        if not content:
            return jsonify({'error': 'Content is required'}), 400
        
        if script_type == 'camera':
            file_path = CAMERA_DIR / 'PubgCamera.cs'
        else:
            file_path = PLAYER_DIR / 'PlayerRotate.cs'
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return jsonify({
            'success': True,
            'message': f'{script_type} script saved successfully',
            'file': str(file_path)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/create-unity-package')
def create_unity_package():
    """Create a Unity package with all scripts"""
    try:
        # Create a temporary directory for package
        import shutil
        import zipfile
        
        package_dir = BASE_DIR / 'unity_package'
        package_dir.mkdir(exist_ok=True)
        
        # Copy scripts to package
        shutil.copytree(CAMERA_DIR, package_dir / 'Camera', dirs_exist_ok=True)
        shutil.copytree(PLAYER_DIR, package_dir / 'Player', dirs_exist_ok=True)
        
        # Create readme
        readme_content = """# PUBG-Style Camera System for Unity

## Installation
1. Copy the scripts to your Unity project's Assets folder
2. Attach to your player game object

## Features
- PUBG-style third-person camera
- Advanced player rotation
- Mouse orbit controls
- Smooth transitions
- Wall collision detection
- Weapon sway
- Camera bobbing
- ADS (Aim Down Sight)
- Sprint, Crouch, Prone support

## Usage
1. Attach PubgCamera.cs to your camera
2. Attach PlayerRotate.cs to your player
3. Assign references in inspector
4. Configure settings as needed

## Controls
- Mouse Movement: Look around
- Right Click: ADS
- Shift: Sprint
- Ctrl: Crouch
- Z: Prone
- Q/E: Peek

For detailed documentation, visit the project repository.
"""
        
        with open(package_dir / 'README.txt', 'w') as f:
            f.write(readme_content)
        
        # Create zip file
        zip_path = BASE_DIR / 'UnityCameraPackage.zip'
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for root, dirs, files in os.walk(package_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, package_dir)
                    zipf.write(file_path, arcname)
        
        # Cleanup temp directory
        shutil.rmtree(package_dir)
        
        return send_file(
            zip_path,
            as_attachment=True,
            download_name='UnityCameraPackage.zip',
            mimetype='application/zip'
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Resource not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    # Production-ready settings
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True,  # Set to False in production
        threaded=True,
        use_reloader=False
    )