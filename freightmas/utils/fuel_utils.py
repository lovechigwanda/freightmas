import frappe
from frappe import _
from typing import Dict, Any, Optional
from frappe.utils import flt

def calculate_trip_fuel_consumption(trip_name: str) -> Dict[str, Any]:
    """
    Calculate overall fuel consumption (km/l) for the trip
    
    Args:
        trip_name (str): Trip document name
        
    Returns:
        Dict[str, Any]: Contains consumption rates and related data
    """
    try:
        trip = frappe.get_doc("Trip", trip_name)
        
        # Validate trip document
        if not trip:
            return {
                "consumption": 0.0,
                "error": "Trip not found"
            }
            
        # Get truck details and validate
        if not trip.truck:
            return {
                "consumption": 0.0,
                "error": "No truck specified"
            }
            
        truck = frappe.get_doc("Truck", trip.truck)
        if not truck:
            return {
                "consumption": 0.0,
                "error": "Truck not found"
            }
            
        # Calculate total distances
        total_loaded_distance = flt(trip.distance_loaded or 0) + flt(trip.extra_distance_loaded or 0)
        total_empty_distance = flt(trip.distance_empty or 0) + flt(trip.extra_distance_empty or 0)
        total_distance = total_loaded_distance + total_empty_distance
        
        # Get standard consumption rates
        standard_loaded = flt(truck.loaded_fuel_consumption)
        standard_empty = flt(truck.empty_fuel_consumption)
        
        # Calculate weighted standard consumption based on distance ratio
        if total_distance > 0:
            loaded_ratio = total_loaded_distance / total_distance
            empty_ratio = total_empty_distance / total_distance
            weighted_standard = (standard_loaded * loaded_ratio) + (standard_empty * empty_ratio)
        else:
            weighted_standard = 0
            loaded_ratio = 0
            empty_ratio = 0
        
        # Calculate expected fuel separately for loaded and empty
        expected_loaded_fuel = total_loaded_distance / standard_loaded if standard_loaded > 0 else 0
        expected_empty_fuel = total_empty_distance / standard_empty if standard_empty > 0 else 0
        
        # Total expected fuel is sum of both portions
        total_expected_fuel = round(expected_loaded_fuel + expected_empty_fuel, 2)
        
        # Get actual fuel used
        fuel_entries = frappe.get_all(
            "Trip Fuel Allocation",
            filters={
                "parent": trip.name,
                "is_invoiced": 1
            },
            fields=["qty"]
        )
        
        total_fuel = sum(flt(entry.qty) for entry in fuel_entries)
        
        # Calculate variance (negative means better than expected)
        fuel_variance = round(total_fuel - total_expected_fuel, 2)
        
        return {
            "total_distance": total_distance,
            "loaded_ratio": round(loaded_ratio * 100, 1),
            "empty_ratio": round(empty_ratio * 100, 1),
            "expected_fuel": total_expected_fuel,
            "total_fuel": total_fuel,
            "consumption": round(total_distance / total_fuel, 2) if total_fuel > 0 else 0,
            "standard_consumption": round(weighted_standard, 2),
            "fuel_variance": fuel_variance
        }
        
    except Exception as e:
        frappe.log_error(f"Fuel consumption calculation error: {str(e)}")
        return {
            "consumption": 0.0,
            "error": str(e)
        }