import pandas as pd

def mean(x):
    return sum(x) / len(x)

def get_channel_ratings(ratings):
    channel_ids = [int(r['channel_id']) for r in ratings]
    channel_ratings = {channel_id: mean([r['rating'] for r in ratings if int(r['channel_id']) == channel_id]) for channel_id in channel_ids}
    return channel_ratings


def get_message_score(msg, channel_ratings, verbose=False):
    now = pd.Timestamp.now(tz='UTC')
    msg_dt = pd.to_datetime(msg['date'])

    hours_past = (now - msg_dt).total_seconds() / 3600
    is_last_hours = hours_past < 3
    is_last_days = (hours_past / 24) < 2
    is_this_month = (hours_past / 24 / 30) < 1
    time_of_day = msg_dt - pd.Timestamp(msg_dt.date(), tz='UTC')

    channel_mean_rate = channel_ratings.get(msg['channel_id'], 3)

    if verbose:
        print("msg_dt, now")
        print(msg_dt, now)
        print("is_last_hours * 1000 + is_last_days * 100  + is_this_month * 10 + channel_mean_rate")
        print(is_last_hours * 1000, is_last_days * 100,  is_this_month * 10, channel_mean_rate)
    msg_score = is_last_hours * 1000 + is_last_days * 100  + is_this_month * 10 + channel_mean_rate
    
    return msg_score, msg_dt.date(), -time_of_day