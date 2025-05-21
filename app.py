from flask import Flask, request, jsonify
from flask_cors import CORS
import openai
import os
import json
import time

app = Flask(__name__)
CORS(app)

openai.api_key = os.getenv("OPENAI_API_KEY")

# ---- НАЧАЛО БЛОКА КЭШИРОВАНИЯ ----
IMAGE_CACHE = {}  # Словарь для хранения URL изображений. Ключ - полный промпт для DALL-E.
MAX_CACHE_SIZE = 50 # Максимальное количество кэшированных изображений.
# ---- КОНЕЦ БЛОКА КЭШИРОВАНИЯ ----

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

- One cinematic image.
- No collage. No multi-panel. No text.
"""

# Модифицируем функцию generate_image для использования кэша
def generate_image(full_dalle_prompt): # Изменил имя параметра для ясности, что это полный промпт
    # ---- НАЧАЛО ПРОВЕРКИ И ИСПОЛЬЗОВАНИЯ КЭША ----
    if full_dalle_prompt in IMAGE_CACHE:
        print(f"CACHE HIT for prompt: {full_dalle_prompt[:70]}...") # Логируем начало промпта
        return IMAGE_CACHE[full_dalle_prompt]
    # ---- КОНЕЦ ПРОВЕРКИ И ИСПОЛЬЗОВАНИЯ КЭША ----

    try:
        print(f"Generating image for prompt: {full_dalle_prompt[:70]}...") # Логируем начало промпта
        response = openai.images.generate(
            model="dall-e-3",
            prompt=full_dalle_prompt, # Используем полный промпт
            n=1,
            size="1024x1024"
        )
        time.sleep(12)  # respect DALL·E rate limit
        image_url = response.data[0].url if response.data else "Image not generated"

        # ---- НАЧАЛО ДОБАВЛЕНИЯ В КЭШ И УПРАВЛЕНИЯ РАЗМЕРОМ ----
        if image_url != "Image not generated":
            if len(IMAGE_CACHE) >= MAX_CACHE_SIZE:
                # Простая стратегия вытеснения: удалить первый (старейший в Python 3.7+) элемент
                try:
                    oldest_key = next(iter(IMAGE_CACHE))
                    IMAGE_CACHE.pop(oldest_key)
                    print(f"CACHE full. Removed oldest entry for: {oldest_key[:70]}...")
                except StopIteration: # Если кэш был пуст (маловероятно здесь, но для полноты)
                    pass
            IMAGE_CACHE[full_dalle_prompt] = image_url
            print(f"CACHED result for prompt: {full_dalle_prompt[:70]}...")
        # ---- КОНЕЦ ДОБАВЛЕНИЯ В КЭШ И УПРАВЛЕНИЯ РАЗМЕРОМ ----
        return image_url
    except Exception as e:
        print(f"Image generation failed for prompt '{full_dalle_prompt[:70]}...': {e}")
        return "Image not generated"

@app.route("/generate-storyboard", methods=["POST"])
def generate_storyboard():
    data = request.json
    prompt = data.get("prompt", "")
    character = data.get("character", "")
    camera = data.get("camera", "")
    style = data.get("style", "")

    system_message = f"""
Generate a JSON array of exactly 3 scenes that form a coherent story with a clear beginning, middle, and end.
Each scene must include:
- scene_number
- title (e.g., "Introduction", "Conflict", "Resolution")
- narrative: a short description of what happens in the scene.
- shots: an array of 2–3 shots, each containing:
    - frame_number
    - description
    - camera_angle
    - shot_type (e.g., wide, medium, close-up)
    - emotion
    - dialogue

Ensure that the scenes are connected as a single story using the following character details: {character}.
Start with a wide shot, then progress to closer shots.

Return ONLY JSON.
"""
    try:
        gpt_response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": f"Prompt: {prompt}"}
            ],
            max_tokens=1600
        )
        scenes_data_str = gpt_response.choices[0].message.content.strip()
        # Добавим попытку исправить JSON, если он не совсем корректен (простая попытка)
        try:
            scenes = json.loads(scenes_data_str)
        except json.JSONDecodeError:
            print(f"Initial JSON parsing failed. Attempting to fix and re-parse. Original data: {scenes_data_str}")
            # Попытка удалить лишние символы до/после JSON объекта/массива
            # Это очень упрощенная попытка, реальное исправление может быть сложнее
            fixed_scenes_data_str = scenes_data_str[scenes_data_str.find('['):scenes_data_str.rfind(']')+1] if '[' in scenes_data_str else scenes_data_str[scenes_data_str.find('{'):scenes_data_str.rfind('}')+1]
            scenes = json.loads(fixed_scenes_data_str)
            print("JSON re-parsed successfully after basic fix.")


        for scene in scenes:
            for shot in scene["shots"]:
                prompt_text = f"{shot['description']} (Emotion: {shot['emotion']})"
                # `full_prompt_for_dalle` будет использоваться как ключ для кэша
                full_prompt_for_dalle = dalle_prompt(style, character, shot["camera_angle"], prompt_text, shot["emotion"])
                shot["image_url"] = generate_image(full_prompt_for_dalle)
        return jsonify({"storyboard": scenes})
    except Exception as e:
        print(f"Error in /generate-storyboard: {e}") # Улучшенное логирование ошибок
        return jsonify({"error": str(e)}), 500

@app.route("/regenerate-scene", methods=["POST"])
def regenerate_scene():
    data = request.json
    scene = data["scene"]
    style = data["style"]
    character = data["character"]
    for shot in scene["shots"]:
        prompt_text = f"{shot['description']} (Emotion: {shot['emotion']})"
        # `full_prompt_for_dalle` будет использоваться как ключ для кэша
        full_prompt_for_dalle = dalle_prompt(style, character, shot["camera_angle"], prompt_text, shot["emotion"])
        shot["image_url"] = generate_image(full_prompt_for_dalle)
    return jsonify(scene)

@app.route("/regenerate-shot", methods=["POST"])
def regenerate_shot():
    data = request.json
    shot = data["shot"]
    style = data["style"]
    character = data["character"]
    prompt_text = f"{shot['description']} (Emotion: {shot['emotion']})"
    # `full_prompt_for_dalle` будет использоваться как ключ для кэша
    full_prompt_for_dalle = dalle_prompt(style, character, shot["camera_angle"], prompt_text, shot["emotion"])
    shot["image_url"] = generate_image(full_prompt_for_dalle)
    return jsonify(shot)

@app.route("/add-shot", methods=["POST"])
def add_shot():
    data = request.json
    style = data["style"]
    character = data["character"]
    camera = data["camera"]
    shot_data = { # Переименовал переменную, чтобы не конфликтовать с именем 'shot' из других функций
        "frame_number": data.get("frame_number"),
        "description": data.get("description", "New action shot"),
        "camera_angle": camera,
        "shot_type": "static", # Можно сделать настраиваемым
        "emotion": "neutral", # Можно сделать настраиваемым
        "dialogue": "", # Можно сделать настраиваемым
    }
    prompt_text = f"{shot_data['description']} (Emotion: {shot_data['emotion']})"
    # `full_prompt_for_dalle` будет использоваться как ключ для кэша
    full_prompt_for_dalle = dalle_prompt(style, character, shot_data["camera_angle"], prompt_text, shot_data["emotion"])
    shot_data["image_url"] = generate_image(full_prompt_for_dalle)
    return jsonify(shot_data)

@app.route("/delete-shot", methods=["POST"])
def delete_shot():
    # Эта конечная точка в основном для подтверждения, логика удаления на клиенте
    return jsonify({"deleted": True})

if __name__ == "__main__":
    app.run(debug=True)