---
layout: post
title: EOD Bomb Squad Robot
description:  Currently developing a low-cost, teleoperated bomb squad robot for X-Ray system deployment and explosive ordnance disposal applications. The project focuses on designing an open-source drivetrain capable of navigating uneven terrain and steep inclines, while minimizing cost through 3D printed components, off the shelf materials, and simplified mechanical design.
skills: 
- Dynamics Analysis
- Solidworks
- 3D printing
- Rasberry PI
- Python
- Tracked/Tread System Design
- Low Cost Prototyping
- Motor Selection
main-image: /EOD.png
---

## My Role
I am responsible for drivetrain development and system integration for a low-cost, teleoperated bomb squad robot designed to transport and ultimately position portable X-ray equipment in hazardous environments. My work has expanded beyond the mechanical drivetrain to include motor selection and sizing, chassis and component packaging, power-system architecture, embedded control hardware, radio communications, and development of the robot's motion-control strategy.

I designed the four-wheel drivetrain around independently controlled DDSM115 hub motors and helped develop the chassis around the payload, battery, electronics, and terrain requirements. I have also been the main source of work and knowledge for  the electrical architecture, including the 18 V lithium-ion battery system, BMS, charging interface, power distribution, wiring, and protection strategy.

On the controls side, I am developing the architecture that connects a handheld ELRS radio controller to a Raspberry Pi, which communicates with the four motors over RS485. This includes defining skid-steer behavior, speed and torque control, motor-feedback handling, communications timing, failsafe behavior, emergency stopping logic, and the separation between low-level motor commands and higher-level robot control software.

A major focus of my work has been treating the drivetrain as a complete electromechanical system rather than designing individual components in isolation—balancing mechanical performance, electrical limitations, software responsiveness, safety, manufacturability, cost, and future expansion.

## Technical Details
The current drivetrain uses four DDSM115 integrated hub motors in an independently driven, skid-steer configuration. The chassis has been designed around the motors, X-ray payload, battery system, and onboard electronics, with emphasis on a compact and modular architecture that can be manufactured economically and modified as the project develops. The current design intentionally avoids suspension for the first prototype, allowing testing to determine whether the added mechanical complexity is justified.

The robot is powered by an 18 V, 5 Ah lithium-ion battery system using a 5S battery pack and Daly BMS. I have worked through battery selection, current requirements, BMS sizing, charging architecture, connector selection, wire sizing, power distribution, and protection while accounting for both drivetrain loads and onboard electronics.

Control is centered around a Raspberry Pi communicating with a Waveshare DDSM Driver HAT, which interfaces with the motors over RS485. A RadioMaster Pocket transmitter and ELRS receiver provide the wireless operator interface. The planned software architecture separates low-level motor communication from higher-level robot behavior, allowing the main controller to handle skid-steer mixing, wheel-speed targets, operating limits, feedback monitoring, fault detection, and arming logic.

Because motor feedback is received sequentially over the shared communications bus rather than simultaneously, the control system must account for timing and data staleness when coordinating four independently driven wheels. I am exploring closed-loop control that uses measured wheel speed to regulate motor current within an operator-defined torque limit, allowing the robot to maintain commanded motion while adapting to changing terrain and loads.

Safety and fault handling are also being incorporated into the control architecture. The design includes detection of lost or invalid radio communication, commanded stopping of all four motors, and deliberate re-arming before motion can resume. Additional hardware-level watchdog and telemetry functionality are being considered as the system matures.

The overall project combines mechanical design, power electronics, embedded systems, communications, and feedback control into a single field-deployable robotic platform, with an emphasis on developing a system that is capable, serviceable, expandable, and substantially lower-cost than existing specialized EOD platforms.

{% include image-gallery.html images="Capstone1.png, Capstone2.png, IMG_0080.MOV" height="400" %}
