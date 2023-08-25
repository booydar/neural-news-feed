import os
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
			print('All messages loaded')
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

async def main():
	with open(os.path.join(save_path, 'channel_names.txt'), 'r') as f:
		names = f.read().split('\n')

	async for dialog in client.iter_dialogs():
		if dialog.is_channel and (dialog.name in set(names)):
			print(f"Loading messages from {dialog.name}")
			messages_path = os.path.join(save_path, 'all_messages.csv')
			await dump_all_messages(dialog, messages_path)


with client:
	client.loop.run_until_complete(main())

    


    

