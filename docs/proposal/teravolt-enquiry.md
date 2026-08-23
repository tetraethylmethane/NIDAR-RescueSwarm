# Supplier enquiry — Teravolt GNSS

Draft for sending from the university address. Adjust the closing to match how
the earlier exchange was signed.

---

**Subject:** Quotation request — AeroNav-Pro RTK and AeroNav-X5 (qty 4, academic UAV programme)

Dear Teravolt team,

Thank you for confirming that both the AeroNav-Pro RTK and the AeroNav-X5
operate as RTK rovers, and for the note that moving-baseline dual-antenna
heading is still in development. That is useful — our design currently takes
heading from a magnetometer, and we have costed the resulting error, so the
absence of moving baseline is not a blocker for this build.

We are a student team at the Thapar Institute of Engineering and Technology,
Patiala, building a three-aircraft autonomous search-and-delivery UAS. Survivor
coordinate accuracy is the primary output of the system, so the GNSS receiver
is one of the few components we will not compromise on. We would like to
specify an Indian receiver, and yours is the closest match we have found to our
requirement.

**Quotation requested**

| Item | Qty | Purpose |
|---|---|---|
| AeroNav-Pro RTK *or* AeroNav-X5 (whichever you recommend) | 3 | Rover, one per aircraft |
| Same model | 1 | Ground base station |
| Antennas, cabling, mounts as required | — | Please quote as needed |

Please include GST, and indicate lead time for four units and whether an
educational or bulk discount applies.

**Technical questions**

1. **Price.** Neither model is listed on teravolt.in — are both available for
   order, and at what unit price?

2. **Constellations on the X5.** The X5 performance page gives 0.6 cm + 0.5 ppm
   horizontal RTK and 7 s initialisation, which is better than the Pro RTK's
   1 cm + 1 ppm, but does not list the constellations or bands. Does the X5
   track NavIC, and on which bands? Indigenous content is a design requirement
   for us, and NavIC support specifically is part of how we justify the choice.

3. **Which model would you recommend** for a 6.4 kg multirotor flying 40 m AGL
   surveys, where the receiver drives survivor geolocation? We care most about
   horizontal accuracy and re-acquisition after a brief obstruction.

4. **RTCM3.** We plan to run our own base station and inject corrections over
   the aircraft's existing telemetry link rather than a separate radio. Could
   you confirm the RTCM3 message set required, the correction bandwidth in
   bytes per second, and the maximum correction age the receiver tolerates
   before dropping from fixed to float?

5. **Base station.** Can one of these units serve as the base, or do you supply
   a separate base product? If it can, what survey-in time and accuracy should
   we plan for?

6. **ArduPilot.** Your documentation covers ArduPilot integration. Is there a
   recommended driver or GPS_TYPE setting, and any firmware version floor?

7. **Moving baseline.** Purely for planning — is there an expected timeframe
   for the dual-antenna heading firmware? We have a flight-test phase that
   measures achieved heading accuracy, and if a dedicated heading source is
   needed we would prefer to stay with an Indian supplier.

8. **Mass and power.** The X5 documentation gives 20 g and 0.6 W typical. Could
   you confirm the equivalent figures for the Pro RTK, including the antenna?

We would be glad to acknowledge Teravolt in the resulting publication and to
share our field accuracy results with you.

With thanks,

Swastik Kumar
Department of Electronics and Communication Engineering
Thapar Institute of Engineering and Technology, Patiala
skumar6_be24@thapar.edu
