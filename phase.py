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

#init pusher
pusher = pysher.Pusher(key=pusher_key, custom_host=pusher_host, port=pusher_port)


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
        name = str(d["market_hash_name"])
        if d['phase']:
            item_id = d['item_id']
            x = get_item_info(item_id)
            if x == "Sold": #this is a shitty way to deal with it, good luck dealing with bitskins fucking garbage api
                print("Item {} not on sale.".format(name))
                return
            if x is None:
                print("Item {} has no data.".format(name))
                insp = item_float = None
            else:
                insp = x[0]
                fv = x[1]
            price = float(d['price'])
            phase = str(d['phase'])
            market = urllib.request.pathname2url(name)
            phase_data = get_phase_prices(phase, market)
            avg_phase_price = phase_data[0]
            app_id_name = "Counter-Strike: Global Offensive"
            app_id = int(d['app_id'])
            clean_phase = phase.lower().replace("phase", "phase ")
            msg = "\nItem: {}\n".format(d['market_hash_name'])
            msg+="Phase: {}\n".format(clean_phase.title())
            if fv is not None:
                if fv == "-1.0000000000":
                    pass
                elif fv != "None":
                    if fv == 5:
                        msg+="Float: n/a\n".format(float(fv))
                    else:
                        msg+="Float: {:.10f}\n".format(float(fv))
                msg+="\n"
            wd = int(d['withdrawable_at'] - time.time())
            if wd <= 0:
                msg+="Tradeable: Instantly\n"
            else:
                msg+="Tradeable: {}\n".format(secondsToText(wd))
            msg+="\n"
            delta = float(avg_phase_price) - price
            perc = delta/price*100
            msg+="Price: ${}\nLowest Listing: {}{}\n \n".format(price,avg_phase_price," (Lowest price)" if price == avg_phase_price else "")
            msg+="Delta: ${:.3f}\nDelta: {:.3f}% \n".format(delta, perc)
            webhook = DiscordWebhook(url=wh_url)
            log = DiscordEmbed()
            log.title = "Game: {}".format(app_id_name)
            log.color = 0xe74c3c
            thumb = str(d['image'])
            log.set_thumbnail(url=thumb)
            log.description = msg
            log.add_field(name='{}/5 Current Listings:'.format(len(phase_data)), value='{}'.format(', '.join(str(v) for v in phase_data)), inline=False)
            log.add_field(name='Item Link:', value='[[URL](https://bitskins.com/view_item?app_id={}&item_id={})]'.format(d['app_id'], d['item_id']), inline=True)
            log.add_field(name='Sales Page:', value='[[URL](https://bitskins.com/?app_id={}&market_hash_name={}&sort_by=price&order=asc)]'.format(d['app_id'], market), inline=True)
            log.add_field(name='Pricecheck Page:', value='[[URL](https://bitskins.com/price/?market_hash_name={})]'.format(market), inline=True)
            if insp is not None:
                log.add_field(name='Screenshot:', value='[[URL](https://csgo.gallery/{})]'.format(insp), inline=True)
            webhook.add_embed(log)
            webhook.execute()
    except Exception as e:
        print("Error: {}\n TB: {}".format(e, traceback.format_exc()))
        
def get_phase_prices(p,m):
    try:
        p = p.upper()
        sales = []
        prices = []
        for i in range(1,5):
            url = "https://bitskins.com/?appid=730&page={}&app_id=730&market_hash_name={}&sort_by=price&order=asc".format(i,m)
            r=session.get(url)
            sales += r.html.find('.item-solo')   
        for listing in sales:
                phase = listing.find("div > p:nth-child(1)")[0].text
                price = listing.find('span', containing="$")
                price = str(price[0].text).replace("$", "")
                price = float(price)
                if phase == p:
                    if len(prices) == 5:
                        break
                    else:
                        prices.append(price)
                else:
                    continue
        return prices
    except Exception as e:
        print("Error: {}\n TB: {}".format(e, traceback.format_exc()))
    
def get_item_info(i):
    try:
        url = bit_base_url+"get_specific_items_on_sale/?api_key={}&code={}&item_ids={}&app_id=730".format(bit_api_key,totp.now(),i)
        r = requests.get(url)
        if r.status_code == 200:
            item=r.json()
            fv = None
            insp = None
            if item['data']['items_on_sale'][0]:
                if item['data']['items_on_sale'][0]['float_value'] is not None:
                    fv = item['data']['items_on_sale'][0]['float_value']
                if item['data']['items_on_sale'][0]['inspect_link'] is not None:
                    insp = str(item['data']['items_on_sale'][0]['inspect_link']).replace("%asset_id%", item['data']['items_on_sale'][0]['asset_id'])
                return [insp, fv]
            else:
                print("Item {} not on sale.".format(i)) 
                return "Sold"
        else:
            print("Status Code {} for req {}".format(r.status_code, i))
            return None
    except IndexError:
        return "Sold" #shitty fucking api strikes again
    except Exception as e:
        print("Item Data Error: {}\nTB: {}\n".format(e,traceback.format_exc()))
        print("Status: {}".format(r.status_code))
        print("JSON: {}".format(item))
        return None
    
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