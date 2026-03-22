from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from google import genai
from google.genai import types
import os, time, uuid

app = FastAPI()

# ✅ CORS (important for frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Gemini / Veo Client
client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY"),
    http_options={"api_version": "v1beta"}
)

@app.post("/generate-video")
async def generate_video(
    prompt: str = Form(...),
    startFrame: UploadFile = File(...),
    endFrame: UploadFile = File(...)
):
    try:
        # Read images (optional use)
        start_bytes = await startFrame.read()
        end_bytes = await endFrame.read()

        final_prompt = f"""
        Create a cinematic video.

        Scene: {prompt}

        The video should smoothly transition from the first frame to the last frame.

        Maintain:
        - visual consistency
        - smooth motion
        - cinematic lighting
        """

        operation = client.models.generate_videos(
            model="veo-2.0-generate-001",
            source=types.VideoGenerationSource(prompt=final_prompt),
            config=types.GenerateVideosConfig(
                duration_seconds=8,
                aspect_ratio="16:9",
                resolution="720p"
            )
        )

        # ⏳ Polling
        while not operation.done:
            time.sleep(5)
            operation = client.operations.get(operation)

        result = operation.result

        if not result or not result.generated_videos:
            return {"error": "Video generation failed"}

        video = result.generated_videos[0].video

        filename = f"output_{uuid.uuid4()}.mp4"

        client.files.download(file=video)
        video.save(filename)

        return FileResponse(filename, media_type="video/mp4")

    except Exception as e:
        return {"error": str(e)}
