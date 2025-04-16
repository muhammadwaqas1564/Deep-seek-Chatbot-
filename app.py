from flask import Flask, render_template, request, jsonify, session
import requests, json, os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.urandom(24)

API_URL = "https://openrouter.ai/api/v1/chat/completions"
API_KEY = os.getenv("OPENROUTER_API_KEY")

# Ensure chat_logs folder exists
if not os.path.exists("chat_logs"):
    os.makedirs("chat_logs")

def save_chat_history(history):
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"chat_history_{timestamp}.json"
    filepath = os.path.join("chat_logs", filename)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=4)
    return filename

@app.route('/')
def index():
    # Initialize session conversation if not present.
    if 'conversation' not in session:
        session['conversation'] = []
    # Render index.html. The sidebar sessions list will be loaded via AJAX.
    return render_template('index.html', current_session=session['conversation'])

@app.route('/chat', methods=['POST'])
def chat():
    user_message = request.json.get('message')
    if not user_message:
        return jsonify({"error": "No message provided"}), 400

    conversation = session.get('conversation', [])
    conversation.append({"role": "user", "content": user_message})

    response = requests.post(
        url=API_URL,
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        },
        data=json.dumps({
            "model": "deepseek/deepseek-r1:free",
            "messages": conversation
        })
    )

    if response.status_code == 200:
        result = response.json()
        bot_reply = result['choices'][0]['message']['content']
        conversation.append({"role": "assistant", "content": bot_reply})
        session['conversation'] = conversation
        
        # Save session history to file (each API call saves the conversation)
        saved_filename = save_chat_history(conversation)
        # For debugging you might print the filename.
        print(f"Saved session as: {saved_filename}")
        
        return jsonify({"reply": bot_reply})
    else:
        return jsonify({"error": "Error with API call"}), 500

@app.route('/sessions', methods=['GET'])
def sessions():
    """List all saved sessions (filenames) in descending order of modification time."""
    files = os.listdir("chat_logs")
    # Sort files by modification time (descending)
    files_sorted = sorted(files, key=lambda f: os.path.getmtime(os.path.join("chat_logs", f)), reverse=True)
    # Return only the filenames; these serve as session IDs or titles.
    return jsonify({"sessions": files_sorted})

@app.route('/load_session', methods=['GET'])
def load_session():
    filename = request.args.get("filename")
    if not filename:
        return jsonify({"error": "No filename provided"}), 400
    filepath = os.path.join("chat_logs", filename)
    if not os.path.exists(filepath):
        return jsonify({"error": "File not found"}), 404
    with open(filepath, "r", encoding="utf-8") as f:
         conversation = json.load(f)
    return jsonify({"conversation": conversation})


@app.route('/delete_session', methods=['DELETE'])
def delete_session():
    filename = request.args.get("filename")
    if not filename:
        return jsonify({"error": "No filename provided"}), 400
    filepath = os.path.join("chat_logs", filename)
    if not os.path.exists(filepath):
        return jsonify({"error": "File not found"}), 404
    os.remove(filepath)  # Delete the file
    return jsonify({"message": "Session deleted successfully"})

if __name__ == '__main__':
    app.run(debug=True)
