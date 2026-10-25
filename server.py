import os
import uuid
from flask import Flask, request, jsonify
from silma_tts.api import SilmaTTS

app = Flask(__name__)

print("⏳ Loading SILMA TTS into Mac RAM (this takes a moment on first boot)...")
tts_engine = SilmaTTS()
print("✅ Model loaded successfully!")

OUTPUT_DIR = os.path.expanduser("/Volumes/Alhamdulillah/Developer/Cache/ar-output/Hermes_Poetry")
os.makedirs(OUTPUT_DIR, exist_ok=True)

@app.route('/generate_poetry', methods=['POST'])
def generate_poetry():
    data = request.json or {}
    poem_text = data.get("text")
    
    if not poem_text:
        return jsonify({"error": "No text provided"}), 400
        
    filename = f"poem_{uuid.uuid4().hex[:8]}.wav"
    output_path = os.path.join(OUTPUT_DIR, filename)
    
    try:
        tts_engine.infer(
            ref_file=None,
            ref_text=None,
            gen_text=poem_text,
            file_wave=output_path,
            speed=1.0
        )
        return jsonify({
            "status": "success",
            "file_path": output_path
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5050)
