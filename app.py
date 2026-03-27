from flask import Flask, render_template, request, jsonify
import google.generativeai as genai
import requests
import os
import traceback

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
        prompt = f"""Write a short YouTube script (30 seconds) about: {topic}
        
        Format:
        HOOK: One line to grab attention
        CONTENT: Main points (2-3 lines)
        CTA: Call to action (1 line)
        """
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Script error: {e}")
        return f"HOOK: Want to learn about {topic}?\nCONTENT: Here's what you need to know.\nCTA: Subscribe for more!"

def get_pexels_video(keyword):
    """Get stock video from Pexels"""
    try:
        api_key = os.environ.get("PEXELS_API_KEY")
        if not api_key:
            return None
        url = f"https://api.pexels.com/videos/search?query={keyword}&per_page=1"
        headers = {"Authorization": api_key}
        response = requests.get(url, headers=headers)
        data = response.json()
        if data.get("videos"):
            return data["videos"][0]["video_files"][0]["link"]
    except Exception as e:
        print(f"Pexels error: {e}")
    return None

@app.route('/')
def index():
    """Home page"""
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate():
    """Generate video script and get stock footage"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data"}), 400
        
        topic = data.get('topic', '')
        if not topic:
            return jsonify({"error": "No topic provided"}), 400
        
        script = generate_script(topic)
        video_url = get_pexels_video(topic.split()[0])
        
        return jsonify({
            "script": script,
            "video_url": video_url,
            "topic": topic,
            "status": "success"
        })
    except Exception as e:
        print(f"Generate error: {traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({"status": "ok", "gemini_configured": api_key is not None})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
