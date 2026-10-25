import sys
import os
import uuid
import site
import argparse
import re
import subprocess
from silma_tts.api import SilmaTTS

def find_native_ref():
    """Locates the built-in default reference audio file inside the package."""
    for path in site.getsitepackages():
        test_path = os.path.join(path, "silma_tts", "infer", "ref_audio_samples", "ar.ref.24k.wav")
        if os.path.exists(test_path):
            return test_path
    return None

def get_voice_profile(voice_name):
    """Returns the (audio_path, transcript_text) for custom voices."""
    voices_base_dir = "/Volumes/Alhamdulillah/Developer/Cache/ar-output/Voices"
    
    # Locate native library assets
    women_audio = find_native_ref()
    women_text = "ويدقق النظر في القرآن الكريم وسائر الكتب السماوية ويتبع مسالك الرسل العظام عليهم الصلاة والسلام."
    
    # 1. Fallback mapping swap logic
    if not voice_name:
        voice_name = "faleh"

    # Explicit routing for the bundled package woman voice
    if voice_name.lower() == "women":
        print("👤 Applying built-in package voice profile: women")
        return women_audio, women_text

    # Route normal custom voice names stored on external drive
    custom_audio_path = os.path.join(voices_base_dir, f"{voice_name}_voice.wav")
    custom_text_path = os.path.join(voices_base_dir, f"{voice_name}_voice.txt")

    if os.path.exists(custom_audio_path) and os.path.exists(custom_text_path):
        print(f"👤 Applying cloned voice profile: {voice_name}")
        with open(custom_text_path, 'r', encoding='utf-8') as f:
            custom_text = f.read().strip()
        return custom_audio_path, custom_text
    else:
        # Default behavior: If 'faleh' files don't exist, log warning and use package baseline
        print(f"⚠️ Voice profile files for '{voice_name}' not found in {voices_base_dir}.")
        print("➡️ Falling back to default native voice.")
        return women_audio, women_text

def convert_to_spoken_arabic(text):
    """Transforms written shapes into true spoken phonetic Arabic structures line by line."""
    if not text:
        return text

    # EXEMPTION PASS: Protect "حَتَّى", "إِلَّا", "ذِي", and "فِي" from formatting loops
    text = re.sub(r'\bحَتَّى\b', '__HATTA__', text)
    text = re.sub(r'\bحَتى\b', '__HATTA__', text)
    text = re.sub(r'\bإِلَّا\b', '__ILLA__', text)
    text = re.sub(r'\bإِلّا\b', '__ILLA__', text)
    text = re.sub(r'\bذِي\b', '__THEE__', text)
    text = re.sub(r'\bفِي\b', '__FEE__', text)

    # Pre-pass: Strip the silent 'و' from Amr variations cleanly
    text = re.sub(r'(عَمْ?رِ?)و([\u064b\u064c\u064d\u064e\u064f\u0650])', r'\1\2', text)
    text = re.sub(r'(عَمْ?رِ?)([\u064b\u064c\u064d\u064e\u064f\u0650])و', r'\1\2', text)

    phonetic_replacements = [
        # Shaddah + Tanween Kasr (ٍّ) -> Double Letter + Kasra + Noon Sukun
        (r'([\u0621-\u064a])\u0651\u064d', r'\1ْ\1ِنْ'),
        (r'([\u0621-\u064a])\u064d\u0651', r'\1ْ\1ِنْ'),

        # Shaddah + Tanween Damm (ٌّ) -> Double Letter + Damma + Noon Sukun
        (r'([\u0621-\u064a])\u0651\u064c', r'\1ْ\1ُنْ'),
        (r'([\u0621-\u064c])\u064c\u0651', r'\1ْ\1ُنْ'),

        # Shaddah + Tanween Fath (ًّ) -> Double Letter + Fatha + Noon Sukun
        (r'([\u0621-\u064a])\u0651\u064b', r'\1ْ\1َنْ'),
        (r'([\u0621-\u064a])\u064b\u0651', r'\1ْ\1َنْ'),

        # Standalone Tanween Kasr (ٍ) -> Kasra + Noon Sukun
        (r'([\u0621-\u064a])\u064d', r'\1ِنْ'),

        # Standalone Tanween Damm (ٌ) -> Damma + Noon Sukun
        (r'([\u0621-\u064a])\u064c', r'\1ُنْ'),

        # Standalone Tanween Fath (ً) -> Fatha + Noon Sukun
        (r'([\u0621-\u064a])\u064b\u0627?', r'\1َنْ'),

        # Standard Shaddah variants
        (r'([\u0621-\u064a])\u0651\u0650', r'\1ْ\1ِ'),
        (r'([\u0621-\u064a])\u0650\u0651', r'\1ْ\1ِ'),
        (r'([\u0621-\u064a])\u0651\u064f', r'\1ْ\1ُ'),
        (r'([\u0621-\u064a])\u064f\u0651', r'\1ْ\1ُ'),
        (r'([\u0621-\u064a])\u0651\u064e', r'\1ْ\1َ'),
        (r'([\u0621-\u064a])\u064e\u0651', r'\1ْ\1َ'),
    ]

    for pattern, replacement in phonetic_replacements:
        text = re.sub(pattern, replacement, text)

    # RESTORE PASS: Swap the protected words back natively right before sending to the engine
    text = re.sub(r'__HATTA__', 'حَتَّى', text)
    text = re.sub(r'__ILLA__', 'إِلَّا', text)
    text = re.sub(r'__THEE__', 'ذِي', text)
    text = re.sub(r'__FEE__', 'فِي', text)
            
    return text

def main():
    parser = argparse.ArgumentParser(description="Arabic Poetic TTS Engine CLI")
    parser.add_argument("input", help="Raw Arabic text string OR path to a text file.")
    parser.add_argument("--voice", help="Name of the custom voice profile.", default=None)
    
    if len(sys.argv) < 2:
        parser.print_help()
        sys.exit(1)
        
    args = parser.parse_args()

    if os.path.isfile(args.input):
        print(f"📄 Reading text from file: {args.input}")
        with open(args.input, 'r', encoding='utf-8') as f:
            raw_text = f.read()
    else:
        raw_text = args.input

    # Split lines safely based on punctuation or verse endings
    raw_text = re.sub(r'(ناصِبِ|الكَواكِبِ|بِمُنقَضٍ|بِآئِبِ|هَمِّهِ|جانِبِ|نِعمَةٍ|عَقارِبِ|مَثنَوِيَّةٍ|بِصاحِبِ)', r'\1\n', raw_text)
    raw_lines = [line.strip() for line in raw_text.split('\n') if line.strip()]

    if not raw_lines:
        print("❌ Error: Provided text content is empty.")
        sys.exit(1)

    ref_audio, ref_text = get_voice_profile(args.voice)
    if not ref_audio:
        print("❌ Error: Could not locate reference audio asset.")
        sys.exit(1)

    OUTPUT_DIR = "/Volumes/Alhamdulillah/Developer/Cache/ar-output/Hermes_Poetry"
    TMP_DIR = os.path.join(OUTPUT_DIR, f"tmp_{uuid.uuid4().hex[:6]}")
    os.makedirs(TMP_DIR, exist_ok=True)

    print("⏳ Initializing SILMA TTS Engine onto Apple Silicon GPU (mps)...")
    tts_engine = SilmaTTS()

    temp_files = []
    
    print(f"🔊 Processing {len(raw_lines)} Poetic Lines Independently...")
    for idx, raw_line in enumerate(raw_lines):
        processed_line = convert_to_spoken_arabic(raw_line)
        if not processed_line.endswith("..."):
            processed_line += "..."

        print(f"  ➡️ Chunk #{idx}: [ {processed_line} ]")
        tmp_output_path = os.path.join(TMP_DIR, f"part_{idx}.wav")
        
        try:
            tts_engine.infer(
                ref_file=ref_audio,
                ref_text=ref_text,
                gen_text=processed_line,
                file_wave=tmp_output_path,
                speed=1.0,
                progress=True
            )
            temp_files.append(tmp_output_path)
        except Exception as e:
            print(f"❌ Error during generation on line {idx}: {e}")

    if not temp_files:
        print("❌ Error: No audio tracks were generated.")
        sys.exit(0)

    # Use the requested voice name or fallback explicitly to default marker
    voice_prefix = args.voice if args.voice else "default"
    final_filename = f"{voice_prefix}_poem_{uuid.uuid4().hex[:8]}.wav"
    final_output_path = os.path.join(OUTPUT_DIR, final_filename)

    concat_list_path = os.path.join(TMP_DIR, "concat_list.txt")
    with open(concat_list_path, 'w', encoding='utf-8') as f:
        for f_path in temp_files:
            f.write(f"file '{f_path}'\n")

    print("🎬 Stitching segments back together via ffmpeg...")
    ffmpeg_cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", 
        "-i", concat_list_path, "-c", "copy", final_output_path
    ]
    
    subprocess.run(ffmpeg_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    for f_path in temp_files:
        try: os.remove(f_path)
        except: pass
    try:
        os.remove(concat_list_path)
        os.rmdir(TMP_DIR)
    except: pass

    print(f"✅ Success! Your complete poem audio is safely stored at:\n🎯 {final_output_path}")

if __name__ == '__main__':
    main()
