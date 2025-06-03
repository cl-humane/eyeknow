import requests

def upload_image_to_roboflow(api_key, project_name, image_path):
    url = f"https://api.roboflow.com/dataset/{project_name}/upload"
    with open(image_path, "rb") as img_file:
        response = requests.post(
            url,
            files={"file": img_file},
            data={"api_key": api_key}
        )
    return response.json()
 H