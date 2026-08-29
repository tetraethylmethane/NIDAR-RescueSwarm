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
2. **Moving base RTK on the X5.** Your signal-tracking page lists *moving base
   RTK* as an X5 capability, while your earlier note said dual-antenna heading
   is still in development. We read that as the receiver supporting moving
   base while the heading-output firmware is not yet finished — is that right?
   If two X5 units can already give a relative baseline, we would rather plan
   around that than around a magnetometer.
3. **Which model** would you recommend for a 6.4 kg multirotor surveying at
   40 m AGL, where horizontal accuracy and re-acquisition after a brief
   obstruction matter most? On paper the X5 looks the stronger part — Septentrio
   GNSS+, 448 channels, 0.6 cm + 0.5 ppm, AIM+ interference mitigation — but the
   Pro RTK carries NavIC across more bands and adds L-band and NavIC
   corrections. If the price difference is modest we would take the X5.
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
