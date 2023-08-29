import os
import pandas as pd
import asyncio
from threading import Timer

from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup
from telebot.async_telebot import AsyncTeleBot

import configparser
from telethon.sync import TelegramClient

from load_all_messages import *

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
        self.wait = False
        self.filter_by_group = None
        self.start_timer()
    
    def load_messages(self):
        print(f"{pd.Timestamp.now().round('s')}\nLoading all messages")
        os.system("python -u load_all_messages.py")
        messages = pd.read_csv(MESSAGES_PATH)

        if self.filter_by_group is not None:
            group = messages.channel_id.apply(handler.get_group_name)
            messages = messages[group == self.filter_by_group]

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

    def filter_messages(self, filter_by_group):
        messages = pd.read_csv(MESSAGES_PATH)

        self.filter_by_group = filter_by_group
        group = messages.channel_id.apply(handler.get_group_name)
        messages = messages[group == self.filter_by_group]
        if os.path.exists(RATINGS_PATH):
            ratings = pd.read_csv(RATINGS_PATH)
            messages_ids = messages.id.astype(str) + '-' + messages.channel_id.astype(str)
            rated_ids = ratings.id.astype(str) + '-' + ratings.channel_id.astype(str)
            self.messages = messages[~messages_ids.isin(rated_ids.unique())].sort_values('date', ascending=False)
            self.ratings = ratings
            print(f"Found {messages.shape[0]} total messages and {self.ratings.shape[0]} ratings")
    
    def remove_message(self, msg):
        messages = pd.read_csv(MESSAGES_PATH)
        remove_mask = (messages.channel_id == msg.channel_id.values[0]) & (messages.id == msg.id.values[0])
        print(f"Removing {remove_mask.sum()} messages")
        messages = messages[~remove_mask]
        messages.to_csv(MESSAGES_PATH)
        self.messages = self.messages.iloc[1:]

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
handler = MessageHandler()

def rate_markup():
    markup = InlineKeyboardMarkup()
    markup.row_width = 4
    markup.add(InlineKeyboardButton("Ad", callback_data="is_ad"),
               InlineKeyboardButton("0", callback_data="rate_0"),
               InlineKeyboardButton("1", callback_data="rate_1"),
               InlineKeyboardButton("2", callback_data="rate_2"))
    return markup

def group_markup():
    markup = InlineKeyboardMarkup()
    markup.row_width = 1
    groups = handler.get_groups()
    buttons = [InlineKeyboardButton(g, callback_data=f"group_{g}") for g in groups]
    markup.add(*buttons)
    return markup

def filter_by_group_markup():
    markup = InlineKeyboardMarkup()
    markup.row_width = 1
    groups = handler.get_groups()
    buttons = [InlineKeyboardButton(g, callback_data=f"filter_by_group_{g}") for g in groups]
    markup.add(*buttons)
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
    elif call.data.startswith("rate_"):
        rating = call.data.split("rate_")[-1]
        bot.set_rating(int(rating), False)
    elif call.data.startswith("group_"):
        bot.group = call.data.split("group_")[-1]
        return
    elif call.data.startswith("filter_by_group_"):
        group = call.data.split("filter_by_group_")[-1]
        bot.filter_messages(group)
        await bot.send_message(bot.chat_id, f"Selected group {bot.filter_by_group}")
    msg = bot.get_message()
    try:
        async with TelegramClient(username, api_id, api_hash) as client:
            await client.forward_messages(chat_id, int(msg.id.iloc[0]), int(msg.channel_id.iloc[0]))
        await bot.send_message(bot.chat_id, "Rate this post", reply_markup=rate_markup())
    except Exception as e:
        print(f'Got exception {e}')
        bot.remove_message(msg)
        await bot.send_message(bot.chat_id, f'Got exception {e}. Please use /start')

@bot.message_handler(content_types=["text"])
async def handle_text(message):
    bot.chat_id = message.chat.id
    if message.text.startswith("/get_channels"):
        channel_repr = handler.get_channel_repr()
        await bot.send_message(bot.chat_id, channel_repr)
    elif message.text.startswith("/select_group"):
        await bot.send_message(bot.chat_id, "Select a group", reply_markup=filter_by_group_markup())
    elif message.text.startswith("/add_channel"):
        bot.wait = 'add'
        await bot.send_message(bot.chat_id, "Select a group and send the channel name/link", reply_markup=group_markup())
    elif message.text.startswith("/remove_channel"):
        bot.wait = 'remove'
        await bot.send_message(bot.chat_id, "Send the channel name/link")
    elif message.text.startswith("/load_messages"):
        bot.load_messages()
        await bot.send_message(bot.chat_id, "Loaded all messages.")
    elif bot.wait == 'add':
        handler.add_channel(message.text, bot.group)
        bot.wait = False
        bot.group = None
        await bot.send_message(bot.chat_id, f"Added {message.text}")
    elif bot.wait == 'remove':
        handler.remove_channel(message.text)
        await bot.send_message(bot.chat_id, f"Removed {message.text}")
        bot.wait = False
        bot.group = None

asyncio.run(bot.infinity_polling())
