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
# Each voice has its own optimal rate & pitch
# =============================================
VOICE_PROFILES = {
    'ur-PK-UzmaNeural': {'rate': '+0%', 'pitch': '+0Hz'},      # Crystal clear Urdu
    'ur-PK-AsadNeural': {'rate': '+0%', 'pitch': '-1Hz'},       # Deep, natural Urdu
    'hi-IN-SwaraNeural': {'rate': '+0%', 'pitch': '+0Hz'},      # Crisp Hindi
    'hi-IN-MadhurNeural': {'rate': '+0%', 'pitch': '-1Hz'},     # Warm, natural Hindi
    # Default for all other voices
    'default': {'rate': '+0%', 'pitch': '+0Hz'}
}

# Style mappings - these get applied ON TOP of the voice profile
STYLE_SETTINGS = {
    'neutral': {'rate': '+0%', 'pitch': '+0Hz'},
    'cheerful': {'rate': '+5%', 'pitch': '+2Hz'},
    'sad': {'rate': '-10%', 'pitch': '-5Hz'},
    'angry': {'rate': '+10%', 'pitch': '+8Hz'},
    'whisper': {'rate': '-15%', 'pitch': '-3Hz'},
    'narration': {'rate': '-5%', 'pitch': '+0Hz'},
    'excited': {'rate': '+8%', 'pitch': '+5Hz'},
    'friendly': {'rate': '+3%', 'pitch': '+1Hz'},
    'hopeful': {'rate': '+0%', 'pitch': '+2Hz'}
}

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/generate', methods=['POST'])
def generate_tts():
    try:
        data = request.json
        text = data.get('text', '').strip()
        voice = data.get('voice', 'ur-PK-UzmaNeural')
        rate = data.get('rate', '+0%')
        pitch = data.get('pitch', '+0Hz')
        style = data.get('style', 'neutral')
        
        if not text:
            return jsonify({'success': False, 'error': 'Text is required'}), 400
        
        if len(text) > 5000:
            return jsonify({'success': False, 'error': 'Text exceeds 5000 characters'}), 400
        
        # Generate unique filename
        filename = f"{uuid.uuid4().hex}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3"
        output_path = os.path.join("static/outputs", filename)
        
        # ===== VOICE OPTIMIZATION LOGIC =====
        # 1. Start with the voice-specific optimal profile
        voice_profile = VOICE_PROFILES.get(voice, VOICE_PROFILES['default'])
        final_rate = voice_profile['rate']
        final_pitch = voice_profile['pitch']
        
        # 2. Apply style adjustments ON TOP of the voice profile
        if style in STYLE_SETTINGS:
            style_rate = STYLE_SETTINGS[style]['rate']
            style_pitch = STYLE_SETTINGS[style]['pitch']
            # Combine: Add the style rate/pitch to the base profile
            # Simple string manipulation - extract numeric values and add
            try:
                base_rate_val = int(voice_profile['rate'].replace('%', '').replace('+', ''))
                style_rate_val = int(style_rate.replace('%', '').replace('+', ''))
                final_rate_val = base_rate_val + style_rate_val
                final_rate = f"{'+' if final_rate_val >= 0 else ''}{final_rate_val}%"
                
                base_pitch_val = int(voice_profile['pitch'].replace('Hz', '').replace('+', ''))
                style_pitch_val = int(style_pitch.replace('Hz', '').replace('+', ''))
                final_pitch_val = base_pitch_val + style_pitch_val
                final_pitch = f"{'+' if final_pitch_val >= 0 else ''}{final_pitch_val}Hz"
            except:
                # Fallback if parsing fails
                final_rate = voice_profile['rate']
                final_pitch = voice_profile['pitch']
        
        # 3. Override with user-provided rate/pitch if they are not default
        # (This ensures user sliders still work)
        if rate != '+0%':
            final_rate = rate
        if pitch != '+0Hz':
            final_pitch = pitch
        
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