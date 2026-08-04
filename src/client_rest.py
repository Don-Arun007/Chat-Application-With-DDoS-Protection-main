import requests
import re
import asyncio
import websockets
import json
import threading

async def chat(uid):
    async with websockets.connect(f"ws://20.2.82.52:8000/ws/{uid}") as websocket:
        print("Connected to real-time chat!")
        print("Send messages in this format: <receiver_id>|<your message>\n")

        async def listen():
            while True:
                try:
                    msg = await websocket.recv()
                    data = json.loads(msg)
                    sender = "You" if data["sender_id"] == uid else f"User {data['sender_id']}"
                    receiver = "You" if data["receiver_id"] == uid else f"User {data['receiver_id']}"
                    print(f"\n[{sender} -> {receiver}]: {data['message']}\nYou: ", end="", flush=True)
                except websockets.exceptions.ConnectionClosed:
                    print("\n Connection closed.")
                    break

        asyncio.create_task(listen())

        while True:
            try:
                text = input("You: ")
                if "|" not in text:
                    print("Format error! Use: receiver_id|message")
                    continue

                receiver_id, message = text.split("|", 1)
                payload = {
                    "sender_id": uid,
                    "receiver_id": int(receiver_id.strip()),
                    "message": message.strip()
                }
                await websocket.send(json.dumps(payload))

            except KeyboardInterrupt:
                print("\n Exiting chat...")
                break


usesrname = input("Enter your username: ")

pattern = re.compile(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,}$')
ch = input("Do you want to register or login?: ").lower()

if ch == "register":
    for i in range(4):
        password = input("Enter the password: ")
        if pattern.match(password):
            resp = requests.post("http://20.2.82.52:8000/register", data={"username":usesrname, "password": password})
            print("Try logging in now :D")
            exit()

        elif i == 3:
            print("Sorry cannot process your request!")
            exit()

        else:
            print("Password must be moe than 7 characters with uppercase, lowercase and number")
            print()

elif ch == "login":
    password = input("Enter your password: ")
    resp = requests.post("http://20.2.82.52:8000/login", data={"username": usesrname, "password": password})
    
    data = resp.json()


    if data.get("status") == "success":
        user_id = data["user"]["id"]
        print(f"Logged in successfully! Your ID: {user_id}\n")

        print("=== Your Chat History ===")
        for msg in data["chats"]:
            sender = "You" if msg["sender_id"] == user_id else f"User {msg['sender_id']}"
            receiver = "You" if msg["receiver_id"] == user_id else f"User {msg['receiver_id']}"
            print(f"[{msg['timestamp']}] {sender} -> {receiver}: {msg['message']}")
        print("========================\n")

        asyncio.run(chat(user_id))

    else:
        print(data.get("message"))
        exit()

else:
    print("Invalid option!!!")
    exit()