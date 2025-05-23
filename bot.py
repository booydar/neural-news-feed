import os
import asyncio
import datetime
from threading import Timer

from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup
from telebot.async_telebot import AsyncTeleBot

import configparser
from telethon.sync import TelegramClient
from telethon.errors import MessageIdInvalidError, ChatForwardsRestrictedError

from load_messages import *
from ranking import get_channel_ratings, get_message_score

config = configparser.ConfigParser()
config.read(os.environ.get('news_config'))
api_id   = config['Telegram']['api_id']
api_hash = config['Telegram']['api_hash']
username = config['Telegram']['username']
api_token = config['Telegram']['bot_token']
save_path = config['Telegram']['save_path']
update_interval = config['Telegram'].get("update_interval", 3600)

MESSAGES_PATH = os.path.join(save_path, "all_messages.json")
RATINGS_PATH = os.path.join(save_path, "ratings.json")

class NewsBot(AsyncTeleBot):
    def __init__(self, api_token, update_interval=3600):
        super().__init__(api_token)
        self.wait = False
        self.selected_message = None
        self.filter_by_group = None
        self.last_msg_id = None
        self.channel_ratings = None
        self.start_timer(update_interval)
        self.load_messages()
    
    def load_messages(self):
        print(f"{datetime.datetime.now().strftime('%H:%M %d.%m.%Y')}\nLoading all messages")
        os.system("python -u load_messages.py")
        with open(MESSAGES_PATH, 'r') as f:
            messages = json.load(f)

        if self.filter_by_group not in {'all', None}:
            messages = list(filter(lambda msg: handler.get_group_name(msg['channel_id']) == self.filter_by_group, messages))

        if os.path.exists(RATINGS_PATH):
            with open(RATINGS_PATH, 'r') as f:
                ratings = json.load(f)
            rated_ids = {str(r['id']) + '-' + str(r['channel_id']) for r in ratings}
            messages = list(filter(lambda msg: str(msg['id']) + '-' + str(msg['channel_id']) not in rated_ids, messages))

            self.ratings = ratings
            self.channel_ratings = get_channel_ratings(ratings)
            self.messages = self.sort(messages)
            print(f"Found {len(messages)} total messages and {len(self.ratings)} ratings")
            if self.messages[0] == self.selected_message:
                self.messages = self.messages[1:]
            return
            
        self.messages = messages
        self.ratings = []

    def filter_messages(self, filter_by_group):
        with open(MESSAGES_PATH, 'r') as f:
            messages = json.load(f)

        if filter_by_group not in {'all', None}:
            messages = list(filter(lambda msg: handler.get_group_name(msg['channel_id']) == self.filter_by_group, messages))

        if os.path.exists(RATINGS_PATH):
            with open(RATINGS_PATH, 'r') as f:
                ratings = json.load(f)
            rated_ids = {str(r['id']) + '-' + str(r['channel_id']) for r in ratings}
            messages = list(filter(lambda msg: str(msg['id']) + '-' + str(msg['channel_id']) not in rated_ids, messages))

            self.ratings = ratings
            self.channel_ratings = get_channel_ratings(ratings)
            self.messages = self.sort(messages)
            print(f"Found {len(messages)} total messages and {len(self.ratings)} ratings")
    
    def remove_message(self, message):
        with open(MESSAGES_PATH, 'r') as f:
            messages = json.load(f)

        prevoius_len = len(messages)
        messages = list(filter(lambda msg: (msg['id'] != message['id']) or \
                                      (msg['channel_id'] != message['channel_id']), messages))
        print(f"Removing {prevoius_len - len(messages)} messages")
        with open(MESSAGES_PATH, 'w') as f:
            json.dump(messages, f, ensure_ascii=False)
        self.selected_message = None

    def get_message(self):
        if self.selected_message is not None:
            return self.selected_message
        else:
            message = self.messages[0]
            self.messages = self.messages[1:]
            self.selected_message = message
            return message
    
    def set_rating(self, rating, is_advertisement=False):
        message = dict(**self.selected_message)
        message.pop('message')
        message['rating'] = rating
        message['is_advertisement'] = is_advertisement
        if hasattr(self, "channel_ratings"):
            message['ranking_method'] = "channel_ratings_v2"
        self.ratings.append(message)
        self.selected_message = None

        with open(RATINGS_PATH, 'w') as f:
            json.dump(self.ratings, f, ensure_ascii=False)
    
    def sort(self, messages):
        last_messages = sorted(messages, key=lambda msg: msg['date'], reverse=True)
        last_messages = last_messages[:2048]
        print('\n\n\nLatest:')
        for msg in last_messages[:5]:
            print(get_message_score(msg, self.channel_ratings, verbose=True), msg)
            print()

        sorted_messages = sorted(last_messages, key=lambda msg: get_message_score(msg, self.channel_ratings), reverse=True)

        print('\n\n\nSorted:')
        for msg in sorted_messages[:5]:
            print(get_message_score(msg, self.channel_ratings, verbose=True), msg)
            print()
        return sorted_messages

    def start_timer(self, update_interval):
        class RepeatTimer(Timer):
            def run(self):
                while not self.finished.wait(self.interval):
                    self.function(*self.args, **self.kwargs)

        self.timer = RepeatTimer(update_interval, self.load_messages)
        self.timer.start()
        

chat_id = int(api_token.split(":")[0])
bot = NewsBot(api_token, int(update_interval))
handler = MessageHandler()

def rate_markup():
    markup = InlineKeyboardMarkup()
    num_rates = 5
    markup.row_width = num_rates + 1
    buttons = [InlineKeyboardButton("Ad", callback_data="is_ad")]
    buttons += [InlineKeyboardButton(str(r), callback_data=f"rate_{r}") for r in range(1, num_rates+1)]
    markup.add(*buttons)
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
    buttons.append(InlineKeyboardButton('All groups', callback_data=f"filter_by_group_all"))
    markup.add(*buttons)
    return markup

async def main():
    msg = bot.get_message()
    try:
        async with TelegramClient(username, api_id, api_hash) as client:
            await client.forward_messages(chat_id, int(msg['id']), int(msg['channel_id']))
        msg = await bot.send_message(bot.chat_id, "Rate this post", reply_markup=rate_markup())
        bot.last_msg_id = msg.message_id
    except MessageIdInvalidError as e:
        print(f'Got exception {e}')
        bot.remove_message(msg)
        await main()
    except ChatForwardsRestrictedError as e:
        print(f'Got exception {e}')
        bot.remove_message(msg)
        await main()
    except Exception as e:
        print(f'Got exception {e}')
        await bot.send_message(bot.chat_id, f'Got exception {e}. Please use /start or restart the bot.')

@bot.message_handler(commands=['start'])
async def start_message(message):    
    bot.chat_id = message.chat.id
    await main()

@bot.callback_query_handler(func=lambda call: True)
async def callback_query(call):
    if call.data == "is_ad":
        bot.set_rating(0, True)
        await bot.delete_message(bot.chat_id, bot.last_msg_id)
        await bot.delete_message(bot.chat_id, bot.last_msg_id - 1)
    elif call.data.startswith("rate_"):
        rating = call.data.split("rate_")[-1]
        bot.set_rating(int(rating), False)
        await bot.delete_message(bot.chat_id, bot.last_msg_id)
        if int(rating) < 4:
            await bot.delete_message(bot.chat_id, bot.last_msg_id - 1)
    elif call.data.startswith("group_"):
        bot.group = call.data.split("group_")[-1]
        await bot.send_message(bot.chat_id, "Send the channel name/link")
        return
    elif call.data.startswith("filter_by_group_"):
        group = call.data.split("filter_by_group_")[-1]
        bot.filter_by_group = group
        bot.filter_messages(group)
        await bot.send_message(bot.chat_id, f"Selected group {bot.filter_by_group}")
    await main()

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
        await bot.send_message(bot.chat_id, "Select a group", reply_markup=group_markup())
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
