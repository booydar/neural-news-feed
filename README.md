## Telegram news feed with personal recommendations

### This bot 
1. Parses news from selected telegram channels
2. Sends you news one by one to get your rating and ad marks
3. Filters out ads from news and sorts based on your rating


### Usage
Add channel names to ```channels.json``` and telegram bot token and client credentials to ```config.ini```

#### As a package
```
pip install -r requirements.txt

export news_config="path-to-config.ini"

python bot.py
```

#### With docker
```
docker build container_name .

docker run -v /home:/app/home -e news_config="path-to-config.ini" container_name
```