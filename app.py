from flask import Flask, request, jsonify
from flask_cors import CORS
import openai
import os
import threading

app = Flask(__name__)
CORS(app)

openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    raise ValueError("Missing OpenAI API Key! Set it as an environment variable.")

client = openai.OpenAI(api_key=openai_api_key)

STYLE_PROMPTS = {
    "cinematic": "Highly detailed, realistic, cinematic shot, dramatic lighting.",
    "realism": "Photo-realistic, natural lighting, high detail.",
    "anime": "Anime style, bright colors, stylized characters.",
    "comic": "Comic book illustration, bold lines, vibrant colors."
}

# 🔄 Исправленный разбор сцен
def generate_full_scenes(user_prompt):
    try:
        print(f"🔄 Generating scenes for: {user_prompt}")
        response = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {
                    "role": "system",
                    "content": "You are a professional scriptwriter. Given a short idea, break it into exactly three structured scenes. "
                               "Each scene must have:\n"
                               "- **Title** (short, 5-7 words)\n"
                               "- **Setting** (where it happens)\n"
                               "- **Characters** (who is involved)\n"
                               "- **Actions** (what is happening)\n"
                               "- **Mood** (atmosphere and emotions)\n"
                               "Each scene should be separated by `### Scene X:`."
                },
                {"role": "user", "content": f"Create a structured three-scene breakdown for: {user_prompt}"}
            ],
            max_tokens=700
        )

        raw_scenes = response.choices[0].message.content.strip()
        print(f"📩 GPT Raw Response:\n{raw_scenes}")  # Лог для отладки

        scenes = raw_scenes.split("### Scene")
        scenes = [s.strip() for s in scenes if s.strip()]

        if len(scenes) < 3:
            print(f"⚠️ GPT вернул {len(scenes)} сцен вместо 3. Генерируем снова...")
            return ["Scene 1: No data", "Scene 2: No data", "Scene 3: No data"]

        return scenes[:3]
    
    except Exception as e:
        print(f"❌ GPT Error: {e}")
        return ["Scene 1: Error", "Scene 2: Error", "Scene 3: Error"]

# 🔄 Улучшенная генерация изображений
def generate_image(scene_text, style):
    if "Placeholder" in scene_text or "Error" in scene_text:
        print("🚨 Skipping image generation for placeholder scenes.")
        return None

    full_prompt = f"""
        {STYLE_PROMPTS.get(style, "Cinematic, realistic style")}  

        **Scene Description**: {scene_text}

        - High detail, strong composition.
        - Single-frame shot, not a storyboard.
        - No multiple panels, no split frames.
    """
    try:
        print(f"🔄 Sending prompt to DALL·E:\n{full_prompt}")
        response = client.images.generate(
            model="dall-e-3",
            prompt=full_prompt,
            n=1,
            size="1024x1024"
        )
        image_url = response.data[0].url if response.data else None
        print(f"✅ Image Generated: {image_url}")
        return image_url
    except Exception as e:
        print(f"❌ Image Generation Error: {e}")
        return None

@app.route('/generate-storyboard', methods=['POST'])
def generate_storyboard():
    data = request.json
    user_prompt = data.get("prompt", "A random adventure")
    style = data.get("style", "cinematic")

    print(f"🚀 User request: {user_prompt} (Style: {style})")

    scenes = generate_full_scenes(user_prompt)
    images = []

    def process_scene(i, scene):
        short_description = scene.split("\n")[0] if isinstance(scene, str) else "No description available"
        image_url = generate_image(scene, style)

        images.append({
            "scene": f"Scene {i+1}",
            "description": short_description,
            "image_url": image_url if image_url else "Error: Image not generated."
        })

    threads = []
    for i, scene in enumerate(scenes):
        t = threading.Thread(target=process_scene, args=(i, scene))
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

    return jsonify({"storyboard": images})

if __name__ == '__main__':
    app.run(debug=True)
