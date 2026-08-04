import uvicorn
import mysql.connector as ms
import fastapi as fa
import json

app = fa.FastAPI()

db_config = {"host": "localhost", "user": "server", "password": "zaza", "database": "chatapp"}

def get_connection():
    return ms.connect(**db_config)

@app.post("/register")
def register(username: str = fa.Form(...), password: str = fa.Form(...)):
    con = get_connection()
    cur = con.cursor()
    try:
        cur.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, password))
        con.commit()
        return "Success!!! The user has been registered :D"
    
    except ms.Error as e:
        return f"Error!!! {str(e)}"
    
    finally:
        cur.close()
        con.close()

@app.post("/login")
def login(username: str = fa.Form(...), password: str = fa.Form(...)):
    con = get_connection()
    cur = con.cursor(dictionary=True)
    cur.execute("SELECT * FROM users WHERE username=%s AND password=%s", (username, password))
    user = cur.fetchone()
    if not user:
        print(f"Login failed: Invalid details for {username}")
        cur.close()
        con.close()
        return {"status": "error", "message": "Invalid username or password!"}

    cur.execute("SELECT * FROM messages WHERE sender_id=%s OR receiver_id=%s ORDER BY timestamp", (user["id"], user["id"]))
    chats = cur.fetchall()

    cur.close()
    con.close()
    return {"status": "success", "user": user, "chats": chats}

@app.post("/send_message")
def send_message(sender_id: int = fa.Form(...), receiver_id: int = fa.Form(...), content: str = fa.Form(...)):
    con = get_connection()
    cur = con.cursor()
    cur.execute("INSERT INTO messages (sender_id, receiver_id, message) VALUES (%s, %s, %s)", (sender_id, receiver_id, content))
    con.commit()
    cur.close()
    con.close()
    return "Success!!! Mesgew stpred"

@app.get("/get_messages")
def get_messages(user1: int, user2: int):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM messages WHERE (sender_id=%s AND receiver_id=%s) OR (sender_id=%s AND receiver_id=%s) ORDER BY timestamp",(user1, user2, user2, user1))
    messages = cursor.fetchall()
    cursor.close()
    conn.close()
    return {"messages":messages}


# WEBSOCKET CONNECTIONNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNN 

class ConnectionWeb:
    def __init__(self):
        self.active_connections = {}

    async def connect(self, websocket: fa.WebSocket, user_id: int):
        await websocket.accept()
        self.active_connections[user_id] = websocket

    def disconnect(self, user_id: int):
        if user_id in self.active_connections:
           del self.active_connections[user_id]

    async def send_to_sender_and_receiver(self, sender_id: int, receiver_id: int, message: str):
        if sender_id in self.active_connections:
            await self.active_connections[sender_id].send_text(message)
        
        if receiver_id in self.active_connections:
            await self.active_connections[receiver_id].send_text(message)

manager = ConnectionWeb()

@app.websocket("/ws/{user_id}")
async def websock_endpoint(websocket: fa.WebSocket, user_id: int):
    await manager.connect(websocket, user_id)
    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            sender_id = int(msg["sender_id"])
            receiver_id = int(msg["receiver_id"])
            message = msg["message"]

            con = get_connection()
            cur = con.cursor()
            cur.execute("INSERT INTO messages (sender_id, receiver_id, message) VALUES (%s, %s, %s)",(sender_id, receiver_id, message),)
            con.commit()
            cur.close()
            con.close()

            payload = {
                "sender_id": sender_id,
                "receiver_id": receiver_id,
                "message": message
            }
            await manager.send_to_sender_and_receiver(sender_id, receiver_id, json.dumps(payload))

    except Exception as e:
        print(f"WebSocket error for {user_id}: {e}")
        manager.disconnect(user_id)
