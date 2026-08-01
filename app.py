from flask import Flask, render_template, request, jsonify, Response
import os
import asyncio
import edge_tts
import uuid
from datetime import datetime

app = Flask(__name__)

# Create directories
os.makedirs("static/outputs", exist_ok=True)

# =============================================
# HIGH-QUALITY VOICE PROFILES FOR OPTIMIZATION
# Each voice has optimal settings for clarity
# =============================================
VOICE_PROFILES = {
    # ----- VIRAL VOICES (Optimized for Urdu/Hindi) -----
    'en-US-AdamNeural': {
        'rate': '-2%',
        'pitch': '+0Hz'
    },
    'en-US-AntoniNeural': {
        'rate': '-3%',
        'pitch': '-1Hz'
    },
    'en-US-BellaNeural': {
        'rate': '-2%',
        'pitch': '+1Hz'
    },
    'en-US-RachelNeural': {
        'rate': '-2%',
        'pitch': '+0Hz'
    },
    'en-US-EmilyNeural': {
        'rate': '-2%',
        'pitch': '+1Hz'
    },
    'en-US-NeilNeural': {
        'rate': '-3%',
        'pitch': '+0Hz'
    },
    'en-US-LiamNeural': {
        'rate': '-3%',
        'pitch': '-1Hz'
    },
    'en-US-MarcusNeural': {
        'rate': '-2%',
        'pitch': '+0Hz'
    },
    # ----- URDU / HINDI VOICES (Crystal Clear) -----
    'ur-PK-UzmaNeural': {
        'rate': '-5%',
        'pitch': '+0Hz'
    },
    'ur-PK-AsadNeural': {
        'rate': '-5%',
        'pitch': '-2Hz'
    },
    'hi-IN-SwaraNeural': {
        'rate': '-3%',
        'pitch': '+0Hz'
    },
    'hi-IN-MadhurNeural': {
        'rate': '-3%',
        'pitch': '-1Hz'
    },
    # ----- OTHER LANGUAGES (Default Profiles) -----
    'default': {
        'rate': '+0%',
        'pitch': '+0Hz'
    }
}

# Style mappings - applied ON TOP of the voice profile
STYLE_SETTINGS = {
    'neutral': {'rate': '+0%', 'pitch': '+0Hz'},
    'cheerful': {'rate': '+5%', 'pitch': '+3Hz'},
    'sad': {'rate': '-10%', 'pitch': '-5Hz'},
    'angry': {'rate': '+10%', 'pitch': '+8Hz'},
    'whisper': {'rate': '-15%', 'pitch': '-3Hz'},
    'narration': {'rate': '-5%', 'pitch': '+0Hz'},
    'excited': {'rate': '+8%', 'pitch': '+5Hz'},
    'friendly': {'rate': '+3%', 'pitch': '+2Hz'},
    'hopeful': {'rate': '+0%', 'pitch': '+3Hz'}
}

@app.route('/')
def home():
    return render_template('index.html')

def _combine_percentages(base, style, user, param_type='rate'):
    """
    Safely combine rate/pitch percentages.
    Base + Style + User with clamping to valid ranges.
    """
    try:
        # Extract numeric values
        base_val = int(base.replace('%', '').replace('Hz', '').replace('+', '').replace('-', ''))
        style_val = int(style.replace('%', '').replace('Hz', '').replace('+', '').replace('-', ''))
        user_val = int(user.replace('%', '').replace('Hz', '').replace('+', '').replace('-', ''))
        
        # Preserve signs
        if base.startswith('-'):
            base_val = -base_val
        if style.startswith('-'):
            style_val = -style_val
        if user.startswith('-'):
            user_val = -user_val
        
        # Combine
        final_val = base_val + style_val + user_val
        
        # Clamp to reasonable ranges based on parameter type
        if 'rate' in param_type:
            final_val = max(-50, min(50, final_val))
            suffix = '%'
        else:  # pitch
            final_val = max(-20, min(20, final_val))
            suffix = 'Hz'
            
        return f"{'+' if final_val >= 0 else ''}{final_val}{suffix}"
    except:
        return user  # Fallback to user value

@app.route('/api/generate', methods=['POST'])
def generate_tts():
    try:
        data = request.json
        text = data.get('text', '').strip()
        voice = data.get('voice', 'ur-PK-UzmaNeural')
        user_rate = data.get('rate', '+0%')
        user_pitch = data.get('pitch', '+0Hz')
        style = data.get('style', 'neutral')
        
        if not text:
            return jsonify({'success': False, 'error': 'Text is required'}), 400
        
        if len(text) > 5000:
            return jsonify({'success': False, 'error': 'Text exceeds 5000 characters'}), 400
        
        # Generate unique filename
        filename = f"{uuid.uuid4().hex}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3"
        output_path = os.path.join("static/outputs", filename)
        
        # ===== LAYERED OPTIMIZATION LOGIC =====
        # 1. Get the voice-specific optimal profile
        voice_profile = VOICE_PROFILES.get(voice, VOICE_PROFILES['default'])
        base_rate = voice_profile['rate']
        base_pitch = voice_profile['pitch']
        
        # 2. Get style adjustments
        style_settings = STYLE_SETTINGS.get(style, STYLE_SETTINGS['neutral'])
        style_rate = style_settings['rate']
        style_pitch = style_settings['pitch']
        
        # 3. Combine all layers (Base + Style + User)
        final_rate = _combine_percentages(base_rate, style_rate, user_rate, 'rate')
        final_pitch = _combine_percentages(base_pitch, style_pitch, user_pitch, 'pitch')
        
        # ===== GENERATE AUDIO USING OPTIMIZED PARAMS =====
        async def generate():
            communicate = edge_tts.Communicate(text, voice, rate=final_rate, pitch=final_pitch)
            await communicate.save(output_path)
        
        asyncio.run(generate())
        
        return jsonify({
            'success': True, 
            'audio_url': f'/static/outputs/{filename}',
            'filename': filename,
            'debug': f'Voice: {voice}, Rate: {final_rate}, Pitch: {final_pitch}, Style: {style}'
        })
        
    except Exception as e:
        print(f"Error: {str(e)}")  # Log for debugging
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/stream', methods=['POST'])
def stream_tts():
    try:
        data = request.json
        text = data.get('text', '').strip()
        voice = data.get('voice', 'ur-PK-UzmaNeural')
        rate = data.get('rate', '+0%')
        pitch = data.get('pitch', '+0Hz')
        
        if not text:
            return jsonify({'error': 'Text is required'}), 400
        
        async def generate_audio():
            communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    yield chunk["data"]
        
        return Response(generate_audio(), mimetype='audio/mpeg')
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)