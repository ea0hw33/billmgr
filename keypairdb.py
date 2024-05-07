import sqlite3

conn = sqlite3.connect('pairs.db')

cur = conn.cursor()

# Создание таблицы pairs
cur.execute('''CREATE TABLE IF NOT EXISTS pairs
               (elid TEXT, paymentid TEXT)''')

# Добавление записи в таблицу pairs
def add_pair(elid, paymentid):
    cur.execute("INSERT INTO pairs (elid, paymentid) VALUES (?, ?)", (elid, paymentid))
    conn.commit()

# Получение записи из таблицы pairs по elid
def get_pair_by_elid(elid):
    cur.execute("SELECT * FROM pairs WHERE elid=?", (elid,))
    return cur.fetchone()

# Удаление записи из таблицы pairs по elid
def delete_pair_by_elid(elid):
    cur.execute("DELETE FROM pairs WHERE elid=?", (elid,))
    conn.commit()


# add_pair('123', 'payment_123')
# print(get_pair_by_elid('123'))
# delete_pair_by_elid('123')