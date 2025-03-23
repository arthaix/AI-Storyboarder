
from flask import Flask, request, jsonify
from flask_cors import CORS
import openai
import os
import json
import time

app = Flask(__name__)
CORS(app)

openai.api_key = os.getenv("OPENAI_API_KEY")

STYLE_PROMPTS = {
    "cinematic": "Highly detailed, realistic, cinematic shot, dramatic lighting.",
    "realism": "Photo-realistic, natural lighting, high detail.",
    "anime": "Anime style, bright colors, stylized characters.",
    "comic": "Comic book illustration, bold lines, vibrant colors."
}

def dalle_prompt(style, character_description, camera_angle, shot_description, emotion):
    return f"""
{STYLE_PROMPTS.get(style, "Cinematic, high detail")}

Character: {character_description}
Camera angle: {camera_angle}
Shot: {shot_description}
Emotion: {emotion}

- One cinematic frame.
- No collage. No multi-panel. No text.
"""

def generate_image(prompt):
    try:
        print("Generating image...")
        response = openai.images.generate(
            model="dall-e-3",
            prompt=prompt,
            n=1,
            size="1024x1024"
        )
        time.sleep(12)  # respect DALL·E rate limit
        return response.data[0].url if response.data else "Image not generated"
    except Exception as e:
        print("Image generation failed:", e)
        return "Image not generated"

@app.route("/generate-storyboard", methods=["POST"])
def generate_storyboard():
    data = request.json
    prompt = data.get("prompt", "")
    character = data.get("character", "")
    camera = data.get("camera", "")
    style = data.get("style", "")

    try:
        gpt_response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": f"""
Generate a JSON array of exactly 3 scenes for a storyboard.
Each scene must contain:
- scene_number
- title
- shots: array of 2–3 shots, each with:
  - frame_number
  - description
  - camera_angle
  - shot_type
  - emotion
  - dialogue

Use this character throughout: {character}
Start wide, then go closer.

Return ONLY JSON.
"""},
                {"role": "user", "content": f"Prompt: {prompt}"}
            ],
            max_tokens=1600
        )

        scenes = json.loads(gpt_response.choices[0].message.content.strip())

        for scene in scenes:
            for shot in scene["shots"]:
                prompt_text = f"{shot['description']} (Emotion: {shot['emotion']})"
                full_prompt = dalle_prompt(style, character, shot["camera_angle"], prompt_text, shot["emotion"])
                shot["image_url"] = generate_image(full_prompt)

        return jsonify({"storyboard": scenes})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/regenerate-scene", methods=["POST"])
def regenerate_scene():
    data = request.json
    scene = data["scene"]
    style = data["style"]
    character = data["character"]

    for shot in scene["shots"]:
        prompt_text = f"{shot['description']} (Emotion: {shot['emotion']})"
        full_prompt = dalle_prompt(style, character, shot["camera_angle"], prompt_text, shot["emotion"])
        shot["image_url"] = generate_image(full_prompt)

    return jsonify(scene)

@app.route("/regenerate-shot", methods=["POST"])
def regenerate_shot():
    data = request.json
    shot = data["shot"]
    style = data["style"]
    character = data["character"]

    prompt_text = f"{shot['description']} (Emotion: {shot['emotion']})"
    full_prompt = dalle_prompt(style, character, shot["camera_angle"], prompt_text, shot["emotion"])
    shot["image_url"] = generate_image(full_prompt)

    return jsonify(shot)

@app.route("/add-shot", methods=["POST"])
def add_shot():
    data = request.json
    style = data["style"]
    character = data["character"]
    camera = data["camera"]

    shot = {
        "frame_number": data.get("frame_number"),
        "description": data.get("description", "New action shot"),
        "camera_angle": camera,
        "shot_type": "static",
        "emotion": "neutral",
        "dialogue": "",
    }

    prompt_text = f"{shot['description']} (Emotion: {shot['emotion']})"
    full_prompt = dalle_prompt(style, character, shot["camera_angle"], prompt_text, shot["emotion"])
    shot["image_url"] = generate_image(full_prompt)

    return jsonify(shot)

@app.route("/delete-shot", methods=["POST"])
def delete_shot():
    return jsonify({"deleted": True})

if __name__ == "__main__":
    app.run(debug=True)
