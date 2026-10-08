import webbrowser
import urllib.parse

def search_youtube(query: str) -> str:
    """Opens the default web browser and searches YouTube for the given query."""
    try:
        url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}"
        webbrowser.open(url)
        return f"Successfully opened YouTube and searched for '{query}'."
    except Exception as e:
        return f"Error opening YouTube: {str(e)}"

# ==========================================
# SCHEMAS
# ==========================================

search_youtube_schema = {
    "type": "function",
    "function": {
        "name": "search_youtube",
        "description": "Opens the user's web browser and searches YouTube for the specified query. Use this ONLY when the user explicitly asks to search for something on YouTube or watch a video on YouTube.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The exact search query to look for on YouTube."
                }
            },
            "required": ["query"]
        }
    }
}
