from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from google import genai
from google.genai import types
from dotenv import load_dotenv
import os
import time
import uuid

# Load environment variables
load_dotenv()

app = FastAPI(title="Veo 3.1 Video API")

# CRITICAL: Allow your GitHub Pages frontend to talk to this Render backend!
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://honest25.github.io", # Your live frontend
        "http://localhost:8080",      # For local testing
        "*"                           # Fallback
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# New Model Initialization
MODEL = "veo-3.1-fast-generate-preview"
client = genai.Client(
    http_options={"api_version": "v1beta"},
    api_key=os.environ.get("GEMINI_API_KEY"),
)

@app.get("/")
async def health_check():
    return {
        "status": "Veo 3.1 API running ✅", 
        "frontend": "https://honest25.github.io/vd/",
        "message": "Send POST requests to /generate-video"
    }

@app.post("/generate-video")
async def generate_video(
    prompt: str = Form(...),
    duration: int = Form(5),
    resolution: str = Form("720p"),
    # Keeping these so your frontend doesn't break, even if Veo 3.1 Fast uses mostly text right now
    startFrame: UploadFile = File(None), 
    endFrame: UploadFile = File(None)
):
    try:
        print(f"Received prompt: {prompt}")
        
        # 1. Setup Veo 3.1 Config from your snippet
        video_config = types.GenerateVideosConfig(
            person_generation="allow_all", # Changed to allow_all so it doesn't block character generations
            aspect_ratio="16:9",
            number_of_videos=1,
            duration_seconds=int(duration),
            resolution=resolution,
        )

        # 2. Call Veo 3.1 API
        print("Sending request to Veo 3.1...")
        operation = client.models.generate_videos(
            model=MODEL,
            source=types.VideoGenerationSource(
                prompt=f"Cinematic video sequence. {prompt}",
            ),
            config=video_config,
        )

        # 3. Polling for completion (Wait loop)
        while not operation.done:
            print("Video is generating... checking again in 10 seconds.")
            time.sleep(10)
            operation = client.operations.get(operation)

        result = operation.result
        
        if not result or not result.generated_videos:
            raise Exception("No videos were generated or an error occurred.")

        # 4. Save and return the video (Using your snippet's logic)
        generated_video = result.generated_videos[0]
        print(f"Generation complete! URI: {generated_video.video.uri}")
        
        output_filename = f"veo_output_{uuid.uuid4()}.mp4"
        
        # Download and save
        client.files.download(file=generated_video.video)
        generated_video.video.save(output_filename) 
        
        print(f"Successfully saved to {output_filename}")

        # 5. Send back to your GitHub Pages frontend
        return FileResponse(output_filename, media_type="video/mp4", filename="veo_3_1_cinematic.mp4")

    except Exception as e:
        print(f"Backend Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
