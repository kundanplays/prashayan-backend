import requests
import json
import sys

BASE_URL = "http://localhost:8002/api/v1"
EMAIL = "verify_test_new@example.com"
PASSWORD = "SecurePassword123!"

def print_response(name, response):
    print(f"--- {name} ---")
    print(f"Status: {response.status_code}")
    try:
        print(json.dumps(response.json(), indent=2))
    except:
        print(response.text)
    print("\n")

def run_verification():
    # 1. Register
    print("1. Registering User...")
    resp = requests.post(f"{BASE_URL}/auth/register", json={
        "email": EMAIL,
        "password": PASSWORD,
        "phone": "9876543210"
    })
    print_response("Register", resp)

    # 2. Login (Trigger Login History)
    print("2. Logging in...")
    resp = requests.post(f"{BASE_URL}/auth/token", data={
        "username": EMAIL,
        "password": PASSWORD
    })
    print_response("Login", resp)
    if resp.status_code != 200:
        print("Login failed, aborting.")
        return
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 3. List Products (Trigger Search History)
    print("3. Searching Products...")
    resp = requests.get(f"{BASE_URL}/products/?q=Shilajit", headers=headers)
    print_response("Search Products", resp)

    # 4. Create Order
    print("4. Creating Order...")
    # Assuming Product ID 1 exists from seed
    resp = requests.post(f"{BASE_URL}/orders/", headers=headers, json={
        "items": [{"product_id": 1, "quantity": 1}],
        "total_amount": 1499.0,
        "shipping_address": "Test Address, India"
    })
    print_response("Create Order", resp)

    # 5. Password Reset Request
    print("5. Requesting Password Reset...")
    resp = requests.post(f"{BASE_URL}/auth/password-reset/request", json={
        "email": EMAIL
    })
    print_response("Password Reset Request", resp)
    
    # 6. Password Reset Confirm (Simulated Token)
    # We can't easily get the token without peeking DB, so we'll test the Fail case
    print("6. Confirming Password Reset (Expected Failure)...")
    resp = requests.post(f"{BASE_URL}/auth/password-reset/confirm", json={
        "token": "invalid_token",
        "new_password": "NewPassword123!"
    })
    print_response("Password Reset Confirm (Invalid)", resp)

if __name__ == "__main__":
    run_verification()
