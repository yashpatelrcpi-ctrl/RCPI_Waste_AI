"""
Comprehensive AI Knowledge Base for Waste Management
Provides detailed information about waste, categories, recycling, and best practices
"""

WASTE_KNOWLEDGE_BASE = {
    "categories": {
        "organic": {
            "name": "Organic Waste",
            "description": "Biodegradable waste from plants and animals",
            "examples": ["Food waste", "Garden waste", "Paper napkins", "Cardboard", "Plant leaves", "Fruit/vegetable peels"],
            "disposal": "Composting, Biogas generation",
            "time_to_decompose": "2-6 months",
            "environmental_impact": "Can be converted to fertilizer, reduces landfill burden",
            "tips": [
                "Separate food waste before mixing with other waste",
                "Keep organic waste in a separate bin",
                "Compost at home if possible",
                "Avoid contaminating with plastic"
            ]
        },
        "recyclable": {
            "name": "Recyclable Waste",
            "description": "Materials that can be reprocessed into new products",
            "examples": ["Plastic bottles", "Glass bottles", "Aluminum cans", "Paper", "Cardboard", "Newspapers", "Magazines"],
            "disposal": "Recycling centers, Blue bins",
            "time_to_decompose": "Plastic: 450-1000 years, Glass: Never",
            "environmental_impact": "Reduces need for raw materials, saves energy",
            "tips": [
                "Clean containers before recycling",
                "Remove lids and labels",
                "Flatten boxes to save space",
                "Check local recycling guidelines",
                "Don't mix contaminated items"
            ]
        },
        "mixed": {
            "name": "Mixed Waste",
            "description": "Non-separable combination of different waste types",
            "examples": ["Laminated materials", "Composite packaging", "Treated wood", "Old textiles"],
            "disposal": "Landfill, Waste-to-energy facilities",
            "time_to_decompose": "Variable (5-500+ years)",
            "environmental_impact": "Last resort disposal option",
            "tips": [
                "Try to separate before disposing",
                "Reduce mixed waste generation",
                "Choose products with recyclable packaging",
                "Avoid composite materials when possible"
            ]
        },
        "electronic": {
            "name": "Electronic Waste (E-waste)",
            "description": "Discarded electrical or electronic devices",
            "examples": ["Mobile phones", "Computers", "Televisions", "Batteries", "Chargers", "Circuit boards"],
            "disposal": "E-waste recycling centers, Authorized dealers",
            "time_to_decompose": "Never (accumulates in environment)",
            "environmental_impact": "Contains toxic materials, Heavy metals leaching",
            "tips": [
                "Never throw in regular bins",
                "Find certified e-waste recyclers",
                "Data wipe before disposal",
                "Donate working electronics",
                "Keep batteries separate"
            ]
        },
        "construction": {
            "name": "Construction & Demolition Waste",
            "description": "Materials from building and demolition activities",
            "examples": ["Concrete", "Bricks", "Wood", "Metal", "Glass", "Plaster", "Tiles"],
            "disposal": "Construction waste facilities, Recycling centers",
            "time_to_decompose": "Concrete: Never, Wood: 10-15 years",
            "environmental_impact": "Bulk disposal, Some materials recyclable",
            "tips": [
                "Sort by material type",
                "Reuse materials when possible",
                "Find recycling yards",
                "Proper segregation required",
                "Safety precautions needed"
            ]
        },
        "hazardous": {
            "name": "Hazardous Waste",
            "description": "Toxic or dangerous materials requiring special handling",
            "examples": ["Paints", "Chemicals", "Batteries", "Oil", "Pesticides", "Medical waste"],
            "disposal": "Hazardous waste facilities, Special collection",
            "time_to_decompose": "Varies (may never decompose)",
            "environmental_impact": "Severe - Contamination, pollution risk",
            "tips": [
                "Never mix with regular waste",
                "Use proper protective equipment",
                "Contact specialized handlers",
                "Store safely until disposal",
                "Follow regulations strictly"
            ]
        }
    },
    "recycling_process": {
        "collection": "Waste collected from homes and businesses",
        "sorting": "Separating different material types at facilities",
        "processing": "Cleaning, shredding, or granulating materials",
        "manufacturing": "Converting processed materials into new products",
        "distribution": "New products sold in market",
        "consumer": "Using recycled products completes the cycle"
    },
    "benefits": [
        "Reduces landfill waste (saves 1000 kg CO2 per ton recycled)",
        "Saves natural resources (50-75% energy savings)",
        "Creates jobs in recycling industry",
        "Reduces pollution and environmental damage",
        "Saves money on waste disposal",
        "Extends landfill lifespan"
    ],
    "best_practices": [
        "Reduce - Use less stuff",
        "Reuse - Find new uses for items",
        "Recycle - Process materials for new products",
        "Compost - Convert organic waste to soil",
        "Segregate - Separate waste at source",
        "Educate - Spread awareness",
        "Monitor - Track waste generation"
    ]
}

RECYCLING_GUIDELINES = {
    "plastic": {
        "accepted": "PET (1), HDPE (2), LDPE (4), PP (5)",
        "not_accepted": "PVC (3), PS (6), Other (7)",
        "preparation": "Rinse, remove labels, dry completely",
        "items": ["Bottles", "Containers", "Bags", "Cups"]
    },
    "glass": {
        "accepted": "All clear, green, brown glass",
        "not_accepted": "Ceramic, window glass, mirrors, light bulbs",
        "preparation": "Remove caps/lids, rinse thoroughly",
        "items": ["Bottles", "Jars", "Glass containers"]
    },
    "paper": {
        "accepted": "Newspaper, cardboard, magazines, clean paper",
        "not_accepted": "Wax-coated paper, plastic-coated, contaminated",
        "preparation": "Bundle or place in recycling bin",
        "items": ["Newspapers", "Cardboard", "Magazines", "Boxes"]
    },
    "metal": {
        "accepted": "Aluminum, steel cans, tin containers",
        "not_accepted": "Paint cans, aerosol cans (if not empty)",
        "preparation": "Empty completely, rinse, flatten cans",
        "items": ["Cans", "Tins", "Aluminum foil", "Metal containers"]
    }
}

WASTE_REDUCTION_TIPS = {
    "shopping": [
        "Buy in bulk to reduce packaging",
        "Choose products with minimal packaging",
        "Use reusable bags and containers",
        "Avoid single-use items",
        "Buy recycled products"
    ],
    "home": [
        "Start composting organic waste",
        "Repair items instead of replacing",
        "Donate unused items",
        "Use digital alternatives to paper",
        "Buy quality products that last"
    ],
    "daily": [
        "Use reusable water bottles",
        "Carry reusable shopping bags",
        "Use cloth napkins instead of paper",
        "Print double-sided when needed",
        "Unsubscribe from unnecessary mail"
    ]
}

ENVIRONMENTAL_FACTS = {
    "global_waste": "2.12 billion tonnes per year",
    "recycling_rate": "35% globally (target: 75%)",
    "landfill_impact": "Produces methane, a potent greenhouse gas",
    "plastic_pollution": "8 million tonnes enter oceans annually",
    "decomposition": "Plastic bags: 10-20 years, Aluminum: 80-200 years",
    "energy_saved": "Recycling saves 95% energy vs virgin aluminum",
    "job_creation": "1 ton recycled waste creates 1.5 jobs"
}
