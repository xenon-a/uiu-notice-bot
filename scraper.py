# Thanks to Ifte Refat Vai for making this script open source
# This script has been taken from https://github.com/RefatHex/UIU_NOTICE_BOT.git

import requests
from bs4 import BeautifulSoup

url = 'https://www.uiu.ac.bd/'

previous_title = ""


def get_notices(x=0):
    global previous_title

    response = requests.get(url)

    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')

        notices = soup.find_all('a', class_='single-notice')
        date = notices[x].find('h6', class_='subtitle').get_text()
        title = notices[x].find('h4', class_='title').get_text()
        link = notices[x]['href']


        return date, title, link
