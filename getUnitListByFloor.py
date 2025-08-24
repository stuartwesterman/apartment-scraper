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

large_units = []  # Units > 750 sq ft
target_floor_units = []  # 4th and 5th floor units (14xx, 15xx, 24xx, 25xx, 34xx, 35xx)
ideal_units = []  # Units that meet both criteria

def is_target_floor(unit_number):
    """Check if unit is on 4th or 5th floor based on unit number pattern"""
    if not unit_number or unit_number == 'N/A':
        return False

    # Check for 4th and 5th floor patterns: 14xx, 15xx, 24xx, 25xx, 34xx, 35xx
    patterns = ['14', '15', '24', '25', '34', '35']
    return any(unit_number.startswith(pattern) for pattern in patterns)

def extract_sqft_number(sqft_text):
    """Extract numeric square footage from text like '908 SQFT'"""
    if not sqft_text or sqft_text == 'N/A':
        return 0

    numbers = re.findall(r'\d+', sqft_text)
    return int(numbers[0]) if numbers else 0

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

            # Process unit for summary
            sqft_num = extract_sqft_number(unitSQFT)
            is_large = sqft_num > 750
            is_target = is_target_floor(unitNumber)

            unit_info = {
                'unit_number': unitNumber,
                'sqft': sqft_num,
                'sqft_text': unitSQFT,
                'price': startingAtNum,
                'availability': availabilityDate,
                'floor_plan_id': floorPlanID
            }

            # Categorize units
            if is_large:
                large_units.append(unit_info)

            if is_target:
                target_floor_units.append(unit_info)

            if is_large and is_target:
                ideal_units.append(unit_info)


    else:
        print(f"[-] Request failed with status code {response.status_code} for floorPlanID {floonPlanID}")


# Print Summary
print("\n" + "=" * 60)
print("SUMMARY - UNITS MATCHING YOUR CRITERIA")
print("=" * 60)

print(f"\n🎯 IDEAL UNITS (4th/5th Floor + >750 sq ft): {len(ideal_units)} units")
if ideal_units:
    # Sort by square footage (largest first)
    ideal_units.sort(key=lambda x: x['sqft'], reverse=True)
    for unit in ideal_units:
        floor_type = "4th Floor" if unit['unit_number'][:2] in ['14', '24', '34'] else "5th Floor"
        print(f"   • Unit {unit['unit_number']} - {unit['sqft']} sq ft - ${unit['price']} - Available {unit['availability']} ({floor_type})")

print(f"\n📏 ALL LARGE UNITS (>750 sq ft): {len(large_units)} units")
if large_units:
    # Group by square footage
    large_units.sort(key=lambda x: x['sqft'], reverse=True)
    current_sqft = None
    for unit in large_units:
        if unit['sqft'] != current_sqft:
            current_sqft = unit['sqft']
            print(f"\n   {current_sqft} sq ft units:")
        floor_info = ""
        if is_target_floor(unit['unit_number']):
            floor_type = "4th Floor" if unit['unit_number'][:2] in ['14', '24', '34'] else "5th Floor"
            floor_info = f" ⭐ ({floor_type})"
        print(f"      Unit {unit['unit_number']} - ${unit['price']} - Available {unit['availability']}{floor_info}")

print(f"\n🏢 4th/5th FLOOR UNITS (All sizes): {len(target_floor_units)} units")
if target_floor_units:
    # Group by floor
    fourth_floor = [u for u in target_floor_units if u['unit_number'][:2] in ['14', '24', '34']]
    fifth_floor = [u for u in target_floor_units if u['unit_number'][:2] in ['15', '25', '35']]

    if fourth_floor:
        print(f"\n   4th Floor Units ({len(fourth_floor)}):")
        fourth_floor.sort(key=lambda x: x['sqft'], reverse=True)
        for unit in fourth_floor:
            size_info = " ⭐ (>750 sq ft)" if unit['sqft'] > 750 else ""
            print(f"      Unit {unit['unit_number']} - {unit['sqft']} sq ft - ${unit['price']} - Available {unit['availability']}{size_info}")

    if fifth_floor:
        print(f"\n   5th Floor Units ({len(fifth_floor)}):")
        fifth_floor.sort(key=lambda x: x['sqft'], reverse=True)
        for unit in fifth_floor:
            size_info = " ⭐ (>750 sq ft)" if unit['sqft'] > 750 else ""
            print(f"      Unit {unit['unit_number']} - {unit['sqft']} sq ft - ${unit['price']} - Available {unit['availability']}{size_info}")

print(f"\n💡 RECOMMENDATION:")
if ideal_units:
    best_unit = ideal_units[0]  # Largest ideal unit
    print(f"   Best match: Unit {best_unit['unit_number']} with {best_unit['sqft']} sq ft for ${best_unit['price']}")
else:
    print("   No units found that meet both criteria (4th/5th floor + >750 sq ft)")

print("\n" + "=" * 60)
