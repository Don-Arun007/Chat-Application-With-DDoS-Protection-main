import mysql.connector as ms

def get_connection():
    return ms.connect(host = "local")