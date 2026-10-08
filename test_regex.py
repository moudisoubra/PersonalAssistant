import re

wake_word = "victoria"
test_cases = [
    "Victoria, what color is the sky?",
    "Hey Victoria, what color is the sky?",
    "Hi Victoria what color is the sky",
    "Hello Victoria, what color is the sky?",
    "Who was Queen Victoria?",
    "Victoria",
    "Hey Victoria"
]

for text in test_cases:
    clean_prompt = re.sub(rf'^(?i)(?:hey\s+|hi\s+|hello\s+)?\b{wake_word}\b[,\s]*', '', text).strip()
    print(f"'{text}' -> '{clean_prompt}'")
