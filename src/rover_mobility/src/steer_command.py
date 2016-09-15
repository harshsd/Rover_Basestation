#!/usr/bin/env python
from math import pi, cos, sin

import diagnostic_msgs
import diagnostic_updater
from roboclaw import RoboClaw
import rospy
import tf
from geometry_msgs.msg import Quaternion, Twist
from nav_msgs.msg import Odometry
from std_msgs.msg import Float64MultiArray

from serial.serialutil import SerialException as SerialException


class SteerClaw:

	def __init__(self, address, dev_name, baud_rate, kp1 = 0.25, kp2 = 0.25, qpps1 = 5.34, qpps2 = 5.34, deadzone1 = 50, deadzone2 = 50, kon1 = 10, kon2 = 10, ovf = 1922):
		self.ERRORS = {0x0000: (diagnostic_msgs.msg.DiagnosticStatus.OK, "Normal"),
		0x0001: (diagnostic_msgs.msg.DiagnosticStatus.WARN, "M1 over current"),
		0x0002: (diagnostic_msgs.msg.DiagnosticStatus.WARN, "M2 over current"),
		0x0004: (diagnostic_msgs.msg.DiagnosticStatus.ERROR, "Emergency Stop"),
		0x0008: (diagnostic_msgs.msg.DiagnosticStatus.ERROR, "Temperature1"),
		0x0010: (diagnostic_msgs.msg.DiagnosticStatus.ERROR, "Temperature2"),
		0x0020: (diagnostic_msgs.msg.DiagnosticStatus.ERROR, "Main batt voltage high"),
		0x0040: (diagnostic_msgs.msg.DiagnosticStatus.ERROR, "Logic batt voltage high"),
		0x0080: (diagnostic_msgs.msg.DiagnosticStatus.ERROR, "Logic batt voltage low"),
		0x0100: (diagnostic_msgs.msg.DiagnosticStatus.WARN, "M1 driver fault"),
		0x0200: (diagnostic_msgs.msg.DiagnosticStatus.WARN, "M2 driver fault"),
		0x0400: (diagnostic_msgs.msg.DiagnosticStatus.WARN, "Main batt voltage high"),
		0x0800: (diagnostic_msgs.msg.DiagnosticStatus.WARN, "Main batt voltage low"),
		0x1000: (diagnostic_msgs.msg.DiagnosticStatus.WARN, "Temperature1"),
		0x2000: (diagnostic_msgs.msg.DiagnosticStatus.WARN, "Temperature2"),
		0x4000: (diagnostic_msgs.msg.DiagnosticStatus.OK, "M1 home"),
		0x8000: (diagnostic_msgs.msg.DiagnosticStatus.OK, "M2 home")}
		
		self.claw = RoboClaw(address, dev_name, baud_rate)
		self.claw.ResetEncoders()
		self.targetAngleM1 = 0
		self.targetAngleM2 = 0
		self.kp1 = kp1
		self.kp2 = kp2
		self.qpps1 = qpps1
		self.qpps2 = qpps2
		self.deadzone1 = deadzone1
		self.deadzone2 = deadzone2
		self.kon1 = kon1
		self.kon2 = kon2
		self.ovf = ovf

	def update(self):
		enc1Pos = self.claw.ReadEncM1()[1]
		finalEnc1Val = int(self.qpps1*self.targetAngleM1)
		diff1 = finalEnc1Val - enc1Pos
		velM1 = int(self.kp1*diff1)
		if enc1Pos < (finalEnc1Val - self.deadzone1):
			velM1 = velM1 + self.kon1
			self.claw.ForwardM1(min(255, velM1))
		elif enc1Pos > (finalEnc1Val + self.deadzone1):
			velM1 = velM1 - self.kon1
			self.claw.BackwardM1(min(255, -velM1))
		else:
			self.claw.ForwardM1(0)

		enc2Pos = self.claw.ReadEncM2()[1] 
		finalEnc2Val = int(self.qpps2*self.targetAngleM2)
		diff2 = finalEnc2Val - enc2Pos
		velM2 = int(self.kp2*diff2)
		if enc2Pos < (finalEnc2Val - self.deadzone2):
			velM2 = velM2 + self.kon2
			self.claw.BackwardM2(min(255, velM2))
		elif enc2Pos > (finalEnc2Val + self.deadzone2):
			velM2 = velM2 - self.kon2
			self.claw.ForwardM2(min(255, -velM2))
		else:
			self.claw.ForwardM2(0)
		rospy.loginfo("%d %d %d %d ", diff1, self.targetAngleM1, self.claw.ReadEncM1()[1], velM1)
		
	

def steer_callback(inp):
	
	roboclaw1.targetAngleM1 = inp.data[6]
	roboclaw1.targetAngleM2 = inp.data[7]
	roboclaw2.targetAngleM1 = inp.data[8]
	roboclaw2.targetAngleM2 = inp.data[9]


if __name__ == "__main__":
	
	rospy.init_node("roboclaw_node")
	rospy.loginfo("Starting steer node")

	rospy.Subscriber("/rover/ard_directives", Float64MultiArray, steer_callback)
	
	r_time = rospy.Rate(1)
	for i in range(20):
		try:
			roboclaw1 = SteerClaw(0x81, "/dev/ttyACM0", 9600)
		except SerialException:
			rospy.logwarn("Could not connect to RoboClaw1, retrying...")
			r_time.sleep()
	rospy.loginfo("Connected to RC")
	
	for i in range(20):
		try:
			roboclaw2 = SteerClaw(0x81, "/dev/ttyACM1", 9600)
		except SerialException:
			rospy.logwarn("Could not connect to RoboClaw2, retrying...")
			r_time.sleep()
	
	r_time = rospy.Rate(20)
	roboclaw1.claw.ForwardM1(0)
	roboclaw1.claw.ForwardM2(0)
	roboclaw2.claw.ForwardM1(0)
	roboclaw2.claw.ForwardM2(0)
	
	while not rospy.is_shutdown():
		roboclaw1.update()
		roboclaw2.update()
		r_time.sleep()

	roboclaw1.claw.ForwardM1(0)
	roboclaw1.claw.ForwardM2(0)
	roboclaw2.claw.ForwardM1(0)
	roboclaw2.claw.ForwardM2(0)