import requests

URL = "http://localhost:8000"

def register():
    # Send as JSON
    json_data = {
        "username": "testuser",
        "password": "testpassword",
    }

    response = requests.post(url=f"{URL}/register", json=json_data)

    print(response.status_code)
    print(response.json())
    
def login():
    data = {
        "username": "testuser",
        "password": "testpassword"
    }
    
    response = requests.post(url=f"{URL}/token", data=data)
    print(response.status_code)
    access_token = response.json().get("access_token")
    token_type = response.json().get("token_type")
    print(access_token)
    
    auth_header = { "Authorization": f"{token_type} {access_token}" }
    
    info = requests.get(f"{URL}/users/me", headers=auth_header)
    print(info.text)
    
def main(): 
    register()
    login()
    
main()