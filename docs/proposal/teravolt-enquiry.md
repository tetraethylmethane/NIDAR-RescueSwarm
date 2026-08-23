# Supplier enquiry — Teravolt GNSS

Draft for sending from the university address.

---

**Subject:** Quotation request — AeroNav-Pro RTK / AeroNav-X5, qty 4

Dear Teravolt team,

Thank you for confirming RTK rover operation on both receivers, and for the note
that moving-baseline heading is still in development. That is not a blocker for
us — our design takes heading from a magnetometer and we have costed the
resulting error.

We are a student team at Thapar Institute of Engineering and Technology,
Patiala, building a three-aircraft autonomous search-and-rescue UAS. Survivor
coordinate accuracy is the system's primary output, so the GNSS receiver is one
of the few components we will not compromise on, and we would like to specify an
Indian part.

**Please quote four units** — three airborne rovers and one ground base station,
with antennas and cabling — including GST and lead time.

Five questions:

1. **Price.** Neither model is listed on teravolt.in. Are both available to
   order, and at what unit price?
2. **NavIC on the X5.** The X5 quotes better RTK accuracy than the Pro RTK
   (0.6 cm + 0.5 ppm against 1 cm + 1 ppm) but does not list its constellations.
   Does it track NavIC, and on which bands? Indigenous content is a design
   requirement for us and NavIC support is part of how we justify the choice.
3. **Which model** would you recommend for a 6.4 kg multirotor surveying at
   40 m AGL, where horizontal accuracy and re-acquisition after a brief
   obstruction matter most?
4. **Base station.** Can one of these serve as the base, or do you supply a
   separate product? If it can, what survey-in time and accuracy should we plan
   for?
5. **RTCM3 particulars.** Your documentation covers the injection path — RTCM
   3.x into UART2, with `GPS_INJECT_TO` forwarding it over telemetry — which is
   exactly our intended architecture. What it does not give is the message set
   the receiver expects, the correction bandwidth, and the maximum correction
   age before it drops from fixed to float. We need those three to size the
   telemetry link.

With thanks,

Swastik Kumar
Department of Electronics and Communication Engineering
Thapar Institute of Engineering and Technology, Patiala
skumar6_be24@thapar.edu
