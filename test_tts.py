import os
# Temporarily hide global Git credentials
os.environ["GIT_CONFIG_GLOBAL"] = ""
os.environ.pop("GITHUB_TOKEN", None)
os.environ.pop("GITHUB_AUTH", None)

import torch
import sounddevice as sd
import time

print("Downloading/Loading Silero TTS model...")
# FIX: The correct repository is 'snakers4/silero-models'
model, example_text = torch.hub.load(
    repo_or_dir='snakers4/silero-models',
    model='silero_tts',
    language='en',
    speaker='v3_en'
)

# Move the model to the GPU for instant processing
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
model.to(device)

def speak_neural(text: str, speaker: str = 'en_67'):
    """
    Synthesizes and plays text using a neural voice.
    'en_21' is a clear male voice. Try 'en_0' for a female voice.
    """
    print(f"\nSynthesizing: {text}")
    start_time = time.time()
    
    # Generate the audio waveform array
    audio_tensor = model.apply_tts(
        text=text,
        speaker=speaker,
        sample_rate=24000
    )
    
    generation_time = time.time() - start_time
    print(f"Audio generated in {generation_time:.2f} seconds")
    
    # Convert tensor to numpy array and play it
    audio_array = audio_tensor.cpu().numpy()
    sd.play(audio_array, samplerate=24000)
    sd.wait()

if __name__ == "__main__":
    test_phrase = "System initialization complete. The neural voice pipeline is now online."
    speak_neural(test_phrase)