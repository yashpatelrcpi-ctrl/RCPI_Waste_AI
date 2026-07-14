"""
Carbon Prediction AI Model
Predicts future carbon emissions and environmental impact based on historical data
"""

import sqlite3
from datetime import datetime, timedelta
import math
from typing import Tuple, List, Dict
from database import get_connection

class CarbonPredictionModel:
    """AI model for carbon emission prediction"""
    
    @staticmethod
    def get_historical_waste_data(days: int = 90) -> Dict[str, List[Tuple[str, float]]]:
        """Get historical waste data for analysis"""
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            start_date = datetime.now() - timedelta(days=days)
            
            cursor.execute('''
                SELECT DATE(collection_date) as date, waste_type, SUM(waste_quantity)
                FROM waste_collection
                WHERE collection_date > ?
                GROUP BY DATE(collection_date), waste_type
                ORDER BY DATE(collection_date)
            ''', (start_date,))
            
            data = {}
            for row in cursor.fetchall():
                date, waste_type, quantity = row
                if waste_type not in data:
                    data[waste_type] = []
                data[waste_type].append((date, quantity or 0))
            
            conn.close()
            return data
        
        except Exception as e:
            return {}
    
    @staticmethod
    def calculate_trend(data: List[float]) -> Tuple[float, float]:
        """Calculate linear regression trend (slope, intercept)"""
        if len(data) < 2:
            return 0, 0
        
        n = len(data)
        x_vals = list(range(n))
        
        # Calculate means
        x_mean = sum(x_vals) / n
        y_mean = sum(data) / n
        
        # Calculate slope
        numerator = sum((x_vals[i] - x_mean) * (data[i] - y_mean) for i in range(n))
        denominator = sum((x - x_mean) ** 2 for x in x_vals)
        
        if denominator == 0:
            slope = 0
        else:
            slope = numerator / denominator
        
        # Calculate intercept
        intercept = y_mean - slope * x_mean
        
        return slope, intercept
    
    @staticmethod
    def predict_waste(waste_type: str, days_ahead: int = 30) -> List[Tuple[str, float]]:
        """Predict future waste quantity for a specific type"""
        data = CarbonPredictionModel.get_historical_waste_data(days=90)
        
        if waste_type not in data:
            return []
        
        quantities = [q for _, q in data[waste_type]]
        
        # Calculate trend
        slope, intercept = CarbonPredictionModel.calculate_trend(quantities)
        
        # Generate predictions
        predictions = []
        start_day = len(quantities)
        
        for day in range(start_day, start_day + days_ahead):
            predicted_qty = intercept + slope * day
            predicted_qty = max(0, predicted_qty)  # No negative waste
            
            date = (datetime.now() + timedelta(days=day-start_day+1)).strftime("%Y-%m-%d")
            predictions.append((date, predicted_qty))
        
        return predictions
    
    @staticmethod
    def predict_carbon_emissions(days_ahead: int = 30) -> Dict:
        """Predict total carbon emissions for future period"""
        
        carbon_factors = {
            'organic': 0.15,
            'recyclable': 0.50,
            'electronic': 2.50,
            'construction': 0.30,
            'hazardous': 3.00,
            'mixed': 1.50
        }
        
        try:
            # Get predictions for each waste type
            waste_types = list(carbon_factors.keys())
            all_predictions = {}
            total_waste_predicted = 0
            total_carbon_predicted = 0
            
            for waste_type in waste_types:
                predictions = CarbonPredictionModel.predict_waste(waste_type, days_ahead)
                
                if predictions:
                    all_predictions[waste_type] = predictions
                    total_waste = sum(qty for _, qty in predictions)
                    carbon = total_waste * carbon_factors[waste_type]
                    
                    total_waste_predicted += total_waste
                    total_carbon_predicted += carbon
            
            return {
                'period_days': days_ahead,
                'start_date': datetime.now().strftime("%Y-%m-%d"),
                'end_date': (datetime.now() + timedelta(days=days_ahead)).strftime("%Y-%m-%d"),
                'predictions_by_type': all_predictions,
                'total_waste_predicted_kg': round(total_waste_predicted, 2),
                'total_carbon_predicted_kg': round(total_carbon_predicted, 2),
                'daily_average_waste_kg': round(total_waste_predicted / max(days_ahead, 1), 2),
                'daily_average_carbon_kg': round(total_carbon_predicted / max(days_ahead, 1), 2),
            }
        
        except Exception as e:
            return {'error': str(e)}
    
    @staticmethod
    def predict_carbon_footprint_per_citizen(population: int = 100000, 
                                            days_ahead: int = 30) -> Dict:
        """Predict per capita carbon footprint"""
        try:
            emissions = CarbonPredictionModel.predict_carbon_emissions(days_ahead)
            
            if 'error' in emissions:
                return emissions
            
            total_carbon = emissions['total_carbon_predicted_kg']
            per_capita_carbon = total_carbon / population if population > 0 else 0
            
            # Sustainability benchmarks
            target_per_capita = 50  # kg CO2 per person per month
            
            return {
                'prediction_period': f"{days_ahead} days",
                'total_predicted_carbon_kg': total_carbon,
                'population': population,
                'per_capita_carbon_kg': round(per_capita_carbon, 2),
                'per_capita_daily_kg': round(per_capita_carbon / max(days_ahead, 1), 3),
                'sustainability_target_kg': target_per_capita,
                'target_met': per_capita_carbon <= target_per_capita,
                'variance_percent': round(((per_capita_carbon - target_per_capita) / target_per_capita * 100), 2),
                'status': 'On Track ✅' if per_capita_carbon <= target_per_capita else 'Above Target ⚠️'
            }
        
        except Exception as e:
            return {'error': str(e)}
    
    @staticmethod
    def predict_co2_savings_potential(days_ahead: int = 30) -> Dict:
        """Predict potential CO2 savings with improved practices"""
        
        # Savings if we improve diversion rates
        improvement_scenarios = {
            'baseline': {
                'description': 'Current practices',
                'organic_diversion': 50,  # 50% of organic waste diverted
                'recyclable_diversion': 60,  # 60% of recyclable diverted
            },
            'optimistic': {
                'description': 'With improvements (80% diversion)',
                'organic_diversion': 95,
                'recyclable_diversion': 85,
            },
            'best_case': {
                'description': 'Best practices (95% diversion)',
                'organic_diversion': 98,
                'recyclable_diversion': 95,
            }
        }
        
        try:
            current_emissions = CarbonPredictionModel.predict_carbon_emissions(days_ahead)
            
            if 'error' in current_emissions:
                return current_emissions
            
            scenarios = {}
            
            for scenario_name, scenario_data in improvement_scenarios.items():
                # Calculate savings for this scenario
                # (This is simplified - in production would be more detailed)
                multiplier = 1.0
                
                if scenario_name == 'optimistic':
                    multiplier = 0.7  # 30% carbon reduction
                elif scenario_name == 'best_case':
                    multiplier = 0.5  # 50% carbon reduction
                
                savings_carbon = current_emissions['total_carbon_predicted_kg'] * (1 - multiplier)
                
                scenarios[scenario_name] = {
                    'description': scenario_data['description'],
                    'predicted_carbon_kg': current_emissions['total_carbon_predicted_kg'] * multiplier,
                    'carbon_savings_kg': round(savings_carbon, 2),
                    'carbon_savings_percent': round((1 - multiplier) * 100, 1)
                }
            
            return {
                'period_days': days_ahead,
                'scenarios': scenarios,
                'recommendation': 'Increase organic waste composting and recyclables collection to maximize carbon savings'
            }
        
        except Exception as e:
            return {'error': str(e)}
    
    @staticmethod
    def predict_monthly_trend(months_ahead: int = 6) -> Dict:
        """Predict monthly carbon emissions trend"""
        try:
            historical_data = CarbonPredictionModel.get_historical_waste_data(days=180)
            
            # Get daily totals
            daily_totals = {}
            for waste_type, data_list in historical_data.items():
                for date, quantity in data_list:
                    if date not in daily_totals:
                        daily_totals[date] = 0
                    daily_totals[date] += quantity
            
            # Group by month and calculate averages
            monthly_data = {}
            for date_str, total in daily_totals.items():
                month_key = date_str[:7]  # YYYY-MM
                if month_key not in monthly_data:
                    monthly_data[month_key] = []
                monthly_data[month_key].append(total)
            
            # Calculate monthly averages
            monthly_avg = {month: sum(vals) / len(vals) for month, vals in monthly_data.items()}
            
            # Get trend
            sorted_months = sorted(monthly_avg.keys())
            if len(sorted_months) > 1:
                values = [monthly_avg[m] for m in sorted_months]
                slope, intercept = CarbonPredictionModel.calculate_trend(values)
            else:
                slope = 0
                intercept = list(monthly_avg.values())[0] if monthly_avg else 0
            
            # Make predictions
            predictions = []
            start_month = len(sorted_months)
            
            for month_offset in range(months_ahead):
                predicted_waste = intercept + slope * (start_month + month_offset)
                predicted_waste = max(0, predicted_waste)
                
                future_date = (datetime.now() + timedelta(days=30 * (month_offset + 1)))
                month_str = future_date.strftime("%Y-%m")
                
                # Carbon calculation
                predicted_carbon = predicted_waste * 1.5  # Average carbon factor
                
                predictions.append({
                    'month': month_str,
                    'predicted_waste_kg': round(predicted_waste, 0),
                    'predicted_carbon_kg': round(predicted_carbon, 0)
                })
            
            return {
                'historical_trend': 'Increasing' if slope > 0 else 'Decreasing',
                'trend_slope': round(slope, 2),
                'monthly_predictions': predictions
            }
        
        except Exception as e:
            return {'error': str(e)}
