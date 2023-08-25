import os
import pandas as pd
import asyncio
from threading import Timer

from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup
from telebot.async_telebot import AsyncTeleBot

import configparser
from telethon.sync import TelegramClient

config = configparser.ConfigParser()
config.read(os.environ.get('news_config'))
api_id   = config['Telegram']['api_id']
api_hash = config['Telegram']['api_hash']
username = config['Telegram']['username']
api_token = config['Telegram']['bot_token']
save_path = config['Telegram']['save_path']

MESSAGES_PATH = os.path.join(save_path, "all_messages.csv")
RATINGS_PATH = os.path.join(save_path, "ratings.csv")

class NewsBot(AsyncTeleBot):
    def __init__(self, api_token):
        super().__init__(api_token)
        self.load_messages()
        self.start_timer()
    
    def load_messages(self):
        print(f"{pd.Timestamp.now().round('s')}\nLoading all messages")
        os.system("python load_all_messages.py")
        messages = pd.read_csv(MESSAGES_PATH)
        if os.path.exists(RATINGS_PATH):
            ratings = pd.read_csv(RATINGS_PATH)
            messages_ids = messages.id.astype(str) + '-' + messages.channel_id.astype(str)
            rated_ids = ratings.id.astype(str) + '-' + ratings.channel_id.astype(str)
            self.messages = messages[~messages_ids.isin(rated_ids.unique())].sort_values('date', ascending=False)
            self.ratings = ratings
            print(f"Found {messages.shape[0]} total messages and {self.ratings.shape[0]} ratings")
            return
            
        self.messages = messages
        self.ratings = pd.DataFrame()

    def get_message(self):
        message = self.messages.iloc[:1]
        return message
    
    def set_rating(self, rating, is_advertisement=False):
        message = self.messages.iloc[:1].copy()
        message['rating'] = rating
        message['is_advertisement'] = is_advertisement
        self.messages = self.messages.iloc[1:]
        self.ratings = pd.concat((self.ratings, message))
        self.ratings.to_csv(RATINGS_PATH, index=False)

    def start_timer(self):
        class RepeatTimer(Timer):
            def run(self):
                while not self.finished.wait(self.interval):
                    self.function(*self.args, **self.kwargs)

        self.timer = RepeatTimer(3600, self.load_messages)
        self.timer.start()
        

chat_id = int(api_token.split(":")[0])
bot = NewsBot(api_token)

def rate_markup():
    markup = InlineKeyboardMarkup()
    markup.row_width = 4
    markup.add(InlineKeyboardButton("Ad", callback_data="is_ad"),
               InlineKeyboardButton("0", callback_data="rate_0"),
               InlineKeyboardButton("1", callback_data="rate_1"),
               InlineKeyboardButton("2", callback_data="rate_2"))
    return markup

@bot.message_handler(commands=['start'])
async def start_message(message):    
    bot.chat_id = message.chat.id
    msg = bot.get_message()
    async with TelegramClient(username, api_id, api_hash) as client:
        await client.forward_messages(chat_id, int(msg.id.iloc[0]), int(msg.channel_id.iloc[0]))
    await bot.send_message(bot.chat_id, "Rate this post", reply_markup=rate_markup())

@bot.callback_query_handler(func=lambda call: True)
async def callback_query(call):
    if call.data == "is_ad":
        bot.set_rating(0, True)
    elif call.data == 'rate_0':
        bot.set_rating(0, False)
    elif call.data == 'rate_1':
        bot.set_rating(1, False)
    elif call.data == 'rate_2':
        bot.set_rating(2, False)
    msg = bot.get_message()
    async with TelegramClient(username, api_id, api_hash) as client:
        await client.forward_messages(chat_id, int(msg.id.iloc[0]), int(msg.channel_id.iloc[0]))
    await bot.send_message(bot.chat_id, "Rate this post", reply_markup=rate_markup())
    

asyncio.run(bot.infinity_polling())
