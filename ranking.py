import numpy as np
import pandas as pd

def get_channel_ratings(ratings):
    channel_ids = [int(r['channel_id']) for r in ratings]
    channel_ratings = {channel_id: np.mean([r['rating'] for r in ratings if int(r['channel_id']) == channel_id]) for channel_id in channel_ids}
    return channel_ratings

now = pd.Timestamp.now(tz='UTC')

def get_message_score(msg, channel_ratings):
    msg_dt = pd.to_datetime(msg['date'])

    hours_past = (now - msg_dt).total_seconds() / 3600
    is_last_hours = hours_past < 3
    is_today = now.date == msg_dt.date
    is_this_week = (now.weekofyear == msg_dt.weekofyear) & ((now.year == msg_dt.year))

    channel_mean_rate = channel_ratings[msg['channel_id']]

    msg_score = is_last_hours * 100 + is_today * 10  + is_this_week * 0.1 + channel_mean_rate
    return msg_score