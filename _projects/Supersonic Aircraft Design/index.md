---
layout: post
title: Supersonic Aircraft Concept — Design & Aerodynamic Analysis
context: >-
  <strong>Lehigh University · MECH 328</strong><br>Individual Course Project | Spring 2025
description: >-
  I independently designed and analyzed a conceptual twin-engine air-superiority aircraft using OpenVSP and VSPAERO. Over the semester, I developed the aircraft’s configuration and evaluated how changes to its wings, tail, and control surfaces affected aerodynamic performance.
  <br><br>
  The design targeted subsonic cruise, Mach 1.5 supercruise, and Mach 2.0 flight. The central challenge was developing a configuration that could achieve pitch trim at each of these analysis conditions through control-surface adjustments.
skills:
- OpenVSP
- VSPAERO
- Aircraft Configuration Design
- Pitch Trim Analysis
- Control-Surface Integration
- Conceptual Performance Estimation
main-image: /Aircraft.png
hero-viewer: aircraft-model
---

## Design Goals

I defined mission requirements for a supersonic fighter concept with internal and external payload capacity. Goals included cruise range above 1,500 miles, supercruise range above 750 miles, and an afterburning thrust-to-weight ratio above one in at least one loading configuration.

These requirements guided the conceptual sizing and performance calculations. Propulsion performance was represented using assumed engine characteristics.

## My Role

I completed the aircraft geometry, aerodynamic analysis, and performance assessment independently. My work included configuring the fuselage, wings, and tail in OpenVSP; running VSPAERO analyses; and evaluating pitching moment, lift, drag, estimated range and endurance, and thrust requirements.

## Design Challenge

Wing placement and tail geometry were closely coupled. A change that improved the aircraft’s behavior at one speed could require further adjustments at another, so I repeatedly evaluated the configuration at Mach 0.9, 1.5, and 2.0.

The process required balancing wing geometry and position with the horizontal tail’s ability to counter the aircraft’s pitching moment.

## Design Iteration & Control Surfaces

I refined the wing into a diamond planform and adjusted wing and tail incidence and planform areas to improve control authority.

For the final configuration, I adjusted the leading-edge flaps, trailing-edge flaps, and horizontal stabilizer to obtain pitch trim at the selected conditions. The horizontal stabilizer provided most of the pitching-moment correction, while the flaps supported finer adjustments and changes in lift.

## Final Dimensions

| Dimension | Value |
|---|---|
| Overall length | 78.1 ft |
| Fuselage length | 70.8 ft |
| Wingspan | 44.0 ft |
| Height (without landing gear) | 13.3 ft |
| Wing reference area | 1,020 ft² |
| Reference chord | 16.3 ft |
| Aspect ratio | 1.9 |
| Horizontal tail span | 33.0 ft |
| Vertical tail cant | 35° from vertical |
| Maximum weight | 88,824 lb |
| Fuel | 20,429 lb |

## Analysis Results

The final analysis achieved near-zero pitching-moment coefficients at selected conditions at Mach 0.9, 1.5, and 2.0. Pitching-moment sweeps also showed how the configuration’s response to angle of attack changed between these speeds.

{% include selectable-plots.html
  group="cmy"
  legend="Select a Mach number"
  images="cmy-mach-0.9.jpg, cmy-mach-1.5.jpg, cmy-mach-2.0.jpg"
  labels="Mach 0.9, Mach 1.5, Mach 2.0"
  alts="VSPAERO plot of pitching-moment coefficient CMy against angle of attack at Mach 0.9. The curve stays near zero up to about 2 degrees, then falls to about -0.2 at 10 degrees. | VSPAERO plot of pitching-moment coefficient CMy against angle of attack at Mach 1.5. The curve falls from about 0.2 at -5 degrees to about -0.4 at 10 degrees, with a small deviation between 0 and 2 degrees. | VSPAERO plot of pitching-moment coefficient CMy against angle of attack at Mach 2.0. The curve falls almost linearly from about 0.17 at -5 degrees to about -0.38 at 10 degrees."
  caption="VSPAERO pitching-moment sweeps (CMy vs. angle of attack) for the final configuration." %}

I compared estimated available thrust with calculated thrust requirements for different aircraft weights and payload configurations. These calculations indicated sufficient thrust for the evaluated operational load cases, while identifying limitations at maximum weight at the higher Mach numbers.

The results represent a conceptual simulation study using assumed propulsion characteristics. They establish the outcomes of the evaluated cases rather than flight-tested performance or validation of the complete flight envelope.

## How I Reached These Conclusions

**Pitch trim.** At each Mach number, I ran a VSPAERO sweep from −5° to 10° angle of attack and adjusted the leading-edge flaps, trailing-edge flaps, and horizontal stabilizer until the pitching moment at the selected condition was near zero. When the control surfaces could not trim the aircraft on their own, I changed the wing and tail geometry and repeated the sweeps.

The slope of each curve showed how the aircraft responds to a change in angle of attack. At Mach 1.5 and 2.0, pitching moment fell steadily as angle of attack increased, which indicates static stability. At Mach 0.9, the curve was nearly flat at low angles of attack, so I assumed a flight control system would be needed to keep the aircraft stable.

**Load cases.** I evaluated four takeoff weights, each with the same fuel load: 58,624 lb with no missiles, 60,772 lb with 6 internal AIM-120s, 63,636 lb with 14 AIM-120s, and 88,824 lb at maximum weight.

**Engine assumptions.** I modeled two F119 engines producing 26,000 lb of thrust each without afterburner and 35,000 lb each with it, using a specific fuel consumption of 0.76 and 1.79, respectively. Real performance data for the engine was not available, so I used textbook relationships to correct takeoff thrust for cruise and Mach number.

**Endurance and range.** I estimated endurance with the Breguet equation, using the lift-to-drag ratio at each condition, the specific fuel consumption, and the aircraft’s weight before and after burning its fuel. With 6 internal missiles, estimated endurance was 5.8 hours at Mach 0.9, 3.5 hours at Mach 1.5, and 1.1 hours at Mach 2.0 on afterburner. I compared the range estimates against the mission goals, and the missile-load cases met both the 1,500-mile cruise and 750-mile supercruise targets.

**Thrust.** I calculated thrust required at each condition by dividing the aircraft’s weight by its lift-to-drag ratio, then compared the result with estimated thrust available.

| Condition | Thrust available | Required with 14 missiles | Required at maximum weight |
|---|---|---|---|
| Mach 0.9, no afterburner | 11,184 lb | 5,875 lb | 8,201 lb |
| Mach 1.5, no afterburner | 12,303 lb | 9,784 lb | 13,657 lb |
| Mach 2.0, afterburner | 16,977 lb | 13,112 lb | 18,302 lb |

Thrust was sufficient for every missile-load case at all three speeds. At maximum weight, it fell short at Mach 1.5 and Mach 2.0, which is the limitation noted above. With afterburner, sea-level thrust-to-weight was 1.15 with 6 internal missiles and 0.79 at maximum weight, so the aircraft met the goal of a thrust-to-weight ratio above one in at least one loading configuration.

## What I Learned

The project taught me to treat aircraft geometry and aerodynamic performance as an interconnected design problem. Wing position, tail sizing, incidence, and control-surface settings had to be considered together and reassessed across multiple operating conditions.

It also strengthened my ability to use simulation results to guide design changes and distinguish a design objective from a result supported by analysis.
