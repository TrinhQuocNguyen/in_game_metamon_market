import matplotlib.pyplot as plt
from streamlit_autorefresh import st_autorefresh
import streamlit as st
import argparse
from tqdm import trange
import requests
import os
import sys
import csv
import pandas as pd
from time import sleep
from datetime import datetime


# URLs to make api calls
BASE_URL = "https://metamon-api.radiocaca.com/usm-api"
TOKEN_URL = f"{BASE_URL}/login"
LIST_MONSTER_URL = f"{BASE_URL}/getWalletPropertyBySymbol"
CHANGE_FIGHTER_URL = f"{BASE_URL}/isFightMonster"
START_FIGHT_URL = f"{BASE_URL}/startBattle"
LIST_BATTLER_URL = f"{BASE_URL}/getBattelObjects"
WALLET_PROPERTY_LIST = f"{BASE_URL}/getWalletPropertyList"
LVL_UP_URL = f"{BASE_URL}/updateMonster"
MINT_EGG_URL = f"{BASE_URL}/composeMonsterEgg"
EGG_PRICE_URL = f"{BASE_URL}/shop-order/sellList"

# update every minute (60*1000)
st_autorefresh(interval= 1*60*1000, key="dataframerefresh")

def datetime_now():
    return datetime.now().strftime("%m/%d/%Y %H:%M:%S")


def post_formdata(payload, url="", headers=None):
    """Method to send request to game"""
    files = []
    if headers is None:
        headers = {}

    # Add delay to avoid error from too many requests per second
    sleep(1)

    for _ in range(5):
        try:
            response = requests.request("POST",
                                        url,
                                        headers=headers,
                                        data=payload,
                                        files=files)
            return response.json()
        except:
            continue
    return {}


def get_battler_score(monster):
    """ Get opponent's power score"""
    return monster["sca"]


def picker_battler(monsters_list):
    """ Picking opponent """
    battlers = list(filter(lambda m: m["rarity"] == "N", monsters_list))

    if len(battlers) == 0:
        battlers = list(filter(lambda m: m["rarity"] == "R", monsters_list))

    battler = battlers[0]
    score_min = get_battler_score(battler)
    for i in range(1, len(battlers)):
        score = get_battler_score(battlers[i])
        if score < score_min:
            battler = battlers[i]
            score_min = score
    return battler


def pick_battle_level(level=1):
    # pick highest league for given level
    if 21 <= level <= 40:
        return 2
    if 41 <= level <= 60:
        return 3
    return 1


class MetamonPlayer:

    def __init__(self,
                 address,
                 sign,
                 msg="LogIn",
                 auto_lvl_up=False,
                 output_stats=False):
        self.no_enough_money = False
        self.output_stats = output_stats
        self.total_bp_num = 0
        self.total_success = 0
        self.total_fail = 0
        self.mtm_stats_df = []
        self.token = None
        self.address = address
        self.sign = sign
        self.msg = msg
        self.auto_lvl_up = auto_lvl_up

    def init_token(self):
        """Obtain token for game session to perform battles and other actions"""
        payload = {"address": self.address, "sign": self.sign, "msg": self.msg}
        response = post_formdata(payload, TOKEN_URL)
        self.token = response.get("data")
 
    def get_wallet_properties(self):
        """ Obtain list of metamons on the wallet"""
        data = []
        page = 1
        while True:
            payload = {"address": self.address, "page": page, "pageSize": 60}
            headers = {
                "accessToken": self.token,
            }
            response = post_formdata(payload, WALLET_PROPERTY_LIST, headers)
            mtms = response.get("data", {}).get("metamonList", [])
            if len(mtms) > 0:
                data.extend(mtms)
                page += 1
            else:
                break
        return data

    def get_egg_price(self):
        while True:
            payload = {
                "address": self.address, 
                'type':'6',
                'orderType':'2',
                'orderId':'-1',
                'pageSize':'10',
                'orderAmount':'',
            }
            headers = {
                "accessToken": self.token,
            }
            response = post_formdata(payload, EGG_PRICE_URL, headers)
            egg_price = response.get("data", {}).get("shopOrderList", [])
            
            return egg_price

    def get_potion_price(self):
        while True:
            payload = {
                "address": self.address, 
                'type':'2',
                'orderType':'2',
                'orderId':'-1',
                'pageSize':'10',
                'orderAmount':'',
            }
            headers = {
                "accessToken": self.token,
            }
            response = post_formdata(payload, EGG_PRICE_URL, headers)
            potion_price = response.get("data", {}).get("shopOrderList", [])
            
            return potion_price

    def list_monsters(self):
        """ Obtain list of metamons on the wallet (deprecated)"""
        payload = {"address": self.address, "page": 1, "pageSize": 60, "payType": -6}
        headers = {"accessToken": self.token}
        response = post_formdata(payload, LIST_MONSTER_URL, headers)
        monsters = response.get("data", {}).get("data", {})
        return monsters

    def battle(self, w_name=None):
        """ Main method to run all battles for the day"""
        if w_name is None:
            w_name = self.address

        summary_file_name = f"{w_name}_summary.tsv"
        mtm_stats_file_name = f"{w_name}_stats.tsv"
        self.init_token()

        self.get_wallet_properties()
        monsters = self.list_monsters()
        wallet_monsters = self.get_wallet_properties()
        print(f"Monsters total: {len(wallet_monsters)}")


    def get_lowest_price(self, w_name=None):
        """ Main method to run all battles for the day"""
        if w_name is None:
            w_name = self.address

        self.init_token()

        self.get_wallet_properties()
        # wallet_monsters = self.get_wallet_properties()
        # print(f"Monsters total: {len(wallet_monsters)}")

        egg_price = self.get_egg_price()
        potion_price = self.get_potion_price()

        return egg_price[0]['amount'], potion_price[0]['amount'], 

    def mint_eggs(self):
        self.init_token()

        headers = {
            "accessToken": self.token,
        }
        payload = {"address": self.address}

        minted_eggs = 0

        while True:
            res = post_formdata(payload, MINT_EGG_URL, headers)
            code = res.get("code")
            if code != "SUCCESS":
                break
            minted_eggs += 1
        print(f"Minted Eggs Total: {minted_eggs}")

def write_to_file(egg_price, potion_price):
    now = datetime.now()
    st.subheader('Last Update: '+ now.strftime("%d/%m/%Y %H:%M:%S"))    
    row_egg = [now.strftime("%d/%m/%Y %H:%M:%S"), egg_price]
    # open the file in the write mode
    with open('data\streamlit_egg.csv', 'a', newline='', encoding='UTF8') as f:
        # create the csv writer
        writer = csv.writer(f)
        # write a row to the csv file
        writer.writerow(row_egg)

    row_potion = [now.strftime("%d/%m/%Y %H:%M:%S"), potion_price]    
    # open the file in the write mode
    with open('data\streamlit_potion.csv', 'a', newline='', encoding='UTF8') as f:
        # create the csv writer
        writer = csv.writer(f)
        # write a row to the csv file
        writer.writerow(row_potion)

def draw_graph():
    df = pd.read_csv('data\egg_potion.csv')

    fig, (ax1, ax2) = plt.subplots(2,sharex=True)
    fig.suptitle('Axes values are scaled individually by default')

    # https://matplotlib.org/stable/api/_as_gen/matplotlib.axes.Axes.grid.html
    ax1.plot(df['Time'], df['Egg_Price'], color='b')
    ax1.set_xlabel('Time')
    ax1.set_ylabel('Egg_Price')
    ax1.grid(True)

    ax2.plot(df['Time'], df['Potion_Price'], color='y')
    ax2.set_xlabel('Time')
    ax2.set_ylabel('Potion_Price')
    ax2.grid(True)

    plt.show()

def notify(egg_price, potion_price, egg_below=4000, egg_over=5000, potion_below=1000, potion_over=1500):
    # print("-----")
    
    st.markdown('Egg Lowest Price   :  **'+ str(egg_price) +'**.')
    st.markdown('Potion Lowest Price:  **'+ str(potion_price) +'**.')

    if (float(egg_price) < float(egg_below)):
        st.markdown('******************************')
        new_title = '<p style="font-family:sans-serif; color:Red; font-size: 42px;">' + 'WARNING: Egg Price is below: **'+ str(egg_below) +'**.'+ '</p>'
        st.markdown(new_title, unsafe_allow_html=True)
        # st.markdown('WARNING: Egg Price is below: **'+ str(egg_below) +'**.')
    if (float(egg_price) > float(egg_over)):
        st.markdown('******************************')
        new_title = '<p style="font-family:sans-serif; color:Red; font-size: 42px;">' + 'WARNING: Egg Price is over: **'+ str(egg_over) +'**.'+ '</p>'
        st.markdown(new_title, unsafe_allow_html=True)
        # st.markdown('WARNING: Egg Price is over: **'+ str(egg_over) +'**.')
    if (float(potion_price) < float(potion_below)):
        st.markdown('******************************')
        new_title = '<p style="font-family:sans-serif; color:Red; font-size: 42px;">' + 'WARNING: Potion Price is below: **'+ str(potion_below) +'**.' + '</p>'
        st.markdown(new_title, unsafe_allow_html=True)        
        # st.markdown('WARNING: Potion Price is below: **'+ str(potion_below) +'**.')
    if (float(potion_price) > float(potion_over)):
        st.markdown('******************************')
        new_title = '<p style="font-family:sans-serif; color:Red; font-size: 42px;">' + 'WARNING: Potion Price is over: **'+ str(potion_over) +'**.' + '</p>'
        st.markdown(new_title, unsafe_allow_html=True)        
        # st.markdown('WARNING: Potion Price is over: **'+ str(potion_over) +'**.')


def run(args):
    # determine delimiter char from given input file
    with open(args.input_tsv) as csvfile:
        dialect = csv.Sniffer().sniff(csvfile.readline(), "\t ;,")
        delim = dialect.delimiter

    wallets = pd.read_csv(args.input_tsv, sep=delim)

    auto_lvlup = not args.no_lvlup
    for i, r in wallets.iterrows():
        mtm = MetamonPlayer(address=r.address,
                            sign=r.sign,
                            msg=r.msg,
                            auto_lvl_up=auto_lvlup,
                            output_stats=args.save_results)
        # draw_egg_price()
    
        egg_price, potion_price = mtm.get_lowest_price(w_name=r["name"])
        notify(egg_price, potion_price, egg_below=5000, egg_over=4300, potion_below=1291, potion_over=1400)
        write_to_file(egg_price, potion_price)
        st.subheader('Egg Graph')
        df_egg = pd.read_csv("data\streamlit_egg.csv")
        st.line_chart(df_egg)

        st.subheader('Potion Graph')
        df_potion = pd.read_csv("data\streamlit_potion.csv")    
        st.line_chart(df_potion)



if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument("-i", "--input-tsv", help="Path to tsv file with wallets' "
                                                  "access records (name, address, sign, login message) "
                                                  "name is used for filename with table of results. "
                                                  "Results for each wallet are saved in separate files",
                        default="get_price_wallet.tsv", type=str)
    parser.add_argument("-nl", "--no-lvlup", help="Disable automatic lvl up "
                                                  "(if not enough potions/diamonds it will be disabled anyway) "
                                                  "by default lvl up will be attempted after each battle",
                        action="store_true", default=False)
    parser.add_argument("-nb", "--skip-battles", help="No battles, use when need to only mint eggs from shards",
                        action="store_true", default=False)
    parser.add_argument("-e", "--mint-eggs", help="Automatically mint eggs after all battles done for a day",
                        action="store_true", default=True)
    parser.add_argument("-s", "--save-results", help="To enable saving results on disk use this option. "
                                                     "Two files <name>_summary.tsv and <name>_stats.tsv will "
                                                     "be saved in current dir.",
                        action="store_true", default=True)

    args = parser.parse_args()

    if not os.path.exists(args.input_tsv):
        print(f"Input file {args.input_tsv} does not exist")
        sys.exit(-1)

    
    st.dataframe(run(args))
       


            


