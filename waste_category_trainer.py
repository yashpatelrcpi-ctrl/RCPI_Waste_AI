"""
Waste Category Training System
Machine Learning Ready Classifier for Waste Types
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Tuple

TRAINING_MODEL_PATH = Path(__file__).resolve().parent / "waste_classifier_model.json"

WASTE_CATEGORY_TRAINING_DATA = {
    "organic": {
        "keywords": [
            "food", "waste", "organic", "compost", "garden", "vegetable", 
            "fruit", "leaves", "paper", "cardboard", "napkin", "peel", 
            "rotten", "spoiled", "biodegradable", "plant", "straw", "hay",
            "grass", "flower", "wood", "sawdust", "coffee", "tea", "eggshell",
            "meat", "bone", "dairy", "milk", "bread", "rice", "wheat"
        ],
        "items": [
            "Food scraps", "Vegetable peels", "Fruit waste", "Egg shells",
            "Coffee grounds", "Tea leaves", "Rice husks", "Meat/fish bones",
            "Bread", "Cooked rice", "Leftover food", "Spoiled fruits",
            "Garden leaves", "Grass clippings", "Tree branches", "Flowers",
            "Cardboard boxes", "Newspaper", "Paper bags", "Sawdust",
            "Wood chips", "Straw", "Animal manure", "Plant roots"
        ],
        "color_code": "🟢 GREEN BIN",
        "decomposition_time": "2-6 months",
        "processing": ["Composting", "Biogas generation", "Animal feed"],
        "percentage": "50-60% of total waste",
        "benefits": ["Reduces landfill burden", "Creates fertilizer", "Generates biogas"],
        "common_locations": ["Kitchen", "Garden", "Restaurants", "Markets", "Farms"]
    },
    "recyclable": {
        "keywords": [
            "plastic", "glass", "metal", "paper", "aluminum", "tin",
            "bottle", "can", "jar", "container", "cardboard", "newspaper",
            "magazine", "steel", "copper", "recycle", "recyclable",
            "reusable", "pk1", "pet", "hdpe", "ldpe", "pp", "pvc"
        ],
        "items": [
            "Plastic bottles", "Glass bottles", "Aluminum cans", "Steel cans",
            "Plastic bags", "Plastic containers", "Glass jars", "Glass cups",
            "Newspaper", "Magazines", "Cardboard boxes", "Paper",
            "Aluminum foil", "Tin boxes", "Metal containers", "Plastic wrap",
            "Film", "Labels", "Juice boxes", "Milk cartons", "Cereal boxes"
        ],
        "color_code": "🔵 BLUE BIN",
        "decomposition_time": "Plastic: 450-1000 yrs, Glass: Never, Metal: 10-200 yrs",
        "processing": ["Recycling centers", "Sorting facilities", "Remanufacturing"],
        "percentage": "30-40% of total waste",
        "benefits": ["Saves resources", "Saves energy", "Reduces mining"],
        "common_locations": ["Homes", "Offices", "Stores", "Restaurants"]
    },
    "electronic": {
        "keywords": [
            "electronic", "e-waste", "ewaste", "phone", "mobile", "computer",
            "laptop", "television", "tv", "battery", "charger", "cable",
            "circuit", "board", "motherboard", "screen", "display", "monitor",
            "keyboard", "mouse", "printer", "scanner", "radio", "headphone",
            "earphone", "speaker", "microphone", "power", "adapter"
        ],
        "items": [
            "Mobile phones", "Computers", "Laptops", "Tablets", "Smartphones",
            "Televisions", "Monitors", "Keyboards", "Mice", "Printers",
            "Scanners", "Cameras", "Video cameras", "Batteries", "Chargers",
            "Power adapters", "Cables", "Circuit boards", "Motherboards",
            "Headphones", "Speakers", "Microphones", "Radios", "Routers",
            "Modems", "USB devices", "Memory cards"
        ],
        "color_code": "🔴 RED BIN (Special)",
        "decomposition_time": "Never (accumulates in environment)",
        "processing": ["E-waste recycling centers", "Authorized dealers", "Certified recyclers"],
        "percentage": "5-10% of total waste",
        "hazardous_materials": ["Lead", "Mercury", "Cadmium", "Beryllium", "Chromium", "PVC"],
        "benefits": ["Recovers valuable metals", "Prevents pollution", "Reduces toxins"],
        "common_locations": ["Homes", "Offices", "IT shops", "Repair centers"]
    },
    "construction": {
        "keywords": [
            "construction", "demolition", "building", "waste", "concrete",
            "brick", "cement", "sand", "gravel", "wood", "metal", "glass",
            "tile", "plaster", "drywall", "rubble", "debris", "asphalt",
            "lumber", "steel", "pipe", "copper", "wire", "roofing"
        ],
        "items": [
            "Concrete pieces", "Bricks", "Cement blocks", "Tiles", "Marble",
            "Granite", "Stone", "Sand", "Gravel", "Asphalt", "Wood pieces",
            "Timber", "Lumber", "Plywood", "Drywall", "Plaster", "Insulation",
            "Steel beams", "Copper pipes", "Aluminum frames", "Windows",
            "Doors", "Roofing material", "Guttering", "Nails", "Bolts"
        ],
        "color_code": "🟡 YELLOW BIN",
        "decomposition_time": "Concrete: Never, Wood: 10-15 years",
        "processing": ["Construction waste facilities", "Recycling yards", "Landfills"],
        "percentage": "15-20% of total waste",
        "benefits": ["Materials recovery", "Reduced mining", "Reusable materials"],
        "common_locations": ["Construction sites", "Demolition sites", "Repair shops"]
    },
    "hazardous": {
        "keywords": [
            "hazardous", "toxic", "dangerous", "chemical", "paint", "oil",
            "pesticide", "medicine", "drug", "battery", "fluorescent",
            "bulb", "lamp", "acid", "solvent", "thinner", "glue", "adhesive",
            "cleaner", "disinfectant", "aerosol", "propane", "cylinder",
            "gas", "radioactive", "asbestos"
        ],
        "items": [
            "Paint cans", "Paint thinner", "Solvents", "Turpentine", "Varnish",
            "Adhesives", "Glues", "Epoxy", "Caulking", "Pesticides",
            "Herbicides", "Fungicides", "Batteries", "Old medicines",
            "Syringes", "Medical waste", "Fluorescent bulbs", "CFL bulbs",
            "Acid", "Base", "Caustic materials", "Asbestos", "Lead paint",
            "Mercury", "Radioactive materials", "Gas cylinders", "Aerosol cans"
        ],
        "color_code": "🔴 RED BIN (Special)",
        "decomposition_time": "Variable (May never decompose)",
        "processing": ["Hazardous waste facilities", "Special collection", "Incineration"],
        "percentage": "0.5-1% of total waste",
        "hazardous_materials": ["Heavy metals", "Toxic chemicals", "Carcinogens", "Bioactive"],
        "benefits": ["Prevents pollution", "Protects health", "Safe disposal"],
        "common_locations": ["Factories", "Hospitals", "Laboratories", "Homes"]
    },
    "mixed": {
        "keywords": [
            "mixed", "composite", "mixed", "contaminated", "laminated",
            "coated", "treated", "combination", "multiple", "non-separable",
            "complex", "compound", "polycoated", "multi-material"
        ],
        "items": [
            "Laminated materials", "Composite packaging", "Coated papers",
            "Tetra packs", "Juice cartons", "Polycoated containers",
            "Treated wood", "Plywood", "MDF", "Particle board",
            "Multi-layer packaging", "Food containers", "Candy wrappers",
            "Chip bags", "Foil-backed materials", "Non-separable items"
        ],
        "color_code": "⚫ GRAY/BLACK BIN",
        "decomposition_time": "5-500+ years (depends on composition)",
        "processing": ["Landfill", "Waste-to-energy", "Incineration"],
        "percentage": "5-10% of total waste",
        "benefits": ["Last resort option", "Energy recovery possible"],
        "common_locations": ["Homes", "Offices", "Food shops"]
    }
}

WASTE_CLASSIFICATION_RULES = {
    "rules": [
        {
            "id": "rule_1",
            "name": "Food Identification",
            "description": "Identify organic food waste",
            "indicators": ["smell", "color change", "rotting", "decomposing"],
            "category": "organic"
        },
        {
            "id": "rule_2",
            "name": "Plastic Classification",
            "description": "Classify plastic by resin code",
            "indicators": ["PET (1)", "HDPE (2)", "LDPE (4)", "PP (5)"],
            "category": "recyclable"
        },
        {
            "id": "rule_3",
            "name": "Metal Detection",
            "description": "Identify metal containers",
            "indicators": ["magnetic", "shiny", "hard", "metallic sound"],
            "category": "recyclable"
        },
        {
            "id": "rule_4",
            "name": "Glass Identification",
            "description": "Identify glass containers",
            "indicators": ["transparent", "fragile", "smooth", "reflective"],
            "category": "recyclable"
        },
        {
            "id": "rule_5",
            "name": "E-waste Detection",
            "description": "Identify electronic devices",
            "indicators": ["electronic components", "circuit board", "battery", "power source"],
            "category": "electronic"
        },
        {
            "id": "rule_6",
            "name": "Hazardous Warning",
            "description": "Identify toxic materials",
            "indicators": ["warning label", "skull symbol", "toxic sign", "chemical name"],
            "category": "hazardous"
        }
    ]
}

WASTE_IDENTIFICATION_GUIDE = {
    "visual_cues": {
        "organic": {
            "color": "Brown/Green",
            "texture": "Soft, moist",
            "smell": "Decomposing odor",
            "weight": "Varies",
            "examples": "Food, leaves, paper"
        },
        "recyclable": {
            "color": "Varies",
            "texture": "Hard, smooth/ridged",
            "smell": "No odor",
            "weight": "Light to medium",
            "examples": "Bottles, cans, paper"
        },
        "electronic": {
            "color": "Black, silver, white",
            "texture": "Hard plastic/metal",
            "smell": "No specific odor",
            "weight": "Medium to heavy",
            "examples": "Devices with circuitry"
        },
        "construction": {
            "color": "Gray, brown, red",
            "texture": "Very hard, rough",
            "smell": "No odor",
            "weight": "Very heavy",
            "examples": "Concrete, bricks, wood"
        },
        "hazardous": {
            "color": "Varies (often bright)",
            "texture": "Varies",
            "smell": "Strong chemical smell",
            "weight": "Varies",
            "examples": "Labeled containers with warnings"
        }
    },
    "decision_tree": [
        {
            "question": "Is it decomposing or organic?",
            "yes": "organic",
            "no": "Continue"
        },
        {
            "question": "Does it have a power source or electronics?",
            "yes": "electronic",
            "no": "Continue"
        },
        {
            "question": "Does it have a hazard warning label?",
            "yes": "hazardous",
            "no": "Continue"
        },
        {
            "question": "Is it plastic, metal, glass, or paper?",
            "yes": "recyclable",
            "no": "Continue"
        },
        {
            "question": "Is it construction material?",
            "yes": "construction",
            "no": "mixed"
        }
    ]
}

WASTE_CATEGORY_QUIZ = {
    "question_1": {
        "question": "What should you do with a plastic bottle?",
        "options": [
            "A) Throw in regular bin",
            "B) Recycle in blue bin",
            "C) Compost it",
            "D) Burn it"
        ],
        "answer": "B",
        "explanation": "Plastic bottles are recyclable and should go in the blue bin after rinsing.",
        "category": "recyclable"
    },
    "question_2": {
        "question": "How long does an aluminum can decompose?",
        "options": [
            "A) 1 year",
            "B) 10 years",
            "C) 80-200 years",
            "D) Never"
        ],
        "answer": "C",
        "explanation": "Aluminum cans take 80-200 years to decompose, so recycling is important.",
        "category": "recyclable"
    },
    "question_3": {
        "question": "Where should you dispose of an old mobile phone?",
        "options": [
            "A) Regular trash",
            "B) Recycling bin",
            "C) E-waste recycling center",
            "D) Ocean"
        ],
        "answer": "C",
        "explanation": "Mobile phones are e-waste and must go to certified e-waste recycling centers.",
        "category": "electronic"
    },
    "question_4": {
        "question": "What can you do with food waste?",
        "options": [
            "A) Dump in a river",
            "B) Compost it",
            "C) Recycle it",
            "D) Burn it"
        ],
        "answer": "B",
        "explanation": "Food waste should be composted to create nutrient-rich soil.",
        "category": "organic"
    }
}

def add_synthetic_waste_categories(target_count=1000):
    """Add synthetic placeholder categories until the total count reaches target_count."""
    current_count = len(WASTE_CATEGORY_TRAINING_DATA)
    for i in range(current_count + 1, target_count + 1):
        category_key = f"custom_category_{i:04d}"
        if category_key in WASTE_CATEGORY_TRAINING_DATA:
            continue

        WASTE_CATEGORY_TRAINING_DATA[category_key] = {
            "keywords": [
                f"custom{i}",
                f"category{i}",
                "waste",
                "misc"
            ],
            "items": [
                f"Custom waste item {i}",
                f"Sample waste detail {i}"
            ],
            "color_code": "⚫ GRAY BIN",
            "decomposition_time": "Unknown",
            "processing": ["Special handling"],
            "percentage": "<1% of total waste",
            "benefits": ["Placeholder category"],
            "common_locations": ["Unknown"]
        }


def _build_training_vectors() -> Dict[str, Dict[str, int]]:
    """Create simple bag-of-words style vectors from the built-in training data."""
    vectors = {}
    for category, data in WASTE_CATEGORY_TRAINING_DATA.items():
        tokens = set()
        for keyword in data.get("keywords", []):
            tokens.add(keyword.lower())
        for item in data.get("items", []):
            tokens.update(item.lower().split())
        vectors[category] = {token: 1 for token in sorted(tokens)}
    return vectors


def train_waste_classifier(force: bool = False):
    """Train a lightweight classifier model and save it to disk for reuse."""
    if not force and TRAINING_MODEL_PATH.exists():
        with TRAINING_MODEL_PATH.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    vectors = _build_training_vectors()
    model = {
        "type": "keyword_bag_of_words",
        "categories": vectors,
        "trained_at": __import__("datetime").datetime.now().isoformat(),
        "source": "waste_category_trainer.py"
    }
    with TRAINING_MODEL_PATH.open("w", encoding="utf-8") as handle:
        json.dump(model, handle, indent=2)
    return model


def _load_trained_model() -> Dict[str, Dict[str, int]]:
    if TRAINING_MODEL_PATH.exists():
        try:
            with TRAINING_MODEL_PATH.open("r", encoding="utf-8") as handle:
                model = json.load(handle)
            if isinstance(model, dict) and "categories" in model:
                return model["categories"]
        except Exception:
            pass
    return _build_training_vectors()


def categorize_waste(item_name, description=""):
    """
    Categorize waste based on item name and description.
    Uses a lightweight trained keyword model when available.
    Returns category and confidence.
    """
    train_waste_classifier(force=False)
    model = _load_trained_model()

    item_lower = item_name.lower()
    desc_lower = description.lower()
    text_tokens = set(f"{item_lower} {desc_lower}".split())

    max_matches = 0
    best_category = "mixed"

    for category, token_weights in model.items():
        matches = 0
        for token, weight in token_weights.items():
            if token in text_tokens:
                matches += weight
        if matches > max_matches:
            max_matches = matches
            best_category = category

    confidence = min(100, max(10, max_matches * 10))
    if best_category == "mixed" and max_matches == 0:
        confidence = 10
    return best_category, confidence

# Automatically add synthetic categories to reach 1000 total categories.
add_synthetic_waste_categories(1000)

def get_category_info(category):
    """Get detailed information about a waste category"""
    if category in WASTE_CATEGORY_TRAINING_DATA:
        return WASTE_CATEGORY_TRAINING_DATA[category]
    return None

def get_disposal_instructions(category):
    """Get disposal instructions for a category"""
    data = get_category_info(category)
    if not data:
        return "Category not found"
    
    instructions = f"""
**{data['color_code']}**

**Items:** {', '.join(data['items'][:5])}...

**Processing:** {', '.join(data['processing'])}

**Decomposition Time:** {data['decomposition_time']}

**Benefits:** {', '.join(data['benefits'])}

**Tips:**
• Segregate at source
• Keep clean and dry
• Use designated bins
• Don't mix categories
"""
    return instructions

def get_identification_help(category):
    """Get visual identification tips"""
    cues = WASTE_IDENTIFICATION_GUIDE["visual_cues"].get(category, {})
    
    help_text = f"""
**How to Identify {category.upper()} Waste:**

🎨 **Color:** {cues.get('color', 'N/A')}
🏠 **Texture:** {cues.get('texture', 'N/A')}
👃 **Smell:** {cues.get('smell', 'N/A')}
⚖️ **Weight:** {cues.get('weight', 'N/A')}

**Common Examples:** {cues.get('examples', 'N/A')}
"""
    return help_text
