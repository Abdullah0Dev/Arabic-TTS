import os
import gradio as gr
import tempfile
from importlib.resources import files
from silma_tts.api import SilmaTTS

print("Loading SILMA TTS model...", flush=True)
silma_tts = SilmaTTS()

current_dir = os.path.dirname(os.path.abspath(__file__))
ref_audio_dir = os.path.join(current_dir, "infer", "ref_audio_samples")

def do_inference(ref_audio, ref_text, gen_text):
    if not ref_audio:
        return None
    
    _, output_wav_path = tempfile.mkstemp(suffix=".wav")

    wav, sr, _ = silma_tts.infer(
        ref_file=ref_audio,
        ref_text=ref_text,
        gen_text=gen_text,
        file_wave=output_wav_path,
    )

    return output_wav_path


with gr.Blocks() as demo:
    gr.Markdown("# SILMA TTS Demo")
    gr.Markdown("Add reference audio, reference text and generation text then click 'Generate Speech'")
    
    with gr.Row():
        with gr.Column():
            # Define inputs
            ref_audio_input = gr.Audio(
                label="Reference Audio", 
                type="filepath", 
                value=ref_audio_dir+"/ar.ref.24k.wav"
            )
            ref_text_input = gr.Textbox(
                label="Reference Text", 
                value="ويدقق النظر في القرآن الكريم وسائر الكتب السماوية ويتبع مسالك الرسل العظام عليهم الصلاة والسلام."
            )
            gen_text_input = gr.Textbox(
                label="Generation Text", 
                lines=5,
                value="""
أنا نموذج جديد من سلمى لتحويل النص إلى كلام، يمكنني التحدث باللغة العربية مع أو بدون علامات التشكيل.
I am the new SILMA model for converting text to speech, I can speak Arabic with or without diacritics.
""".strip()
            )
            submit_btn = gr.Button("Generate Speech")
            
        with gr.Column():
            audio_output = gr.Audio(label="Generated Speech")


    # When ref_audio_input changes, we update ref_text_input with an empty string
    ref_audio_input.input(
        fn=lambda: "", 
        inputs=None, 
        outputs=ref_text_input
    )
    
    # Set up the click event for the button
    submit_btn.click(
        fn=do_inference,
        inputs=[ref_audio_input, ref_text_input, gen_text_input],
        outputs=audio_output
    )

def main():
    print("Starting app...")

    demo.queue().launch(server_name="0.0.0.0", server_port=7860, allowed_paths=[ref_audio_dir])

if __name__ == "__main__":
    main()