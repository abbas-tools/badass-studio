from flask import Flask, render_template, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
import os
import json
import uuid
import base64
from datetime import datetime
import requests
import edge_tts
import asyncio
import io
import random
from PIL import Image, ImageDraw, ImageFont
import numpy as np

app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)

# Configure upload folders
UPLOAD_FOLDER = 'static/uploads'
AUDIO_FOLDER = 'static/audio'
IMAGE_FOLDER = 'static/images'
VIDEO_FOLDER = 'static/videos'

for folder in [UPLOAD_FOLDER, AUDIO_FOLDER, IMAGE_FOLDER, VIDEO_FOLDER]:
    os.makedirs(folder, exist_ok=True)

# ============================================
# VOICE GENERATION (Edge TTS)
# ============================================

async def generate_tts_audio(text, voice, rate, pitch, style):
    """Generate TTS audio using Edge TTS"""
    try:
        # Create SSML with style support
        ssml = f'''<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" 
                    xmlns:mstts="http://www.w3.org/2001/mstts" xml:lang="en-US">
            <voice name="{voice}">
                <prosody rate="{rate}" pitch="{pitch}">
                    <mstts:express-as style="{style}" styledegree="1.0">
                        {text}
                    </mstts:express-as>
                </prosody>
            </voice>
        </speak>'''
        
        # Generate audio
        communicate = edge_tts.Communicate(ssml, voice)
        audio_data = b""
        
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data += chunk["data"]
        
        # Save audio file
        filename = f"voice_{uuid.uuid4().hex[:8]}.mp3"
        filepath = os.path.join(AUDIO_FOLDER, filename)
        
        with open(filepath, 'wb') as f:
            f.write(audio_data)
        
        return {
            'success': True,
            'audio_url': f'/static/audio/{filename}',
            'filename': filename
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

@app.route('/generate-voice', methods=['POST'])
def generate_voice():
    """Generate voice from text using Edge TTS"""
    try:
        data = request.get_json()
        text = data.get('text', '')
        voice = data.get('voice', 'en-US-JennyNeural')
        rate = data.get('rate', '0%')
        pitch = data.get('pitch', '0Hz')
        style = data.get('style', 'neutral')
        
        if not text:
            return jsonify({'success': False, 'error': 'No text provided'})
        
        # Run async function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(
            generate_tts_audio(text, voice, rate, pitch, style)
        )
        loop.close()
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ============================================
# IMAGE GENERATION (Simulated with Unsplash/Picsum)
# ============================================

@app.route('/generate-image', methods=['POST'])
def generate_image():
    """Generate image from text prompt (simulated)"""
    try:
        data = request.get_json()
        prompt = data.get('prompt', '')
        
        if not prompt:
            return jsonify({'success': False, 'error': 'No prompt provided'})
        
        # For demo, use picsum with seed based on prompt
        seed = hash(prompt) % 10000
        image_url = f'https://picsum.photos/seed/{seed}/800/600'
        
        # In production, you could use:
        # - Stable Diffusion API
        # - DALL-E API
        # - Replicate.com
        
        return jsonify({
            'success': True,
            'image_url': image_url,
            'prompt': prompt
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ============================================
# LIP SYNC (Simulated)
# ============================================

@app.route('/lip-sync', methods=['POST'])
def process_lip_sync():
    """Process lip sync with uploaded files (simulated)"""
    try:
        if 'avatar' not in request.files or 'audio' not in request.files:
            return jsonify({'success': False, 'error': 'Avatar and audio required'})
        
        avatar = request.files['avatar']
        audio = request.files['audio']
        
        if avatar.filename == '' or audio.filename == '':
            return jsonify({'success': False, 'error': 'Empty files'})
        
        # Save uploaded files
        avatar_filename = f"avatar_{uuid.uuid4().hex[:8]}.jpg"
        audio_filename = f"audio_{uuid.uuid4().hex[:8]}.mp3"
        
        avatar_path = os.path.join(UPLOAD_FOLDER, avatar_filename)
        audio_path = os.path.join(AUDIO_FOLDER, audio_filename)
        
        avatar.save(avatar_path)
        audio.save(audio_path)
        
        # For demo, create a simple animated video placeholder
        # In production, you would use:
        # - Wav2Lip
        # - SadTalker
        # - Google's Lip Sync API
        
        # Simulate processing time
        import time
        time.sleep(2)
        
        # Create a simple video file (simulated)
        video_filename = f"lip_sync_{uuid.uuid4().hex[:8]}.mp4"
        video_path = os.path.join(VIDEO_FOLDER, video_filename)
        
        # For demo, create a placeholder video file
        # In reality, you'd generate actual video with lip sync
        with open(video_path, 'w') as f:
            f.write("This is a placeholder for the generated video")
        
        return jsonify({
            'success': True,
            'video_url': f'/static/videos/{video_filename}',
            'message': 'Lip sync processing complete (simulated)'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ============================================
# SERVE STATIC FILES
# ============================================

@app.route('/static/<path:path>')
def serve_static(path):
    """Serve static files"""
    return send_from_directory('static', path)

# ============================================
# MAIN ROUTE - Serve the HTML
# ============================================

@app.route('/')
def index():
    """Serve the main page"""
    # Read the HTML content from the frontend code
    html_content = '''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Badass Media Studio · AI Voice + Image + Lip Sync</title>
  <!-- Font & Icons -->
  <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css">
  <style>
    /* ----- MODERN DARK THEME (inspired by original Badass) ----- */
    * {
      margin: 0;
      padding: 0;
      box-sizing: border-box;
      font-family: 'Outfit', sans-serif;
    }

    body {
      background: #070913;
      background-image: radial-gradient(circle at 20% 30%, rgba(255, 42, 95, 0.12) 0%, transparent 40%),
                        radial-gradient(circle at 80% 70%, rgba(0, 242, 254, 0.12) 0%, transparent 40%);
      min-height: 100vh;
      display: flex;
      justify-content: center;
      align-items: center;
      padding: 24px;
      color: #ffffff;
    }

    .container {
      width: 100%;
      max-width: 820px;
      background: rgba(18, 22, 38, 0.8);
      backdrop-filter: blur(20px);
      -webkit-backdrop-filter: blur(20px);
      border: 1px solid rgba(255, 255, 255, 0.08);
      border-radius: 32px;
      padding: 32px 30px;
      box-shadow: 0 25px 60px rgba(0, 0, 0, 0.7), 0 0 40px rgba(255, 42, 95, 0.15);
      transition: all 0.2s ease;
    }

    /* ----- HEADER / LOGO (Badass Studio flavour) ----- */
    .logo-area {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 14px;
      margin-bottom: 8px;
    }

    .logo-icon {
      font-size: 2.6rem;
      animation: pulse-glow 2.6s infinite;
    }
    @keyframes pulse-glow {
      0% { transform: scale(1); filter: drop-shadow(0 0 2px #ff2a5f); }
      50% { transform: scale(1.08); filter: drop-shadow(0 0 18px #ff2a5f); }
      100% { transform: scale(1); filter: drop-shadow(0 0 2px #ff2a5f); }
    }

    header h1 {
      font-size: 2.4rem;
      font-weight: 800;
      background: linear-gradient(135deg, #ff2a5f, #ff7e5f, #00f2fe);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
      letter-spacing: -0.5px;
    }

    .tagline {
      text-align: center;
      color: #94a3b8;
      font-weight: 300;
      letter-spacing: 0.6px;
      margin-bottom: 28px;
      font-size: 0.95rem;
      border-bottom: 1px solid rgba(255,255,255,0.05);
      padding-bottom: 18px;
    }
    .tagline i {
      color: #ff2a5f;
      margin: 0 6px;
    }

    /* ----- TABS (glass-morphism) ----- */
    .tabs {
      display: flex;
      gap: 10px;
      background: rgba(0, 0, 0, 0.35);
      padding: 6px;
      border-radius: 60px;
      border: 1px solid rgba(255, 255, 255, 0.06);
      margin-bottom: 32px;
      backdrop-filter: blur(4px);
    }

    .tab-btn {
      flex: 1;
      background: transparent;
      color: #94a3b8;
      border: none;
      padding: 14px 8px;
      border-radius: 40px;
      font-weight: 600;
      font-size: 0.95rem;
      cursor: pointer;
      transition: 0.3s ease;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
    }
    .tab-btn i {
      font-size: 1.1rem;
    }
    .tab-btn:hover {
      color: #fff;
      background: rgba(255, 255, 255, 0.04);
    }
    .tab-btn.active {
      background: linear-gradient(135deg, #ff2a5f, #ff5e62);
      color: white;
      box-shadow: 0 4px 18px rgba(255, 42, 95, 0.5);
    }

    /* ----- CONTENT CARDS ----- */
    .tab-content {
      display: none;
      animation: fadeSlide 0.35s ease forwards;
    }
    .tab-content.active {
      display: block;
    }
    @keyframes fadeSlide {
      0% { opacity: 0; transform: translateY(10px); }
      100% { opacity: 1; transform: translateY(0); }
    }

    .card h2 {
      font-size: 1.5rem;
      font-weight: 600;
      margin-bottom: 12px;
      display: flex;
      align-items: center;
      gap: 12px;
    }
    .card h2 i {
      color: #ff2a5f;
      font-size: 1.6rem;
    }
    .card p {
      color: #94a3b8;
      font-size: 0.9rem;
      margin-bottom: 18px;
      line-height: 1.5;
    }

    /* ----- FORM ELEMENTS (unified dark style) ----- */
    textarea, select, input[type="file"] {
      width: 100%;
      background: rgba(7, 9, 19, 0.75);
      border: 1px solid rgba(255, 255, 255, 0.08);
      color: #fff;
      border-radius: 16px;
      padding: 16px 18px;
      font-size: 1rem;
      outline: none;
      transition: 0.2s ease;
      margin-bottom: 18px;
      backdrop-filter: blur(4px);
    }
    textarea {
      resize: vertical;
      min-height: 120px;
    }
    select {
      appearance: none;
      background-image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2"><path d="M6 9l6 6 6-6"/></svg>');
      background-repeat: no-repeat;
      background-position: right 18px center;
      background-size: 16px;
    }
    textarea:focus, select:focus, input[type="file"]:focus {
      border-color: #ff2a5f;
      box-shadow: 0 0 0 4px rgba(255, 42, 95, 0.15);
    }
    input[type="file"] {
      padding: 14px;
      cursor: pointer;
      color: #94a3b8;
    }
    input[type="file"]::file-selector-button {
      background: rgba(255,42,95,0.2);
      border: none;
      color: white;
      padding: 8px 18px;
      border-radius: 30px;
      font-weight: 600;
      margin-right: 14px;
      cursor: pointer;
      transition: 0.2s;
    }
    input[type="file"]::file-selector-button:hover {
      background: #ff2a5f;
      box-shadow: 0 0 16px rgba(255,42,95,0.4);
    }

    /* ----- ACTION BUTTON (primary) ----- */
    .action-btn {
      background: linear-gradient(135deg, #ff2a5f, #ff5e62);
      color: white;
      border: none;
      padding: 16px 20px;
      width: 100%;
      border-radius: 40px;
      font-weight: 700;
      font-size: 1.05rem;
      cursor: pointer;
      transition: all 0.3s ease;
      box-shadow: 0 4px 20px rgba(255, 42, 95, 0.35);
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 12px;
      letter-spacing: 0.3px;
    }
    .action-btn i {
      font-size: 1.2rem;
    }
    .action-btn:hover {
      transform: translateY(-3px);
      box-shadow: 0 10px 30px rgba(255, 42, 95, 0.6);
    }
    .action-btn:active {
      transform: scale(0.97);
    }

    /* ----- RESULT BOX (with subtle glow) ----- */
    .result-box {
      margin-top: 22px;
      padding: 16px 14px;
      background: rgba(0, 0, 0, 0.3);
      border-radius: 20px;
      border: 1px solid rgba(255, 255, 255, 0.04);
      text-align: center;
      color: #b9c7e0;
      font-size: 0.95rem;
      transition: 0.2s;
      min-height: 60px;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
    }
    .result-box audio {
      width: 100%;
      border-radius: 40px;
      margin-top: 6px;
    }
    .result-box img {
      max-width: 100%;
      max-height: 300px;
      border-radius: 16px;
      margin: 8px 0;
      border: 1px solid rgba(255,255,255,0.06);
      box-shadow: 0 8px 24px rgba(0,0,0,0.6);
    }
    .result-box .lip-sync-placeholder {
      font-size: 1rem;
      padding: 20px 0;
    }

    /* ----- TOAST / mini notif (reused from original) ----- */
    .toast {
      position: fixed;
      bottom: 30px;
      left: 50%;
      transform: translateX(-50%);
      background: rgba(255, 42, 95, 0.95);
      backdrop-filter: blur(12px);
      color: white;
      padding: 14px 30px;
      border-radius: 60px;
      font-weight: 500;
      font-size: 0.95rem;
      box-shadow: 0 12px 40px rgba(0, 0, 0, 0.6);
      z-index: 999;
      border: 1px solid rgba(255,255,255,0.1);
      animation: slideUp 0.3s ease;
      max-width: 90%;
    }
    .toast.error {
      background: rgba(220, 50, 50, 0.95);
    }
    @keyframes slideUp {
      0% { opacity: 0; transform: translateX(-50%) translateY(20px); }
      100% { opacity: 1; transform: translateX(-50%) translateY(0); }
    }

    /* ----- responsiveness ----- */
    @media (max-width: 600px) {
      .container { padding: 20px 16px; }
      header h1 { font-size: 1.9rem; }
      .tab-btn { font-size: 0.8rem; padding: 12px 6px; }
      .tab-btn i { margin-right: 2px; }
      .action-btn { font-size: 0.95rem; }
    }
  </style>
</head>
<body>

<div class="container">
  <!-- HEADER with Badass Studio vibe -->
  <div class="logo-area">
    <span class="logo-icon">🔥</span>
    <header>
      <h1>Badass Media Studio</h1>
    </header>
  </div>
  <div class="tagline">
    <i class="fas fa-bolt"></i> AI Voice · Text to Picture · Neural Lip Sync <i class="fas fa-bolt"></i>
  </div>

  <!-- TABS -->
  <div class="tabs">
    <button class="tab-btn active" onclick="switchTab(event, 'voiceSection')"><i class="fas fa-microphone-alt"></i> Voice</button>
    <button class="tab-btn" onclick="switchTab(event, 'imageSection')"><i class="fas fa-image"></i> Image</button>
    <button class="tab-btn" onclick="switchTab(event, 'lipSyncSection')"><i class="fas fa-comment-dots"></i> Lip Sync</button>
  </div>

  <!-- ====== VOICE TAB ====== -->
  <div id="voiceSection" class="tab-content active">
    <div class="card">
      <h2><i class="fas fa-wave-square"></i> AI Voice Generator</h2>
      <p>Type any text – from a speech to a poem – and get a natural AI voice.</p>
      <textarea id="voiceText" placeholder="Enter your text here (supports English, Urdu, Hindi, etc.)">Assalam o Alaikum! Badass Studio is live.</textarea>
      <select id="voiceSelect">
        <optgroup label="🇺🇸 English">
          <option value="en-US-AriaNeural">Aria (Female)</option>
          <option value="en-US-GuyNeural">Guy (Male)</option>
          <option value="en-US-JennyNeural">Jenny (Female)</option>
        </optgroup>
        <optgroup label="🇵🇰 Urdu / 🇮🇳 Hindi">
          <option value="ur-PK-AsadNeural" selected>Asad (Urdu Male)</option>
          <option value="ur-PK-UzmaNeural">Uzma (Urdu Female)</option>
          <option value="hi-IN-MadhurNeural">Madhur (Hindi Male)</option>
        </optgroup>
        <optgroup label="🇬🇧 UK / 🇦🇺 AU">
          <option value="en-GB-SoniaNeural">Sonia (UK Female)</option>
          <option value="en-AU-NatashaNeural">Natasha (AU Female)</option>
        </optgroup>
      </select>
      <button class="action-btn" onclick="generateVoice()"><i class="fas fa-play-circle"></i> Generate Voice</button>
      <div id="voiceResult" class="result-box">🎧 Your voice will appear here.</div>
    </div>
  </div>

  <!-- ====== IMAGE TAB ====== -->
  <div id="imageSection" class="tab-content">
    <div class="card">
      <h2><i class="fas fa-palette"></i> Text to Picture</h2>
      <p>Describe your vision – from cyberpunk to serene landscapes – and watch it appear.</p>
      <textarea id="imagePrompt" placeholder="e.g. A futuristic city at sunset, neon lights, flying cars, 4k, cinematic">A majestic wolf howling at a glowing moon, digital art, mystical atmosphere</textarea>
      <button class="action-btn" onclick="generateImage()"><i class="fas fa-magic"></i> Generate Image</button>
      <div id="imageResult" class="result-box">🖼️ Your masterpiece will be displayed here.</div>
    </div>
  </div>

  <!-- ====== LIP SYNC TAB ====== -->
  <div id="lipSyncSection" class="tab-content">
    <div class="card">
      <h2><i class="fas fa-film"></i> AI Lip Sync Studio</h2>
      <p>Upload an avatar image and an audio file – we'll animate the lips in real-time.</p>
      <input type="file" id="avatarFile" accept="image/*">
      <input type="file" id="audioFile" accept="audio/*">
      <button class="action-btn" onclick="processLipSync()"><i class="fas fa-sync-alt"></i> Start Lip Sync</button>
      <div id="lipSyncResult" class="result-box">
        <span class="lip-sync-placeholder">📽️ Upload files and hit start.</span>
      </div>
    </div>
  </div>
</div>

<script>
  (function() {
    "use strict";

    // ---------- TOAST SYSTEM (from original) ----------
    function showToast(message, type = 'success') {
      const existing = document.querySelector('.toast');
      if (existing) existing.remove();

      const toast = document.createElement('div');
      toast.className = `toast ${type}`;
      toast.textContent = message;
      document.body.appendChild(toast);
      setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transition = 'opacity 0.5s';
        setTimeout(() => toast.remove(), 500);
      }, 3000);
    }

    // ---------- TAB SWITCH ----------
    window.switchTab = function(evt, sectionId) {
      // remove active from all tabs & contents
      document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
      document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));

      document.getElementById(sectionId).classList.add('active');
      evt.currentTarget.classList.add('active');
    };

    // ---------- VOICE GENERATION ----------
    window.generateVoice = async function() {
      const text = document.getElementById('voiceText').value.trim();
      const voice = document.getElementById('voiceSelect').value;
      const resultBox = document.getElementById('voiceResult');

      if (!text) {
        showToast('Please enter some text first!', 'error');
        resultBox.innerHTML = '⚠️ Enter text to generate voice.';
        return;
      }

      resultBox.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Generating crystal-clear AI voice...';
      
      try {
        const response = await fetch('/generate-voice', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ 
            text, 
            voice,
            rate: '0%',
            pitch: '0Hz',
            style: 'neutral'
          })
        });

        const data = await response.json();

        if (data.success && data.audio_url) {
          resultBox.innerHTML = `
            <audio controls src="${data.audio_url}" style="width:100%;"></audio>
            <div style="margin-top:8px;font-size:0.85rem;color:#94a3b8;">
              <i class="fas fa-check-circle" style="color:#00f2fe;"></i> Voice ready
            </div>
          `;
          showToast('✅ Voice generated successfully!');
        } else {
          resultBox.innerHTML = '⚠️ Error: ' + (data.error || 'Unknown error');
          showToast('❌ Failed to generate voice', 'error');
        }
      } catch (err) {
        console.error('Voice error:', err);
        resultBox.innerHTML = '⚠️ Network error. Please try again.';
        showToast('⚠️ Network error', 'error');
      }
    };

    // ---------- IMAGE GENERATION ----------
    window.generateImage = async function() {
      const prompt = document.getElementById('imagePrompt').value.trim();
      const resultBox = document.getElementById('imageResult');

      if (!prompt) {
        showToast('Please describe an image.', 'error');
        resultBox.innerHTML = '⚠️ Enter a prompt.';
        return;
      }

      resultBox.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Rendering 4K AI image...';

      try {
        const response = await fetch('/generate-image', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ prompt })
        });
        const data = await response.json();

        if (data.success && data.image_url) {
          resultBox.innerHTML = `
            <img src="${data.image_url}" alt="AI generated image" style="max-width:100%;border-radius:16px;margin:10px 0;">
            <div style="font-size:0.85rem;color:#94a3b8;"><i class="fas fa-check-circle" style="color:#00f2fe;"></i> Image generated</div>
          `;
          showToast('🖼️ Image created!');
        } else {
          resultBox.innerHTML = '⚠️ Error: ' + (data.error || 'Unknown error');
          showToast('❌ Failed to generate image', 'error');
        }
      } catch (err) {
        console.error('Image error:', err);
        resultBox.innerHTML = '⚠️ Network error. Please try again.';
        showToast('⚠️ Network error', 'error');
      }
    };

    // ---------- LIP SYNC ----------
    window.processLipSync = async function() {
      const avatarFile = document.getElementById('avatarFile').files[0];
      const audioFile = document.getElementById('audioFile').files[0];
      const resultBox = document.getElementById('lipSyncResult');

      if (!avatarFile || !audioFile) {
        showToast('Please upload both an image and an audio file.', 'error');
        resultBox.innerHTML = '⚠️ Both avatar and audio are required.';
        return;
      }

      resultBox.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 🚀 Initializing AI Lip Sync pipeline...';

      try {
        const formData = new FormData();
        formData.append('avatar', avatarFile);
        formData.append('audio', audioFile);

        const response = await fetch('/lip-sync', {
          method: 'POST',
          body: formData
        });
        const data = await response.json();

        if (data.success && data.video_url) {
          resultBox.innerHTML = `
            <video controls width="100%" style="border-radius:16px;margin:8px 0;">
              <source src="${data.video_url}" type="video/mp4">
            </video>
            <div style="font-size:0.85rem;color:#94a3b8;"><i class="fas fa-check-circle" style="color:#00f2fe;"></i> Lip Sync complete</div>
          `;
          showToast('🎬 Lip sync video ready!');
        } else {
          resultBox.innerHTML = '⚠️ Error: ' + (data.error || 'Unknown error');
          showToast('❌ Lip sync failed', 'error');
        }
      } catch (err) {
        console.error('Lip sync error:', err);
        resultBox.innerHTML = '⚠️ Network error. Please try again.';
        showToast('⚠️ Network error', 'error');
      }
    };

    // ---------- (optional) show welcome toast ----------
    setTimeout(() => {
      const toast = document.createElement('div');
      toast.className = 'toast';
      toast.textContent = '🔥 Badass Studio · AI triple-threat ready';
      document.body.appendChild(toast);
      setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transition = 'opacity 0.6s';
        setTimeout(() => toast.remove(), 600);
      }, 2500);
    }, 400);

  })();
</script>

</body>
</html>'''
    
    return html_content

# ============================================
# RUN THE APP
# ============================================

if __name__ == '__main__':
    # Install required packages if not present
    try:
        import edge_tts
    except ImportError:
        print("Installing edge-tts...")
        os.system("pip install edge-tts")
    
    try:
        from flask_cors import CORS
    except ImportError:
        print("Installing flask-cors...")
        os.system("pip install flask-cors")
    
    print("🔥 Badass Media Studio Server Starting...")
    print(f"📍 Server running on http://localhost:5000")
    print("📡 Voice, Image, and Lip Sync endpoints active")
    print("⚠️  Note: Some features are simulated for demo")
    
    app.run(host='0.0.0.0', port=5000, debug=True)
