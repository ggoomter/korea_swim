import json
import re

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
            print(f"Skipping {pool.get('name')} due to missing coordinates.")
            continue

        # 2. Extract Gu from Address if missing
        # Default strategy: Look for "XX구" in address
        if not pool.get('gu'):
            address = pool.get('address', '')
            match = re.search(r'(\w+구)', address)
            if match:
                pool['gu'] = match.group(1)
            else:
                # Fallback for non-standard addresses or just keep as is
                pass

        # 3. Convert prices to string (Schema requirement)
        if 'free_swim_price' in pool:
            pool['free_swim_price'] = str(pool['free_swim_price'])

        if 'daily_price' in pool:
             # Just in case we want to preserve it even if schema ignores it currently
             pass

        # 4. Ensure source is present
        if not pool.get('source'):
            pool['source'] = "Automated Processor"

        processed_data.append(pool)

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(processed_data, f, ensure_ascii=False, indent=2)

    print(f"Done. Processed {len(processed_data)} pools.")

if __name__ == "__main__":
    process_pools()
