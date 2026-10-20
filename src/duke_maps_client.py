#!/usr/bin/env python3
"""
duke_maps_client.py — DukeMaps GraphQL GIS scraper and catalog generator.

Automates fetching official Duke University campus building footprints and
spatial geometries via the Duke OIT Maps GraphQL API (maps.duke.edu).

Merges official GIS building polygons with high-resolution food stall micro-coordinates,
verified halal notes, operating metadata, and Duke Mobile Order assets.

Exports:
  - dukeislam/data/campus-buildings.json
  - dukeislam/data/campus-dining-venues.json
  - outputs/campus_buildings.geojson
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.error

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(REPO_ROOT, "dukeislam", "data")
OUTPUTS_DIR = os.path.join(REPO_ROOT, "outputs")

GRAPHQL_URL = "https://dm-graphql.api.oit.duke.edu/api"

# Official Duke Campus Buildings Configuration
BUILDINGS_CONFIG = [
    {
        "id": "35",
        "shortName": "Brodhead Center (West Union)",
        "isFocus": True,
        "campus": "West",
        "hasHalal": True,
        "fillColor": "#001A57",       # Signature Duke Navy
        "strokeColor": "#c82d30",     # Duke Red Accent border matching DukeMaps focus=35
        "fillOpacity": 1.0,           # Solid 1.0 to ensure clean vector presentation
        "strokeWidth": 2.5,
    },
    {
        "id": "96",
        "shortName": "Bryan Center",
        "isFocus": False,
        "campus": "West",
        "hasHalal": True,
        "fillColor": "#1D3557",
        "strokeColor": "#001A57",
        "fillOpacity": 1.0,
        "strokeWidth": 2.0,
    },
    {
        "id": "201",
        "shortName": "East Campus Union (Marketplace)",
        "isFocus": False,
        "campus": "East",
        "hasHalal": True,
        "fillColor": "#1D3557",
        "strokeColor": "#001A57",
        "fillOpacity": 1.0,
        "strokeWidth": 2.0,
    },
    {
        "id": "392",
        "shortName": "Perkins Library (The Perk)",
        "isFocus": False,
        "campus": "West",
        "hasHalal": True,
        "fillColor": "#2B4C6F",
        "strokeColor": "#001A57",
        "fillOpacity": 1.0,
        "strokeWidth": 1.5,
    },
    {
        "id": "202",
        "shortName": "Sanford School (Sanford Deli)",
        "isFocus": False,
        "campus": "West",
        "hasHalal": True,
        "fillColor": "#2B4C6F",
        "strokeColor": "#001A57",
        "fillOpacity": 1.0,
        "strokeWidth": 1.5,
    },
    {
        "id": "335",
        "shortName": "Divinity School (Zweli's Cafe)",
        "isFocus": False,
        "campus": "West",
        "hasHalal": False,
        "fillColor": "#4A6FA5",
        "strokeColor": "#001A57",
        "fillOpacity": 0.45,
        "strokeWidth": 1.5,
    },
    {
        "id": "101",
        "shortName": "Hudson Hall Engineering (Twinnie's)",
        "isFocus": False,
        "campus": "West",
        "hasHalal": False,
        "fillColor": "#4A6FA5",
        "strokeColor": "#001A57",
        "fillOpacity": 0.45,
        "strokeWidth": 1.5,
    },
    {
        "id": "330",
        "shortName": "Duke Law (Cafe at Duke Law)",
        "isFocus": False,
        "campus": "West",
        "hasHalal": False,
        "fillColor": "#4A6FA5",
        "strokeColor": "#001A57",
        "fillOpacity": 0.45,
        "strokeWidth": 1.5,
    },
    {
        "id": "184",
        "shortName": "Keohane Quad (Bella Union & Pitchfork's)",
        "isFocus": False,
        "campus": "West",
        "hasHalal": False,
        "fillColor": "#4A6FA5",
        "strokeColor": "#001A57",
        "fillOpacity": 0.45,
        "strokeWidth": 1.5,
    },
    {
        "id": "129",
        "shortName": "Freeman Center for Jewish Life",
        "isFocus": False,
        "campus": "Central",
        "hasHalal": False,
        "fillColor": "#4A6FA5",
        "strokeColor": "#001A57",
        "fillOpacity": 0.45,
        "strokeWidth": 1.5,
    },
    # Surrounding Landmark Buildings for Contextual Duke Campus Feel
    {
        "id": "290",
        "shortName": "Duke Chapel",
        "isFocus": False,
        "campus": "West",
        "isLandmark": True,
        "fillColor": "#8C9BAE",
        "strokeColor": "#5C6B7E",
        "fillOpacity": 0.35,
        "strokeWidth": 1.2,
    },
    {
        "id": "36",
        "shortName": "Page Auditorium",
        "isFocus": False,
        "campus": "West",
        "isLandmark": True,
        "fillColor": "#8C9BAE",
        "strokeColor": "#5C6B7E",
        "fillOpacity": 0.35,
        "strokeWidth": 1.2,
    },
    {
        "id": "331",
        "shortName": "Penn Pavilion",
        "isFocus": False,
        "campus": "West",
        "isLandmark": True,
        "fillColor": "#8C9BAE",
        "strokeColor": "#5C6B7E",
        "fillOpacity": 0.35,
        "strokeWidth": 1.2,
    },
    {
        "id": "327",
        "shortName": "Few Quad",
        "isFocus": False,
        "campus": "West",
        "isLandmark": True,
        "fillColor": "#8C9BAE",
        "strokeColor": "#5C6B7E",
        "fillOpacity": 0.3,
        "strokeWidth": 1.0,
    },
    {
        "id": "325",
        "shortName": "Kilgo Quad",
        "isFocus": False,
        "campus": "West",
        "isLandmark": True,
        "fillColor": "#8C9BAE",
        "strokeColor": "#5C6B7E",
        "fillOpacity": 0.3,
        "strokeWidth": 1.0,
    },
]

# Dining Venues Catalog with Micro-Coordinates & Official Mobile Order Icons
DINING_VENUES = [
    # --- Brodhead Center (Building 35) ---
    {
        "id": "ginger-soy",
        "name": "Ginger + Soy",
        "menuName": "Ginger + Soy",
        "building": "Brodhead Center (West Union)",
        "buildingId": 35,
        "campus": "West",
        "floor": "Main Level (Floor 1)",
        "coordinates": [36.000912, -78.939266],
        "isHalalCertified": True,
        "halalNotes": "Halal certified chicken and beef options (Ginger Chicken, Grilled Teriyaki Chicken). Verify sauces.",
        "cuisine": "Pan-Asian, Noodles & Bowls",
        "mobileOrderId": 170,
        "iconUrl": "/images/mobile-order/icon_restaurant_19_18_129_1585676052860.jpg",
        "googleMapsUrl": "https://maps.google.com/?q=Ginger+%2B+Soy+Duke+University",
        "dukeMapsUrl": "https://maps.duke.edu/?focus=21594-PL",
    },
    {
        "id": "tandoor-indian-cuisine",
        "name": "Tandoor Indian Cuisine",
        "menuName": "Tandoor Indian Cuisine",
        "building": "Brodhead Center (West Union)",
        "buildingId": 35,
        "campus": "West",
        "floor": "Main Level (Floor 1)",
        "coordinates": [36.001080, -78.939580],
        "isHalalCertified": True,
        "halalNotes": "100% Halal certified meats (Chicken Tikka Masala, Chicken Biryani, Beef Vindaloo, Lamb Curry, Chicken 65).",
        "cuisine": "Authentic North & South Indian Curries",
        "mobileOrderId": 965,
        "iconUrl": "/images/mobile-order/icon_location_19_18_129_1610975190893.jpg",
        "googleMapsUrl": "https://maps.google.com/?q=Tandoor+Indian+Cuisine+Duke+University",
        "dukeMapsUrl": "https://maps.duke.edu/?focus=21634-PL",
    },
    {
        "id": "il-forno",
        "name": "Il Forno",
        "menuName": "Il Forno",
        "building": "Brodhead Center (West Union)",
        "buildingId": 35,
        "campus": "West",
        "floor": "Main Level (Floor 1)",
        "coordinates": [36.000679, -78.939423],
        "isHalalCertified": True,
        "halalNotes": "Halal roasted chicken breast available for made-to-order pasta dishes and pizzas.",
        "cuisine": "Wood-Fired Pizza & Made-to-Order Pasta",
        "mobileOrderId": 1410,
        "iconUrl": "/images/mobile-order/icon_location_19_18_127_1701730116543.jpg",
        "googleMapsUrl": "https://maps.google.com/?q=Il+Forno+Duke+University",
        "dukeMapsUrl": "https://maps.duke.edu/?focus=21604-PL",
    },
    {
        "id": "sazon",
        "name": "Sazon",
        "menuName": "Sazon",
        "building": "Brodhead Center (West Union)",
        "buildingId": 35,
        "campus": "West",
        "floor": "Main Level (Floor 1)",
        "coordinates": [36.000550, -78.939480],
        "isHalalCertified": True,
        "halalNotes": "Halal certified Mexican-style shredded and grilled chicken.",
        "cuisine": "Latin & Mexican Burrito Bowls",
        "mobileOrderId": 1409,
        "iconUrl": "/images/mobile-order/icon_location_19_18_127_1701729943321.jpg",
        "googleMapsUrl": "https://maps.google.com/?q=Sazon+Duke+University",
        "dukeMapsUrl": "https://maps.duke.edu/?focus=21626-PL",
    },
    {
        "id": "the-skillet",
        "name": "The Skillet",
        "menuName": "The Skillet",
        "building": "Brodhead Center (West Union)",
        "buildingId": 35,
        "campus": "West",
        "floor": "Main Level (Floor 1)",
        "coordinates": [36.000720, -78.939850],
        "isHalalCertified": True,
        "halalNotes": "Halal Southern fried chicken tenders and grilled chicken breast options.",
        "cuisine": "Southern Comfort Food & Fried Chicken",
        "mobileOrderId": 964,
        "iconUrl": "/images/mobile-order/icon_location_19_18_129_1610975062760.jpg",
        "googleMapsUrl": "https://maps.google.com/?q=The+Skillet+Duke+University",
        "dukeMapsUrl": "https://maps.duke.edu/?focus=21631-PL",
    },
    {
        "id": "the-farmstead",
        "name": "The Farmstead",
        "menuName": "The Farmstead",
        "building": "Brodhead Center (West Union)",
        "buildingId": 35,
        "campus": "West",
        "floor": "Main Level (Floor 1)",
        "coordinates": [36.000750, -78.939200],
        "isHalalCertified": True,
        "halalNotes": "Certified halal grilled chicken breast and organic vegetarian grains.",
        "cuisine": "Farm-to-Fork Salads & Warm Grain Bowls",
        "mobileOrderId": 242,
        "iconUrl": "/images/mobile-order/icon_restaurant_19_18_129_1594924817707.jpg",
        "googleMapsUrl": "https://maps.google.com/?q=The+Farmstead+Duke+University",
        "dukeMapsUrl": "https://maps.duke.edu/?focus=21591-PL",
    },
    {
        "id": "cafe-brodhead",
        "name": "Cafe",
        "menuName": "Cafe",
        "building": "Brodhead Center (West Union)",
        "buildingId": 35,
        "campus": "West",
        "floor": "East Plaza Entrance",
        "coordinates": [36.000450, -78.939350],
        "isHalalCertified": True,
        "halalNotes": "Halal Chicken Parmesan Panini and Crispy Chicken Sandwiches.",
        "cuisine": "Artisan Paninis, Espresso & Grab-and-Go",
        "mobileOrderId": 236,
        "iconUrl": "/images/mobile-order/icon_restaurant_19_18_129_1594924391116.jpg",
        "googleMapsUrl": "https://maps.google.com/?q=Duke+Cafe+Brodhead+Center",
        "dukeMapsUrl": "https://maps.duke.edu/?focus=21588-PL",
    },
    {
        "id": "jbs-roast-chops",
        "name": "J.B.'s Roast & Chops",
        "menuName": "J.B.'s Roast & Chops",
        "building": "Brodhead Center (West Union)",
        "buildingId": 35,
        "campus": "West",
        "floor": "Main Level (Floor 1)",
        "coordinates": [36.000980, -78.939450],
        "isHalalCertified": True,
        "halalNotes": "Halal flame-roasted half chicken with herbs and seasoned sides.",
        "cuisine": "Rotisserie & Carvery",
        "mobileOrderId": 237,
        "iconUrl": "/images/mobile-order/icon_restaurant_19_18_129_1594924426731.jpg",
        "googleMapsUrl": "https://maps.google.com/?q=JBs+Roast+and+Chops+Duke",
        "dukeMapsUrl": "https://maps.duke.edu/?focus=21607-PL",
    },
    {
        "id": "the-chefs-kitchen",
        "name": "The Chef's Kitchen",
        "menuName": "The Chef's Kitchen",
        "building": "Brodhead Center (West Union)",
        "buildingId": 35,
        "campus": "West",
        "floor": "Main Level (Floor 1)",
        "coordinates": [36.000850, -78.939500],
        "isHalalCertified": False,
        "halalNotes": "Rotating culinary station and pop-up teaching kitchen.",
        "cuisine": "Rotating Pop-Up Kitchen",
        "mobileOrderId": 1494,
        "iconUrl": "/images/mobile-order/icon_location_19_18_127_1735832782689.jpg",
        "googleMapsUrl": "https://maps.google.com/?q=Chefs+Kitchen+Duke",
        "dukeMapsUrl": "https://maps.duke.edu/?focus=21590-PL",
    },
    {
        "id": "gyotaku",
        "name": "Gyotaku",
        "menuName": "Gyotaku",
        "building": "Brodhead Center (West Union)",
        "buildingId": 35,
        "campus": "West",
        "floor": "Main Level (Floor 1)",
        "coordinates": [36.000720, -78.939410],
        "isHalalCertified": False,
        "halalNotes": "Sushi, sashimi, poke bowls, and Japanese appetizers. Seafood is halal-friendly.",
        "cuisine": "Sushi, Poke Bowls & Japanese",
        "mobileOrderId": 1032,
        "iconUrl": "/images/mobile-order/icon_location_19_18_129_1632331043265.jpg",
        "googleMapsUrl": "https://maps.google.com/?q=Gyotaku+Duke",
        "dukeMapsUrl": "https://maps.duke.edu/?focus=21597-PL",
    },
    {
        "id": "sprout",
        "name": "Sprout",
        "menuName": "Sprout",
        "building": "Brodhead Center (West Union)",
        "buildingId": 35,
        "campus": "West",
        "floor": "Main Level (Floor 1)",
        "coordinates": [36.000800, -78.939220],
        "isHalalCertified": False,
        "halalNotes": "100% vegetarian and vegan specialty dishes.",
        "cuisine": "Vegetarian & Vegan Specialties",
        "mobileOrderId": 242,
        "iconUrl": "/images/mobile-order/icon_restaurant_19_18_129_1594924817707.jpg",
        "googleMapsUrl": "https://maps.google.com/?q=Sprout+Duke",
        "dukeMapsUrl": "https://maps.duke.edu/?focus=21630-PL",
    },
    {
        "id": "the-devils-krafthouse",
        "name": "The Devil's Krafthouse",
        "menuName": "The Devil's Krafthouse",
        "building": "Brodhead Center (West Union)",
        "buildingId": 35,
        "campus": "West",
        "floor": "Lower Level",
        "coordinates": [36.000550, -78.939750],
        "isHalalCertified": False,
        "halalNotes": "Gastropub serving burgers, flatbreads, and pub fare.",
        "cuisine": "Campus Gastropub & Grill",
        "mobileOrderId": 1031,
        "iconUrl": "/images/mobile-order/icon_location_19_18_129_1632330819887.jpg",
        "googleMapsUrl": "https://maps.google.com/?q=Devils+Krafthouse+Duke",
        "dukeMapsUrl": "https://maps.duke.edu/?focus=21593-PL",
    },

    # --- Bryan Center (Building 96) ---
    {
        "id": "its-thyme",
        "name": "It's Thyme",
        "menuName": "It's Thyme",
        "building": "Bryan Student Center",
        "buildingId": 96,
        "campus": "West",
        "floor": "Plaza Level",
        "coordinates": [36.001180, -78.941050],
        "isHalalCertified": True,
        "halalNotes": "Mediterranean bowls and wraps with certified halal chicken shawarma and falafel.",
        "cuisine": "Mediterranean Bowls, Wraps & Hummus",
        "mobileOrderId": 1459,
        "iconUrl": "/images/mobile-order/icon_location_19_18_127_1704385673480.jpg",
        "googleMapsUrl": "https://maps.google.com/?q=Its+Thyme+Bryan+Center+Duke",
        "dukeMapsUrl": "https://maps.duke.edu/?focus=10014-PL",
    },
    {
        "id": "gothic-grill",
        "name": "Gothic Grill",
        "menuName": "Gothic Grill",
        "building": "Bryan Student Center",
        "buildingId": 96,
        "campus": "West",
        "floor": "Plaza Level",
        "coordinates": [36.000980, -78.941120],
        "isHalalCertified": False,
        "halalNotes": "Classic smash burgers, chicken tenders, crinkle fries, and milkshakes.",
        "cuisine": "American Smashburgers & Shakes",
        "mobileOrderId": 1458,
        "iconUrl": "/images/mobile-order/icon_location_19_18_127_1704385658448.jpg",
        "googleMapsUrl": "https://maps.google.com/?q=Gothic+Grill+Bryan+Center+Duke",
        "dukeMapsUrl": "https://maps.duke.edu/?focus=10013-PL",
    },
    {
        "id": "mcdonalds",
        "name": "McDonald's",
        "menuName": "McDonald's",
        "building": "Bryan Student Center",
        "buildingId": 96,
        "campus": "West",
        "floor": "Lower Level",
        "coordinates": [36.001080, -78.941250],
        "isHalalCertified": False,
        "halalNotes": "Full-service McDonald's on campus accepting Duke Food Points. Meats are not certified halal.",
        "cuisine": "Fast Food & Breakfast",
        "mobileOrderId": 172,
        "iconUrl": "/images/mobile-order/icon_restaurant_19_18_129_1585934781669.jpg",
        "googleMapsUrl": "https://maps.google.com/?q=McDonalds+Bryan+Center+Duke",
        "dukeMapsUrl": "https://maps.duke.edu/?focus=10015-PL",
    },
    {
        "id": "beyu-blue",
        "name": "Beyu Blue Coffee",
        "menuName": "Beyu Blue Coffee",
        "building": "Bryan Student Center",
        "buildingId": 96,
        "campus": "West",
        "floor": "Plaza Level",
        "coordinates": [36.000850, -78.941400],
        "isHalalCertified": False,
        "halalNotes": "Locally owned Durham specialty coffee roaster, pastries, smoothies, and breakfast sandwiches.",
        "cuisine": "Specialty Coffee, Tea & Pastries",
        "mobileOrderId": 232,
        "iconUrl": "/images/mobile-order/icon_restaurant_19_18_129_1594924368372.jpg",
        "googleMapsUrl": "https://maps.google.com/?q=Beyu+Blue+Duke+University",
        "dukeMapsUrl": "https://maps.duke.edu/?focus=10012-PL",
    },

    # --- East Campus (Building 201) ---
    {
        "id": "marketplace",
        "name": "Marketplace",
        "menuName": "Marketplace",
        "building": "East Campus Union",
        "buildingId": 201,
        "campus": "East",
        "floor": "Main Dining Hall",
        "coordinates": [36.007598, -78.913940],
        "isHalalCertified": True,
        "halalNotes": "First-year dining hall with dedicated daily halal protein stations (Chicken Sausage, Rotisserie Meats, Carvery).",
        "cuisine": "All-You-Care-to-Eat Dining Hall",
        "mobileOrderId": None,
        "iconUrl": "/images/mobile-order/icon_restaurant_19_18_129_1594924836000.jpg",
        "googleMapsUrl": "https://maps.google.com/?q=Marketplace+East+Campus+Duke",
        "dukeMapsUrl": "https://maps.duke.edu/?focus=20-PL",
    },
    {
        "id": "trinity-cafe",
        "name": "Trinity Cafe",
        "menuName": "Trinity Cafe",
        "building": "East Campus Union",
        "buildingId": 201,
        "campus": "East",
        "floor": "Lower Level",
        "coordinates": [36.007450, -78.913800],
        "isHalalCertified": False,
        "halalNotes": "East Campus coffeehouse, bagels, fresh bakery items, and late-night snacks.",
        "cuisine": "Coffeehouse, Bagels & Bakery",
        "mobileOrderId": 243,
        "iconUrl": "/images/mobile-order/icon_restaurant_19_18_129_1594924836000.jpg",
        "googleMapsUrl": "https://maps.google.com/?q=Trinity+Cafe+Duke+University",
        "dukeMapsUrl": "https://maps.duke.edu/?focus=21-PL",
    },

    # --- Perkins Library (Building 392) ---
    {
        "id": "saladalia-perk",
        "name": "Saladalia @ The Perk",
        "menuName": "Saladalia @ The Perk",
        "building": "Perkins Library",
        "buildingId": 392,
        "campus": "West",
        "floor": "First Floor",
        "coordinates": [36.002126, -78.938610],
        "isHalalCertified": True,
        "halalNotes": "Halal certified Chicken Shawarma wrap and Moroccan lentil soup.",
        "cuisine": "Mediterranean Cafe, Salads & Coffee",
        "mobileOrderId": 238,
        "iconUrl": "/images/mobile-order/icon_location_19_18_127_1757693875654.jpg",
        "googleMapsUrl": "https://maps.google.com/?q=The+Perk+Saladelia+Perkins+Library+Duke",
        "dukeMapsUrl": "https://maps.duke.edu/?focus=10022-PL",
    },

    # --- Sanford School of Public Policy (Building 202) ---
    {
        "id": "sanford-deli",
        "name": "Sanford Deli",
        "menuName": "Sanford Deli",
        "building": "Sanford School of Public Policy",
        "buildingId": 202,
        "campus": "West",
        "floor": "Ground Level",
        "coordinates": [35.999450, -78.944070],
        "isHalalCertified": True,
        "halalNotes": "Halal Chicken Shawarma, Chicken Arugula Sandwich, and Southwest Chicken Wrap.",
        "cuisine": "Deli Sandwiches, Salads & Soups",
        "mobileOrderId": 1411,
        "iconUrl": "/images/mobile-order/icon_location_19_18_127_1757693875654.jpg",
        "googleMapsUrl": "https://maps.google.com/?q=Sanford+Deli+Duke+University",
        "dukeMapsUrl": "https://maps.duke.edu/?focus=19-PL",
    },

    # --- Divinity School (Building 335) ---
    {
        "id": "zwelis-cafe",
        "name": "Zweli's Cafe at Duke Divinity",
        "menuName": "Zweli's Cafe at Duke Divinity",
        "building": "Divinity School",
        "buildingId": 335,
        "campus": "West",
        "floor": "Ground Refectory",
        "coordinates": [36.001980, -78.939500],
        "isHalalCertified": False,
        "halalNotes": "Afro-fusion cuisine, peri-peri chicken, spiced stews, and fair-trade coffee.",
        "cuisine": "Zimbabwean & Afro-Fusion Cuisine",
        "mobileOrderId": 1493,
        "iconUrl": "/images/mobile-order/icon_location_19_18_127_1662996806081.jpg",
        "googleMapsUrl": "https://maps.google.com/?q=Zwelis+Cafe+Duke+Divinity",
        "dukeMapsUrl": "https://maps.duke.edu/?focus=17-PL",
    },

    # --- Hudson Hall Engineering (Building 101) ---
    {
        "id": "twinnies",
        "name": "Twinnie's",
        "menuName": "Twinnie's",
        "building": "Hudson Hall Engineering",
        "buildingId": 101,
        "campus": "West",
        "floor": "Main Level",
        "coordinates": [36.003319, -78.939754],
        "isHalalCertified": False,
        "halalNotes": "Irish pub-style cafe serving pressed paninis, hot soups, espresso, and craft beverages.",
        "cuisine": "Irish Pub-Style Cafe & Paninis",
        "mobileOrderId": None,
        "iconUrl": "/images/mobile-order/icon_restaurant_19_18_129_1585848973577.jpg",
        "googleMapsUrl": "https://maps.google.com/?q=Twinnies+Duke+University",
        "dukeMapsUrl": "https://maps.duke.edu/?focus=10031-PL",
    },

    # --- Duke Law School (Building 330) ---
    {
        "id": "cafe-duke-law",
        "name": "Cafe at Duke Law",
        "menuName": "Cafe at Duke Law",
        "building": "Duke Law School",
        "buildingId": 330,
        "campus": "West",
        "floor": "Third Floor (Star Commons)",
        "coordinates": [35.999690, -78.945160],
        "isHalalCertified": False,
        "halalNotes": "Made-to-order sandwiches, rotating hot bar dishes, fresh sushi, and espresso.",
        "cuisine": "Sandwiches, Hot Entrees & Espresso",
        "mobileOrderId": 2095,
        "iconUrl": "/images/mobile-order/icon_location_19_18_127_1756835590933.jpg",
        "googleMapsUrl": "https://maps.google.com/?q=Duke+Law+Cafe",
        "dukeMapsUrl": "https://maps.duke.edu/?focus=16-PL",
    },

    # --- Keohane Quad / McClendon Tower (Building 184) ---
    {
        "id": "bella-union",
        "name": "Bella Union",
        "menuName": "Bella Union",
        "building": "Keohane Quad (McClendon Tower)",
        "buildingId": 184,
        "campus": "West",
        "floor": "Lower Level",
        "coordinates": [35.999300, -78.937150],
        "isHalalCertified": False,
        "halalNotes": "Late-night coffee bar, fruit smoothies, local pastries, and Hershey's ice cream.",
        "cuisine": "Late-Night Coffee, Smoothies & Ice Cream",
        "mobileOrderId": 966,
        "iconUrl": "/images/mobile-order/icon_location_19_18_129_1610989976402.jpg",
        "googleMapsUrl": "https://maps.google.com/?q=Bella+Union+Duke",
        "dukeMapsUrl": "https://maps.duke.edu/?focus=15-PL",
    },
    {
        "id": "pitchforks",
        "name": "Pitchfork's",
        "menuName": "Pitchfork's",
        "building": "Keohane Quad (McClendon Tower)",
        "buildingId": 184,
        "campus": "West",
        "floor": "Lower Level",
        "coordinates": [35.999300, -78.937070],
        "isHalalCertified": False,
        "halalNotes": "All-day breakfast diner, grilled tenders, quesadillas, and hearty sides.",
        "cuisine": "24/7 Style Grill & Breakfast",
        "mobileOrderId": 233,
        "iconUrl": "/images/mobile-order/icon_restaurant_19_18_129_1594924756817.jpg",
        "googleMapsUrl": "https://maps.google.com/?q=Pitchforks+Duke",
        "dukeMapsUrl": "https://maps.duke.edu/?focus=18-PL",
    },

    # --- Freeman Center for Jewish Life (Building 129) ---
    {
        "id": "freeman-cafe",
        "name": "Freeman Cafe",
        "menuName": "Freeman Cafe",
        "building": "Freeman Center for Jewish Life",
        "buildingId": 129,
        "campus": "Central",
        "floor": "Main Dining Room",
        "coordinates": [36.000520, -78.922310],
        "isHalalCertified": False,
        "halalNotes": "Certified Kosher dining room serving rotating meat and dairy-free kosher dinners.",
        "cuisine": "Certified Kosher Dining",
        "mobileOrderId": 234,
        "iconUrl": "/images/mobile-order/icon_restaurant_19_18_129_1594924410229.jpg",
        "googleMapsUrl": "https://maps.google.com/?q=Freeman+Center+Duke",
        "dukeMapsUrl": "https://maps.duke.edu/?focus=14-PL",
    },
]

def fetch_building_geometry(loc_id: str):
    """
    Executes GraphQL query to DukeMaps API for a given location ID.
    Returns parsed dictionary containing name, lat, long, and GeoJSON geometry.
    """
    query = """
    query GetLocation($id: String!) {
      location(byId: $id) {
        id
        bldgId
        nameDisplay
        lat
        long
        geojson {
          geometry {
            type
            coordinates
          }
        }
      }
    }
    """
    payload = json.dumps({"query": query, "variables": {"id": loc_id}}).encode("utf-8")
    req = urllib.request.Request(
        GRAPHQL_URL,
        data=payload,
        headers={"Content-Type": "application/json", "User-Agent": "DukeHalalMapScraper/1.0"}
    )
    try:
        with urllib.request.urlopen(req, timeout=12) as res:
            res_data = json.loads(res.read().decode("utf-8"))
            loc = res_data.get("data", {}).get("location")
            if not loc:
                return None
            geom = loc.get("geojson", {}).get("geometry")
            if not geom:
                return None
            raw_coords = geom.get("coordinates")
            if isinstance(raw_coords, str):
                coords = json.loads(raw_coords)
            else:
                coords = raw_coords
            return {
                "id": loc.get("id"),
                "bldgId": loc.get("bldgId"),
                "name": loc.get("nameDisplay"),
                "lat": loc.get("lat"),
                "long": loc.get("long"),
                "geometryType": geom.get("type", "Polygon"),
                "coordinates": coords,
            }
    except Exception as e:
        print(f"Error requesting location {loc_id}: {e}", file=sys.stderr)
        return None

def build_feature_collection(buildings_cfg=BUILDINGS_CONFIG, venues=DINING_VENUES):
    """
    Fetches official GIS polygons for all configured buildings and
    merges them with associated dining venues.
    """
    features = []
    print(f"Querying DukeMaps GraphQL endpoint ({GRAPHQL_URL}) for {len(buildings_cfg)} campus buildings...")
    
    for cfg in buildings_cfg:
        bid = str(cfg["id"])
        data = fetch_building_geometry(bid)
        if not data:
            print(f"  [!] Missing geometry for building {bid} ({cfg['shortName']})")
            continue
        
        matching_venues = [v["id"] for v in venues if str(v.get("buildingId")) == bid]
        coords = data["coordinates"]
        vertex_count = len(coords[0]) if coords and len(coords) > 0 and isinstance(coords[0], list) else 0

        feature = {
            "type": "Feature",
            "id": bid,
            "properties": {
                "id": bid,
                "name": data["name"],
                "shortName": cfg["shortName"],
                "campus": cfg["campus"],
                "isFocus": cfg.get("isFocus", False),
                "isLandmark": cfg.get("isLandmark", False),
                "hasHalal": cfg.get("hasHalal", False),
                "fillColor": cfg["fillColor"],
                "strokeColor": cfg["strokeColor"],
                "fillOpacity": cfg.get("fillOpacity", 1.0),
                "strokeWidth": cfg.get("strokeWidth", 2.0),
                "center": [data["lat"], data["long"]],
                "venueIds": matching_venues,
            },
            "geometry": {
                "type": data["geometryType"],
                "coordinates": coords,
            }
        }
        features.append(feature)
        print(f"  ✓ {cfg['shortName']} (ID: {bid}) — {vertex_count} GIS vertices")

    return {
        "type": "FeatureCollection",
        "features": features
    }

def main():
    parser = argparse.ArgumentParser(
        description="DukeMaps GIS Building Footprint & Dining POI Scraper"
    )
    parser.add_argument(
        "--fetch-all",
        action="store_true",
        default=True,
        help="Fetch official GIS footprints for all Duke dining & landmark buildings (default: True)"
    )
    parser.add_argument(
        "--building-id",
        type=str,
        help="Fetch and inspect a single building by DukeMaps ID (e.g. 35 for Brodhead Center)"
    )
    parser.add_argument(
        "--output-buildings",
        type=str,
        default=os.path.join(DATA_DIR, "campus-buildings.json"),
        help="Path for campus-buildings.json export"
    )
    parser.add_argument(
        "--output-venues",
        type=str,
        default=os.path.join(DATA_DIR, "campus-dining-venues.json"),
        help="Path for campus-dining-venues.json export"
    )
    parser.add_argument(
        "--export-geojson",
        type=str,
        default=os.path.join(OUTPUTS_DIR, "campus_buildings.geojson"),
        help="Secondary path to save raw GeoJSON in outputs/ directory"
    )

    args = parser.parse_args()

    if args.building_id:
        print(f"Fetching building ID {args.building_id} from {GRAPHQL_URL}...")
        res = fetch_building_geometry(args.building_id)
        if res:
            print(json.dumps(res, indent=2))
        else:
            print("Failed to fetch building.")
        return

    # Execute full campus GIS scrape
    geojson_data = build_feature_collection(BUILDINGS_CONFIG, DINING_VENUES)

    # Ensure parent directories exist
    os.makedirs(os.path.dirname(args.output_buildings), exist_ok=True)
    os.makedirs(os.path.dirname(args.output_venues), exist_ok=True)
    os.makedirs(os.path.dirname(args.export_geojson), exist_ok=True)

    # Save campus-buildings.json
    with open(args.output_buildings, "w", encoding="utf-8") as f:
        json.dump(geojson_data, f, indent=2)
    print(f"\nSaved {len(geojson_data['features'])} buildings to {args.output_buildings}")

    # Save outputs/campus_buildings.geojson
    with open(args.export_geojson, "w", encoding="utf-8") as f:
        json.dump(geojson_data, f, indent=2)
    print(f"Saved {len(geojson_data['features'])} buildings to {args.export_geojson}")

    # Save campus-dining-venues.json
    with open(args.output_venues, "w", encoding="utf-8") as f:
        json.dump(DINING_VENUES, f, indent=2)
    print(f"Saved {len(DINING_VENUES)} dining venues to {args.output_venues}")
    print("\nDukeMaps GIS scrape completed successfully.")

if __name__ == "__main__":
    main()
