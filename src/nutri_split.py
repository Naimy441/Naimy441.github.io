#!/usr/bin/env python3
"""
Script to split nutri_menus.json into individual restaurant files
and create an index.json for easy lookup.
"""

import json
import os
import re
from datetime import datetime

def sanitize_filename(name):
    """Convert restaurant name to a safe filename"""
    # Replace spaces and special characters with underscores
    filename = re.sub(r'[^\w\s-]', '', name)  # Remove special chars except spaces and hyphens
    filename = re.sub(r'[\s-]+', '_', filename)  # Replace spaces and hyphens with underscores
    filename = filename.strip('_').lower()  # Remove leading/trailing underscores and lowercase
    return filename

def split_restaurants():
    """Split the main nutrition file into individual restaurant files"""
    
    # Read the main nutrition file
    input_file = "outputs/nutri_menus.json"
    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found!")
        return
    
    print(f"Reading {input_file}...")
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Create output directory for individual restaurant files
    output_dir = "outputs/restaurants"
    os.makedirs(output_dir, exist_ok=True)
    
    # Index to track all restaurants and their files
    index = {
        "created_at": datetime.now().isoformat(),
        "total_restaurants": len(data.get("restaurants", [])),
        "restaurants": {}
    }
    
    print(f"Processing {len(data.get('restaurants', []))} restaurants...")
    
    for restaurant in data.get("restaurants", []):
        restaurant_name = restaurant.get("name", "Unknown")
        print(f"  Processing: {restaurant_name}")
        
        # Create safe filename
        safe_name = sanitize_filename(restaurant_name)
        filename = f"{safe_name}.json"
        filepath = os.path.join(output_dir, filename)
        
        # Create individual restaurant file
        restaurant_data = {
            "name": restaurant_name,
            "hours": restaurant.get("hours", "Hours not available"),
            "categories": restaurant.get("categories", []),
            "total_items": sum(len(cat.get("meals", [])) for cat in restaurant.get("categories", [])),
            "halal_items": sum(
                len([meal for meal in cat.get("meals", []) if meal.get("is_halal", False)]) 
                for cat in restaurant.get("categories", [])
            ),
            "created_at": datetime.now().isoformat()
        }
        
        # Write individual restaurant file
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(restaurant_data, f, indent=2, ensure_ascii=False)
        
        # Add to index
        index["restaurants"][restaurant_name] = {
            "filename": filename,
            "safe_name": safe_name,
            "hours": restaurant.get("hours", "Hours not available"),
            "total_items": restaurant_data["total_items"],
            "halal_items": restaurant_data["halal_items"],
            "categories_count": len(restaurant.get("categories", []))
        }
    
    # Write index file
    index_file = "outputs/restaurants/index.json"
    with open(index_file, 'w', encoding='utf-8') as f:
        json.dump(index, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Split complete!")
    print(f"   📁 Created {len(index['restaurants'])} restaurant files in {output_dir}/")
    print(f"   📋 Created index file: {index_file}")
    print(f"   📊 Total items across all restaurants: {sum(r['total_items'] for r in index['restaurants'].values())}")
    print(f"   🥗 Total halal items: {sum(r['halal_items'] for r in index['restaurants'].values())}")

def create_summary_stats():
    """Create additional summary statistics"""
    index_file = "outputs/restaurants/index.json"
    
    if not os.path.exists(index_file):
        print("Index file not found. Run split_restaurants() first.")
        return
    
    with open(index_file, 'r', encoding='utf-8') as f:
        index = json.load(f)
    
    restaurants = index["restaurants"]
    
    # Calculate statistics
    stats = {
        "summary": {
            "total_restaurants": len(restaurants),
            "total_items": sum(r["total_items"] for r in restaurants.values()),
            "total_halal_items": sum(r["halal_items"] for r in restaurants.values()),
            "average_items_per_restaurant": round(sum(r["total_items"] for r in restaurants.values()) / len(restaurants), 1),
            "restaurants_with_halal": len([r for r in restaurants.values() if r["halal_items"] > 0])
        },
        "top_restaurants_by_items": sorted(
            [(name, data["total_items"]) for name, data in restaurants.items()],
            key=lambda x: x[1], reverse=True
        )[:10],
        "top_restaurants_by_halal": sorted(
            [(name, data["halal_items"]) for name, data in restaurants.items()],
            key=lambda x: x[1], reverse=True
        )[:10],
        "restaurants_by_category_count": sorted(
            [(name, data["categories_count"]) for name, data in restaurants.items()],
            key=lambda x: x[1], reverse=True
        )[:10]
    }
    
    # Write summary stats
    stats_file = "outputs/restaurants/summary_stats.json"
    with open(stats_file, 'w', encoding='utf-8') as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)
    
    print(f"📈 Summary statistics written to: {stats_file}")
    print(f"   🏪 {stats['summary']['total_restaurants']} restaurants")
    print(f"   🍽️  {stats['summary']['total_items']} total menu items")
    print(f"   🥗 {stats['summary']['total_halal_items']} halal items")
    print(f"   📊 {stats['summary']['average_items_per_restaurant']} average items per restaurant")

if __name__ == "__main__":
    print("🔄 Starting restaurant file splitting...")
    split_restaurants()
    print("\n📊 Generating summary statistics...")
    create_summary_stats()
    print("\n✨ All done!")
