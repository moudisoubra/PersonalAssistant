import sys
import subprocess
import importlib.util
import urllib.request
import time

def check_and_install_dependencies():
    # Mapping of module names to their pip package names
    dependencies = {
        "torch": "torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118", # Assuming CUDA but standard torch is fine too
        "sounddevice": "sounddevice",
        "soundfile": "soundfile",
        "numpy": "numpy",
        "faster_whisper": "faster-whisper",
        "ddgs": "ddgs",
        "ollama": "ollama",
        "spotipy": "spotipy",
        "dotenv": "python-dotenv",
        "fastapi": "fastapi",
        "uvicorn": "uvicorn",
        "pydantic": "pydantic"
    }

    missing_packages = []
    
    for module_name, pip_name in dependencies.items():
        if importlib.util.find_spec(module_name) is None:
            # We split by space in case of complex pip names like torch, but add them to missing
            missing_packages.append(pip_name)

    if missing_packages:
        print("Missing dependencies detected!")
        for pkg in missing_packages:
            print(f" - {pkg}")
            
        choice = input("\nWould you like to install them now? (y/n): ").strip().lower()
        if choice == 'y':
            print("\nInstalling missing dependencies...")
            
            # Since torch has custom index urls sometimes, we install packages one by one or parse them
            for pkg in missing_packages:
                print(f"Installing {pkg}...")
                subprocess.check_call([sys.executable, "-m", "pip", "install"] + pkg.split())
                
            print("\nDependencies installed successfully!\n")
        else:
            print("Cannot start the assistant without the required dependencies. Exiting.")
            sys.exit(1)
    else:
        print("All dependencies are satisfied.\n")

if __name__ == "__main__":
    check_and_install_dependencies()
    
    print("Checking if Ollama is running...")
    try:
        urllib.request.urlopen("http://127.0.0.1:11434/", timeout=2)
        print("Ollama is running.")
    except Exception:
        print("Ollama is not running. Starting Ollama in the background...")
        try:
            # 0x08000000 is CREATE_NO_WINDOW so it doesn't pop up a second terminal
            subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=0x08000000)
            time.sleep(3) # Give the server a moment to boot
        except FileNotFoundError:
            print("Warning: Could not find 'ollama' in your system PATH. Please start Ollama manually.")

    print("\nStarting agent.py...")
    try:
        # Launch agent.py
        subprocess.run([sys.executable, "agent.py"])
    except KeyboardInterrupt:
        print("\nAgent stopped.")