import datetime as dt
from dateutil.parser import parse
import logging as log
import os
import re
import requests as req

currentDate = dt.date.today().strftime("%Y%m%d")

### Setup log file, opening it once to ensure an empty log file on each run
logfile = f"log_source_{currentDate}.log"
with open(logfile, 'w'):
    pass
log.basicConfig(filename=logfile, level=log.DEBUG)

def getSource(url):
    ### Gets URL contents after passing through the mandatory gateway on the AIP website
    headers = {
        'Connection': 'keep-alive',
        'Cache-Control': 'max-age=0',
        'sec-ch-ua': '" Not A;Brand";v="99", "Chromium";v="96", "Microsoft Edge";v="96"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'Upgrade-Insecure-Requests': '1',
        'DNT': '1',
        'Content-Type': 'application/x-www-form-urlencoded',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36 Edg/96.0.1054.62',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        'Sec-Fetch-Site': 'same-origin',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-User': '?1',
        'Sec-Fetch-Dest': 'document',
        'Accept-Language': 'en-US,en;q=0.9,id;q=0.8,nl;q=0.7,fr;q=0.6',
    }
    # data = {
    #     'Submit': 'I Agree',
    #     'check': '1'
    # }
    try:
        response = req.get(url, headers=headers)
    except req.exceptions.ConnectionError:
        response = req.get(url, headers=headers)
    return response

rootURL = "https://www.ozrunways.com"

### Generates a list of links to individual helipad pages.
print(f"Getting list of helipads.")
helipads_URL = "/helipads/"
helipads_src_raw = getSource(f"{rootURL}{helipads_URL}").text
helipads_source_lines = helipads_src_raw.splitlines()
helipads_links = []
log.info("======Links on main page:")
for line in helipads_source_lines:
    ### Record only html lines that have relevant href in them
    if "<td><a href=" in line:
        ### get link
        link_start = '<td><a href="'
        link_end = '">'
        link = line.split(link_start)[1].split(link_end)[0]
        link = link.replace("helipad.","content.")
        ### get code
        code_start = '.jsp?code='
        code_end = '">'
        code = line.split(code_start)[1].split(code_end)[0]
        ### add 0 prefix to code to allow for sorting
        if code[0] == "Y":
            code = "0" + code
        helipads_links.append((code,link))
        log.info(f"{code},{link}")

helipads_links.sort()


### Setup csv file
csv_file = f"OZrunways_data_{currentDate}.csv"
with open (csv_file, 'w') as csv:
    pass

### Setup kml file
kml_file = f"OZrunways_{currentDate}.kml"
with open (kml_file, 'w') as kml:
    with open ('kmltemplate_start.txt', 'r') as template:
        for line in template:
            kml.write(line)
    kml.write('\n')

### Open files for writing
csv = open(csv_file, 'a')
kml = open(kml_file, 'a')

### Setup progress counter and limiter
count = 0
total_helipads = len(helipads_links)
processed_helipads = 0
### Indicate that we start by processing published helipads
published_folder = 1
### Iterate through list of helipads and write info to csv and kml
for code,link in helipads_links:
    ### Remove prefix from published helipad codes and start new folder when required
    if code[0] == "0":
        code = code[1:]
    else:
        if published_folder == 1:
            kml.write("        </Folder>\n")
            kml.write("        <Folder>\n")
            kml.write("            <name>Unpublished</name>\n")
        published_folder = 0
    log.info(f"======Processing html for {code}")
    processed_helipads += 1
    print(f"Processing {processed_helipads} of {total_helipads} ...", end=" ")
    helipad_src_raw = getSource(f"{rootURL}{link}").text
    helipad_src_lines = helipad_src_raw.splitlines()
    for line in helipad_src_lines:
        if "&deg;" in line:
            log.info(line)
            coord_start = "<dd>"
            coord_end = "</dd>"
            coord = line.split(coord_start)[1].split(coord_end)[0]
            lat_deg = int(coord.split(" ")[0].split("&")[0])
            lat_min = float(coord.split(" ")[1].split("'")[0])
            lat_dir = coord.split(" ")[1].split("'")[1]
            lat_sign = 1
            if lat_dir == "S":
                lat_sign = -1
            lat_dec = lat_sign * ( lat_deg + lat_min / 60 )
            lon_deg = int(coord.split(" ")[2].split("&")[0])
            lon_min = float(coord.split(" ")[3].split("'")[0])
            lon_dir = coord.split(" ")[3].split("'")[1]
            lon_sign = 1
            if lon_dir == "W":
                lon_sign = -1
            lon_dec = lon_sign * ( lon_deg + lon_min / 60 )
            ### Write info to both csv and kml
            csv.write(f"{code},{lat_dir},{lat_deg},{lat_min},{lat_dec},{lon_dir},{lon_deg},{lon_min},{lon_dec}\n")
            kml.write(f"            <Placemark>\n")
            kml.write(f"                <name>{code}</name>\n")
            kml.write(f"                <open>1</open>\n")
            kml.write(f"                <styleUrl>#msn_heliport</styleUrl>\n")
            kml.write(f"                <Point>\n")
            kml.write(f"                    <coordinates>{lon_dec},{lat_dec},0</coordinates>\n")
            kml.write(f"                </Point>\n")
            kml.write(f"            </Placemark>\n")
    print("done")
    # count += 1
    # if count == 5:
    #     break

with open ('kmltemplate_end.txt', 'r') as template:
    for line in template:
        kml.write(line)

### Close files
csv.close()
kml.close()