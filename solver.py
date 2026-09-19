import json

def load_catalog(filepath='catalog.json'):
    with open(filepath, 'r') as f:
        return json.load(f).get('products', [])

def solve_bathroom_bundle(room_length_ft, room_width_ft, budget_usd, theme="Minimalist Modern"):
    catalog = load_catalog()
    
    room_area_sqft = room_length_ft * room_width_ft
    max_usable_sqft = room_area_sqft * 0.40 
    
    theme_matches = [p for p in catalog if theme in p.get('aesthetic_themes', [])]
    if not theme_matches:
        theme_matches = catalog

    categories = ['toilet', 'shower', 'vanity', 'faucet']
    bundle = []
    total_cost = 0
    total_footprint_sqft = 0
    
    # Track water consumption separately per metric
    total_gpf = 0.0
    total_gpm = 0.0

    for cat in categories:
        cat_products = [p for p in theme_matches if p['category'] == cat]
        if not cat_products:
            cat_products = [p for p in catalog if p['category'] == cat]
            
        cat_products.sort(key=lambda x: x['price_usd'])
        
        selected = None
        for p in cat_products:
            dims = p['dimensions_in']
            footprint = (dims['width'] * dims['depth']) / 144.0
            
            if (total_cost + p['price_usd'] <= budget_usd) and ((total_footprint_sqft + footprint) <= max_usable_sqft):
                selected = p
                
        if not selected and cat_products:
            selected = cat_products[0]

        if selected:
            bundle.append(selected)
            total_cost += selected['price_usd']
            dims = selected['dimensions_in']
            total_footprint_sqft += (dims['width'] * dims['depth']) / 144.0
            
            # Accumulate flow rates properly
            if 'gpf' in selected and selected['gpf'] > 0:
                total_gpf += selected['gpf']
            if 'gpm' in selected and selected['gpm'] > 0:
                total_gpm += selected['gpm']

    space_utilization_pct = round((total_footprint_sqft / room_area_sqft) * 100, 1)
    
    # Eco Calculation (Household of 2: 8 flushes/day + 10 min shower/day)
    # Legacy Baseline: 3.5 GPF toilet + 2.5 GPM showerhead
    legacy_annual_gal = (3.5 * 8 + 2.5 * 10) * 365
    selected_annual_gal = (total_gpf * 8 + total_gpm * 10) * 365
    
    annual_water_savings_gal = max(0, round(legacy_annual_gal - selected_annual_gal, 0))

    return {
        "room_dimensions_ft": {"length": room_length_ft, "width": room_width_ft},
        "budget_cap_usd": budget_usd,
        "selected_theme": theme,
        "total_bundle_cost_usd": total_cost,
        "space_utilization_pct": space_utilization_pct,
        "annual_water_savings_gal": annual_water_savings_gal,
        "budget_compliant": total_cost <= budget_usd,
        "bundle": bundle
    }

if __name__ == '__main__':
    res = solve_bathroom_bundle(10, 8, 10000, "Japanese Zen")
    print("Solver Test Output:")
    print(f"Items Selected: {len(res['bundle'])}")
    print(f"Total Cost: ${res['total_bundle_cost_usd']}")
    print(f"Water Savings: {res['annual_water_savings_gal']} Gal/yr")