"""
Environmental Scoring and Carbon Footprint Module
Calculates ESG scores, carbon emissions, and environmental metrics
"""

from datetime import datetime, timedelta
import sqlite3

from database import get_connection


class CarbonCalculator:
    """Calculate carbon footprint and emissions"""
    
    # Carbon emissions per kg by waste type (kg CO2 equivalent)
    CARBON_FACTORS = {
        'organic': 0.15,  # Less carbon intensive - composting
        'recyclable': 0.50,  # Recycling saves energy
        'electronic': 2.50,  # High carbon for e-waste processing
        'construction': 0.30,  # Medium carbon
        'hazardous': 3.00,  # High carbon for safe disposal
        'mixed': 1.50  # Average
    }
    
    # Waste diversion rates (% that can be diverted from landfill)
    DIVERSION_RATES = {
        'organic': 95,  # Can be composted
        'recyclable': 90,  # Can be recycled
        'electronic': 85,  # Can be refurbished/recycled
        'construction': 75,  # Partial reuse
        'hazardous': 0,  # Must be safely disposed
        'mixed': 30  # Some components recyclable
    }
    
    # Carbon savings per kg (kg CO2 saved vs landfill)
    CARBON_SAVINGS = {
        'organic': 0.50,  # Composting avoids methane
        'recyclable': 1.50,  # Recycling saves production energy
        'electronic': 2.00,  # Refurbishment/recycling
        'construction': 0.75,  # Reuse/recycling
        'hazardous': 0.00,  # No savings
        'mixed': 0.25
    }
    
    @staticmethod
    def calculate_co2_saved(waste_type: str, quantity_kg: float) -> float:
        """Calculate CO2 saved by proper waste management"""
        factor = CarbonCalculator.CARBON_SAVINGS.get(waste_type, 0.5)
        return quantity_kg * factor
    
    @staticmethod
    def calculate_carbon_footprint(waste_type: str, quantity_kg: float) -> float:
        """Calculate carbon footprint of waste processing"""
        factor = CarbonCalculator.CARBON_FACTORS.get(waste_type, 1.0)
        return quantity_kg * factor
    
    @staticmethod
    def estimate_landfill_emission(waste_type: str, quantity_kg: float) -> float:
        """Estimate emissions if sent to landfill"""
        # Landfill emissions are higher
        landfill_factor = 3.0  # kg CO2 per kg waste
        return quantity_kg * landfill_factor
    
    @staticmethod
    def calculate_carbon_credit(co2_saved: float) -> float:
        """Convert CO2 saved to carbon credits (1 credit = 1 tonne CO2)"""
        # Returns carbon credits earned
        return co2_saved / 1000  # Convert kg to tonnes

class EnvironmentalScore:
    """Calculate Environmental (E) score"""
    
    @staticmethod
    def calculate(waste_data: dict) -> float:
        """
        Calculate environmental score (0-100)
        Based on: waste diversion rate, CO2 saved, recycling rate
        """
        total_waste = waste_data.get('total_waste', 0)
        recycled_waste = waste_data.get('recycled_waste', 0)
        organic_waste = waste_data.get('organic_waste', 0)
        
        if total_waste == 0:
            return 50  # Default score
        
        # Diversion rate (40% weight)
        diverted = recycled_waste + organic_waste
        diversion_rate = (diverted / total_waste) * 100
        diversion_score = min(100, (diversion_rate / 100) * 100)  # Max 100
        
        # Waste reduction (30% weight)
        # Compare to baseline (assume 100kg/month per person)
        waste_per_capita = total_waste / (waste_data.get('population', 1) or 1)
        baseline_per_capita = 100
        reduction_score = max(0, 100 - (waste_per_capita / baseline_per_capita) * 100)
        
        # Hazardous waste handling (30% weight)
        hazardous_waste = waste_data.get('hazardous_waste', 0)
        hazard_rate = (hazardous_waste / total_waste * 100) if total_waste > 0 else 0
        hazard_score = max(100 - (hazard_rate * 2), 0)  # Penalize hazardous waste
        
        # Calculate weighted score
        score = (diversion_score * 0.40) + (reduction_score * 0.30) + (hazard_score * 0.30)
        
        return round(score, 2)

class SocialScore:
    """Calculate Social (S) score"""
    
    @staticmethod
    def calculate(compliance_data: dict) -> float:
        """
        Calculate social score (0-100)
        Based on: complaint resolution, community engagement, staff training
        """
        total_complaints = compliance_data.get('total_complaints', 0)
        resolved_complaints = compliance_data.get('resolved_complaints', 0)
        
        if total_complaints == 0:
            resolution_score = 75  # Default
        else:
            resolution_rate = (resolved_complaints / total_complaints) * 100
            resolution_score = min(100, resolution_rate)
        
        # Community engagement (30% weight)
        engagement_events = compliance_data.get('community_events', 0)
        engagement_score = min(100, engagement_events * 10)  # 10 events = 100
        
        # Citizen satisfaction (40% weight - assumed from resolution rate)
        satisfaction_score = resolution_score
        
        # Calculate weighted score
        score = (satisfaction_score * 0.40) + (engagement_score * 0.30) + (resolution_score * 0.30)
        
        return round(score, 2)

class GovernanceScore:
    """Calculate Governance (G) score"""
    
    @staticmethod
    def calculate(governance_data: dict) -> float:
        """
        Calculate governance score (0-100)
        Based on: compliance, transparency, data collection
        """
        # Policy compliance (30% weight)
        policies_implemented = governance_data.get('policies_implemented', 0)
        total_policies = governance_data.get('total_policies', 10)
        compliance_score = (policies_implemented / total_policies) * 100 if total_policies > 0 else 50
        
        # Data transparency (30% weight)
        data_reports_published = governance_data.get('data_reports_published', 0)
        transparency_score = min(100, data_reports_published * 20)  # 5 reports = 100
        
        # System monitoring (40% weight)
        monitoring_active = governance_data.get('monitoring_active', 0)
        monitoring_score = 100 if monitoring_active else 50
        
        # Calculate weighted score
        score = (compliance_score * 0.30) + (transparency_score * 0.30) + (monitoring_score * 0.40)
        
        return round(score, 2)

class ESGReportGenerator:
    """Generate comprehensive ESG reports"""
    
    @staticmethod
    def generate_report(period: str = 'monthly') -> dict:
        """Generate ESG report"""
        try:
            conn = get_connection()
            cursor = conn.cursor()
                      # Get waste collection data
            cursor.execute('''
                SELECT waste_type, SUM(waste_quantity) 
                FROM waste_collection 
                GROUP BY waste_type
            ''')
            waste_by_type = {row[0]: row[1] for row in cursor.fetchall()}
            
            # Get complaint data
            cursor.execute('''
                SELECT COUNT(*), SUM(CASE WHEN status='resolved' THEN 1 ELSE 0 END)
                FROM complaints
            ''')
            complaint_result = cursor.fetchone()
            total_complaints = complaint_result[0] if complaint_result else 0
            resolved_complaints = complaint_result[1] if complaint_result else 0
            
            conn.close()
            
            # Calculate scores
            waste_data = {
                'total_waste': sum(waste_by_type.values()),
                'recycled_waste': waste_by_type.get('recyclable', 0) + waste_by_type.get('organic', 0),
                'organic_waste': waste_by_type.get('organic', 0),
                'hazardous_waste': waste_by_type.get('hazardous', 0),
                'population': 100000  # Placeholder
            }
            
            compliance_data = {
                'total_complaints': total_complaints,
                'resolved_complaints': resolved_complaints,
                'community_events': 5,
            }
            
            governance_data = {
                'policies_implemented': 8,
                'total_policies': 10,
                'data_reports_published': 3,
                'monitoring_active': 1
            }
            
            e_score = EnvironmentalScore.calculate(waste_data)
            s_score = SocialScore.calculate(compliance_data)
            g_score = GovernanceScore.calculate(governance_data)
            
            # Calculate ESG average
            esg_score = (e_score + s_score + g_score) / 3
            
            # Calculate carbon metrics
            total_co2_saved = sum([
                CarbonCalculator.calculate_co2_saved(waste_type, qty)
                for waste_type, qty in waste_by_type.items()
            ])
            
            carbon_credits = CarbonCalculator.calculate_carbon_credit(total_co2_saved)
            carbon_credit_value = carbon_credits * 15  # $15 per carbon credit
            
            report = {
                'period': period,
                'generated_at': datetime.now().isoformat(),
                'environmental_score': e_score,
                'social_score': s_score,
                'governance_score': g_score,
                'esg_score': round(esg_score, 2),
                'waste_data': waste_data,
                'compliance_data': compliance_data,
                'carbon_metrics': {
                    'total_co2_saved_kg': round(total_co2_saved, 2),
                    'carbon_credits_earned': round(carbon_credits, 4),
                    'carbon_credit_value_usd': round(carbon_credit_value, 2),
                    'carbon_footprint_kg': round(waste_data['total_waste'] * 1.5, 2)
                },
                'recommendations': ESGReportGenerator.get_recommendations(e_score, s_score, g_score)
            }
            
            return report
        
        except Exception as e:
            return {'error': str(e)}
    
    @staticmethod
    def get_recommendations(e_score: float, s_score: float, g_score: float) -> list:
        """Generate recommendations based on scores"""
        recommendations = []
        
        if e_score < 60:
            recommendations.append("Increase waste diversion efforts - target 75%+ diversion rate")
        if e_score < 40:
            recommendations.append("Implement comprehensive waste segregation program")
        
        if s_score < 60:
            recommendations.append("Improve community engagement programs")
        if s_score < 40:
            recommendations.append("Establish citizen feedback system and act on complaints")
        
        if g_score < 60:
            recommendations.append("Publish more transparent data reports")
        if g_score < 40:
            recommendations.append("Strengthen data collection and monitoring systems")
        
        if not recommendations:
            recommendations.append("Maintain current ESG performance - all metrics healthy!")
        
        return recommendations
