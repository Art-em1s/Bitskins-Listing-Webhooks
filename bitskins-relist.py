#
# Copyright 2019, Artemis, All rights reserved.
#
import pysher, logging, sys, time, json, requests, pyotp, numpy as np, traceback, urllib, datetime
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

#time limiter
last_post = 0

#games
app_id_lookup = [{"a":"730", "n":"Counter-Strike: Global Offensive"},{"a":"570", "n":"Defense of the Ancients 2"},{"a":"433850", "n":"Z1 Battle Royale"},{"a":"440", "n":"Team Fortress 2"},{"a":"304930", "n":"Unturned"},{"a":"218620", "n":"PayDay 2"},{"a":"252490", "n":"Rust"},{"a":"295110", "n":"Just Survive"},{"a":"232090", "n":"Killing Floor 2"},{"a":"489940", "n":"Battalion 1944"},{"a":"274940", "n":"Depth"},{"a":"550650", "n":"Black Squad"}]

#init pusher
pusher = pysher.Pusher(key=pusher_key, custom_host=pusher_host, port=pusher_port)

#ignore list for checking floats/stickers
item_data_check_ignore = ["Graffiti", "Sticker", "Case Key", "Case", "Pin"]

#stickers to trigger on
good_stickers = ["Crown (Foil)", "Katowice 2015", "Katowice 2014", "Howling Dawn", "Flammable (Foil)", "Headhunter (Foil)"]

#knife names
knife_channel = ["knife", "daggers", "karambit", "bayonet"]

#ch patterns to watch for
ch_trigger_patterns = [4,9,1,25,28,32,34,57,58,65,81,82,88,92,101,103,108,112,117,122,126,139,147,151,152,156,166,167,168,172,177,179,182,189,204,205,215,228,246,256,262,265,269,273,278,281,293,295,298,310,319,321,322,323,330,334,341,344,345,354,355,3,3,369,372,381,387,393,413,426,428,429,430,434,442,445,450,455,463,468,470,472,475,479,487,490,494,499,503,507,509,510,512,516,517,519,523,525,526,529,532,539,541,550,555,557,563,567,571,585,592,601,605,610,613,615,616,617,627,628,631,637,639,643,648,661,664,670,674,676,681,685,689,690,695,698,700,708,711,713,721,724,728,733,750,752,754,760,764,768,770,776,790,791,793,798,803,808,809,811,813,814,819,822,823,833,843,844,849,852,853,859,862,868,871,872,874,875,878,879,880,887,888,891,892,902,903,905,910,916,922,927,935,950,955,969,970,974,978,979,996,1000]

def callback(data):
    data = json.loads(data)
    parse_data(data)
    
def parse_data(data):
    try:
        global last_post
        app_id = int(data['app_id'])
        price = float(data['price'])
        phase = None
        item_id = data['item_id']
        name = data['market_hash_name']
        if "Case Key" in str(name):
            # print("Dropping {} to prevent api spam".format(name))
            return
        item_average = get_avg(app_id, name, item_id)
        if item_average is None:
            print("No AVG for {}".format(name))
        else:
            if not any(item_ignore in name for item_ignore in item_data_check_ignore) and app_id == 730:
                time.sleep(1)
                x = get_item_info(item_id)
                if x == "Sold":
                    print("Item {} not on sale.".format(name))
                    return
                if x is None:
                    print("Item {} has no data.".format(name))
                    insp = item_float = item_stickers = seed = phase = None
                else:
                    insp = x[0]
                    item_float = x[1]
                    item_stickers = x[2]
                    seed = int(x[3]) if x[3] else None
                    phase = x[4]
            else:
                # print("Item {} is in blacklist.".format(name))
                insp = item_float = item_stickers = seed = None

            if price < float(item_average[0]):
                post_message(data, item_float, item_average, 0x00ff00, item_stickers, seed, insp, phase)
                
            elif len(item_average[3]) >= 2:
                if price < item_average[3][1]:
                    delta = float(item_average[3][1]) - price
                    delta = delta / price * 100
                    if delta >= 5:
                        post_message(data, item_float, item_average, 0xeeffff, item_stickers, seed, insp, phase)
                        
            if item_float is not None:
                if float(item_float) <= 0.009:
                    post_message(data, item_float, item_average, 0x0000ff, item_stickers, seed, insp, phase)
                    
                if 0.07 <= float(item_float) <= 0.075:
                    post_message(data, item_float, item_average, 0x0000ff, item_stickers, seed, insp, phase)
                    
                if  0.15 <= float(item_float) <= 0.155:
                    post_message(data, item_float, item_average, 0x0000ff, item_stickers, seed, insp, phase)

                if  float(item_float) >= 0.95:
                    post_message(data, item_float, item_average, 0x0000ff, item_stickers, seed, insp, phase)
                    
            if item_stickers is not None:
                if any(sticker in str(item_stickers) for sticker in good_stickers):
                    post_message(data, item_float, item_average, 0xff0000, item_stickers, seed, insp, phase)
                        
            if seed is not None:
                if int(seed) in ch_trigger_patterns and "case hardened" in name.lower():
                    post_message(data, item_float, item_average, 0x85ffff, item_stickers, seed, insp, phase)

    except Exception as e:
        print("Error: {}\n TB: {}".format(e, traceback.format_exc()))
    
def get_avg(a,n,i):
    try:
        x = get_recent_sales(a, n)
        y = get_current_listings(a, n)
        try:
            z = x + y
        except:
            if x:
                z = x
            elif y:
                z = y
            else:
                print("No data for {}".format(n))
                return
        data_points = np.array(z)
        data_points = reject_outliers(data_points)
        avg_from = len(data_points)
        averaged_clean_price = build_avg(data_points)
        #build a record to cache, cache for 3 hours, speeds up response
        # [ time of creation, name, avg, avg from ]
        cache_record = [int(time.time()), n, averaged_clean_price, avg_from]
        record = [averaged_clean_price, avg_from, x, y]
        return record
    except Exception as e:
        print("Error: {}\n TB: {}\nItem: {}".format(e,traceback.format_exc(),n))

def get_recent_sales(a,n):
    try:
        url = bit_base_url+"get_sales_info/?api_key={}&code={}&market_hash_name={}&page={}&app_id={}".format(bit_api_key,totp.now(),n,1,a)
        time.sleep(0.01)
        r = requests.get(url).json()
        if r['status'] == "success":
            if not r['data']['sales'] or len(r['data']['sales']) == 0:
                print("No sales data for {}".format(n))
                return None
            else:
                records = []
                i=0
                date_limit = int(time.time() - 60*60*24*2.5) #2.5 days worth of data on previous sales
                for record in r['data']['sales']:
                    if record['sold_at'] >= date_limit:
                        records.append(float(record['price']))
                        i+=1
                return records
    except:
        print("{} Get Recent Sales Req: {}".format(n, r))
        return None
        
def get_current_listings(a,n):
    try:
        url = "https://bitskins.com/?app_id={}&market_hash_name={}&sort_by=price&order=asc".format(a,n)
        r=session.get(url)
        sales = r.html.find('.buyItemPrice')
        records = []
        i=0
        for entry in sales:
            if i>4:
                break
            else:
                sale = float(entry.text)
                records.append(sale)
                i+=1
        return records
    except Exception as e:
        print("Error getting current listings: {}\n TB: {}\nItem: {}".format(e,traceback.format_exc(),n))
        return None
        
def get_item_info(i):
    try:
        url = bit_base_url+"get_specific_items_on_sale/?api_key={}&code={}&item_ids={}&app_id=730".format.format(bit_api_key,totp.now(),i)
        r = requests.get(url)
        if r.status_code == 200:
            item=r.json()
            stickers = None
            fv = None
            insp = None
            seed = None
            phase = None
            if item['data']['items_on_sale'][0]:
                if item['data']['items_on_sale'][0]['stickers'] is not None:
                    stickers = []
                    x = item['data']['items_on_sale'][0]['stickers']
                    for sticker in x:
                        a = sticker['wear_value']
                        y = {"w":a, "n":"{}".format(sticker['name'])}
                        stickers.append(y)
                if item['data']['items_on_sale'][0]['float_value'] is not None:
                    fv = item['data']['items_on_sale'][0]['float_value']
                if item['data']['items_on_sale'][0]['phase'] is not None:
                    phase = item['data']['items_on_sale'][0]['phase']
                if item['data']['items_on_sale'][0]['inspect_link'] is not None:
                    insp = str(item['data']['items_on_sale'][0]['inspect_link']).replace("%asset_id%", item['data']['items_on_sale'][0]['asset_id'])
                if item['data']['items_on_sale'][0]['pattern_info']:
                    if item['data']['items_on_sale'][0]['pattern_info']['paintseed'] is not None:
                        seed = item['data']['items_on_sale'][0]['pattern_info']['paintseed'] 
                return [insp, fv, stickers, seed, phase]
            else:
                print("Item {} not on sale.".format(i))
                return "Sold"
        else:
            print("Status Code {} for req {}".format(r.status_code, i))
            return None
    except IndexError:
        return "Sold"
    except Exception as e:
        print("Item Data Error: {}\nTB: {}\n".format(e,traceback.format_exc()))
        print("Status: {}".format(r.status_code))
        print("JSON: {}".format(item))
        return None
        
def get_item_data_alt(ins):
    url = "https://api.csgofloat.com/?url={}".format(ins)
    r = requests.get(url).json()
    try:
        return r['iteminfo']['floatvalue'] if r['iteminfo']['floatvalue'] else None
    except:
        print("{} Get Float Req (2): {}".format(i, r))
        return None

def post_message(d,fv,avg,c,stickers,seed=None, insp=None, phase=None):
    try:
        app_id_name = next((item for item in app_id_lookup if item['a'] == d['app_id']), None)
        name = str(d['market_hash_name'])
        app_id = int(d['app_id'])
        price = float(d['price'])
        if app_id == 570: #dota
            wh_url = "000"
        elif app_id == 433850: #z1
            wh_url = "000"
        elif app_id == 252490:
            wh_url = "000"
        elif app_id == 730:
            if c == 0x0000ff: #floats
                wh_url = "000"
            if c == 0x00ff00: #avg
                if any(knife in name.lower() for knife in knife_channel):
                    wh_url = "000"
                elif "sticker" in name.lower():
                    wh_url = "000"
                elif price <= 1:
                    wh_url = "000"
                elif 1 <= price <= 5:
                    wh_url = "000"
                elif 5 <= price <= 10:
                    wh_url = "000"
                elif 10 <= price <= 50:
                    wh_url = "000"
                elif price > 50:
                    wh_url = "000"
            if c == 0xeeffff: #price
                if any(knife in name.lower() for knife in knife_channel):
                    wh_url = "000"
                elif "sticker" in name.lower():
                    wh_url = "000"
                elif price <= 1:
                    wh_url = "000"
                elif 1 <= price <= 5:
                    wh_url = "000"
                elif 5 <= price <= 10:
                    wh_url = "000"
                elif 10 <= price <= 50:
                    wh_url = "000"
                elif price > 50:
                    wh_url = "000"
            if c == 0xff0000: #stickers
                wh_url = "000"
            if c == 0x85ffff: #ch
                wh_url = "000"
        else:
            wh_url = "000"
        market = urllib.request.pathname2url(d['market_hash_name'])
        msg = "\nItem: {}\n".format(d['market_hash_name'])
        if app_id == 730:
            if seed and "case hardened" in str(d['market_hash_name']).lower():
                msg+="Pattern Seed: {}\n".format(seed)
            if phase is not None:
                msg+="Phase: {}\n".format(str(phase).replace("phase", "Phase "))
            if fv is not None:
                if fv == "-1.0000000000":
                    pass
                elif fv != "None":
                    if fv == 5:
                        msg+="Float: n/a\n".format(float(fv))
                    else:
                        msg+="Float: {:.10f}\n".format(float(fv))
            if stickers is not None:
                msg+="\nStickers:\n"
                stick_len = 1
                for sticker in stickers:
                    msg+="{}) [{}] {}\n".format(stick_len, "{:.0%}".format(float(sticker['w'])) if sticker['w'] != "None" else "0%", sticker['n'])
                    stick_len+=1
                msg+="\n"
            wd = int(d['withdrawable_at'] - time.time())
            if wd <= 0:
                msg+="Tradeable: Instantly\n"
            else:
                msg+="Tradeable: {}\n".format(secondsToText(wd))
        msg+="\n"
        avg_sale_price = "${:.3f}".format(avg[0])
        
        # if avg[3][1]:
            # delta_prof = float(avg[3][1]) - price
            # perc_prof = delta / price * 100
        # else:
        delta = float(avg[0]) - price
        perc = delta/price*100
            
        if c == 0x00ff00:    
            if price < 0.07:
                # print("{} - ${}".format(d['market_hash_name'], price))
                return
            if perc < 4.86:
                # print("{} - {}%".format(d['market_hash_name'], perc))
                return
        msg+="Price: ${}\n".format(price)
        msg+="AVG Price: {}\nAverage From: {}\n \n".format(avg_sale_price, avg[1])
        msg+="Delta: ${:.3f}\nDelta: {:.3f}% \n".format(delta, perc)
        msg+="\nPrevious Sale AVG: ${:.3f}\nCurrent Listing AVG: ${:.3f}\n".format(build_avg(avg[2]), build_avg(avg[3]))
        webhook = DiscordWebhook(url=wh_url)
        log = DiscordEmbed()
        log.title = "Game: {}".format(app_id_name['n'])
        log.color = c
        thumb = str(d['image'])
        log.set_thumbnail(url=thumb)
        log.description = msg
        prev_sales = list(dict.fromkeys(avg[2]))
        log.add_field(name='{} Previous {}:'.format(len(prev_sales), "Sale" if len(prev_sales) == 1 else "Sales"), value='{}'.format(', '.join(str(v) for v in prev_sales)), inline=False)
        log.add_field(name='{}/5 Current Listings:'.format(len(avg[3])), value='{}'.format(', '.join(str(v) for v in avg[3])), inline=False)
        log.add_field(name='Item Link:', value='[[URL](https://bitskins.com/view_item?app_id={}&item_id={})]'.format(d['app_id'], d['item_id']), inline=True)
        log.add_field(name='Sales Page:', value='[[URL](https://bitskins.com/?app_id={}&market_hash_name={}&sort_by=price&order=asc)]'.format(d['app_id'], market), inline=True)
        log.add_field(name='Pricecheck Page:', value='[[URL](https://bitskins.com/price/?market_hash_name={})]'.format(market), inline=True)
        if insp is not None:
            log.add_field(name='Screenshot:', value='[[URL](https://csgo.gallery/{})]'.format(insp), inline=True)
        log.set_footer(text="Price Modified: ${} -> ${}".format(d['old_price'],d['price']))
        webhook.add_embed(log)
        webhook.execute()
        print(d)
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
    
def build_avg(l):
    return sum(l) / len(l) 

def reject_outliers(data, m = 2.):
    d = np.abs(data - np.median(data))
    mdev = np.median(d)
    s = d/(mdev if mdev else 1.)
    return data[s<m]
    
def exit():
    pusher.disconnect()
    sys.exit(0)
    quit()

def connect_handler(data):
    channel = pusher.subscribe("inventory_changes")
    channel.bind("price_changed", callback)
    
pusher.connection.bind('pusher:connection_established', connect_handler)
pusher.connect()

while True:
    time.sleep(0.1)