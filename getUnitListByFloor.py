import requests
import json
from bs4 import BeautifulSoup
import re

BASE_URL = 'https://www.thestandardatdomainnorthside.com'
FLOOR_PLANS_URL = f'{BASE_URL}/floor-plans/'

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36',
}

# Preferred lease term for price display (months)
PREFERRED_LEASE_TERM = 12

large_units = []  # Units > 750 sq ft
target_floor_units = []  # 4th and 5th floor units (14xx, 15xx, 24xx, 25xx, 34xx, 35xx)
ideal_units = []  # Units that meet both criteria


def is_target_floor(unit_number):
    """Check if unit is on 4th or 5th floor based on unit number pattern"""
    if not unit_number or unit_number == 'N/A':
        return False
    patterns = ['14', '15', '24', '25', '34', '35']
    return any(unit_number.startswith(pattern) for pattern in patterns)


def get_floor_plan_slugs():
    """Fetch the main floor plans page and extract individual floor plan URLs."""
    response = requests.get(FLOOR_PLANS_URL, headers=HEADERS)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, 'html.parser')
    ld_json = soup.find('script', type='application/ld+json')
    if not ld_json:
        print("[-] Could not find JSON-LD data on floor plans page")
        return []

    data = json.loads(ld_json.string)
    graph = data.get('@graph', [])

    # Find the ApartmentComplex entry which lists all floor plans
    for item in graph:
        if item.get('@type') == 'ApartmentComplex':
            plans = item.get('accommodationFloorPlan', [])
            return [(p['name'], p['url']) for p in plans]

    return []


def scrape_floor_plan_page(name, url):
    """Scrape a single floor plan page for unit details and pricing."""
    response = requests.get(url, headers=HEADERS)
    if response.status_code != 200:
        print(f"[-] Request failed with status code {response.status_code} for floor plan {name}")
        return

    soup = BeautifulSoup(response.text, 'html.parser')
    ld_json = soup.find('script', type='application/ld+json')
    if not ld_json:
        print(f"[-] No JSON-LD data found for floor plan {name}")
        return

    data = json.loads(ld_json.string)
    graph = data.get('@graph', [])

    # Extract floor plan details
    floor_plan_info = None
    apartments = {}  # keyed by @id
    offers = []

    for item in graph:
        item_type = item.get('@type')
        if item_type == 'FloorPlan' and item.get('name') == name:
            floor_plan_info = item
        elif item_type == 'Apartment':
            apartments[item['@id']] = item
        elif item_type == 'OfferForLease':
            offers.append(item)

    if not floor_plan_info:
        print(f"[-] Could not find FloorPlan details for {name}")
        return

    # Get floor plan sqft
    floor_size = floor_plan_info.get('floorSize', {})
    sqft_min = floor_size.get('minValue', 0)
    sqft_max = floor_size.get('maxValue', sqft_min)
    beds = floor_plan_info.get('numberOfBedrooms', 0)
    baths = floor_plan_info.get('numberOfBathroomsTotal', 0)
    available_count = floor_plan_info.get('numberOfAvailableAccommodationUnits', 0)
    total_count = floor_plan_info.get('numberOfAccommodationUnits', 0)

    # Build per-unit pricing: unit_id -> {lease_term: price}
    unit_pricing = {}
    for offer in offers:
        offered_item = offer.get('itemOffered', {})
        unit_id = offered_item.get('@id', '')
        lease_months = offer.get('leaseLength', {}).get('value', 0)
        price = offer.get('priceSpecification', {}).get('price', 0)
        if unit_id not in unit_pricing:
            unit_pricing[unit_id] = {}
        unit_pricing[unit_id][lease_months] = price

    print("-" * 20)
    print(f"Floor Plan: {name} | {beds} bed / {baths} bath | {sqft_min}-{sqft_max} sq ft | {available_count}/{total_count} available")
    print("-" * 20)

    for apt_id, apt in apartments.items():
        unit_number = apt.get('name', 'N/A')
        unit_sqft = apt.get('floorSize', {}).get('value', sqft_min)

        # Get preferred lease term price, fall back to lowest available
        pricing = unit_pricing.get(apt_id, {})
        price_12mo = pricing.get(PREFERRED_LEASE_TERM, 0)
        price_min = min(pricing.values()) if pricing else 0
        price_display = price_12mo if price_12mo else price_min

        # Extract apply URL for unit ID info
        apply_url = ''
        action = apt.get('potentialAction', {})
        target = action.get('target', {})
        if isinstance(target, dict):
            apply_url = target.get('urlTemplate', '')

        available = bool(pricing)
        status = "Available" if available else "Not Available"
        if available:
            print(f"  Unit {unit_number} | {unit_sqft} sq ft | ${price_display}/mo ({PREFERRED_LEASE_TERM}mo) | min ${price_min}/mo | {status}")
        else:
            print(f"  Unit {unit_number} | {unit_sqft} sq ft | {status}")

        # Process unit for summary
        is_large = unit_sqft > 750
        is_target = is_target_floor(unit_number)

        unit_info = {
            'unit_number': unit_number,
            'sqft': unit_sqft,
            'price': str(price_display),
            'price_min': str(price_min),
            'pricing': pricing,
            'floor_plan': name,
            'beds': beds,
            'baths': baths,
            'apply_url': apply_url,
            'available': available,
        }

        if is_large:
            large_units.append(unit_info)
        if is_target:
            target_floor_units.append(unit_info)
        if is_large and is_target:
            ideal_units.append(unit_info)


# Main
print("Fetching floor plans from The Standard at Domain Northside...")
print("=" * 60)

floor_plans = get_floor_plan_slugs()
if not floor_plans:
    print("[-] No floor plans found. Exiting.")
    exit(1)

print(f"Found {len(floor_plans)} floor plans: {', '.join(name for name, _ in floor_plans)}\n")

for name, url in floor_plans:
    scrape_floor_plan_page(name, url)
    print()

# Print Summary
print("\n" + "=" * 60)
print("SUMMARY - UNITS MATCHING YOUR CRITERIA")
print("=" * 60)

print(f"\n🎯 IDEAL UNITS (4th/5th Floor + >750 sq ft): {len(ideal_units)} units")
if ideal_units:
    ideal_units.sort(key=lambda x: (x['available'], x['sqft']), reverse=True)
    for unit in ideal_units:
        floor_type = "4th Floor" if unit['unit_number'][:2] in ['14', '24', '34'] else "5th Floor"
        avail = "" if unit['available'] else " [Not Available]"
        price_str = f"${unit['price']}/mo" if unit['available'] else "N/A"
        print(f"   • Unit {unit['unit_number']} ({unit['floor_plan']}) - {unit['sqft']} sq ft - {price_str} - {floor_type}{avail}")

print(f"\n📏 ALL LARGE UNITS (>750 sq ft): {len(large_units)} units")
if large_units:
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
        avail = "" if unit['available'] else " [Not Available]"
        price_str = f"${unit['price']}/mo" if unit['available'] else "N/A"
        print(f"      Unit {unit['unit_number']} ({unit['floor_plan']}) - {price_str}{floor_info}{avail}")

print(f"\n🏢 4th/5th FLOOR UNITS (All sizes): {len(target_floor_units)} units")
if target_floor_units:
    fourth_floor = [u for u in target_floor_units if u['unit_number'][:2] in ['14', '24', '34']]
    fifth_floor = [u for u in target_floor_units if u['unit_number'][:2] in ['15', '25', '35']]

    if fourth_floor:
        print(f"\n   4th Floor Units ({len(fourth_floor)}):")
        fourth_floor.sort(key=lambda x: (x['available'], x['sqft']), reverse=True)
        for unit in fourth_floor:
            size_info = " ⭐ (>750 sq ft)" if unit['sqft'] > 750 else ""
            avail = "" if unit['available'] else " [Not Available]"
            price_str = f"${unit['price']}/mo" if unit['available'] else "N/A"
            print(f"      Unit {unit['unit_number']} ({unit['floor_plan']}) - {unit['sqft']} sq ft - {price_str}{size_info}{avail}")

    if fifth_floor:
        print(f"\n   5th Floor Units ({len(fifth_floor)}):")
        fifth_floor.sort(key=lambda x: (x['available'], x['sqft']), reverse=True)
        for unit in fifth_floor:
            size_info = " ⭐ (>750 sq ft)" if unit['sqft'] > 750 else ""
            avail = "" if unit['available'] else " [Not Available]"
            price_str = f"${unit['price']}/mo" if unit['available'] else "N/A"
            print(f"      Unit {unit['unit_number']} ({unit['floor_plan']}) - {unit['sqft']} sq ft - {price_str}{size_info}{avail}")

print(f"\n💡 RECOMMENDATION:")
available_ideal = [u for u in ideal_units if u['available']]
if available_ideal:
    best_unit = available_ideal[0]
    print(f"   Best match: Unit {best_unit['unit_number']} ({best_unit['floor_plan']}) with {best_unit['sqft']} sq ft for ${best_unit['price']}/mo")
elif ideal_units:
    print("   Units exist matching both criteria but none are currently available")
else:
    print("   No units found that meet both criteria (4th/5th floor + >750 sq ft)")

print("\n" + "=" * 60)
