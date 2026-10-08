import sounddevice as sd
import soundfile as sf
import numpy as np
from faster_whisper import WhisperModel

# Load the Whisper model into your GPU
# The "medium.en" model is larger but significantly more accurate for natural speech.
print("Loading Whisper model into VRAM...")
model = WhisperModel("medium.en", device="cuda", compute_type="int8_float16")
print("Model loaded!")

def record_audio(duration=5, fs=16000):
    """Records audio from the default microphone."""
    print(f"\nRecording for {duration} seconds... Speak now!")
    # Record audio as a NumPy array
    recording = sd.rec(int(duration * fs), samplerate=fs, channels=1, dtype=np.int16)
    sd.wait() # Block execution until the recording finishes
    print("Recording complete.")
    
    # Save it to a temporary file
    filename = "temp_audio.wav"
    sf.write(filename, recording, fs)
    return filename

def transcribe(filename):
    """Passes the audio file to Whisper for transcription."""
    print("Transcribing...")
    segments, info = model.transcribe(filename, beam_size=5)
    
    print(f"Detected language: {info.language} with {info.language_probability:.2f} probability")
    
    full_text = ""
    for segment in segments:
        full_text += segment.text
        
    print(f"\nTranscript: '{full_text.strip()}'")

# Run the test
if __name__ == "__main__":
    audio_file = record_audio(duration=5)
    transcribe(audio_file)