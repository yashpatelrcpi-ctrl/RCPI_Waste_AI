"""
Advanced AI Engine for Waste Management Queries
Provides intelligent responses based on knowledge base
"""

from ai_knowledge_base import (
    WASTE_KNOWLEDGE_BASE, RECYCLING_GUIDELINES, 
    WASTE_REDUCTION_TIPS, ENVIRONMENTAL_FACTS
)
from waste_category_trainer import (
    categorize_waste, get_category_info, get_disposal_instructions,
    get_identification_help, WASTE_CATEGORY_TRAINING_DATA
)

class WasteAI:
    def __init__(self):
        self.kb = WASTE_KNOWLEDGE_BASE
        self.recycling = RECYCLING_GUIDELINES
        self.reduction = WASTE_REDUCTION_TIPS
        self.facts = ENVIRONMENTAL_FACTS

    def _normalize_query(self, query):
        return (query or "").strip().lower()
    
    def generate_response(self, query):
        """Generate comprehensive AI response based on user query"""
        query_lower = self._normalize_query(query)
        
        # Check for waste identification/categorization first for real-world item questions
        if self._contains_keywords(query_lower, ["what", "category", "type", "classify", "identify", "which bin", "where", "put", "throw", "recycle", "dispose", "bin", "bottle", "plastic", "glass", "metal", "paper", "phone", "computer"]):
            result = self._identify_waste_category(query)
            if result:
                return result
        
        # Check for waste category questions
        if self._contains_keywords(query_lower, ["organic", "food", "plant", "garden", "compost"]):
            return self._handle_organic_waste(query)
        
        elif self._contains_keywords(query_lower, ["recycle", "recyclable", "recycling", "recycled"]):
            return self._handle_recycling(query)
        
        elif self._contains_keywords(query_lower, ["electronic", "e-waste", "phone", "computer", "battery", "charger"]):
            return self._handle_ewaste(query)
        
        elif self._contains_keywords(query_lower, ["plastic", "glass", "metal", "paper", "material"]):
            return self._handle_materials(query)
        
        elif self._contains_keywords(query_lower, ["construction", "demolition", "building", "concrete", "brick"]):
            return self._handle_construction(query)
        
        elif self._contains_keywords(query_lower, ["hazardous", "toxic", "dangerous", "chemical", "paint", "oil"]):
            return self._handle_hazardous(query)
        
        elif self._contains_keywords(query_lower, ["reduce", "reduction", "less", "minimize", "reuse", "repair"]):
            return self._handle_waste_reduction(query)
        
        elif self._contains_keywords(query_lower, ["environment", "impact", "climate", "pollution", "global"]):
            return self._handle_environmental(query)

        elif self._contains_keywords(query_lower, ["carbon", "credit", "co2", "emission", "offset"]):
            return self._handle_carbon_credit(query)
        
        elif self._contains_keywords(query_lower, ["best", "practice", "how", "should", "tips", "help"]):
            return self._handle_best_practices(query)
        
        elif self._contains_keywords(query_lower, ["collection", "schedule", "ward", "vehicle", "driver"]):
            return self._handle_collection(query)
        
        elif self._contains_keywords(query_lower, ["complaint", "issue", "problem", "report"]):
            return self._handle_complaints(query)
        
        else:
            return self._handle_general_query(query)
    
    def _contains_keywords(self, text, keywords):
        """Check if text contains any keywords"""
        return any(keyword in text for keyword in keywords)
    
    def _identify_waste_category(self, query):
        """Identify waste category from user query with detailed practical guidance."""
        query_lower = self._normalize_query(query)
        category, confidence = categorize_waste(query_lower)

        if confidence < 10:
            return None

        category_data = get_category_info(category)
        if not category_data:
            return None

        # Provide a more actionable response for everyday items like bottles, phones, food, etc.
        collection_hint = "Place it in the designated bin for collection day and keep it dry and clean."
        if category == "organic":
            collection_hint = "Put it in the green organics bin or compost it at home if possible."
        elif category == "recyclable":
            collection_hint = "Rinse it, keep it dry, and place it in the blue recycling bin on collection day."
        elif category == "electronic":
            collection_hint = "Do not place it in regular waste; take it to an authorized e-waste collection point."
        elif category == "hazardous":
            collection_hint = "Treat it as special hazardous waste and use a licensed collection service."
        elif category == "construction":
            collection_hint = "Use a construction waste collection service or designated debris site."
        else:
            collection_hint = "Place it in the mixed waste stream only if it cannot be separated safely."

        response = f"""
**WASTE CATEGORY IDENTIFICATION**

**Detected Category:** {category.upper()}
**Confidence Level:** {confidence}%
**Bin Color / Handling:** {category_data['color_code']}

**What this means:**
• {category_data['processing'][0]} is the main handling route.
• This waste should be separated at source to improve collection efficiency.

**Disposal Guidance:**
• {collection_hint}
• Keep the item clean and dry where applicable.
• Avoid mixing with regular waste if a dedicated stream exists.

**Category Details:**
• **Decomposition Time:** {category_data['decomposition_time']}
• **Processing Methods:** {', '.join(category_data['processing'])}
• **Typical Share:** {category_data['percentage']}

**Common Items in This Category:**
"""
        for i, item in enumerate(category_data['items'][:8], 1):
            response += f"\n{i}. {item}"

        response += "\n\n**Recycling / Processing Notes:**\n"
        response += get_disposal_instructions(category)

        response += "\n\n**Quick Identification Tips:**\n"
        response += get_identification_help(category)

        response += "\n\n**Collection Advice:**\n"
        response += "• Put it out on the correct collection day in the correct bin.\n"
        response += "• If the item is bulky or hazardous, arrange a special pickup or visit a designated facility."

        return response
    
    def _handle_organic_waste(self, query):
        organic = self.kb["categories"]["organic"]
        response = f"""
**ORGANIC WASTE MANAGEMENT**

**What is Organic Waste?**
{organic['description']}

**Common Examples:**
• {', '.join(organic['examples'])}

**Best Disposal Methods:**
• {organic['disposal']}
• Home composting for food scraps
• Anaerobic digestion for biogas
• Industrial composting facilities

**Decomposition Time:** {organic['time_to_decompose']}

**Environmental Benefits:**
• {organic['environmental_impact']}
• Can reduce your waste by 30-40%
• Creates nutrient-rich compost

**Practical Tips:**
"""
        for i, tip in enumerate(organic['tips'], 1):
            response += f"\n{i}. {tip}"
        
        response += "\n\n**Did you know?** Composting organic waste reduces methane emissions from landfills by 75%!"
        return response
    
    def _handle_recycling(self, query):
        response = """
**RECYCLING GUIDE**

**Why Recycle?**
"""
        for benefit in self.kb['benefits'][:3]:
            response += f"\n• {benefit}"
        
        response += "\n\n**Recycling Process Steps:**\n"
        for i, (step, description) in enumerate(self.kb['recycling_process'].items(), 1):
            response += f"{i}. **{step.title()}** - {description}\n"
        
        response += "\n**Material Specific Guidelines:**\n"
        for material, guidelines in self.recycling.items():
            response += f"\n**{material.upper()}**\n"
            response += f"• ✅ Accepted: {guidelines['accepted']}\n"
            response += f"• ❌ Not Accepted: {guidelines['not_accepted']}\n"
            response += f"• Preparation: {guidelines['preparation']}\n"
        
        response += "\n**Recycling Saves Resources!** Each ton of recycled aluminum saves 14,000 kWh of electricity!"
        return response
    
    def _handle_ewaste(self, query):
        ewaste = self.kb["categories"]["electronic"]
        response = f"""
**ELECTRONIC WASTE (E-WASTE) MANAGEMENT**

**Why E-waste Matters?**
{ewaste['description']}

**Common E-waste Items:**
• {', '.join(ewaste['examples'])}

**Why Not Trash?**
• Contains toxic materials (lead, mercury, cadmium)
• Damages soil and groundwater
• {ewaste['environmental_impact']}
• Can be harmful to health

**Proper Disposal:**
• Find certified e-waste recycling centers
• Contact authorized electronics dealers
• Check manufacturer take-back programs
• Some retailers offer recycling services

**Important Safety Steps:**
"""
        for i, tip in enumerate(ewaste['tips'], 1):
            response += f"\n{i}. {tip}"
        
        response += "\n\n**NEVER throw electronics in regular trash bins!**"
        return response
    
    def _handle_materials(self, query):
        response = "**MATERIAL-SPECIFIC RECYCLING INSTRUCTIONS**\n"
        
        query_lower = query.lower()
        
        if any(word in query_lower for word in ["plastic"]):
            mat = self.recycling.get("plastic", {})
        elif any(word in query_lower for word in ["glass"]):
            mat = self.recycling.get("glass", {})
        elif any(word in query_lower for word in ["metal", "can", "aluminum"]):
            mat = self.recycling.get("metal", {})
        elif any(word in query_lower for word in ["paper", "cardboard"]):
            mat = self.recycling.get("paper", {})
        else:
            return self._show_all_materials()
        
        for key, value in mat.items():
            response += f"\n**{key.title()}:** {value}"
        
        return response
    
    def _show_all_materials(self):
        response = "**ALL RECYCLING GUIDELINES**\n"
        for material, guidelines in self.recycling.items():
            response += f"\n**{material.upper()}**\n"
            response += f"• {guidelines['accepted']}\n"
        return response
    
    def _handle_construction(self, query):
        construction = self.kb["categories"]["construction"]
        response = f"""
🏗️ **CONSTRUCTION & DEMOLITION WASTE**

**What Includes:**
{construction['description']}

**Common Materials:**
• {', '.join(construction['examples'])}

**Disposal Methods:**
• {construction['disposal']}
• Material recovery facilities
• Authorized recycling centers

**Important Guidelines:**
"""
        for i, tip in enumerate(construction['tips'], 1):
            response += f"\n{i}. {tip}"
        
        response += f"\n\n**Decomposition Timeline:**\n• Concrete: {construction['time_to_decompose'].split(',')[0]}\n• Wood: {construction['time_to_decompose'].split(',')[1]}"
        return response
    
    def _handle_hazardous(self, query):
        hazardous = self.kb["categories"]["hazardous"]
        response = f"""
**HAZARDOUS WASTE ALERT**

**Critical Information:**
{hazardous['description']}

**Common Hazardous Materials:**
• {', '.join(hazardous['examples'])}

**Why It's Dangerous:**
• {hazardous['environmental_impact']}
• Health risks to humans
• Groundwater contamination
• Long-term environmental damage

**Safe Disposal (DO NOT MIX WITH REGULAR WASTE):**
• Find hazardous waste facilities
• Contact environmental agencies
• Use manufacturer disposal services
• Special collection events

**Safety Precautions:**
"""
        for i, tip in enumerate(hazardous['tips'], 1):
            response += f"\n{i}. {tip}"
        
        response += "\n\n🚨 **Improper disposal is illegal and dangerous!**"
        return response
    
    def _handle_waste_reduction(self, query):
        response = "📉 **WASTE REDUCTION STRATEGIES**\n"
        response += "\n**The 3 R's of Sustainability:**\n"
        response += "1. **REDUCE** - Use less stuff\n"
        response += "2. **REUSE** - Find new uses for items\n"
        response += "3. **RECYCLE** - Process materials for new products\n"
        
        response += "\n**Shopping Tips:**\n"
        for tip in self.reduction['shopping']:
            response += f"• {tip}\n"
        
        response += "\n**Home Tips:**\n"
        for tip in self.reduction['home']:
            response += f"• {tip}\n"
        
        response += "\n**Daily Habits:**\n"
        for tip in self.reduction['daily']:
            response += f"• {tip}\n"
        
        response += "\n💪 **Remember:** The most sustainable waste is the waste you don't produce!"
        return response
    
    def _handle_environmental(self, query):
        response = "🌍 **ENVIRONMENTAL IMPACT & FACTS**\n"
        
        response += "\n**Global Waste Statistics:**\n"
        for fact, value in self.facts.items():
            response += f"• **{fact.title()}:** {value}\n"
        
        response += "\n**Climate Impact:**\n"
        response += "• Landfills produce methane (25x more potent than CO2)\n"
        response += "• Waste transportation increases carbon footprint\n"
        response += "• Recycling reduces emissions by 60-75%\n"
        
        response += "\n**Ocean & Marine Life:**\n"
        response += "• Plastic accumulates in ocean gyres\n"
        response += "• Marine animals ingest plastic\n"
        response += "• Microplastics enter food chain\n"
        
        response += "\n**Your Actions Matter!** Every ton recycled saves 1.5 trees!"
        return response
    
    def _handle_carbon_credit(self, query):
        response = "🌿 **CARBON CREDIT & EMISSION REDUCTION GUIDE**\n"
        response += "\n**How carbon credits work:**"
        response += "\n• Recycling and composting reduce methane and landfill emissions."
        response += "\n• Proper waste segregation improves recovery rates and lowers carbon footprint."
        response += "\n• Verified diversion from landfill can earn carbon credits in sustainability programs."
        response += "\n\n**Typical carbon-saving actions:**"
        response += "\n1. Compost organic waste instead of sending it to landfill"
        response += "\n2. Recycle paper, plastic, glass, and metal"
        response += "\n3. Repair and reuse electronics and household items"
        response += "\n4. Reduce single-use packaging"
        response += "\n5. Track waste collection data and improve diversion rates"
        response += "\n\n**Example impact:**"
        response += "\n• 1 tonne of diverted waste can save significant CO2 emissions"
        response += "\n• Better segregation usually increases recycling efficiency"
        response += "\n• Carbon credits reflect verified climate benefits"
        response += "\n\n**For your project:**"
        response += "\n• Use the waste collection records to estimate avoided emissions"
        response += "\n• Track organic diversion, recycling rate, and landfill avoidance"
        response += "\n• Report the results clearly to support sustainability claims"
        return response

    def _handle_best_practices(self, query):
        response = "**BEST PRACTICES FOR WASTE MANAGEMENT**\n"
        response += "\n**Segregation at Source (Most Important):**\n"
        response += "• Organic → Green bin\n"
        response += "• Recyclable → Blue bin\n"
        response += "• Mixed → Gray bin\n"
        response += "• Hazardous → Red bin\n"
        
        response += "\n**Core Principles:**\n"
        for i, principle in enumerate(self.kb['best_practices'], 1):
            response += f"{i}. {principle}\n"
        
        response += "\n**Implementation Steps:**\n"
        response += "• Educate your family/community\n"
        response += "• Set up separate bins\n"
        response += "• Track waste generation\n"
        response += "• Monitor improvements\n"
        response += "• Share success stories\n"
        
        response += "\n✅ **Success Metric:** Aim to reduce waste by 50% within 3 months!"
        return response
    
    def _handle_collection(self, query):
        response = """
🚚 **WASTE COLLECTION INFORMATION**

**Collection Process:**
1. **Segregation** - Separate waste at source into categories
2. **Storage** - Keep in designated bins until collection day
3. **Preparation** - Ensure bins are ready before collection vehicle arrives
4. **Collection** - Our vehicles collect based on ward schedules
5. **Transportation** - Waste transported to processing facilities
6. **Processing** - Materials processed according to type

**Collection Schedule Tips:**
• Check your ward's collection day
• Put bins out the night before
• Ensure proper segregation before collection
• Keep the area clean
• Report missed collections

**Vehicle Information:**
• Modern waste collection vehicles
• Professional trained drivers
• Regular maintenance ensures reliability
• GPS tracking for efficiency

**Contact Your Ward Administrator:**
• For collection schedule details
• To report collection issues
• For special waste arrangements
• To provide feedback
"""
        return response
    
    def _handle_complaints(self, query):
        response = """
📝 **COMPLAINT & ISSUE REPORTING**

**How to File a Complaint:**
1. Go to the Complaints page
2. Provide your contact details
3. Describe the issue clearly
4. Specify waste type involved
5. Include location/ward information
6. Submit the form

**Common Issues:**
• Missed collection
• Improper segregation awareness
• Spillage or littering
• Vehicle maintenance issues
• Collection schedule changes

**Resolution Timeline:**
• Initial review: 24 hours
• Investigation: 3-5 days
• Resolution/Action: 7-10 days

**Follow-up:**
• You'll receive status updates
• Resolution confirmation
• Feedback request for improvement

**For Emergencies:**
• Contact your ward office directly
• Provide immediate situation details
• Request urgent collection/cleanup
"""
        return response
    
    def _handle_general_query(self, query):
        response = f"""
🤖 **WASTE MANAGEMENT AI ASSISTANT**

I can help you with:

✅ **Waste Categorization:**
   • Identify any waste item's category
   • Get disposal instructions
   • Visual identification guides
   • Bin color codes

✅ **Waste Categories:**
   • Organic waste & composting
   • Recyclable materials (plastic, glass, metal, paper)
   • Electronic waste (e-waste)
   • Construction waste
   • Hazardous materials
   • Mixed waste

✅ **Recycling:**
   • Recycling guidelines for each material
   • Preparation tips
   • Recycling process explanation
   • Environmental benefits

✅ **Waste Reduction:**
   • Reduction strategies
   • Shopping tips
   • Daily habits
   • Lifestyle changes

✅ **Environmental Impact:**
   • Climate change effects
   • Ocean pollution
   • Global statistics
   • Conservation facts

✅ **Best Practices:**
   • Waste segregation
   • Implementation steps
   • Community engagement
   • Monitoring progress

✅ **Collection & Services:**
   • Collection schedules
   • Vehicle information
   • Complaint procedures
   • Ward details

**Try asking me:**
• "Where should I put a plastic bottle?"
• "What category is this phone?" 
• "How do I dispose of paint?"
• "Recycle glass bottles how?"
• "Is this hazardous waste?"
• "Classify this item for me"

Your Query: "{query}"

Please ask a specific question about any waste management topic!
"""
        return response

def get_ai_response(query):
    """Main function to get AI response with a safe fallback."""
    try:
        ai = WasteAI()
        response = ai.generate_response(query)
        if not response or not str(response).strip():
            raise ValueError("empty response")
        return response
    except Exception:
        return (
            "I can help with waste classification, recycling guidance, disposal steps, "
            "collection advice, and carbon-credit questions. Please ask about a specific item "
            "or waste type such as a plastic bottle, old phone, or hazardous waste."
        )
