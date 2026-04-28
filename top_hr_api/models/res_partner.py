# -*- coding: utf-8 -*-

from odoo import models, fields, api
import math


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # Geolocation Accuracy Distance field
    geolocation_accuracy_distance = fields.Float(
        string='Geolocation Accuracy Distance',
        help='Distance in meters indicating the accuracy of the geolocation coordinates',
        digits=(10, 2)
    )

    @api.depends('partner_latitude', 'partner_longitude')
    def _compute_geolocation_accuracy_distance(self):
        """
        Compute geolocation accuracy distance based on coordinate precision.
        This is a placeholder computation - you can customize this logic
        based on your specific accuracy requirements.
        """
        for partner in self:
            if partner.partner_latitude and partner.partner_longitude:
                # Example: Calculate accuracy based on decimal places
                # More decimal places = higher accuracy = smaller distance
                lat_str = str(partner.partner_latitude)
                lng_str = str(partner.partner_longitude)
                
                # Count decimal places for accuracy estimation
                lat_decimals = len(lat_str.split('.')[-1]) if '.' in lat_str else 0
                lng_decimals = len(lng_str.split('.')[-1]) if '.' in lng_str else 0
                
                # Average decimal places
                avg_decimals = (lat_decimals + lng_decimals) / 2
                
                # Convert decimal places to approximate accuracy in meters
                # 1 decimal place ≈ 11 km, 2 decimal places ≈ 1.1 km, etc.
                if avg_decimals >= 6:
                    accuracy = 0.1  # Very high accuracy
                elif avg_decimals >= 5:
                    accuracy = 1.0  # High accuracy
                elif avg_decimals >= 4:
                    accuracy = 10.0  # Good accuracy
                elif avg_decimals >= 3:
                    accuracy = 100.0  # Moderate accuracy
                elif avg_decimals >= 2:
                    accuracy = 1000.0  # Low accuracy
                else:
                    accuracy = 10000.0  # Very low accuracy
                
                partner.geolocation_accuracy_distance = accuracy
            else:
                partner.geolocation_accuracy_distance = 0.0

    def calculate_distance_to_point(self, target_lat, target_lng):
        """
        Calculate distance from partner's location to a target point using Haversine formula.
        
        Args:
            target_lat (float): Target latitude
            target_lng (float): Target longitude
            
        Returns:
            float: Distance in meters
        """
        if not self.partner_latitude or not self.partner_longitude:
            return 0.0
            
        # Haversine formula
        R = 6371000  # Earth's radius in meters
        
        lat1_rad = math.radians(self.partner_latitude)
        lat2_rad = math.radians(target_lat)
        delta_lat = math.radians(target_lat - self.partner_latitude)
        delta_lng = math.radians(target_lng - self.partner_longitude)
        
        a = (math.sin(delta_lat / 2) ** 2 + 
             math.cos(lat1_rad) * math.cos(lat2_rad) * 
             math.sin(delta_lng / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        distance = R * c
        return distance

    def is_within_accuracy_radius(self, target_lat, target_lng):
        """
        Check if a target point is within the geolocation accuracy distance.
        
        Args:
            target_lat (float): Target latitude
            target_lng (float): Target longitude
            
        Returns:
            bool: True if target is within accuracy radius
        """
        if not self.geolocation_accuracy_distance:
            return False
            
        distance = self.calculate_distance_to_point(target_lat, target_lng)
        return distance <= self.geolocation_accuracy_distance
