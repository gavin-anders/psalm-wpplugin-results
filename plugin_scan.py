#!/usr/bin/python -tt

import logging
import requests
import sys
import subprocess
import os
import json
import shutil
import multiprocessing
from multiprocessing import Manager, Pool
from json.decoder import JSONDecodeError
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from urllib.request import urlopen
from zipfile import ZipFile

logger = logging.getLogger(__name__)
manager = Manager()
table_list = manager.list()

URL = "http://api.wordpress.org/plugins/info/1.1/?action=query_plugins&request[page]={page}&request[per_page]=100"

def get_page(page=1):
    url = URL.format(page=page)
    response = requests.get(url)
    return response.json()

def range_info():
    resp = requests.get(URL.format(page=1)).json()
    page = resp['info']['page']
    pages = resp['info']['pages']
    return (page, pages)

def get_plugin_details(page):
    #sys.stdout.write("[+] Processing page {}\r".format(page))
    plugin_list = []
    plugins = get_page(page)["plugins"]
    for item in plugins:
        plugin = {}
        plugin["name"]          = item["name"]
        plugin["slug"]          = item["slug"]
        plugin["download"]      = item["download_link"]
        plugin_list.append(plugin)
    return plugin_list

def download_zip(url):
    zip_filename = os.path.basename(url)
    zip_path = os.path.join("/tmp/plugins/", zip_filename)

    try:
        with urlopen(url) as zipresp:
            with ZipFile(BytesIO(zipresp.read())) as zfile:
                zfile.extractall(zip_path[:-4])
        return zip_path[:-4]
    except:
        return None

def scan(plugin_src, report_name):
    process = subprocess.run(['./vendor/bin/psalm', '--taint-analysis', '--report={}'.format(report_name), '--threads=20', plugin_src], stdout=subprocess.PIPE)

def cleanup(path):
    try:
        if os.path.isfile(path):
            os.remove(path)
        else:
            shutil.rmtree(path)
            os.rmdir(path)
    except:
        print("Failed to remove file/directory at {}".format(path))

def main(page):
    try:
        plugin_list = get_plugin_details(page)
        for details in plugin_list:
            report_name = "./reports/{}.json".format(details["slug"])
            if not os.path.exists(report_name):
                print("[+] Processing {}".format(details["name"]))
                plugin_src = download_zip(details["download"])
                if plugin_src:
                    scan(plugin_src, report_name)
                    if os.path.exists(report_name):
                        cleanup(report_name)
                    cleanup(plugin_src)
    except:
        raise

if __name__ == '__main__':
    with ThreadPoolExecutor(max_workers=3, thread_name_prefix='plugin') as executor:
        page, pages = range_info()
        for p in range(page, pages):
            f = executor.submit(main, p)

