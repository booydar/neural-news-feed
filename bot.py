import os
import re
import json
import numpy as np
import telebot
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup
# from neural import Model

class NewsBot(telebot.TeleBot):
    def __init__(self, api_token):
        super().__init__(api_token)
        self.next_channel()
        

    def get_news(self):
        if not self.messages:
            self.next_channel()
            
        message, self.messages = self.messages[0], self.messages[1:]

        news = {'message': message['message']}
        if 'media_path' in message:
            impath = os.path.join('/home/booydar/Desktop/projects/tg_notebot/news_bot/', message['media_path'])
            news['media_path'] = impath

        if not news['message'] and not news.get('media_path'):
            return self.get_news()

        return news

    def load_news(self, channel):
        messages_path = os.path.join('/home/booydar/Desktop/projects/tg_notebot/news_bot/messages/', channel)
        with open(messages_path, 'r') as f:
            self.messages = json.load(f)
        np.random.shuffle(self.messages)

    def next_channel(self):
        self.channels = getattr(self, 'channels', [])
        if not self.channels:
            self.channels = next(os.walk('/home/booydar/Desktop/projects/tg_notebot/news_bot/messages'))[2]
            np.random.shuffle(self.channels)
        else: 
            self.channels = self.channels[1:]
        
        self.channel = self.channels[0]
        self.load_news(self.channel)
        

api_token = '6003977368:AAGMWNOkJglpWGCUGaZjkpwSvG3niqndkaI'
bot = NewsBot(api_token)

def rate_markup():
    markup = InlineKeyboardMarkup()
    markup.row_width = 2
    markup.add(InlineKeyboardButton("next", callback_data="next"),
                InlineKeyboardButton("next channel", callback_data="next_channel"))
    return markup

@bot.message_handler(commands=['start'])
def start_message(message):    
    bot.chat_id = message.chat.id
    bot.send_message(message.chat.id, 'Hello!', reply_markup=rate_markup())



@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    # bot.chat_id = message.chat.id
    if call.data == "next":
        news = bot.get_news()
        if 'media_path' in news:
            with open(news['media_path'], 'rb') as img:
                bot.send_photo(bot.chat_id, img, caption=news['message'], reply_markup=rate_markup())
        else:
            bot.send_message(bot.chat_id, news['message'], reply_markup=rate_markup())

    elif call.data == "next_channel":
        print(bot.channel)
        bot.next_channel()
        print(bot.channel)


    # elif message.text.startswith('/set_'):
    #     bot.wait_value = message.text.split('/set_')[1]
    #     bot.send_message(message.chat.id, f'set {bot.wait_value} to what value?')
    # elif bot.wait_value:
    #     if '.' in message.text:
    #         bot.model.config['generate_config'][bot.wait_value] = float(message.text)
    #     else:
    #         bot.model.config['generate_config'][bot.wait_value] = int(message.text)
    #     bot.wait_value = False
    # elif message.text.startswith('/reset'):
    #     bot.send_message(message.chat.id, "Память бота стерта.")
    #     bot.reset()
    # elif message.text.startswith('/context'):
    #     bot.send_message(message.chat.id, bot.get_context())
    #     bot.reset()
    # elif message.text.startswith('/config'):
    #     msg = '; '.join([f'{k}-{v}' for k, v in bot.get_config().items()])
    #     bot.send_message(message.chat.id, msg)
    # else:
    #     answer = bot.answer(message.text)
    #     bot.send_message(message.chat.id, answer)
    

bot.infinity_polling()