#!/usr/bin/env python3
"""
Wheels API for CyberiadaML diagrams
Usage in diagram actions:
  wheels.forward(0.2)
  wheels.turn_left(90)
  wheels.stop()
"""
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from typing import Optional
import time


class Wheels(Node):
    """Low-level wheel control API - publishes to /cmd_vel"""
    
    # Class-level singleton for diagram usage
    _instance: Optional['Wheels'] = None
    
    # Default parameters
    DEFAULT_LINEAR_SPEED = 0.2      # m/s
    DEFAULT_ANGULAR_SPEED = 0.5     # rad/s
    DEFAULT_TURN_ANGLE = 90.0       # degrees
    
    # Signals for CyberiadaML generator
    SIGNALS = {
        'WHEELS_STOPPED': 'Wheels stopped',
        'WHEELS_MOVED': 'Movement completed',
        'WHEELS_TURNED': 'Turn completed',
    }
    
    def __new__(cls, *args, **kwargs):
        """Singleton pattern for diagram usage"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, node_name: str = 'wheels_api'):
        if hasattr(self, '_initialized') and self._initialized:
            return
        super().__init__(node_name)
        self._cmd_pub = self.create_publisher(Twist, '/cmd_vel', 10)
        self._initialized = True
        self.get_logger().info("Wheels API initialized")
    
    def _publish_vel(self, linear: float, angular: float) -> None:
        """Internal: publish Twist message"""
        cmd = Twist()
        cmd.linear.x = float(linear)
        cmd.linear.y = 0.0
        cmd.linear.z = 0.0
        cmd.angular.x = 0.0
        cmd.angular.y = 0.0
        cmd.angular.z = float(angular)
        self._cmd_pub.publish(cmd)
    
    def stop(self) -> bool:
        """
        Stop all wheel movement
        
        Diagram usage:
          wheels.stop()
        
        Returns:
            bool: True if command published
        
        Generates signal: WHEELS_STOPPED
        """
        self._publish_vel(0.0, 0.0)
        self.get_logger().info("Wheels: stopped")
        return True
    
    def forward(self, distance: Optional[float] = None, speed: Optional[float] = None) -> bool:
        """
        Move forward with optional distance control
        
        Diagram usage:
          wheels.forward()              # Default speed
          wheels.forward(0.5)           # Move 0.5m at default speed
          wheels.forward(0.5, 0.3)      # Move 0.5m at 0.3 m/s
        
        Args:
            distance: Optional distance in meters (for generator timing)
            speed: Optional linear speed in m/s
        
        Returns:
            bool: True if command published
        
        Note: Distance-based movement requires generator to add timing logic
        Generates signal: WHEELS_MOVED when distance reached
        """
        speed = speed if speed is not None else self.DEFAULT_LINEAR_SPEED
        self._publish_vel(speed, 0.0)
        self.get_logger().info(f"Wheels: forward v={speed} m/s")
        return True
    
    def back(self, distance: Optional[float] = None, speed: Optional[float] = None) -> bool:
        """
        Move backward with optional distance control
        
        Diagram usage:
          wheels.back()
          wheels.back(0.3)
        
        Args:
            distance: Optional distance in meters
            speed: Optional linear speed in m/s
        
        Returns:
            bool: True if command published
        """
        speed = speed if speed is not None else self.DEFAULT_LINEAR_SPEED
        self._publish_vel(-speed, 0.0)
        self.get_logger().info(f"Wheels: backward v={speed} m/s")
        return True
    
    def turn_right(self, angle: Optional[float] = None, speed: Optional[float] = None) -> bool:
        """
        Turn right (clockwise) with optional angle control
        
        Diagram usage:
          wheels.turn_right()           # Default 90°
          wheels.turn_right(45)         # 45 degrees
          wheels.turn_right(180, 1.0)   # 180° at 1.0 rad/s
        
        Args:
            angle: Optional angle in degrees (default: 90)
            speed: Optional angular speed in rad/s
        
        Returns:
            bool: True if command published
        
        Note: Angle-based turning requires generator to add timing logic
        Generates signal: WHEELS_TURNED when angle reached
        """
        angle = angle if angle is not None else self.DEFAULT_TURN_ANGLE
        speed = speed if speed is not None else self.DEFAULT_ANGULAR_SPEED
        import math
        angular = -speed  # Negative = clockwise/right
        self._publish_vel(0.0, angular)
        self.get_logger().info(f"Wheels: turn_right angle={angle}° speed={speed} rad/s")
        return True
    
    def turn_left(self, angle: Optional[float] = None, speed: Optional[float] = None) -> bool:
        """
        Turn left (counter-clockwise) with optional angle control
        
        Diagram usage:
          wheels.turn_left()
          wheels.turn_left(90)
        
        Args:
            angle: Optional angle in degrees (default: 90)
            speed: Optional angular speed in rad/s
        
        Returns:
            bool: True if command published
        """
        angle = angle if angle is not None else self.DEFAULT_TURN_ANGLE
        speed = speed if speed is not None else self.DEFAULT_ANGULAR_SPEED
        angular = speed  # Positive = counter-clockwise/left
        self._publish_vel(0.0, angular)
        self.get_logger().info(f"Wheels: turn_left angle={angle}° speed={speed} rad/s")
        return True
    
    @classmethod
    def get_instance(cls) -> 'Wheels':
        """Get singleton instance for diagram usage"""
        if cls._instance is None:
            cls._instance = Wheels()
        return cls._instance


# Global instance for diagram actions
wheels = Wheels.get_instance()