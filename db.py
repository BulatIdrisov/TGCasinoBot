import sqlite3 as sq

# устанавливаем соединение с базой данных
db = sq.connect('tg.db')
cur = db.cursor()
# создание бд
async def db_start():
    global db, cur
    cur.execute('''
    CREATE TABLE IF NOT EXISTS accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tg_id INTEGER,
    first_name TEXT,
    balance INTEGER
    )
    ''')
    db.commit()
# ввод нового пользователя в бд
async def cmd_start_db(user_id,first_name):
    user = cur.execute("SELECT * FROM accounts WHERE tg_id == {key}".format(key=user_id)).fetchone()
    if not user:
        cur.execute("INSERT INTO accounts (tg_id,balance,first_name) VALUES (?,?,?)", (user_id,100000,first_name))

        db.commit()
# обновление баланса
async def update_balance(user_id,sum):
    cur.execute('UPDATE accounts SET balance = balance + ? WHERE tg_id = ?', (sum, user_id))
    db.commit()
    print(user_id,sum)
# функция возвращающая баланс пользователя
def balance(user_id):
    cur.execute('SELECT balance FROM accounts WHERE tg_id = ?', (user_id,))
    balance_row = cur.fetchone()
    if balance_row:
        balance = balance_row[0]
        return balance
# пополнение баланса пользователя
def replenish(user_id, sum):
    cur.execute('UPDATE accounts SET balance = balance + ? WHERE tg_id = ?', (sum, user_id))
    db.commit()
# список пользователей
def users():
    cur.execute("SELECT first_name, tg_id, balance FROM accounts")
    a = cur.fetchall()

    result = ""
    for first_name, tg_id, balance  in a:
        result += f"{first_name} - {tg_id} - {balance}\n"
    return result
# список id пользователей(используется для проверок существования id)
def users_id_array():
    cur.execute("SELECT  tg_id FROM accounts")
    result = cur.fetchall()
    result_array = []
    for i in result:
        result_array.append(str(i[0]))
    return result_array
# рейтинг
def rating():
    cur.execute("SELECT first_name, balance FROM accounts")
    data = cur.fetchall()
    sorted_data = sorted(data, key=lambda x: x[1], reverse=True)

    result = ""
    conter = 1
    for name, balance in sorted_data:
        result += f"{conter}.{name} - {balance}\n"
        conter+=1
    return result

# сохраняем изменения
    db.commit()
    rating()
