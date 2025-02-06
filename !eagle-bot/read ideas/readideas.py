import sqlite3
from tabulate import tabulate

def fetch_and_print_ideas(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM ideas")
    rows = cursor.fetchall()
    
    if rows:
        headers = [desc[0] for desc in cursor.description]
        print(tabulate(rows, headers=headers, tablefmt="grid"))
    else:
        print("Таблица пуста.")
    
    conn.close()

fetch_and_print_ideas(r"C:\Users\user\Desktop\work\!eagle-bot\ideas.db") #тут путь ребят