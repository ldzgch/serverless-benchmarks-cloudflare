"""
 * This is a generic web server wrapper for sebs Python benchmarks.
 * It uses 'Flask' to create a server, imports the benchmark's
 * 'handler.py', and executes it for each incoming POST request.
"""
import os
from flask import Flask, request, jsonify

# Import the benchmark's handler function
import handler

app = Flask(__name__)

@app.route('/', methods=['POST'])
def handle_request():
    """
    Main request handling route.
    Forwards the request JSON to the benchmark handler.
    """
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    try:
        # Get the incoming event
        event = request.get_json()

        # Execute the benchmark handler
        result = handler.handler(event, {})
        
        # Return the result
        return jsonify(result), 200

    except Exception as e:
        print(f"Handler error: {e}", flush=True)
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    # Cloudflare Containers will set the PORT env var
    port = int(os.environ.get("PORT", 8080))
    # Run the Flask server
    app.run(host='0.0.0.0', port=port)