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
        test_path = os.path.join(
            path,
            "silma_tts",
            "infer",
            "ref_audio_samples",
            "ar.ref.24k.wav",
        )
        if os.path.exists(test_path):
            return test_path
    return None


def get_voice_profile(voice_name):
    """Returns the (audio_path, transcript_text) for custom voices."""
    voices_base_dir = (
        "/Volumes/Alhamdulillah/Developer/Cache/ar-output/Voices"
    )

    default_audio = find_native_ref()
    default_text = (
        "ويدقق النظر في القرآن الكريم وسائر الكتب السماوية "
        "ويتبع مسالك الرسل العظام عليهم الصلاة والسلام."
    )

    if not voice_name:
        return default_audio, default_text

    custom_audio_path = os.path.join(
        voices_base_dir, f"{voice_name}_voice.wav"
    )
    custom_text_path = os.path.join(
        voices_base_dir, f"{voice_name}_voice.txt"
    )

    if (
        os.path.exists(custom_audio_path)
        and os.path.exists(custom_text_path)
    ):
        print(f"👤 Applying cloned voice profile: {voice_name}")

        with open(custom_text_path, "r", encoding="utf-8") as f:
            custom_text = f.read().strip()

        return custom_audio_path, custom_text

    print(f"⚠️ Voice profile files not found in {voices_base_dir}.")
    print("➡️ Falling back to default native voice.")

    return default_audio, default_text


def convert_to_spoken_arabic(text):
    """Transforms written shapes into true spoken phonetic Arabic structures line by line."""
    if not text:
        return text

    # EXEMPTION PASS: Protect "حَتَّى" and "إِلَّا"
    # so the Shaddah loop ignores them.
    text = re.sub(r"حَتَّى", "__HATTA__", text)
    text = re.sub(r"حَتى", "__HATTA__", text)
    text = re.sub(r"إِلَّا", "__ILLA__", text)
    text = re.sub(r"إِلّا", "__ILLA__", text)

    # Pre-pass: Strip the silent 'و' from Amr variations cleanly.
    text = re.sub(
        r"(عَمْ?رِ?)و([\u064b\u064c\u064d\u064e\u064f\u0650])",
        r"\1\2",
        text,
    )
    text = re.sub(
        r"(عَمْ?رِ?)([\u064b\u064c\u064d\u064e\u064f\u0650])و",
        r"\1\2",
        text,
    )

    phonetic_replacements = [
        # Shaddah + Tanween Kasr
        (r"([\u0621-\u064a])\u0651\u064d", r"\1ْ\1ِنْ"),
        (r"([\u0621-\u064a])\u064d\u0651", r"\1ْ\1ِنْ"),

        # Shaddah + Tanween Damm
        (r"([\u0621-\u064a])\u0651\u064c", r"\1ْ\1ُنْ"),
        (r"([\u0621-\u064c])\u064c\u0651", r"\1ْ\1ُنْ"),

        # Shaddah + Tanween Fath
        (r"([\u0621-\u064a])\u0651\u064b", r"\1ْ\1َنْ"),
        (r"([\u0621-\u064a])\u064b\u0651", r"\1ْ\1َنْ"),

        # Standalone Tanween Kasr
        (r"([\u0621-\u064a])\u064d", r"\1ِنْ"),

        # Standalone Tanween Damm
        (r"([\u0621-\u064a])\u064c", r"\1ُنْ"),

        # Standalone Tanween Fath
        (r"([\u0621-\u064a])\u064b\u0627?", r"\1َنْ"),

        # Standard Shaddah variants
        (r"([\u0621-\u064a])\u0651\u0650", r"\1ْ\1ِ"),
        (r"([\u0621-\u064a])\u0650\u0651", r"\1ْ\1ِ"),

        (r"([\u0621-\u064a])\u0651\u064f", r"\1ْ\1ُ"),
        (r"([\u0621-\u064a])\u064f\u0651", r"\1ْ\1ُ"),

        (r"([\u0621-\u064a])\u0651\u064e", r"\1ْ\1َ"),
        (r"([\u0621-\u064a])\u064e\u0651", r"\1ْ\1َ"),
    ]

    for pattern, replacement in phonetic_replacements:
        text = re.sub(pattern, replacement, text)

    # RESTORE PASS
    text = re.sub(r"__HATTA__", "حَتَّى", text)
    text = re.sub(r"__ILLA__", "إِلَّا", text)

    return text


def main():
    parser = argparse.ArgumentParser(
        description="Arabic Poetic TTS Engine CLI"
    )

    parser.add_argument(
        "input",
        help="Raw Arabic text string OR path to a text file.",
    )

    parser.add_argument(
        "--voice",
        help="Name of the custom voice profile.",
        default=None,
    )

    # Optional settings from the previous version.
    parser.add_argument(
        "--speed",
        type=float,
        default=0.92,
        help="Speaking speed. Below 1.0 is slower; above 1.0 is faster.",
    )

    parser.add_argument(
        "--steps",
        type=int,
        choices=(16, 24, 32),
        default=24,
        help="Synthesis steps. Higher values take longer.",
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Optional seed for repeatable generation.",
    )

    parser.add_argument(
        "--line-pause",
        choices=("original", "short", "medium", "long", "none"),
        default="original",
        help="Line ending pause. 'original' preserves your existing ellipsis.",
    )

    parser.add_argument(
        "--no-auto-tashkeel",
        action="store_true",
        help="Disable SILMA automatic tashkeel processing.",
    )

    parser.add_argument(
        "--output-dir",
        default=(
            "/Volumes/Alhamdulillah/Developer/Cache/"
            "ar-output/Hermes_Poetry"
        ),
        help="Directory for the output and temporary audio files.",
    )

    parser.add_argument(
        "--output",
        default=None,
        help="Optional exact path for the final WAV file.",
    )

    parser.add_argument(
        "--preview",
        action="store_true",
        help="Preview the split and transformed lines without generating audio.",
    )

    args = parser.parse_args()

    if not 0.4 <= args.speed <= 2.0:
        parser.error("--speed must be between 0.4 and 2.0")

    # FIX: Don't check a multiline poem as a filesystem path.
    # This prevents macOS Errno 63: File name too long.
    input_is_file = False

    if "\n" not in args.input and "\r" not in args.input:
        try:
            input_is_file = os.path.isfile(
                os.path.expanduser(args.input)
            )
        except (OSError, ValueError):
            input_is_file = False

    if input_is_file:
        input_path = os.path.expanduser(args.input)
        print(f"📄 Reading text from file: {input_path}")

        with open(input_path, "r", encoding="utf-8") as f:
            raw_text = f.read()
    else:
        raw_text = args.input

    # SMART SPLITTER: ORIGINAL LOGIC PRESERVED.
    # Handles multi-line jumps even if pasted as one string.
    raw_text = re.sub(
        r"(ناصِبِ|الكَواكِبِ|بِمُنقَضٍ|بِآئِبِ|هَمِّهِ|جانِبِ|نِعمَةٍ|عَقارِبِ|مَثنَوِيَّةٍ)",
        r"\1\n",
        raw_text,
    )

    raw_lines = [
        line.strip()
        for line in raw_text.split("\n")
        if line.strip()
    ]

    if not raw_lines:
        print("❌ Error: Provided text content is empty.")
        sys.exit(1)

    # Apply your original phonetic conversion and prepare each line.
    processed_lines = []

    pause_marks = {
        "short": "،",
        "medium": "؛",
        "long": "...",
        "none": "",
    }

    for raw_line in raw_lines:
        processed_line = convert_to_spoken_arabic(raw_line)

        if args.line_pause == "original":
            # Original behaviour: append ellipsis exactly as before.
            if not processed_line.endswith("..."):
                processed_line += "..."
        else:
            # Only change punctuation when another pause style is requested.
            mark = pause_marks[args.line_pause]

            if mark:
                processed_line = processed_line.rstrip()
                processed_line = re.sub(r"\.{1,3}$", "", processed_line)
                processed_line += mark
            else:
                processed_line = re.sub(
                    r"\.{1,3}$", "", processed_line
                ).rstrip()

        processed_lines.append(processed_line)

    # Preview: no model initialization or audio generation.
    if args.preview:
        print(f"🔎 Previewing {len(processed_lines)} poetic lines:\n")

        for idx, processed_line in enumerate(processed_lines):
            print(f"  ➡️ Chunk #{idx}: [ {processed_line} ]")

        sys.exit(0)

    ref_audio, ref_text = get_voice_profile(args.voice)

    if not ref_audio or not os.path.isfile(ref_audio):
        print("❌ Error: Could not locate reference audio asset.")
        sys.exit(1)

    OUTPUT_DIR = os.path.expanduser(args.output_dir)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    TMP_DIR = os.path.join(
        OUTPUT_DIR,
        f"tmp_{uuid.uuid4().hex[:6]}",
    )
    os.makedirs(TMP_DIR, exist_ok=True)

    auto_tashkeel = not args.no_auto_tashkeel

    print("⏳ Initializing SILMA TTS Engine onto Apple Silicon GPU (mps)...")

    tts_engine = SilmaTTS(force_tashkeel=auto_tashkeel)

    temp_files = []

    print(
        f"🔊 Processing {len(processed_lines)} Poetic Lines Independently..."
    )
    print(
        f"⚙️ Speed: {args.speed} | Steps: {args.steps} | "
        f"Seed: {args.seed if args.seed is not None else 'random'}"
    )

    for idx, processed_line in enumerate(processed_lines):
        print(f"  ➡️ Chunk #{idx}: [ {processed_line} ]")

        tmp_output_path = os.path.join(
            TMP_DIR,
            f"part_{idx}.wav",
        )

        # When seeded, use a repeatable but distinct seed for each line.
        line_seed = (
            None if args.seed is None else args.seed + idx
        )

        try:
            tts_engine.infer(
                ref_file=ref_audio,
                ref_text=ref_text,
                gen_text=processed_line,
                file_wave=tmp_output_path,

                # Optional settings
                speed=args.speed,
                nfe_step=args.steps,
                seed=line_seed,
                force_tashkeel=auto_tashkeel,
            )

            temp_files.append(tmp_output_path)

        except Exception as e:
            print(f"❌ Error during generation on line {idx}: {e}")

    if not temp_files:
        print("❌ Error: No audio tracks were generated.")
        sys.exit(1)

    voice_prefix = args.voice if args.voice else "default"

    if args.output:
        final_output_path = os.path.abspath(
            os.path.expanduser(args.output)
        )
        os.makedirs(
            os.path.dirname(final_output_path),
            exist_ok=True,
        )
    else:
        final_filename = (
            f"{voice_prefix}_poem_{uuid.uuid4().hex[:8]}.wav"
        )
        final_output_path = os.path.join(
            OUTPUT_DIR,
            final_filename,
        )

    concat_list_path = os.path.join(
        TMP_DIR,
        "concat_list.txt",
    )

    with open(concat_list_path, "w", encoding="utf-8") as f:
        for f_path in temp_files:
            f.write(f"file '{os.path.abspath(f_path)}'\n")

    print("🎬 Stitching segments back together via ffmpeg...")

    ffmpeg_cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        concat_list_path,
        "-c",
        "copy",
        final_output_path,
    ]

    result = subprocess.run(
        ffmpeg_cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    for f_path in temp_files:
        try:
            os.remove(f_path)
        except OSError:
            pass

    try:
        os.remove(concat_list_path)
        os.rmdir(TMP_DIR)
    except OSError:
        pass

    if result.returncode != 0:
        print("❌ Error: FFmpeg failed to stitch the audio segments.")
        sys.exit(1)

    print(
        f"✅ Success! Your complete poem audio is safely stored at:\n"
        f"🎯 {final_output_path}"
    )


if __name__ == "__main__":
    main()