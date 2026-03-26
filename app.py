from flask import Flask, render_template, request, jsonify
import google.generativeai as genai
import requests
import os

app = Flask(__name__)

# Gemini setup
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

def generate_script(topic):
    model = genai.GenerativeModel('gemini-1.5-flash')
    prompt = f"""Write a short YouTube script (30 seconds) about: {topic}
    
    Format:
    HOOK: One line to grab attention
    CONTENT: Main points (2-3 lines)
    CTA: Call to action (1 line)
    """
    response = model.generate_content(prompt)
    return response.text

def get_pexels_video(keyword):
    api_key = os.environ.get("PEXELS_API_KEY")
    url = f"https://api.pexels.com/videos/search?query={keyword}&per_page=1"
    headers = {"Authorization": api_key}
    response = requests.get(url, headers=headers)
    data = response.json()
    if data.get("videos"):
        return data["videos"][0]["video_files"][0]["link"]
    return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate():
    topic = request.json.get('topic', '')
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
