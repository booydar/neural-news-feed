import os
import configparser
import json

from telethon.sync import TelegramClient
from telethon import connection

# для корректного переноса времени сообщений в json
from datetime import date, datetime

# классы для работы с каналами
from telethon.tl.functions.channels import GetParticipantsRequest
from telethon.tl.types import ChannelParticipantsSearch

# класс для работы с сообщениями
from telethon.tl.functions.messages import GetHistoryRequest

# Считываем учетные данные
config = configparser.ConfigParser()
config.read("config.ini")

# Присваиваем значения внутренним переменным
api_id   = config['Telegram']['api_id']
api_hash = config['Telegram']['api_hash']
username = config['Telegram']['username']

        
client = TelegramClient(username, api_id, api_hash)

# # if we need proxy

# proxy = (proxy_server, proxy_port, proxy_key)

# client = TelegramClient(username, api_id, api_hash,
#     connection=connection.ConnectionTcpMTProxyRandomizedIntermediate,
#     proxy=proxy)        

client.start()


async def get_channel_names(channel):
	names = []
	async for dialog in client.iter_dialogs():
		if dialog.is_channel:
			names.append(dialog.name)

	print(names)

async def dump_all_messages(channel):
	"""Записывает json-файл с информацией о всех сообщениях канала/чата"""
	offset_msg = 0    # номер записи, с которой начинается считывание
	limit_msg = 100   # максимальное число записей, передаваемых за один раз

	all_messages = []   # список всех сообщений
	total_messages = 0
	total_count_limit = 1_000  # поменяйте это значение, если вам нужны не все сообщения

	class DateTimeEncoder(json.JSONEncoder):
		'''Класс для сериализации записи дат в JSON'''
		def default(self, o):
			if isinstance(o, datetime):
				return o.isoformat()
			if isinstance(o, bytes):
				return list(o)
			return json.JSONEncoder.default(self, o)

	while True:
		history = await client(GetHistoryRequest(
			peer=channel,
			offset_id=offset_msg,
			offset_date=None, add_offset=0,
			limit=limit_msg, max_id=0, min_id=0,
			hash=0))
		if not history.messages:
			break
		messages = history.messages
		for message in messages:
			message_dict = message.to_dict()
			if getattr(message, 'media', None):
				# print("Got media:", message.media)
				if getattr(message.media, 'photo', None):
					# print("Got media photo:", message.media.photo)
					output = await client.download_media(
						message.media,
						file=f"media/{channel.title.replace(' ', '_')}/{channel.title.replace(' ', '_')}",
					)
					message_dict['media_path'] = output
			all_messages.append(message_dict)
		offset_msg = messages[len(messages) - 1].id
		total_messages = len(all_messages)
		if total_count_limit != 0 and total_messages >= total_count_limit:
			break

	for message in all_messages:
		if hasattr(message, 'media') and hasattr(message.media.photo):
			photo_id = message.media.photo.id

	if not os.path.exists('messages'):
		os.system('mkdir messages')

	with open(f"messages/{channel.title.replace(' ', '_')}.json", 'w', encoding='utf8') as outfile:
		 json.dump(all_messages, outfile, ensure_ascii=False, cls=DateTimeEncoder)


async def main():
	# # get all channels
	# await get_channel_names(channel)

	# # dump one channel
	# url = input("Введите ссылку на канал или чат: ")
	# channel = await client.get_entity(url)
	# print("channel", channel)
	# await dump_all_messages(channel)

	# dump all channels
	with open('channel_names.txt', 'r') as f:
		names = f.read().split('\n')

	async for dialog in client.iter_dialogs():
		if dialog.is_channel and (dialog.name in set(names)):
			print(dialog.name)
			await dump_all_messages(dialog)

	# print('\n\n\n\n')
	# print(dialog.message)
	# print('\n\n\n\n')
	# print(dialog.message.message)
	# await dump_all_messages(dialog)


with client:
	client.loop.run_until_complete(main())

    


    

