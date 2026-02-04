import json
import re

def is_valid_pool(pool):
    name = pool.get('name', '')
    category = pool.get('category', '')

    # 1. Block specific categories (Bad Keywords)
    # These categories are almost certainly not swimming pools unless explicitly named so.
    bad_keywords = [
        '한식', '중식', '일식', '양식', '분식', '음식점',
        '카페', '디저트', '술집', '고기', '찌개', '전골',
        '모텔', '펜션', '야영장', '캠핑', '민박', '게스트하우스',
        '유치원', '어린이집', '학원', '교습소' # Exclude educational institutions unless they are sports academies
    ]

    # Exception keywords that save an entry even if it has a bad category
    rescue_keywords = ['수영', '아쿠아', '워터파크', '풀장', '스파']

    for kw in bad_keywords:
        if kw in category:
            # Check for rescue keywords in name
            is_rescued = False
            for rescue in rescue_keywords:
                if rescue in name:
                    is_rescued = True
                    break

            if not is_rescued:
                # Debugging output can be enabled if needed
                # print(f"Filtering out (Category Match): {name} [{category}]")
                return False

    # 2. Require relevant keywords
    # If the category didn't disqualify it, we still want to ensure it's related to swimming/sports/leisure.
    valid_keywords = [
        '수영', '아쿠아', '워터', '풀', '스포츠', '체육', '문화',
        '청소년', '호텔', '리조트', '스파', '짐', '휘트니스', '피트니스',
        '종합운동장', '복지관', '회관', '올림픽', 'YMCA', 'YWCA', '센터'
    ]

    is_relevant = False
    for kw in valid_keywords:
        if kw in name or kw in category:
            is_relevant = True
            break

    if not is_relevant:
        # print(f"Filtering out (No Interest): {name} [{category}]")
        return False

    return True

def process_pools(input_file="advanced_pools.json", output_file="final_pools.json"):
    print(f"Processing {input_file} -> {output_file}...")

    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: {input_file} not found.")
        return

    processed_data = []

    for pool in data:
        # 1. Validate Coordinates
        if not pool.get('lat') or not pool.get('lng'):
            # print(f"Skipping {pool.get('name')} due to missing coordinates.")
            continue

        # 2. Extract Gu from Address if missing
        if not pool.get('gu'):
            address = pool.get('address', '')
            match = re.search(r'(\w+구)', address)
            if match:
                pool['gu'] = match.group(1)
            else:
                pass

        # 3. Convert prices to string
        if 'free_swim_price' in pool:
            pool['free_swim_price'] = str(pool['free_swim_price'])

        if 'daily_price' in pool:
             pass

        # 4. Ensure source is present
        if not pool.get('source'):
            pool['source'] = "Automated Processor"

        # 5. Apply Filtering Logic
        if is_valid_pool(pool):
            processed_data.append(pool)

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(processed_data, f, ensure_ascii=False, indent=2)

    print(f"Done. Processed {len(processed_data)} pools (filtered from {len(data)}).")

if __name__ == "__main__":
    process_pools()
