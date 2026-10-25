
import time
from importlib.resources import files
from silma_tts.api import SilmaTTS

silma_tts = SilmaTTS()

time_start = time.time()
wav, sr, spec = silma_tts.infer(
    ref_file=str(files("silma_tts").joinpath("infer/ref_audio_samples/ar.ref.24k.wav")),
    ref_text="ويدقق النظر في القرآن الكريم وسائر الكتب السماوية ويتبع مسالك الرسل العظام عليهم الصلاة والسلام.",
    gen_text="""
    أنا نموذج جديد من سلمى لتحويل النص إلى كلام، يمكنني التحدث باللغة العربية مع أو بدون علامات التشكيل.
    I am the new SILMA model for converting text to speech, I can speak Arabic with or without diacritics.
    """.strip(),
    file_wave=str("generated_audio.wav"),
    seed=None,
    speed=1
)
time_end = time.time()
print(f"Time elapsed:{(time_end-time_start):.2f} seconds")

## result is saved in generated_audio.wav