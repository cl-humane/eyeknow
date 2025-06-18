from flask import Flask, request, render_template
import requests

app = Flask(__name__)

ROBOFLOW_API_KEY = "your_roboflow_api_key_here"
ROBOFLOW_PROJECT = "your_project_name"
ROBOFLOW_WORKSPACE = "your_workspace_name"

@app.route('/')
def home():
    return render_template('upload.html')

@app.route('/upload', methods=['POST'])
def upload_image():
    image = request.files['image']
    object_name = request.form['object_name']

    # Send to Roboflow
    response = requests.post(
        f"https://api.roboflow.com/dataset/{ROBOFLOW_PROJECT}/upload",
        params={"api_key": ROBOFLOW_API_KEY},
        files={"file": image},
        data={"name": object_name}
    )

    if response.ok:
        return "Upload successful! Image sent to Roboflow."
    else:
        return "Upload failed: " + response.text

if __name__ == '__main__':
    app.run(debug=True)