from telethon import TelegramClient, sync, events

api_id = 12345
api_hash = '0123456789abcdef0123456789abcdef'

client = TelegramClient('session_name', api_id, api_hash)

@client.on(events.NewMessage(chats=('chat_name')))
async def normal_handler(event):
#    print(event.message)
    user_mess=event.message.to_dict()['message']

    s_user_id=event.message.to_dict()['from_id']
    user_id=int(s_user_id)
    user=id.get(user_id)

    mess_date=event.message.to_dict()['date']

    f.write(mess_date.strftime("%d-%m-%Y %H:%M")+"\n")
    f.write(user+"\n")
    f.write(user_mess+"\n\n")

    f.flush()

client.start()

group='group_name'

participants = client.get_participants(group)
users={}

for partic in client.iter_participants(group):
    lastname=""
    if partic.last_name:
       lastname=partic.last_name
    users[partic.id]=partic.first_name+" "+lastname

f=open('messages_from_chat', 'a') 

client.run_until_disconnected()
f.close()