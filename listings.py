#
# Copyright 2019, Artemis, All rights reserved.
#
import pysher, logging, sys, time, json, requests, pyotp, numpy as np, traceback, urllib, random
from webhook import DiscordWebhook, DiscordEmbed
from requests_html import HTMLSession
session = HTMLSession()

#webhook for sending msgs
wh_url = "000"

#pusher config - don't touch
pusher_host = "notifier.bitskins.com"
pusher_port = 443
pusher_key = "c0eef4118084f8164bec65e6253bf195"

#bitskins api stuff
bit_api_key = "000" #put bitskins api key here
bit_secret = "000" #put bitskins secret here
bit_base_url = "https://bitskins.com/api/v1/"

#otp
totp = pyotp.TOTP(bit_secret)

#item cache
item_cache = []

#games
app_id_lookup = [{"a":"730", "n":"Counter-Strike: Global Offensive"},{"a":"570", "n":"Defense of the Ancients 2"},{"a":"433850", "n":"Z1 Battle Royale"},{"a":"440", "n":"Team Fortress 2"},{"a":"304930", "n":"Unturned"},{"a":"218620", "n":"PayDay 2"},{"a":"252490", "n":"Rust"},{"a":"295110", "n":"Just Survive"},{"a":"232090", "n":"Killing Floor 2"},{"a":"489940", "n":"Battalion 1944"},{"a":"274940", "n":"Depth"},{"a":"550650", "n":"Black Squad"}]

#init pusher
pusher = pysher.Pusher(key=pusher_key, custom_host=pusher_host, port=pusher_port)

#knife names
knife_channel = ["knife", "daggers", "karambit", "bayonet"]

glove_channel = ["gloves", "wraps"]

def callback(data):
    data = json.loads(data)
    parse_data(data)
    
def parse_data(data):
    try:
        post_message(data)
    except Exception as e:
        print("Error: {}\n TB: {}".format(e, traceback.format_exc()))

def post_message(d):
    try:
        if float(d['price']) < 10.0:
            return
        app_id_name = next((item for item in app_id_lookup if item['a'] == d['app_id']), None)
        app_id = int(d['app_id'])
        name = str(d["market_hash_name"])
        market = urllib.request.pathname2url(d['market_hash_name'])
        msg = "Name: {}\nListing Price: {}".format(d["market_hash_name"], d['price'])
        if str(d['app_id']) == "730":
            wd = int(d['withdrawable_at'] - time.time())
            if wd <= 0:
                msg+="\nTradeable: Instantly\n"
            else:
                msg+="\nTradeable: {}\n".format(secondsToText(wd))
        if app_id == 730: #CS
            arr = ["000"]
            if any(knife in name.lower() for knife in knife_channel):
                wh_url = "000"
            elif any(glove in name.lower() for glove in glove_channel):
                wh_url = "000"
            else:
                wh_url = "000"
        elif app_id == 570: #dota
            wh_url = "000"
        elif app_id == 440: #tf2
            wh_url = "000"
        else:
            wh_url = "000"
        webhook = DiscordWebhook(url=wh_url)
        log = DiscordEmbed()
        log.title = "Game: {}".format(app_id_name['n'])
        log.color = 0xe74c3c
        thumb = str(d['image'])
        log.set_thumbnail(url=thumb)
        log.description = msg
        log.add_field(name='Item Link:', value='[[URL](https://bitskins.com/view_item?app_id={}&item_id={})]'.format(d['app_id'], d['item_id']), inline=True)
        log.add_field(name='Sales Page:', value='[[URL](https://bitskins.com/?app_id={}&market_hash_name={}&sort_by=price&order=asc)]'.format(d['app_id'], market), inline=True)
        webhook.add_embed(log)
        webhook.execute()
    except Exception as e:
        print("Error: {}\n TB: {}".format(e, traceback.format_exc()))
    
def secondsToText(secs):
    days = secs//86400
    hours = (secs - days*86400)//3600
    minutes = (secs - days*86400 - hours*3600)//60
    result = ("{} days, ".format(days) if days else "") + \
    ("{} hours, ".format(hours) if hours else "") + \
    ("{} minutes".format(minutes) if minutes else "")
    return result
    
def exit():
    pusher.disconnect()
    sys.exit(0)
    quit()

def connect_handler(data):
    channel = pusher.subscribe("inventory_changes")
    channel.bind("listed", callback)
    
def error_logger(data):
    print("Pusher Error: {}".format(data))
    
pusher.connection.bind('pusher:connection_established', connect_handler)
pusher.connection.bind('pusher:pusher:connection_failed', error_logger)
pusher.connect()

while True:
    time.sleep(0.1)