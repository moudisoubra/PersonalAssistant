import os
import sys

# Ensure Windows terminal can print emojis (like in playlist names) without crashing
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
import asyncio
import queue
import re
# Fix for PyTorch downloader
os.environ["GIT_CONFIG_GLOBAL"] = ""
os.environ.pop("GITHUB_TOKEN", None)
os.environ.pop("GITHUB_AUTH", None)

import torch
import sounddevice as sd
import soundfile as sf
import numpy as np
import time
import difflib
import json
from faster_whisper import WhisperModel
from ddgs import DDGS
from datetime import datetime
import ollama
import spotify_tools
import youtube_tools
from dotenv import load_dotenv

load_dotenv()

# ==========================================
# VERIFY API PERMISSIONS
# ==========================================
spotify_tools.init_spotify()

# ==========================================
# INITIALIZE MODELS
# ==========================================
print("Loading Whisper STT...")
# Upgraded to large-v3 for maximum transcription accuracy (especially for foreign names)
whisper_model = WhisperModel("large-v3", device="cuda", compute_type="int8_float16")

print("Loading Silero TTS...")
tts_model, _ = torch.hub.load(repo_or_dir='snakers4/silero-models', model='silero_tts', language='en', speaker='v3_en')
tts_device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
tts_model.to(tts_device)

import ctypes

# ==========================================
# DEFINE THE TOOLS
# ==========================================
def control_media(command: str) -> str:
    """Controls media on Windows using virtual key codes."""
    VK_MEDIA_NEXT_TRACK = 0xB0
    VK_MEDIA_PREV_TRACK = 0xB1
    VK_MEDIA_PLAY_PAUSE = 0xB3
    
    if command == "next":
        ctypes.windll.user32.keybd_event(VK_MEDIA_NEXT_TRACK, 0, 0, 0)
        ctypes.windll.user32.keybd_event(VK_MEDIA_NEXT_TRACK, 0, 2, 0)
        return "Successfully skipped to the next track."
    elif command == "previous":
        # Press twice to actually go to the previous song instead of just restarting
        ctypes.windll.user32.keybd_event(VK_MEDIA_PREV_TRACK, 0, 0, 0)
        ctypes.windll.user32.keybd_event(VK_MEDIA_PREV_TRACK, 0, 2, 0)
        time.sleep(0.1)
        ctypes.windll.user32.keybd_event(VK_MEDIA_PREV_TRACK, 0, 0, 0)
        ctypes.windll.user32.keybd_event(VK_MEDIA_PREV_TRACK, 0, 2, 0)
        return "Successfully went back to the previous track."
    elif command == "restart":
        # Press once to restart the current song
        ctypes.windll.user32.keybd_event(VK_MEDIA_PREV_TRACK, 0, 0, 0)
        ctypes.windll.user32.keybd_event(VK_MEDIA_PREV_TRACK, 0, 2, 0)
        return "Successfully restarted the current track."
    elif command == "pause":
        ctypes.windll.user32.keybd_event(VK_MEDIA_PLAY_PAUSE, 0, 0, 0)
        time.sleep(0.05)
        ctypes.windll.user32.keybd_event(VK_MEDIA_PLAY_PAUSE, 0, 2, 0)
        return "Successfully paused."
    elif command == "play":
        import os
        # Windows often loses track of Spotify when it's paused if another app (like Chrome) steals the media keys.
        # To guarantee it plays, we briefly wake Spotify up via its URI to ensure it grabs focus.
        os.system("start spotify:")
        time.sleep(0.5) # Wait for Spotify to appear and grab focus
        
        # Press the media key now that Spotify is listening
        ctypes.windll.user32.keybd_event(VK_MEDIA_PLAY_PAUSE, 0, 0, 0)
        time.sleep(0.05)
        ctypes.windll.user32.keybd_event(VK_MEDIA_PLAY_PAUSE, 0, 2, 0)
        return "Successfully resumed playing."
    return "Unknown command."



def search_web(query: str) -> str:
    """Searches the internet with automatic retries for rate limits."""
    if not query or query.strip() in ["", "...", "None"]:
        return "SYSTEM ERROR: Invalid search query. The user was likely just making conversation. DO NOT search the web. Reply directly to the user's conversational prompt."
        
    print(f"Searching the web for: {query}...")
    
    for attempt in range(3):
        try:
            # FIX: Increased max_results to 10 to bypass outdated SEO articles and find actual release dates
            results = DDGS().text(query, max_results=10)
            if not results:
                return "No results found. Formulate a slightly different, broader search query and try again."
            
            formatted_data = "\n".join([f"Source: {res['title']} | Info: {res['body']}" for res in results])
            return formatted_data
            
        except Exception as e:
            print(f"Search dropped (Attempt {attempt+1}/3). Retrying...")
            time.sleep(1.5) 
            
    return "The search engine is temporarily blocking requests."

# The schema that tells the model how to use the tool
web_search_schema = {
    "type": "function",
    "function": {
        "name": "search_web",
        "description": "Search the internet for current events, facts, or gaming knowledge. DO NOT use this tool for conversational prompts, greetings, or checking status (e.g., 'can you hear me?', 'hello', 'who are you?'). Reply directly without tools for those.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string", 
                    "description": "The exact search engine query. MUST be highly specific to get the best results. Avoid overly generic terms."
                }
            },
            "required": ["query"]
        }
    }
}

media_control_schema = {
    "type": "function",
    "function": {
        "name": "control_media",
        "description": "Controls media playback on the PC (pause, next, previous, restart). Use this ONLY for general media controls like 'skip song', 'pause', 'go back', or 'play'. DO NOT use this if the user asks to play a specific named song or playlist.",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string", 
                    "enum": ["play", "pause", "next", "previous", "restart"],
                    "description": "The media command to execute."
                }
            },
            "required": ["command"]
        }
    }
}

# The Dynamic Router: Maps the schema name to the actual Python function
available_tools = {
    "search_web": search_web,
    "control_media": control_media,
    "play_spotify_music": spotify_tools.play_spotify_music,
    "list_my_playlists": spotify_tools.list_my_playlists,
    "what_is_playing": spotify_tools.what_is_playing,
    "like_current_song": spotify_tools.like_current_song,
    "search_youtube": youtube_tools.search_youtube,
    "change_wake_word": None # Will be mapped below
}

# ==========================================
# MEMORY FUNCTIONS
# ==========================================

def get_memory():
    try:
        with open("memory.json", "r") as f:
            return json.load(f)
    except:
        return {"wake_word": "bob"}

def save_memory(mem):
    with open("memory.json", "w") as f:
        json.dump(mem, f)

def change_wake_word(new_wake_word: str) -> str:
    """Changes the wake word of the assistant."""
    mem = get_memory()
    mem["wake_word"] = new_wake_word.lower()
    save_memory(mem)
    print(f"UI_WAKE_WORD_CHANGED:{new_wake_word.upper()}")
    return f"Successfully changed wake word to {new_wake_word}."

available_tools["change_wake_word"] = change_wake_word

change_wake_word_schema = {
    "type": "function",
    "function": {
        "name": "change_wake_word",
        "description": "Change the name or wake keyword that the user uses to wake you up. Use this when the user says something like 'change your name to X' or 'I want to call you X'.",
        "parameters": {
            "type": "object",
            "properties": {
                "new_wake_word": {
                    "type": "string", 
                    "description": "The new name or wake word the user wants to use."
                }
            },
            "required": ["new_wake_word"]
        }
    }
}

# ==========================================
# CORE FUNCTIONS
# ==========================================

def get_shared_state():
    try:
        with open("shared_state.json", "r") as f:
            return json.load(f)
    except:
        return {"mute": False, "volume": 1.0}

def listen_auto(fs=16000, threshold=600, silence_duration=2.5):
    """Uses a gapless audio stream to monitor speech without tearing the waveform."""
    print("\nWaiting for you to speak...")
    
    # Create a queue to safely pass audio data from the background stream to our logic
    audio_queue = queue.Queue()
    
    # This callback function runs automatically in the background
    def audio_callback(indata, frames, time, status):
        # We copy the raw audio data and immediately throw it into the queue
        audio_queue.put(indata.copy())
        
    recorded_frames = []
    is_recording = False
    silent_chunks = 0
    
    # We ask the stream to hand us audio in seamless 0.1-second blocks
    chunk_size = int(fs * 0.1)
    max_silent_chunks = int(silence_duration / 0.1)
    
    # Open a continuous gapless stream
    with sd.InputStream(samplerate=fs, channels=1, dtype=np.int16, blocksize=chunk_size, callback=audio_callback):
        while True:
            # Pull the next perfect chunk of audio from the queue
            chunk = audio_queue.get()
            
            # Check for MUTE state
            state = get_shared_state()
            if state.get("mute", False):
                is_recording = False
                recorded_frames = []
                silent_chunks = 0
                continue
                
            volume = np.max(np.abs(chunk))
            
            if not is_recording:
                # Waiting for you to start speaking
                if volume > threshold:
                    print("Speech detected! Listening...")
                    is_recording = True
                    recorded_frames.append(chunk)
                    silent_chunks = 0
            else:
                # You are speaking, collect the audio
                recorded_frames.append(chunk)
                
                # Check if you paused
                if volume < threshold:
                    silent_chunks += 1
                else:
                    silent_chunks = 0 # You kept talking, reset the silence timer!
                    
                # If you hit the silence limit, break the loop
                if silent_chunks >= max_silent_chunks:
                    print("End of sentence detected, processing...")
                    break
                    
    # The stream automatically closes when we break the loop. Now we process it.
    full_audio = np.concatenate(recorded_frames)
    sf.write("temp.wav", full_audio, fs)
    
    segments, _ = whisper_model.transcribe("temp.wav", beam_size=5)
    text = "".join([segment.text for segment in segments]).strip()
    
    print(f"You said: '{text}'")
    return text

# ==========================================
# CORE FUNCTIONS
# ==========================================

# Create a lightweight persistent memory
MAX_HISTORY_TURNS = 3 # Remembers the last 3 questions and answers
conversation_history = []

async def think(user_text: str):
    global conversation_history
    client = ollama.AsyncClient()
    wake_word = get_memory().get("wake_word", "bob")
    
# Build the fresh context with Time Awareness and Strict Search Rules
    current_date = datetime.now().strftime("%B %d, %Y")
    
    messages = [{
        "role": "system", 
        "content": (
            f"You are a highly intelligent conversational voice assistant named {wake_word.capitalize()}. Today's date is {current_date}. "
            "Provide clear, natural-sounding spoken responses. Adapt your response length based on the user's prompt. "
            "CRITICAL TTS RULE: You MUST spell out ALL numbers, decimals, and dates as words (e.g., write 'twenty twenty-six' instead of '2026', 'thirteen point zero six' instead of '13.06', 'thirty' instead of '30') because the text-to-speech engine cannot read numerical digits. "
            "CRITICAL RULE: You have outdated training data. You MUST ALWAYS use the search_web tool "
            "when asked about the 'latest', 'newest', 'current' events, or recent game updates. "
            "CRITICAL RULE: If the user asks to play music, control media, search YouTube, or list their playlists, you MUST use the provided tools. DO NOT hallucinate or make up playlists/songs. "
            "HOWEVER, DO NOT use any tools for basic conversation, greetings, or questions about your own status (e.g., 'can you hear me?', 'how are you?'). Just reply directly."
        )
    }]
    
    # Inject the lightweight conversational history
    messages.extend(conversation_history)
    
    # Add your current question
    messages.append({"role": "user", "content": user_text})

    print("Thinking...")
    
    # Determine if we should allow web searches for this query
    # If the user is just making basic conversation, we drop the tool to prevent hallucinating a search
    conversational_keywords = ["can you hear", "are you there", "hello", "hi ", "hey ", "how are you", "who are you", "goodbye", "stop", "yo ", "whats up", "what's up", "sup"]
    text_lower = user_text.lower()
    
    # If it's a short sentence and contains a greeting/status check, don't pass the tool
    is_conversational = len(text_lower.split()) <= 6 and any(k in text_lower for k in conversational_keywords)
    tools_to_use = [] if is_conversational else [
        web_search_schema, 
        media_control_schema, 
        spotify_tools.play_spotify_schema, 
        spotify_tools.list_playlists_schema,
        spotify_tools.what_is_playing_schema,
        spotify_tools.like_song_schema,
        youtube_tools.search_youtube_schema,
        change_wake_word_schema
    ]

    response = await client.chat(
        model="llama3.1", 
        messages=messages, 
        tools=tools_to_use,
        options={"temperature": 0.1}
    )
    message = response['message']
    
    final_spoken_text = ""
    
    # Handle tool routing
    if message.get('tool_calls'):
        tool_call = message['tool_calls'][0]
        func_name = tool_call['function']['name']
        args = tool_call['function']['arguments']
        
        if func_name in available_tools:
            tool_function = available_tools[func_name]
            try:
                tool_result = tool_function(**args)
            except TypeError as e:
                tool_result = f"Tool Execution Error: You passed invalid arguments to the function. Details: {e}"
            except Exception as e:
                tool_result = f"Tool Execution Error: {e}"
            
            messages.append(message)
            messages.append({"role": "tool", "content": tool_result})
            length_rule = "Provide a comprehensive, detailed, multi-sentence explanation." if any(word in user_text.lower() for word in ['detail', 'long', 'explain', 'everything', 'more']) else "Keep your answer extremely concise (1-2 sentences maximum)."
            
            if func_name == "search_web":
                synthesis_prompt = f"You now have the search results. Synthesize a natural, conversational spoken answer. CRITICAL LENGTH RULE: {length_rule} Only state the facts found in the sources provided."
            else:
                synthesis_prompt = f"You have executed the tool and received the result. Synthesize a very short, natural confirmation. Do not explain what you did, just confirm it naturally."
                
            synthesis_prompt += " Do not output raw JSON, code, or tool formatting. REMEMBER: Spell out ALL numbers as words (e.g., 'twenty twenty-six', 'thirty', 'thirteen point zero six'). ABSOLUTELY NO DIGITS ALLOWED (0-9) IN YOUR FINAL TEXT."
            
            messages.append({
                "role": "user", 
                "content": synthesis_prompt
            })
            
            final_response = await client.chat(
                model="llama3.1", 
                messages=messages,
                options={"temperature": 0.1}
            )
            final_spoken_text = final_response['message']['content']
    else:
        # If no tool was used, the first thought is the final answer
        final_spoken_text = message.get('content', '')

    # Strip any accidental 'assistant' prefix that the model might generate
    final_spoken_text = re.sub(r'(?i)^assistant[:\s]*\n*', '', final_spoken_text.strip())

    # Ensure all digits are spelled out for the TTS
    digit_map = {'0': 'zero', '1': 'one', '2': 'two', '3': 'three', '4': 'four', '5': 'five', '6': 'six', '7': 'seven', '8': 'eight', '9': 'nine'}
    final_spoken_text = re.sub(r'(?<=\d)\.(?=\d)', ' point ', final_spoken_text)
    sanitized_text = ""
    for char in final_spoken_text:
        if char.isdigit():
            sanitized_text += f" {digit_map[char]} "
        else:
            sanitized_text += char
    final_spoken_text = re.sub(r'\s+', ' ', sanitized_text).strip()

    # Save ONLY the clean dialogue to the persistent memory
    if final_spoken_text:
        conversation_history.append({"role": "user", "content": user_text})
        conversation_history.append({"role": "assistant", "content": final_spoken_text})
        
        # Prune the memory to prevent context bloat (multiplying by 2 because each turn has 2 messages)
        if len(conversation_history) > MAX_HISTORY_TURNS * 2:
            conversation_history = conversation_history[-MAX_HISTORY_TURNS * 2:]
            
    return final_spoken_text

def speak(text: str, speaker_id='en_99'): 
    print(f"Assistant: {text}")
    
    # Clean up the text and split it into individual sentences
    text = text.replace('\n', ' ')
    # Splits by period, exclamation, or question mark followed by a space
    sentences = [s.strip() for s in re.split(r'(?<=[.!?]) +', text) if s.strip()]
    
    interrupted = False
    
    # Background callback to monitor your mic volume
    def check_interruption(indata, frames, time_info, status):
        nonlocal interrupted
        if np.max(np.abs(indata)) > 1000: 
            interrupted = True

    # Open the mic stream purely to listen for a volume spike
    with sd.InputStream(samplerate=16000, channels=1, dtype=np.int16, callback=check_interruption):
        
        # Iterate through and play each sentence one by one
        for sentence in sentences:
            if interrupted:
                break
                
            # Failsafe: if a single run-on sentence is still somehow too long, cap it
            if len(sentence) > 900:
                sentence = sentence[:900]
                
            try:
                # Generate audio for just this sentence
                audio_tensor = tts_model.apply_tts(text=sentence, speaker=speaker_id, sample_rate=24000)
                audio_array = audio_tensor.cpu().numpy()
                
                # Apply volume multiplier
                state = get_shared_state()
                vol = float(state.get("volume", 1.0))
                audio_array = audio_array * vol
                
                sd.play(audio_array, samplerate=24000)
                duration = len(audio_array) / 24000.0
                start_time = time.time()
                
                # Wait for the sentence to finish playing, watching for interrupts
                while time.time() - start_time < duration:
                    if interrupted:
                        print("\nBarge-in detected! Stopping playback...")
                        sd.stop() 
                        time.sleep(0.2) 
                        break # Break the inner loop
                    time.sleep(0.05)
                    
            except Exception as e:
                print(f"Skipping chunk due to TTS error: {e}")
                continue
# ==========================================
# THE MASTER LOOP
# ==========================================
async def main_loop():
    sleep_command = "cease"
    timeout_seconds = 30  # Go back to sleep after 30 seconds of silence
    is_awake = False
    last_interaction_time = 0

    wake_word = get_memory().get("wake_word", "bob")
    print(f"\nSystem Online! Waiting for wake word '{wake_word.capitalize()}'...")
    
    while True:
        # Refresh memory dynamically
        wake_word = get_memory().get("wake_word", "bob")
        
        # Check if we should fall asleep due to timeout
        if is_awake and (time.time() - last_interaction_time > timeout_seconds):
            print(f"\nIt's been {timeout_seconds} seconds. Going back to sleep...")
            is_awake = False
            
        # Listen
        text = listen_auto()
        
        if not text:
            continue
            
        text_clean = re.sub(r'[^\w\s]', '', text.lower()).strip()
        
        if not is_awake:
            # We are asleep, only listen for the wake word
            if wake_word in text_clean:
                print(f"Wake word '{wake_word}' detected! Waking up...")
                is_awake = True
                last_interaction_time = time.time()
                
                # If they just said "Victoria", greet them and wait for the next command
                if len(text_clean.split()) <= 2:
                    speak("Yes, how can I help?")
                    continue
            else:
                # Ignore everything else while asleep
                continue
        else:
            # We are awake. Check for sleep command
            if sleep_command in text_clean.split() and len(text_clean.split()) <= 3:
                print("Sleep command detected. Going back to sleep...")
                is_awake = False
                speak("Going to sleep.")
                continue

        # If we reach here, we are awake and have a valid command
        last_interaction_time = time.time()
        
        # Remove the wake word (and optional greetings like "Hey") from the BEGINNING of the prompt so it doesn't pollute web searches.
        # We only remove it from the start so that queries like "Who was Queen Victoria?" still work!
        clean_prompt = re.sub(rf'(?i)^(?:hey\s+|hi\s+|hello\s+)?\b{wake_word}\b[,\s]*', '', text).strip()
        
        # If the user only said the wake word and nothing else, we just skip (already handled greeting)
        if not clean_prompt:
            continue
        
        # Think
        response = await think(clean_prompt)
        
        # Speak
        if response:
            speak(response)

if __name__ == "__main__":
    asyncio.run(main_loop())