from fastapi import FastAPI, Form, File, UploadFile, HTTPException
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

app = FastAPI(title="Veo 3.1 Fast API")

# Allow your GitHub Pages frontend to communicate securely
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup exact model from your script
MODEL = "veo-3.1-fast-generate-preview"
client = genai.Client(
    http_options={"api_version": "v1beta"},
    api_key=os.environ.get("GEMINI_API_KEY"),
)

@app.get("/")
async def health_check():
    return {"status": "Veo 3.1 API is running perfectly! ✅"}

@app.post("/generate-video")
async def generate_video(
    prompt: str = Form(...),
    duration: int = Form(5),
    resolution: str = Form("720p"),
    # We accept these just in case your HTML form sends them, but we IGNORE them.
    startFrame: UploadFile = File(None), 
    endFrame: UploadFile = File(None)
):
    try:
        print(f"Starting generation for prompt: {prompt}")
        
        # 1. Video Config (Matched to your script)
        video_config = types.GenerateVideosConfig(
            person_generation="allow_all", # Set to allow_all so human prompts don't fail
            aspect_ratio="16:9",
            number_of_videos=1,
            duration_seconds=int(duration),
            resolution=resolution,
        )

        # 2. Call the Model
        operation = client.models.generate_videos(
            model=MODEL,
            source=types.VideoGenerationSource(
                prompt=prompt # PURE STRING, no lists or files!
            ),
            config=video_config,
        )

        # 3. Wait for the video(s) to be generated (Polling loop)
        while not operation.done:
            print("Video has not been generated yet. Check again in 10 seconds...")
            time.sleep(10)
            operation = client.operations.get(operation)

        result = operation.result
        if not result or not result.generated_videos:
            raise Exception("No videos were generated. Check prompt safety or quotas.")

        # 4. Save and Download
        generated_video = result.generated_videos[0]
        output_filename = f"video_{uuid.uuid4()}.mp4"
        
        print(f"Video generated: {generated_video.video.uri}")
        client.files.download(file=generated_video.video)
        generated_video.video.save(output_filename) 

        # 5. Return MP4 to Frontend
        return FileResponse(output_filename, media_type="video/mp4", filename="veo_3_1_fast.mp4")

    except Exception as e:
        print(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
