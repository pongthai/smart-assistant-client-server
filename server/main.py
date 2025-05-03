# main.py (on Mac Mini)
from flask import Flask, request, jsonify
from gpt_integration import GPTClient

app = Flask(__name__)
gpt = GPTClient()

@app.route("/ask", methods=["POST"])
def ask():
    data = request.get_json()
    user_text = data.get("text", "")
    if not user_text:
        return jsonify({"error": "No input provided"}), 400

    response = gpt.ask(user_text)
    return jsonify({"response": response})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
    