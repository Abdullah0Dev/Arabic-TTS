import random
from importlib.resources import files
import re

import soundfile as sf
import tqdm
from cached_path import cached_path
from hydra.utils import get_class
from omegaconf import OmegaConf


from silma_tts.infer.utils_infer import (
    infer_process,
    load_model,
    load_vocoder,
    preprocess_ref_audio_text,
    remove_silence_for_generated_wav,
    save_spectrogram,
    transcribe,
    load_nemo_text_normalizer,
    normalize_text,
    load_tashkeel_model
)
from silma_tts.model.utils import seed_everything


class SilmaTTS:
    def __init__(
        self,
        model="SilmaTTS_V1_Small",
        ckpt_file="",
        vocab_file="",
        ode_method="euler",
        use_ema=False,
        vocoder_local_path=None,
        device=None,
        hf_cache_dir=None,
        enable_normalizer=True,
        force_tashkeel=True
    ):
        model_cfg = OmegaConf.load(str(files("silma_tts").joinpath(f"config.yaml")))
        model_cls = get_class(f"silma_tts.model.{model_cfg.model.backbone}")
        model_arc = model_cfg.model.arch

        self.mel_spec_type = model_cfg.model.mel_spec.mel_spec_type
        self.target_sample_rate = model_cfg.model.mel_spec.target_sample_rate

        self.ode_method = ode_method
        self.use_ema = use_ema

        

        if enable_normalizer:
            print("Preloading nemo normalizers ...", flush=True)
            load_nemo_text_normalizer("english")
            load_nemo_text_normalizer("عربي")

        if force_tashkeel:
            print("Loading tashkeel model...")
            load_tashkeel_model()



        if device is not None:
            self.device = device
        else:
            import torch

            self.device = (
                "cuda"
                if torch.cuda.is_available()
                else "xpu"
                if torch.xpu.is_available()
                else "mps"
                if torch.backends.mps.is_available()
                else "cpu"
            )

        print(f"Using device: {self.device}", flush=True)

        # Load models
        self.vocoder = load_vocoder(
            self.mel_spec_type, vocoder_local_path is not None, vocoder_local_path, self.device, hf_cache_dir
        )


        print(f"Loading model weights...", flush=True)

        ckpt_file = str(
            cached_path(f"hf://silma-ai/silma-tts/model.pt", cache_dir=hf_cache_dir)
        )

        vocab_file = str(
            cached_path(f"hf://silma-ai/silma-tts/vocab.txt", cache_dir=hf_cache_dir)
        )

        self.ema_model = load_model(
            model_cls, model_arc, ckpt_file, self.mel_spec_type, vocab_file, self.ode_method, self.use_ema, self.device
        )

    def transcribe(self, ref_audio, language=None):
        return transcribe(ref_audio, language)

    def export_wav(self, wav, file_wave, remove_silence=False):
        sf.write(file_wave, wav, self.target_sample_rate)

        if remove_silence:
            remove_silence_for_generated_wav(file_wave)

    def export_spectrogram(self, spec, file_spec):
        save_spectrogram(spec, file_spec)

    def infer(
        self,
        ref_file,
        ref_text,
        gen_text,
        show_info=print,
        progress=tqdm,
        target_rms=0.1,
        cross_fade_duration=0,
        sway_sampling_coef=-1,
        cfg_strength=2,
        nfe_step=16,
        speed=1.0,
        fix_duration=None,
        remove_silence=False,
        file_wave=None,
        file_spec=None,
        seed=None,
        normalize_numbers=True,
        force_tashkeel=True
    ):
        if seed is None:
            seed = random.randint(0, 4294967295)
        seed_everything(seed)
        self.seed = seed

        ref_file, ref_text = preprocess_ref_audio_text(ref_file, ref_text)


        gen_text = gen_text.strip()

        if "\n" in gen_text:
            gen_text = gen_text.replace("\n\n", "\n")

            gen_text = re.sub(r'\n', '. ', gen_text)
            
            gen_text = gen_text.replace("\n", "")


        if normalize_numbers:  

            gen_text = normalize_text(gen_text)
            print(f"Input text normalized  : {gen_text}")



        wav, sr, spec = infer_process(
            ref_file,
            ref_text,
            gen_text,
            self.ema_model,
            self.vocoder,
            self.mel_spec_type,
            show_info=show_info,
            progress=progress,
            target_rms=target_rms,
            cross_fade_duration=cross_fade_duration,
            nfe_step=nfe_step,
            cfg_strength=cfg_strength,
            sway_sampling_coef=sway_sampling_coef,
            speed=speed,
            fix_duration=fix_duration,
            device=self.device,
            force_tashkeel=force_tashkeel
        )

        if file_wave is not None:
            self.export_wav(wav, file_wave, remove_silence)

        if file_spec is not None:
            self.export_spectrogram(spec, file_spec)

        return wav, sr, spec


if __name__ == "__main__":
    silma_tts = SilmaTTS()

    wav, sr, spec = silma_tts.infer(
        ref_file=str(files("silma_tts").joinpath("infer/ref_audio_samples/ar.ref.24k.wav")),
        ref_text="ويدقق النظر في القرآن الكريم وسائر الكتب السماوية ويتبع مسالك الرسل العظام عليهم الصلاة والسلام.",
        gen_text="""
        أنا نموذج جديد من سلمى لتحويل النص إلى كلام؛ يمكنني التحدث باللغة العربية مع أو بدون علامات التشكيل.
        I am the new SILMA model for converting text to speech, I can speak Arabic with or without diacritics.
        """.strip(),
        file_wave=str(files("silma_tts").joinpath("../../tests/api_out.wav")),
        file_spec=str(files("silma_tts").joinpath("../../tests/api_out.png")),
        seed=None,
    )

    print("seed :", silma_tts.seed)
