# -*- coding: utf-8 -*-
""" Scripts for downloading last episode of a show on certain days and hours. """
import os
import sys
import time
import platform
import datetime
import subprocess
import requests

from m3u8_dl import cli

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException


# In which days of the week is the show available
GOOD_DAYS = {0, 1, 2}
# At what hour is the show available
GOOD_TIME = 0
# Which season to download (e.g.: 01, 02, ...)
SEASON = ''

# Login URL looks like https://server/login
LOGIN_URL = ''
# Base URL looks like https://server/series-name-season-X
BASE_URL = ''
# Base path looks like /home/user/media/series-name/season-X
BASE_PATH = ''


def run() -> None:
    """ Run all """
    start = time.time()
    cli.main()
    print(f"Time elapsed: {time.time() - start}")


def try_get_url(latest: int) -> str:
    """ Tries to get the URL to download """
    # get main URL with requests
    nav_to_url = ""
    while not nav_to_url:
        nav_to_url = get_ep_url(latest)
        if nav_to_url:
            break
        minutes = 5 if datetime.datetime.now().hour != 23 else 3
        print(f"[{datetime.datetime.now()}] Waiting {minutes} minutes...")
        time.sleep(60 * minutes)
    # get video ID with chrome driver
    url = ""
    chrome = start_browser()
    time.sleep(5)
    chrome.get(nav_to_url)
    time.sleep(5)
    while not url:
        try:
            url = (
                chrome
                .find_element(By.TAG_NAME, 'video')
                .find_element(By.CSS_SELECTOR, "*")
                .get_attribute('src')
            )
        except NoSuchElementException as err:
            print(
                f"[{datetime.datetime.now()}] Episode is on server, but cannot get video id: {err}"
            )
        finally:
            if not url:
                minutes = 5 if datetime.datetime.now().hour != 23 else 3
                print(f"[{datetime.datetime.now()}] Cannot find URL. Waiting {minutes} minutes...")
                time.sleep(60 * minutes)
                chrome.refresh()
    chrome.quit()
    if platform.system() == 'Linux':
        subprocess.check_output('killall /opt/google/chrome/chrome', shell=True)
    else:
        subprocess.check_output('taskkill /IM chrome.exe /F', shell=True)
    return get_good_url(url)


def get_good_url(url: str) -> str:
    """  Finds the good URL in the file at given url"""
    req = requests.get(url, timeout=5)
    content = req.content.decode().split('\n')
    for uri in content:
        if uri.startswith('https'):
            return uri
    raise AssertionError(f"Cannot find URI\n\n{content}")


def auto_get_url(latest: int) -> (int, str):
    """ Auto gets URL """
    url = ""
    while not url:
        url = try_get_url(latest)
        try:
            sys.argv[1] = url
        except IndexError:
            sys.argv.append(url)
        full_path = os.path.join(BASE_PATH, f'S{SEASON}E{latest}.mp4')
        if not os.path.exists(BASE_PATH):
            os.makedirs(BASE_PATH)
        try:
            sys.argv[2] = full_path
        except IndexError:
            sys.argv.append(full_path)
        return latest, url
    return latest, url


def get_latest() -> int:
    """ Returns latest episode """
    max_val = 0
    for file in os.listdir(BASE_PATH):
        current_file = file.split('.', 1)[0]
        try:
            current_no = int(current_file.split('E', 1)[-1])
        except ValueError as err:
            print(f"[{datetime.datetime.now()}] {err}")
            continue
        if current_no > max_val:
            max_val = current_no
    return max_val


def run_timers() -> None:
    """ Runs with timers """
    latest = get_latest()
    latest += 1
    tried_first_time = False
    while True:
        print(f"Will look for episode {latest}")
        skip_checks = False
        if not tried_first_time and get_ep_url(latest):
            print(f"Episode {latest} is available sooner! Trying to download it")
            tried_first_time = True
            skip_checks = True
        current_day = datetime.datetime.today().weekday()
        # if it's not sunday, monday or tuesday, sleep 22 hours
        if current_day not in GOOD_DAYS and not skip_checks:
            time.sleep(3600 * 22)
            continue
        print(f"[{datetime.datetime.now()}] Day is {current_day}")
        now = datetime.datetime.now()
        start_hour = now.replace(hour=22, minute=50, second=0, microsecond=0)
        if now < start_hour and not skip_checks:
            time.sleep(60)
            continue
        print(f"[{datetime.datetime.now()}] Time is {now.hour}:{now.minute}. Trying to get URL")
        latest, url = auto_get_url(latest)
        print(f"[{datetime.datetime.now()}] {latest} {url}")
        run()
        if skip_checks:
            sleep_time = 0.2
        elif current_day in (0, 6):
            sleep_time = 23
        elif current_day == 1:
            sleep_time = 23 * 5
        else:
            sleep_time = 24
        print(f"[{datetime.datetime.now()}] Sleeping {sleep_time}h...")
        latest += 1
        time.sleep(3600 * sleep_time)


def get_ep_url(ep_no: int) -> str:
    """ Finds the episode's URL """
    resp = requests.get(BASE_URL, timeout=5).text
    edition_name = resp.split(f'-{ep_no}')[0].rsplit('-', 1)[-1]
    try:
        url = (
            resp
            .split(f'{edition_name}-{ep_no}')[2]
            .split('/', 1)[-1]
            .split(" ", 1)[0]
        )
    except (AttributeError, IndexError) as err:
        print(f"[{datetime.datetime.now()}] Episode {ep_no} not yet on the server... {err}")
        return ''
    return f"{BASE_URL}-{edition_name}-{ep_no}/{url}"


def start_browser() -> webdriver:
    """ Starts Chrome browser """
    # pylint: disable=consider-using-with
    if platform.system() == 'Linux':
        proc = subprocess.Popen('nohup google-chrome --remote-debugging-port=9222 &')
    else:
        proc = subprocess.Popen('start chrome --remote-debugging-port=9222')
    proc.communicate()
    options = webdriver.ChromeOptions()
    options.add_experimental_option('debuggerAddress', '127.0.0.1:9222')
    chrome = webdriver.Chrome(options=options)
    return chrome


if __name__ == '__main__':
    run_timers()
