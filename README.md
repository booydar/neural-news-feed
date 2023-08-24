## Telegram news feed with personal recommendations

### This bot 
1. Parses news from selected telegram channels
2. Sends you news one by one to get your rating and ad marks
3. Filters out ads from news and sorts based on your rating


### Usage
Add channel names to ```channel_names.txt``` telegram bot token and telegram client credentials to ```config.ini```

```
sudo docker build container_name .

sudo docker run -v /home:/app/home -e news_config="path-to-config.ini" container_name
```