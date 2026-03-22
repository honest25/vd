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

app = FastAPI(title="Veo Video API")

# Enable CORS for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this to your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Gemini Client
client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY"),
    http_options={"api_version": "v1beta"}
)
@app.get("/")
def home():
    return {"status": "API running ✅"}

@app.post("/generate-video")
async def generate_video(
    prompt: str = Form(...),
    duration: int = Form(5),
    resolution: str = Form("720p"),
    startFrame: UploadFile = File(...),
    endFrame: UploadFile = File(...)
):
    try:
        # 1. Save uploaded files locally (temporarily)
        start_path = f"temp_start_{uuid.uuid4()}.jpg"
        end_path = f"temp_end_{uuid.uuid4()}.jpg"
        
        with open(start_path, "wb") as f:
            f.write(await startFrame.read())
        with open(end_path, "wb") as f:
            f.write(await endFrame.read())

        # 2. Upload files to Gemini API
        uploaded_start = client.files.upload(file=start_path)
        uploaded_end = client.files.upload(file=end_path)

        # 3. Build Enhanced Prompt
        final_prompt = f"""
        Create a cinematic video.
        Scene: {prompt}
        The video should smoothly transition from the uploaded start frame to the uploaded end frame.
        Maintain visual consistency, smooth motion, and cinematic lighting.
        """

        # 4. Call Veo API
        # Note: We pass the uploaded files alongside the text prompt
        operation = client.models.generate_videos(
            model="veo-2.0-generate-001",
            prompt=[uploaded_start, final_prompt, uploaded_end],
            config=types.GenerateVideosConfig(
                duration_seconds=duration,
                aspect_ratio="16:9",
                person_generation="ALLOW_ADULT" # Adjust based on safety needs
            )
        )

        # 5. Poll for completion
        while not operation.done:
            time.sleep(5)
            operation = client.operations.get(operation.name)
            
        result = operation.result
        
        if not result or not result.generated_videos:
            raise Exception("Video generation failed or returned empty.")

        # 6. Save the generated video
        video_uri = result.generated_videos[0].video.uri
        output_filename = f"output_{uuid.uuid4()}.mp4"
        
        # Download the file using the SDK
        client.files.download(file=video_uri, path=output_filename)

        # 7. Cleanup temp files
        os.remove(start_path)
        os.remove(end_path)
        client.files.delete(name=uploaded_start.name)
        client.files.delete(name=uploaded_end.name)

        # 8. Return the actual video file to the frontend
        return FileResponse(output_filename, media_type="video/mp4", filename="cinematic_ai_video.mp4")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
