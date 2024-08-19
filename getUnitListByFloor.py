import requests
import pickle
import json
from bs4 import BeautifulSoup
import re
from datetime import datetime

today = datetime.today().strftime('%d %B %Y')
moveinDate = today.lstrip('0').replace(' 0', ' ')

floorPlanIDs = [
     '4616626',
     '4616627',
     '4616628',
     '4616629',
     '4616630',
     '4616631',
     '4616632',
     '4616633',
     '4616634',
     '4616635',
     '4616636',
     '4616637',
     '4616638',
     '4616639',
     '4616640',
     '4616641',
     '4616642',
     '4616643',
]

url = 'https://app.repli360.com/admin/getUnitListByFloor'

headers = {
    'Referer': 'https://www.thestandardatdomainnorthside.com/floor-plans',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36',
    'Content-Type': 'application/x-www-form-urlencoded'
}

for floorPlanID in floorPlanIDs:

    # payloads is dynamic based on floorPlanID
    payload = {
        'floorPlanID': floorPlanID,
        'moveinDate': moveinDate,
        'site_id': '1233',
        'template_type': '2',
        'mode': '',
        'type': '2d',
        'currentanuualterm': '',
        'AcademicTerm': '',
        'RentalLevel': ''
    }

    # Make the POST request to fetch the data
    response = requests.post(url, data=payload, headers=headers)

    # Check if the request was successful
    if response.status_code == 200:
        data = response.json()

        # Parse the HTML string with BeautifulSoup
        html_str = data['str']
        soup = BeautifulSoup(html_str, 'html.parser')
        rows = soup.select('tr.unitlisting')

        print("-" * 20)
        for row in rows:
            unitID = row.get('class', [])[1].split('_')[-1]
            unitNumber = row.select_one('.unitNumber').text if row.select_one('.unitNumber') else 'N/A'
            unitSQFT = row.select_one('td:nth-of-type(2) b').text if row.select_one('td:nth-of-type(2) b') else 'N/A'

            startingAt = row.select_one('td:nth-of-type(3)').text.strip() if row.select_one('td:nth-of-type(3)') else 'N/A'
            startingAtNum = re.sub(r'[^\d]', '', startingAt)

            availabilityDate = row.get('data-available_date', 'N/A')

            print(f"floorPlanID: {floorPlanID}")
            print(f"UnitID: {unitID}")
            print(f"Unit Number: {unitNumber}")
            print(f"Unit SQFT: {unitSQFT}")
            print(f"Starting at: {startingAtNum}")
            print(f"Availability: {availabilityDate}")
            print("-" * 20)

    else:
        print(f"[-] Request failed with status code {response.status_code} for floorPlanID {floonPlanID}")

