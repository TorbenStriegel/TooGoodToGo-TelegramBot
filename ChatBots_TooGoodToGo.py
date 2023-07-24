import json
from _thread import start_new_thread
import time
from datetime import datetime, timezone

from telebot import TeleBot, types
from tgtg import TgtgClient

bot = TeleBot('<Telegram-access-token>')


def send_message(telegram_user_id, message):
    bot.send_message(telegram_user_id, text=message)


def send_message_with_link(telegram_user_id, message, item_id):
    bot.send_message(telegram_user_id, text=message, reply_markup=types.InlineKeyboardMarkup(
        keyboard=[
            [
                types.InlineKeyboardButton(
                    text="Open in app 📱",
                    callback_data="open_app",
                    url="https://share.toogoodtogo.com/item/" + item_id
                )
            ],
        ]
    )
                     )


class TooGoodToGo:
    users_login_data = {}
    users_settings_data = {}
    available_items_favorites = {}
    connected_clients = {}
    client = TgtgClient

    def __init__(self):
        self.read_users_login_data_from_txt()
        self.read_users_settings_data_from_txt()
        self.read_available_items_favorites_from_txt()
        start_new_thread(self.get_available_items_per_user, ())
        bot.set_my_commands([
            types.BotCommand("/info", "favorite bags that currently available"),
            types.BotCommand("/login", "log in with your mail"),
            types.BotCommand("/settings", "set when you want to be notified"),
            types.BotCommand("/help", "short explanation"),
        ])

    def read_users_login_data_from_txt(self):
        with open('users_login_data.txt', 'r') as file:
            data = file.read()
            self.users_login_data = json.loads(data)

    def save_users_login_data_to_txt(self):
        with open('users_login_data.txt', 'w') as file:
            file.write(json.dumps(self.users_login_data))

    def read_users_settings_data_from_txt(self):
        with open('users_settings_data.txt', 'r') as file:
            data = file.read()
            self.users_settings_data = json.loads(data)

    def save_users_settings_data_to_txt(self):
        with open('users_settings_data.txt', 'w') as file:
            file.write(json.dumps(self.users_settings_data))

    def read_available_items_favorites_from_txt(self):
        with open('available_items_favorites.txt', 'r') as file:
            data = file.read()
            self.available_items_favorites = json.loads(data)

    def save_available_items_favorites_to_txt(self):
        with open('available_items_favorites.txt', 'w') as file:
            file.write(json.dumps(self.available_items_favorites))

    def add_user(self, telegram_user_id, credentials):
        self.users_login_data[telegram_user_id] = credentials
        self.save_users_login_data_to_txt()
        self.users_settings_data[telegram_user_id] = {'sold_out': 0,
                                                      'new_stock': 1,
                                                      'stock_reduced': 0,
                                                      'stock_increased': 0}
        self.save_users_settings_data_to_txt()

    # Get the credentials
    def new_user(self, telegram_user_id, email):
        client = TgtgClient(email=email)
        credentials = client.get_credentials()
        self.add_user(telegram_user_id, credentials)
        send_message(telegram_user_id, "✅ You are now logged in!")

    # Looks if the user is already logged in
    def find_credentials_by_telegramUserID(self, user_id):
        for key in self.users_login_data.keys():
            if user_id == key:
                return self.users_login_data[key]

    # Checks if a connection already exists, or if it has to be created initially.
    def connect(self, user_id):
        if user_id in self.connected_clients.keys():
            self.client = self.connected_clients[user_id]
        else:
            user_credentials = self.find_credentials_by_telegramUserID(user_id)
            self.client = TgtgClient(access_token=user_credentials["access_token"],
                                     refresh_token=user_credentials["refresh_token"],
                                     user_id=user_credentials["user_id"],
                                     cookie=user_credentials["cookie"])
            self.connected_clients[user_id] = self.client
            time.sleep(3)

    def get_favourite_items(self):
        favourite_items = self.client.get_items()
        return favourite_items

    # /info command
    def send_available_favourite_items_for_one_user(self, user_id):
        self.connect(user_id)
        favourite_items = self.get_favourite_items()
        available_items = []
        for item in favourite_items:
            if item['items_available'] > 0:
                item_id = item['item']['item_id']
                store_name = "🍽 " + str(item['store']['store_name'])
                store_address_line = "🧭 " + str(item['store']['store_location']['address']['address_line'])
                store_price = "💰 " + str(int(item['item']["price_including_taxes"]["minor_units"]) / 100)
                store_items_available = "🥡 " + str(item['items_available'])
                text = "{0}\n{1}\n{2}\n{3}\n⏰ {4} - {5}".format(store_name, store_address_line,
                                                                store_price, store_items_available, str(
                        datetime.strptime(item['pickup_interval']['start'],
                                          "%Y-%m-%dT%H:%M:%SZ").astimezone(
                            timezone.utc).strftime("%a %d.%m at %H:%M")), str(
                        datetime.strptime(item['pickup_interval']['end'], '%Y-%m-%dT%H:%M:%SZ').astimezone(
                            timezone.utc).strftime("%a %d.%m at %H:%M")))
                send_message_with_link(user_id, text, item_id)
                available_items.append(item)
        if len(available_items) == 0:
            send_message(user_id, "Currently all your favorites are sold out 😕")

    # Loop through all users and see if the number has changed
    def get_available_items_per_user(self):
        while True:
            try:
                temp_available_items = {}
                for key in self.users_login_data.keys():
                    self.connect(key)
                    time.sleep(1)
                    available_items = self.get_favourite_items()
                    for item in available_items:
                        status = "null"
                        item_id = item['item']['item_id']
                        if item_id in self.available_items_favorites.keys() and not item_id in temp_available_items.keys():
                            old_items_available = int(self.available_items_favorites[item_id]['items_available'])
                            new_items_available = int(item['items_available'])
                            if new_items_available == 0 and old_items_available > 0:  # Sold out (x -> 0)
                                status = "sold_out"
                            elif old_items_available == 0 and new_items_available > 0:  # New Bag available (0 -> x)
                                status = "new_stock"
                            elif old_items_available > new_items_available:  # Reduced stock available (x -> x-1)
                                status = "stock_reduced"
                            elif old_items_available < new_items_available:  # Increased stock available (x -> x-1)
                                status = "stock_increased"
                            if not status == "null":
                                temp_available_items[item_id] = status
                        self.available_items_favorites[item_id] = item
                        if item_id in temp_available_items and \
                                self.users_settings_data[key][temp_available_items[item_id]] == 1:
                            saved_status = temp_available_items[item_id]
                            store_name = "🍽 " + str(item['store']['store_name'])
                            store_address_line = "🧭 " + str(item['store']['store_location']['address']['address_line'])
                            store_price = "💰 " + str(int(item['item']["price_including_taxes"]["minor_units"]) / 100)
                            store_items_available = "🥡 " + str(item['items_available'])
                            if saved_status == "sold_out":
                                text = store_name \
                                       + "\n" + store_address_line \
                                       + "\n" + store_price \
                                       + "\n" + store_items_available
                            else:
                                text = "{0}\n{1}\n{2}\n{3}\n⏰ {4} - {5}".format(store_name, store_address_line,
                                                                                store_price, store_items_available, str(
                                        datetime.strptime(item['pickup_interval']['start'],
                                                          "%Y-%m-%dT%H:%M:%SZ").astimezone(
                                            timezone.utc).strftime("%a %d.%m at %H:%M")), str(
                                        datetime.strptime(item['pickup_interval']['end'], '%Y-%m-%dT%H:%M:%SZ').astimezone(
                                            timezone.utc).strftime("%a %d.%m at %H:%M")))
                            text += "\n" + saved_status
                            print(saved_status + " Telegram USER_ID: " + key + "\n" + text)
                            send_message_with_link(key, text, item_id)
                self.save_available_items_favorites_to_txt()
                time.sleep(60)
            except Exception as err:
                print(f"Unexpected {err=}, {type(err)=}")