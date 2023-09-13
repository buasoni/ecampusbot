import sqlite3
import requests
import json
from bs4 import BeautifulSoup
from collections import Counter
import telebot
import schedule
import time
import threading

#botid
bot = telebot.TeleBot("")

#create database
def createbase():
    conn = sqlite3.connect('user_database.db')
    cursor = conn.cursor()

    create_table_query = '''
    CREATE TABLE IF NOT EXISTS users (
        userid INTEGER PRIMARY KEY AUTOINCREMENT,
        login TEXT NOT NULL,
        password TEXT NOT NULL,
        rating TEXT 
    );
    '''
    cursor.execute(create_table_query)
    conn.commit()
    conn.close()

createbase()
#start
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "Вітаю, я байрактар і можу моніторить ваш кампус\nДля початку пропишіть '/reg Логін Пароль' від вашого аккаунта\nНа цьому все\nЯкщо в кампусі з'явиться оцінка вам прийде повідомлення")

#reg
@bot.message_handler(commands=['reg'])
def registr(message):
    try:
        messagess = message.text.split()
        user_id = int(message.chat.id)
        login = str(messagess[1])
        password = str(messagess[2])
        marklist,namelist = conect(username=login,password=password, user_id=user_id)
        marklist = json.dumps(marklist)
        conn = sqlite3.connect('user_database.db')
        cursor = conn.cursor()
        insert_query = 'INSERT INTO users (userid, login, password, rating) VALUES (?, ?, ?, ?)'
        cursor.execute(insert_query, (user_id, login, password, marklist))
        conn.commit()
        conn.close()
        bot.send_message(message.chat.id, "Ви успішно зареєстровані")
    except:
        bot.send_message(message.chat.id, "Ви вже зареєстровані(якщо ви бажаєте видалити свій запис, просто пропишіть /delete)")

@bot.message_handler(commands=['delete'])
def delete(message):
    user_id = int(message.chat.id)
    conn = sqlite3.connect('user_database.db')
    cursor = conn.cursor()
    delete_query = 'DELETE FROM users WHERE userid = ?'
    cursor.execute(delete_query, (user_id,))
    conn.commit()
    conn.close()
    bot.send_message(message.chat.id,"Ваш запис успішно видалено")
      
@bot.message_handler(commands=['up'])
def up(message):
    bot.send_sticker(message.chat.id,"CAACAgEAAxkBAAEKRjhk_0NpXdXIODcCZTbFkrUnnricUQACrSMAAnj8xgVKMYgLMPkNijAE")   

def conect(username,password,user_id):
  try:
    gettken = requests.post(url='https://api.campus.kpi.ua/oauth/token', data={'username':username,'password':password})    
    token = json.loads(gettken.text)['access_token']
    sid = json.loads(gettken.text)['sessionId']
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.150 Safari/537.36',
    }
    cookies = {
    'token':token,
    'SID':sid
    }   
    s = requests.session()
    response1 = s.get(url='https://campus.kpi.ua/auth.php',headers=headers,cookies=cookies)
    cookies = response1.cookies.get_dict()
    s.cookies.update(cookies)
    response = s.get(url='https://campus.kpi.ua/student/index.php?mode=studysheet',headers=headers,cookies=cookies)

    soup = BeautifulSoup(response.content, "html.parser")
    links = soup.find_all('a', href=True)
    hreflist = []
    namelist = []
    marklist = {}

    for link in links:
        href = link['href']
        if href[0] == '/':
            text = link.text.strip()
            hreflist.append('https://campus.kpi.ua'+str(href))
            namelist.append(text)

    def is_number(string):
        try:
            float(string)
            return True
        except ValueError:
            return False

    for i in range(len(hreflist)):
        responseLess = s.get(hreflist[i], headers=headers, cookies=cookies)
        soupLess = BeautifulSoup(responseLess.content, "html.parser")
        tr_elements = soupLess.find_all('tr')
        marks = []
        sum_mark = 0
        for tr in tr_elements:
            td_elements = tr.find_all('td')
            if len(td_elements) >= 4:
                mark = td_elements[1].get_text(strip=True)
                if is_number(mark):
                    marks.append(float(mark))
                    sum_mark+=float(mark)
        marks.append(sum_mark)
        marklist[i] = marks
    return marklist,namelist
  except:
    bot.send_message(user_id,'Невірний логін або пароль')
    
def check_mark(marklist,namelist,user_id):
    print('check')
    conn = sqlite3.connect('user_database.db')
    cursor = conn.cursor()
    select_query = 'SELECT * FROM users WHERE userid = ?'
    cursor.execute(select_query, (user_id,))
    records = cursor.fetchall()
    conn.close()
    for record in records:
        rating = record[3]
        data2 = json.loads(rating)
        data2 = {int(key): value for key, value in data2.items()}
        missing_values = {}
        if len(marklist.keys()) != len(data2.keys()):
            for key, values in marklist.items():
                if key not in data2:
                    missing_values[key] = values
            for key, values in missing_values.items():
                bot.send_message(user_id,f'У вас нова оцінка: {values[len(values)-2]} з {namelist[int(key)]}\nЗагалом у вас {marklist[int(key)][len(marklist[int(key)])-1]}')
        else:
            for key, value in data2.items():
                if len(marklist[int(key)]) > len(value):
                    list1 = marklist[int(key)]
                    list1 = list1[:len(marklist[int(key)])-1]
                    list2 = value
                    list2 = list2[:len(value)-1]
                    difference = Counter(list1) - Counter(list2)
                    numbers = difference.keys()
                    for number in numbers:              
                        bot.send_message(user_id,f'У вас нова оцінка: {number} з {namelist[int(key)]}\nЗагалом у вас {marklist[int(key)][len(marklist[int(key)])-1]}')  
    marklist = json.dumps(marklist)
    conn = sqlite3.connect('user_database.db')
    cursor = conn.cursor()
    update_query = 'UPDATE users SET rating = ? WHERE userid = ?'
    cursor.execute(update_query, (marklist, user_id))
    conn.commit()
    conn.close()

@bot.message_handler(commands=['test'])
def tst(message):
    conn = sqlite3.connect('user_database.db')
    cursor = conn.cursor()
    select_all_query = 'SELECT * FROM users'
    cursor.execute(select_all_query)
    records = cursor.fetchall()
    for record in records:
        marklist,namelist = conect(username=record[1],password=record[2],user_id=int(record[0]))
        check_mark(marklist=marklist,namelist=namelist,user_id=int(record[0]))
    
def send_message():
    conn = sqlite3.connect('user_database.db')
    cursor = conn.cursor()
    select_all_query = 'SELECT * FROM users'
    cursor.execute(select_all_query)
    records = cursor.fetchall()
    for record in records:
        marklist,namelist = conect(username=record[1],password=record[2],user_id=int(record[0]))
        check_mark(marklist=marklist,namelist=namelist,user_id=int(record[0]))

schedule.every(30).minutes.do(send_message)

def run_schedule():
    while True:
        schedule.run_pending()
        time.sleep(1)

schedule_thread = threading.Thread(target=run_schedule)
schedule_thread.start()

bot.infinity_polling()
