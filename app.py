from flask import Flask, render_template, request, jsonify, Response
import os
import asyncio
import edge_tts
import uuid
import requests
import base64
from datetime import datetime
import json

app = Flask(__name__)

# Create directories
os.makedirs("static/outputs", exist_ok=True)

# ElevenLabs API endpoint
ELEVENLABS_API_URL = "https://api.elevenlabs.io/v1/text-to-speech"

# ElevenLabs Voice IDs (hardcoded for popular voices)
ELEVENLABS_VOICES = {
    'Neil': '21m00Tcm4TlvDq8ikWAM',  # Default ElevenLabs voice
    'Liam': 'TX3VdzNPVb7RfP5gUqHh',  # Replace with actual voice IDs
    'Marcus': 'i6wFwRZWy2X2gmtm3YyY',
    'Josh': 'o4M7Z0sZ3nX3jY8qRb1g',
    'Sam': 'z9f2Vv6N3sG4hY8rTq1p',
    'Daniel': 'x5g3FfR8tN2kL7wPq1zY',
    'Michael': 'j7q2WwE5rT3yU8iOp0zX',
    'David': 'k8p3GgF9sN2mL7hRq1zY'
}

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
        use_elevenlabs = data.get('use_elevenlabs', False)
        elevenlabs_api_key = data.get('elevenlabs_api_key', '')
        
        if not text:
            return jsonify({'success': False, 'error': 'Text is required'}), 400
        
        if len(text) > 5000:
            return jsonify({'success': False, 'error': 'Text exceeds 5000 characters'}), 400
        
        # If using ElevenLabs and voice is Neil or other ElevenLabs voices
        if use_elevenlabs and voice in ELEVENLABS_VOICES:
            return generate_elevenlabs_tts_internal(text, voice, elevenlabs_api_key)
        
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

def generate_elevenlabs_tts_internal(text, voice_name, api_key):
    """Internal function to generate ElevenLabs TTS"""
    try:
        if not api_key:
            return jsonify({'success': False, 'error': 'ElevenLabs API key is required'}), 400
        
        # Get voice ID
        voice_id = ELEVENLABS_VOICES.get(voice_name)
        if not voice_id:
            return jsonify({'success': False, 'error': f'Voice {voice_name} not found'}), 400
        
        # Generate unique filename
        filename = f"elevenlabs_{uuid.uuid4().hex}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3"
        output_path = os.path.join("static/outputs", filename)
        
        # Prepare the request to ElevenLabs API
        headers = {
            "xi-api-key": api_key,
            "Content-Type": "application/json"
        }
        
        payload = {
            "text": text,
            "model_id": "eleven_monolingual_v1",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75
            }
        }
        
        # Make request to ElevenLabs API
        response = requests.post(
            f"{ELEVENLABS_API_URL}/{voice_id}",
            headers=headers,
            json=payload
        )
        
        if response.status_code == 200:
            # Save the audio
            with open(output_path, 'wb') as f:
                f.write(response.content)
            
            return jsonify({
                'success': True,
                'audio_url': f'/static/outputs/{filename}',
                'filename': filename
            })
        else:
            error_msg = "Unknown error"
            try:
                error_data = response.json()
                error_msg = error_data.get('detail', {}).get('message', str(error_data))
            except:
                error_msg = response.text
            
            return jsonify({
                'success': False,
                'error': f'ElevenLabs API error: {error_msg}'
            }), response.status_code
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/elevenlabs/generate', methods=['POST'])
def generate_elevenlabs_tts():
    try:
        data = request.json
        text = data.get('text', '').strip()
        voice_name = data.get('voice_id', 'Neil')
        api_key = data.get('api_key', '')
        stability = data.get('stability', 0.5)
        similarity_boost = data.get('similarity_boost', 0.75)
        speed = data.get('speed', 1.0)
        pitch = data.get('pitch', 0)
        
        if not text:
            return jsonify({'success': False, 'error': 'Text is required'}), 400
        
        if not api_key:
            return jsonify({'success': False, 'error': 'ElevenLabs API key is required'}), 400
        
        # Get voice ID
        voice_id = ELEVENLABS_VOICES.get(voice_name)
        if not voice_id:
            return jsonify({'success': False, 'error': f'Voice {voice_name} not found'}), 400
        
        # Generate unique filename
        filename = f"elevenlabs_{uuid.uuid4().hex}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3"
        output_path = os.path.join("static/outputs", filename)
        
        # Prepare the request to ElevenLabs API
        headers = {
            "xi-api-key": api_key,
            "Content-Type": "application/json"
        }
        
        payload = {
            "text": text,
            "model_id": "eleven_monolingual_v1",
            "voice_settings": {
                "stability": stability,
                "similarity_boost": similarity_boost,
                "speed": speed,
                "pitch": pitch
            }
        }
        
        # Make request to ElevenLabs API
        response = requests.post(
            f"{ELEVENLABS_API_URL}/{voice_id}",
            headers=headers,
            json=payload
        )
        
        if response.status_code == 200:
            # Save the audio
            with open(output_path, 'wb') as f:
                f.write(response.content)
            
            return jsonify({
                'success': True,
                'audio_url': f'/static/outputs/{filename}',
                'filename': filename
            })
        else:
            error_msg = "Unknown error"
            try:
                error_data = response.json()
                error_msg = error_data.get('detail', {}).get('message', str(error_data))
            except:
                error_msg = response.text
            
            return jsonify({
                'success': False,
                'error': f'ElevenLabs API error: {error_msg}'
            }), response.status_code
        
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