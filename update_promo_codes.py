import os
import re
import sys
import json
import datetime
import urllib.request
from bs4 import BeautifulSoup

def main():
    print("Starting Raid Shadow Legends Promo Codes update...")
    
    # 1. Fetch the SkyCoach page
    url = "https://skycoach.gg/blog/raid-shadow-legends/articles/all-codes"
    req = urllib.request.Request(
        url, 
        headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    )
    
    try:
        with urllib.request.urlopen(req) as response:
            html = response.read().decode('utf-8')
    except Exception as e:
        print(f"Error fetching SkyCoach webpage: {e}", file=sys.stderr)
        sys.exit(1)
        
    soup = BeautifulSoup(html, 'html.parser')
    
    # 2. Find the code tables
    h2_tags = soup.find_all("h2")
    active_table = None
    new_table = None
    
    for h2 in h2_tags:
        text = h2.get_text()
        if "Promo Codes" in text and "New Player" not in text:
            active_table = h2.find_next("table")
        elif "New Player" in text:
            new_table = h2.find_next("table")
            
    if not active_table:
        print("Error: Could not locate the Active Promo Codes table.", file=sys.stderr)
        sys.exit(1)
    if not new_table:
        print("Error: Could not locate the New Player Promo Codes table.", file=sys.stderr)
        sys.exit(1)
        
    # Helper function to parse table rows
    def parse_table(table):
        codes_list = []
        rows = table.find_all("tr")
        for row in rows:
            tds = row.find_all("td")
            if not tds or len(tds) < 2:
                continue
            
            code = tds[0].get_text(strip=True)
            rewards = tds[1].get_text(strip=True)
            
            # Skip header row
            if code.lower() in ("code", "reason", "rewards") or rewards.lower() in ("code", "rewards"):
                continue
            
            if not code:
                continue
                
            # Clean code
            code = code.replace(" ", "").upper()
            
            # Clean rewards
            rewards = re.sub(r'\s+', ' ', rewards) # Normalize spaces
            if rewards.lower() == "rewards" or not rewards:
                rewards = "Free in-game rewards"
                
            codes_list.append({
                "code": code,
                "rewards": rewards
            })
        return codes_list

    active_codes = parse_table(active_table)
    new_player_codes = parse_table(new_table)
    
    print(f"Successfully scraped {len(active_codes)} active codes and {len(new_player_codes)} new player codes.")
    
    if not active_codes or not new_player_codes:
        print("Error: Scraped empty lists of codes. Aborting to prevent corrupting databases.", file=sys.stderr)
        sys.exit(1)
        
    # 3. Generate tags for subfolder database
    # Tags: champion, shards, energy, silver
    champion_keywords = {
        'champion', 'champions', 'character', 'characters', 'chicken', 'tome', 'chicken', 'feed',
        'deliana', 'pelops', 'razelvarg', 'stag knight', 'cheshire', 'fenshi', 'deathknight',
        'alure', 'apothecary', 'cormac', 'chonoru', 'fenax', 'tallia', 'hoskorul', 'jinglehunter',
        'kytis', 'loki', 'luria', 'luthica', 'melga', 'mausoleum', 'mordecai', 'orn', 'oboro',
        'rector', 'sigmund', 'wukong', 'galek', 'tholin', 'thylessia', 'toragi', 'urticata'
    }
    
    def assign_tags(rewards):
        tags = []
        r_lower = rewards.lower()
        
        # Check champion
        if any(kw in r_lower for kw in champion_keywords):
            tags.append("champion")
        # Check shards
        if "shard" in r_lower:
            tags.append("shards")
        # Check energy
        if any(kw in r_lower for kw in ["energy", "refill", "auto-battle", "battles"]):
            tags.append("energy")
        # Check silver
        if any(kw in r_lower for kw in ["silver", "gems", "gem"]):
            tags.append("silver")
            
        return tags

    # Apply tags
    for item in active_codes:
        item["tags"] = assign_tags(item["rewards"])
    for item in new_player_codes:
        item["tags"] = assign_tags(item["rewards"])
        
    total_count = len(active_codes) + len(new_player_codes)
    
    # 4. Get current date info
    now = datetime.datetime.now()
    current_month_name = now.strftime("%B")
    current_year = now.strftime("%Y")
    current_date_str = now.strftime("%Y-%m-%d")
    current_first_of_month_str = now.strftime("%Y-%m-01")
    
    # 5. Define file paths
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Auto-detect if we are running in the root or the subfolder repository
    if os.path.exists(os.path.join(base_dir, "raid-shadow-legends-promo-codes")):
        print("Root repository detected.")
        root_index = os.path.join(base_dir, "index.html")
        root_codes = os.path.join(base_dir, "codes.html")
        sub_index = os.path.join(base_dir, "raid-shadow-legends-promo-codes", "index.html")
        sub_codes = os.path.join(base_dir, "raid-shadow-legends-promo-codes", "codes.html")
        sitemap = os.path.join(base_dir, "raid-shadow-legends-promo-codes", "sitemap.xml")
    else:
        print("Subfolder repository detected.")
        root_index = None
        root_codes = None
        sub_index = os.path.join(base_dir, "index.html")
        sub_codes = os.path.join(base_dir, "codes.html")
        sitemap = os.path.join(base_dir, "sitemap.xml")
        
    # Month replacement helper
    def update_month_year(content):
        months_pattern = r"\b(January|February|March|April|May|June|July|August|September|October|November|December)\b\s+(\d{4})"
        def replace_match(m):
            orig_month = m.group(1)
            if orig_month.isupper():
                new_month = current_month_name.upper()
            elif orig_month.islower():
                new_month = current_month_name.lower()
            else:
                new_month = current_month_name.capitalize()
            return f"{new_month} {current_year}"
        return re.sub(months_pattern, replace_match, content, flags=re.IGNORECASE)

    # Count replacement helper
    def update_count_in_text(content):
        content = re.sub(r"\b\d+\s+Working\s+Codes\b", f"{total_count} Working Codes", content, flags=re.IGNORECASE)
        content = re.sub(r"\b\d+\s+working\s+Raid\b", f"{total_count} working Raid", content, flags=re.IGNORECASE)
        content = re.sub(r"\b\d+\s+Active\s+Codes\b", f"{total_count} Active Codes", content, flags=re.IGNORECASE)
        content = re.sub(r"\b\d+\s+active\s+codes\b", f"{total_count} active codes", content, flags=re.IGNORECASE)
        content = re.sub(r"\b\d+\s+FREE\s+verified\b", f"{total_count} FREE verified", content, flags=re.IGNORECASE)
        content = re.sub(r"\b\d+\s+verified\s+and\s+working\b", f"{total_count} verified and working", content, flags=re.IGNORECASE)
        content = re.sub(r"\b\d+\s+Free\s+Working\b", f"{total_count} Free Working", content, flags=re.IGNORECASE)
        content = re.sub(r"\b\d+\s+unlocked\b", f"{total_count} unlocked", content, flags=re.IGNORECASE)
        content = re.sub(r"See\s+all\s+\d+\s+active\s+promo\s+codes", f"See all {len(active_codes)} active promo codes", content, flags=re.IGNORECASE)
        return content

    # 6. Update codes.html (root)
    if root_codes and os.path.exists(root_codes):
        print("Updating root codes.html...")
        with open(root_codes, "r", encoding="utf-8") as f:
            content = f.read()
            
        # Update Month/Year & counts
        content = update_month_year(content)
        content = update_count_in_text(content)
        
        # Replace arrays
        all_players_js = ",\n".join([f'            {{ code: "{item["code"]}", rewards: "{item["rewards"]}" }}' for item in active_codes])
        new_players_js = ",\n".join([f'            {{ code: "{item["code"]}", rewards: "{item["rewards"]}" }}' for item in new_player_codes])
        
        content = re.sub(
            r"const ALL_PLAYERS_CODES = \[(.*?)\];", 
            f"const ALL_PLAYERS_CODES = [\n{all_players_js}\n        ];", 
            content, 
            flags=re.DOTALL
        )
        content = re.sub(
            r"const NEW_PLAYERS_CODES = \[(.*?)\];", 
            f"const NEW_PLAYERS_CODES = [\n{new_players_js}\n        ];", 
            content, 
            flags=re.DOTALL
        )
        
        with open(root_codes, "w", encoding="utf-8") as f:
            f.write(content)
            
    # 7. Update codes.html (subfolder)
    if sub_codes and os.path.exists(sub_codes):
        print("Updating subfolder codes.html...")
        with open(sub_codes, "r", encoding="utf-8") as f:
            content = f.read()
            
        # Update Month/Year
        content = update_month_year(content)
        content = update_count_in_text(content)
        
        # Replace arrays (with tags)
        all_players_js = ",\n".join([f'            {{ code: "{item["code"]}",       rewards: "{item["rewards"]}", tags: {json.dumps(item["tags"])} }}' for item in active_codes])
        new_players_js = ",\n".join([f'            {{ code: "{item["code"]}",       rewards: "{item["rewards"]}", tags: {json.dumps(item["tags"])} }}' for item in new_player_codes])
        
        content = re.sub(
            r"const ALL_PLAYERS_CODES = \[(.*?)\];", 
            f"const ALL_PLAYERS_CODES = [\n{all_players_js}\n        ];", 
            content, 
            flags=re.DOTALL
        )
        content = re.sub(
            r"const NEW_PLAYERS_CODES = \[(.*?)\];", 
            f"const NEW_PLAYERS_CODES = [\n{new_players_js}\n        ];", 
            content, 
            flags=re.DOTALL
        )
        
        with open(sub_codes, "w", encoding="utf-8") as f:
            f.write(content)

    # 8. Update index.html (root)
    if root_index and os.path.exists(root_index):
        print("Updating root index.html...")
        with open(root_index, "r", encoding="utf-8") as f:
            content = f.read()
            
        # Update Month/Year & counts in text
        content = update_month_year(content)
        content = update_count_in_text(content)
        
        # Update JSON-LD WebPage schema
        schema_pattern = r"(<!-- WebPage Schema -->\s*<script type=\"application/ld\+json\">)(.*?)(</script>)"
        def replace_schema(match_obj):
            prefix = match_obj.group(1)
            raw_json = match_obj.group(2).strip()
            suffix = match_obj.group(3)
            
            try:
                schema_json = json.loads(raw_json)
                # Update properties
                schema_json["name"] = f"Raid Shadow Legends Promo Codes {current_month_name} {current_year} — {total_count} Working Codes | Free Shards, Silver & Energy"
                schema_json["description"] = f"All {total_count} working Raid Shadow Legends promo codes for {current_month_name} {current_year}. Free Sacred Shards, Ancient Shards, Void Shards, Energy, Silver, and Legendary Skill Tomes."
                schema_json["datePublished"] = current_first_of_month_str
                schema_json["dateModified"] = current_date_str
                
                # Update mainEntity
                schema_json["mainEntity"]["name"] = f"Active Raid Shadow Legends Promo Codes {current_month_name} {current_year}"
                schema_json["mainEntity"]["numberOfItems"] = total_count
                
                # Rebuild itemListElement with both active and new player codes
                item_elements = []
                # All active codes first
                pos = 1
                for item in active_codes:
                    item_elements.append({
                        "@type": "ListItem",
                        "position": pos,
                        "name": f"{item['code']} — {item['rewards']}"
                    })
                    pos += 1
                # New player codes second
                for item in new_player_codes:
                    item_elements.append({
                        "@type": "ListItem",
                        "position": pos,
                        "name": f"{item['code']} — {item['rewards']}"
                    })
                    pos += 1
                    
                schema_json["mainEntity"]["itemListElement"] = item_elements
                formatted_json = json.dumps(schema_json, indent=4)
                return f"{prefix}\n{formatted_json}\n    {suffix}"
            except Exception as e:
                print(f"Error parsing root WebPage Schema JSON: {e}", file=sys.stderr)
                return match_obj.group(0)
                
        content = re.sub(schema_pattern, replace_schema, content, flags=re.DOTALL)
        
        with open(root_index, "w", encoding="utf-8") as f:
            f.write(content)

    # 9. Update index.html (subfolder)
    if sub_index and os.path.exists(sub_index):
        print("Updating subfolder index.html...")
        with open(sub_index, "r", encoding="utf-8") as f:
            content = f.read()
            
        # Update Month/Year & counts in text
        content = update_month_year(content)
        content = update_count_in_text(content)
        
        # Update JSON-LD WebPage schema
        schema_pattern = r"(<!-- WebPage Schema -->\s*<script type=\"application/ld\+json\">)(.*?)(</script>)"
        def replace_schema_sub(match_obj):
            prefix = match_obj.group(1)
            raw_json = match_obj.group(2).strip()
            suffix = match_obj.group(3)
            
            try:
                schema_json = json.loads(raw_json)
                # Update properties
                schema_json["name"] = f"Raid Shadow Legends Promo Codes ({current_month_name} {current_year})"
                schema_json["datePublished"] = current_first_of_month_str
                schema_json["dateModified"] = current_date_str
                
                # Update mainEntity
                schema_json["mainEntity"]["name"] = f"Active Raid Shadow Legends Promo Codes {current_month_name} {current_year}"
                
                # Subfolder page usually showcases 10 preview items in JSON-LD
                # Let's take first 7 active and first 3 new player codes
                preview_list = active_codes[:7] + new_player_codes[:3]
                schema_json["mainEntity"]["numberOfItems"] = len(preview_list)
                
                item_elements = []
                pos = 1
                for item in preview_list:
                    item_elements.append({
                        "@type": "ListItem",
                        "position": pos,
                        "name": f"{item['code']} — {item['rewards']}"
                    })
                    pos += 1
                    
                schema_json["mainEntity"]["itemListElement"] = item_elements
                formatted_json = json.dumps(schema_json, indent=4)
                return f"{prefix}\n{formatted_json}\n    {suffix}"
            except Exception as e:
                print(f"Error parsing subfolder WebPage Schema JSON: {e}", file=sys.stderr)
                return match_obj.group(0)
                
        content = re.sub(schema_pattern, replace_schema_sub, content, flags=re.DOTALL)
        
        # Update the preview list and preview cards
        if len(active_codes) >= 2 and len(new_player_codes) >= 1:
            preview_block_pattern = r'(<!-- Blurred preview of codes -->\s*<div class="preview-codes" aria-hidden="true">)(.*?)(</div>)'
            def replace_preview_block(m):
                p1 = m.group(1)
                p3 = m.group(3)
                
                row1 = f'<div class="preview-code-row">\n                        <span class="preview-code-name">All Players Code #1</span>\n                        <span class="preview-code-value">{active_codes[0]["code"]}</span>\n                    </div>'
                row2 = f'<div class="preview-code-row">\n                        <span class="preview-code-name">All Players Code #2</span>\n                        <span class="preview-code-value">{active_codes[1]["code"]}</span>\n                    </div>'
                row3 = f'<div class="preview-code-row">\n                        <span class="preview-code-name">New Player Code #1</span>\n                        <span class="preview-code-value">{new_player_codes[0]["code"]}</span>\n                    </div>'
                return f"{p1}\n                    {row1}\n                    {row2}\n                    {row3}\n                {p3}"
                
            content = re.sub(preview_block_pattern, replace_preview_block, content, flags=re.DOTALL)
            
            # Now update code preview cards:
            card_pattern_1 = r'(All Players Code\s*<span class="status-badge hot">.*?</span>\s*</div>\s*<div class="code-reward">Rewards: <strong>)(.*?)(</strong></div>\s*</div>\s*<div class="code-value" id="code-val-1">)(.*?)(</div>)'
            card_pattern_2 = r'(All Players Code\s*<span class="status-badge active">.*?</span>\s*</div>\s*<div class="code-reward">Rewards: <strong>)(.*?)(</strong></div>\s*</div>\s*<div class="code-value" id="code-val-2">)(.*?)(</div>)'
            card_pattern_3 = r'(New Player Champion Code\s*<span class="status-badge hot">.*?</span>\s*</div>\s*<div class="code-reward">Rewards: <strong>)(.*?)(</strong></div>\s*</div>\s*<div class="code-value" id="code-val-3">)(.*?)(</div>)'
            
            content = re.sub(card_pattern_1, lambda m: f"{m.group(1)}{active_codes[0]['rewards']}{m.group(3)}{active_codes[0]['code']}{m.group(5)}", content, flags=re.DOTALL)
            content = re.sub(card_pattern_2, lambda m: f"{m.group(1)}{active_codes[1]['rewards']}{m.group(3)}{active_codes[1]['code']}{m.group(5)}", content, flags=re.DOTALL)
            content = re.sub(card_pattern_3, lambda m: f"{m.group(1)}{new_player_codes[0]['rewards']}{m.group(3)}{new_player_codes[0]['code']}{m.group(5)}", content, flags=re.DOTALL)
            
        with open(sub_index, "w", encoding="utf-8") as f:
            f.write(content)
            
    # 10. Update sitemap.xml
    if sitemap and os.path.exists(sitemap):
        print("Updating sitemap.xml...")
        with open(sitemap, "r", encoding="utf-8") as f:
            content = f.read()
        content = re.sub(r"<lastmod>\d{4}-\d{2}-\d{2}</lastmod>", f"<lastmod>{current_date_str}</lastmod>", content)
        with open(sitemap, "w", encoding="utf-8") as f:
            f.write(content)
            
    print("Database and HTML pages successfully updated!")

if __name__ == "__main__":
    main()
