import os
import json
import configparser
import pandas as pd

from telethon.sync import TelegramClient
from telethon.tl.functions.messages import GetHistoryRequest

config = configparser.ConfigParser()
config.read(os.environ.get('news_config'))
api_id   = config['Telegram']['api_id']
api_hash = config['Telegram']['api_hash']
username = config['Telegram']['username']
save_path = config['Telegram']['save_path']
        
client = TelegramClient(username, api_id, api_hash)
client.start()

async def dump_all_messages(channel, save_path=save_path):
	offset_msg = 0
	limit_msg = 1000

	all_messages = []
	newest_id = 0
	attributes = ['id', 'peer_id', 'date', 'message']
	full_db = pd.DataFrame(columns=attributes)
	if os.path.exists(save_path):
		full_db = pd.read_csv(save_path)
		channel_id = int(str(channel.id)[4:])
		if channel_id in full_db.channel_id.values:
			newest_id = full_db[full_db.channel_id == channel_id]['id'].astype(int).max()

	while True:
		history = await client(GetHistoryRequest(
			peer=channel,
			offset_id=offset_msg, 
			offset_date=None, add_offset=0,
			limit=limit_msg, 
			max_id=0, 
			min_id=newest_id,
			hash=0))
		if not history.messages:
			break
		messages = history.messages
		for message in messages:
			message_dict = message.to_dict()
			results = {a:v for a, v in message_dict.items() if a in set(attributes)}
			all_messages.append(results)

		offset_msg = messages[-1].id
	
	if len(all_messages) == 0:
		return 
	print(f'Loaded {len(all_messages)} messages')
	
	save_cols = ['id', 'channel_id', 'date', 'message']
	res_df = pd.DataFrame(all_messages)
	res_df.date = res_df.date.apply(pd.to_datetime)
	res_df['id'] = res_df['id'].astype(int)
	res_df['channel_id'] = res_df.peer_id.apply(lambda x: x['channel_id']).astype(int)

	full_db = pd.concat((full_db, res_df))[save_cols]
	full_db.to_csv(save_path, index=False)

class MessageHandler:
	def __init__(self):
		self.load()

	def load(self):
		with open(os.path.join(save_path, 'channels.json'), 'r') as f:
				self.d = json.load(f)
				self._d = {v:key for key, value in self.d.items() for v in value}
		try:
			with open(os.path.join(save_path, 'channel_id_map.json'), 'r') as f:
				self.map = json.load(f)
		except FileNotFoundError:
			self.map = dict()


	def save(self):
		with open(os.path.join(save_path, 'channels.json'), 'w') as f:
			json.dump(self.d, f, ensure_ascii=False)

	def get_channels(self):
		return [c for group in self.d for c in self.d[group]]
	
	def get_groups(self):
		return list(self.d.keys())
	
	def get_channel_repr(self):
		channel_repr = '\n\n'.join([f"{group}:\n" + '\n'.join(channels) for group, channels in self.d.items()])
		return channel_repr
		
	def add_channel(self, name, group):
		if 't.me/' in name:
			name = name.split('t.me/')[-1]
		
		if group in self.d:
			self.d[group].append(name)
		else:
			self.d[group] = [name]
		self.save()

	def remove_channel(self, name):
		for group in self.d:
			self.d[group] = [channel for channel in self.d[group] if channel != name]
		self.save()

	def get_group_name(self, channel_id):
		if str(int(channel_id)) not in self.map:
			return
		name = self.map[str(int(channel_id))]
		if name not in self._d:
			return
		group =  self._d[name]
		return group


async def main():
	handler = MessageHandler()
	names = handler.get_channels()
	
	name_to_id = dict()
	messages_path = os.path.join(save_path, 'all_messages.csv')
	async for dialog in client.iter_dialogs():
		if dialog.is_channel:
			if dialog.name in set(names):
				load_from = dialog.name
			elif dialog.entity.username in set(names):
				load_from = dialog.entity.username
			else:
				continue
				
			print(f"Loading messages from {load_from}")
			name_to_id[int(str(dialog.id)[4:])] = load_from
			await dump_all_messages(dialog, messages_path)

	mapping_path = os.path.join(save_path, 'channel_id_map.json')
	with open(mapping_path, 'w') as f:
		json.dump(name_to_id, f, ensure_ascii=False)


with client:
	client.loop.run_until_complete(main())