import os
import time
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from google import genai
from google.genai import types

app = Flask(__name__)
CORS(app) # Allows your HTML file to communicate with this Python server

# Create a folder to store the generated videos
os.makedirs("generated_videos", exist_ok=True)

# Initialize the Gemini Client
# It will automatically pick up the GEMINI_API_KEY from your environment variables
client = genai.Client(http_options={"api_version": "v1beta"})
MODEL = "veo-2.0-generate-001"

@app.route('/api/generate', methods=['POST'])
def generate_video():
    try:
        data = request.json
        user_prompt = data.get('prompt', 'Cinematic transition')
        print(f"Starting generation for prompt: {user_prompt}")

        # Your exact Veo 2.0 Configuration
        video_config = types.GenerateVideosConfig(
            person_generation="dont_allow", 
            aspect_ratio="16:9", 
            number_of_videos=1, 
            duration_seconds=8, 
            resolution="720p", 
        )

        # Trigger Veo 2.0
        operation = client.models.generate_videos(
            model=MODEL,
            source=types.VideoGenerationSource(prompt=user_prompt),
            config=video_config,
        )

        # Polling loop to wait for generation (Veo takes a few minutes)
        while not operation.done:
            print("Video is generating. Checking again in 10 seconds...")
            time.sleep(10)
            operation = client.operations.get(operation)

        result = operation.result
        if not result or not result.generated_videos:
            return jsonify({"error": "Generation failed or blocked by safety filters."}), 500

        # Save the video
        generated_video = result.generated_videos[0]
        filename = f"veo_video_{int(time.time())}.mp4"
        filepath = os.path.join("generated_videos", filename)
        
        print(f"Downloading video from: {generated_video.video.uri}")
        client.files.download(file=generated_video.video)
        generated_video.video.save(filepath)

        # Return the URL so the frontend can play it
        video_url = f"http://127.0.0.1:5000/videos/{filename}"
        return jsonify({"success": True, "video_url": video_url})

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500

# Route to serve the actual video files to the HTML frontend
@app.route('/videos/<filename>')
def serve_video(filename):
    return send_from_directory("generated_videos", filename)

if __name__ == "__main__":
    print("Veo 2.0 Server running on http://127.0.0.1:5000")
    app.run(port=5000, debug=True)
