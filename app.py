from flask import Flask, render_template, request, jsonify, Response
import os
import asyncio
import edge_tts
import uuid
from datetime import datetime

app = Flask(__name__)

# Create directories
os.makedirs("static/outputs", exist_ok=True)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/generate', methods=['POST'])
def generate_tts():
    try:
        data = request.json
        text = data.get('text', '').strip()
        voice = data.get('voice', 'en-US-AriaNeural')
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
        
        # Style-based adjustments for Edge TTS
        style_settings = {
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
        
        if style in style_settings:
            rate = style_settings[style]['rate']
            pitch = style_settings[style]['pitch']
        
        # Generate audio using Edge TTS
        async def generate():
            communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
            await communicate.save(output_path)
        
        asyncio.run(generate())
        
        return jsonify({
            'success': True, 
            'audio_url': f'/static/outputs/{filename}',
            'filename': filename
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/stream', methods=['POST'])
def stream_tts():
    try:
        data = request.json
        text = data.get('text', '').strip()
        voice = data.get('voice', 'en-US-AriaNeural')
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