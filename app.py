from flask import Flask, render_template, request, jsonify, send_file
import google.generativeai as genai
import requests
import os
import traceback
import edge_tts
import asyncio
import uuid
import re

app = Flask(__name__)

# Gemini setup
api_key = os.environ.get("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)
    print("✅ Gemini configured")
else:
    print("❌ GEMINI_API_KEY not set")

def generate_script(topic):
    """Generate YouTube script using Gemini AI"""
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"""You are a professional YouTube script writer. Write a short, engaging video script about: {topic}

IMPORTANT RULES:
1. The script MUST be directly about "{topic}"
2. Do NOT change the topic to something else
3. Keep it concise and engaging

Format your response exactly like this:

HOOK: (one line that grabs attention about {topic})

CONTENT: (3-4 lines with main information about {topic})

CTA: (one line call to action)

Now write the script for topic: {topic}"""
        
        response = model.generate_content(prompt)
        script = response.text
        
        # Verify script contains topic
        topic_words = topic.lower().split()
        script_lower = script.lower()
        
        # Check if at least one main word from topic appears in script
        topic_mentioned = False
        for word in topic_words[:3]:  # Check first 3 words
            if len(word) > 3 and word in script_lower:
                topic_mentioned = True
                break
        
        if not topic_mentioned and len(topic_words) > 0:
            print(f"⚠️ Script may be off-topic. Regenerating...")
            prompt = f"Write a YouTube script about: {topic}. Stay strictly on this topic. Do not write about anything else. Topic is: {topic}"
            response = model.generate_content(prompt)
            script = response.text
        
        return script
        
    except Exception as e:
        print(f"Script error: {e}")
        return f"""HOOK: Want to learn about {topic}?

CONTENT: Here's everything you need to know about {topic}. 
First, understand the basics of {topic}. 
Second, apply these proven strategies for {topic}. 
Third, track your results with {topic}.

CTA: Subscribe for more videos about {topic}!"""

def get_pexels_video(keyword):
    """Get relevant stock video from Pexels"""
    try:
        api_key = os.environ.get("PEXELS_API_KEY")
        if not api_key:
            print("❌ PEXELS_API_KEY not set")
            return None
        
        # Clean keyword
        keyword = keyword.strip().lower()
        
        # List of related keywords to try
        keywords_to_try = [
            keyword,
            keyword + " business",
            keyword + " technology", 
            keyword + " creative",
            "people working",
            "business",
            "technology"
        ]
        
        for kw in keywords_to_try[:5]:  # Try first 5
            url = f"https://api.pexels.com/videos/search?query={kw}&per_page=3"
            headers = {"Authorization": api_key}
            response = requests.get(url, headers=headers)
            
            if response.status_code != 200:
                continue
                
            data = response.json()
            
            if data.get("videos") and len(data["videos"]) > 0:
                video = data["videos"][0]
                video_files = video.get("video_files", [])
                
                # Get highest quality video
                for vf in video_files:
                    if vf.get("quality") == "hd" or vf.get("width", 0) >= 1280:
                        return vf.get("link")
                
                if video_files:
                    return video_files[0].get("link")
        
        return None
        
    except Exception as e:
        print(f"Pexels error: {e}")
        return None

async def generate_audio(text, filename):
    """Generate audio from text using Edge TTS (free)"""
    try:
        # Clean text for TTS
        clean_text = re.sub(r'HOOK:|CONTENT:|CTA:', '', text)
        clean_text = clean_text.replace('\n', ' ').strip()
        
        if len(clean_text) < 10:
            clean_text = "Welcome to this video. " + clean_text
        
        voice = "en-US-JennyNeural"  # Female voice - natural
        communicate = edge_tts.Communicate(clean_text[:500], voice)  # Limit length
        await communicate.save(filename)
        print(f"✅ Audio saved: {filename}")
        return True
    except Exception as e:
        print(f"Audio error: {e}")
        return False

@app.route('/')
def index():
    """Home page"""
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate():
    """Generate video script, footage, and audio"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data"}), 400
        
        topic = data.get('topic', '').strip()
        if not topic:
            return jsonify({"error": "No topic provided"}), 400
        
        if len(topic) < 3:
            return jsonify({"error": "Topic too short. Please be more specific."}), 400
        
        print(f"🎬 Generating for topic: {topic}")
        
        # Generate script
        script = generate_script(topic)
        print(f"📝 Script generated: {script[:100]}...")
        
        # Get stock video
        main_keyword = topic.split()[0]
        video_url = get_pexels_video(main_keyword)
        print(f"🎥 Video URL: {video_url}")
        
        # Generate audio
        audio_filename = f"audio_{uuid.uuid4().hex[:8]}.mp3"
        audio_path = os.path.join(os.getcwd(), audio_filename)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        audio_success = loop.run_until_complete(generate_audio(script, audio_path))
        
        response_data = {
            "script": script,
            "video_url": video_url,
            "audio_url": f"/download/{audio_filename}" if audio_success else None,
            "topic": topic,
            "status": "success"
        }
        
        print(f"✅ Generation complete")
        return jsonify(response_data)
        
    except Exception as e:
        print(f"Generate error: {traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500

@app.route('/download/<filename>')
def download(filename):
    """Download generated audio file"""
    try:
        filepath = os.path.join(os.getcwd(), filename)
        if os.path.exists(filepath):
            return send_file(filepath, as_attachment=True, download_name=filename)
        else:
            return jsonify({"error": "File not found"}), 404
    except Exception as e:
        print(f"Download error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "ok", 
        "gemini_configured": api_key is not None,
        "message": "AI YouTube Studio is running"
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
