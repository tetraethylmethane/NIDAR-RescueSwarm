# OpenRX Lite-UFL

Open-source 2.4 GHz ExpressLRS receiver for small FPV aircraft. OpenRX Lite-UFL
combines an ESP32-C3 and SX1281 with a U.FL link-antenna connector in a
10.0 x 11.5 mm board.

<p>
<img src="images/front.png" width="400" alt="OpenRX Lite-UFL front" />
<img src="images/back.png" width="400" alt="OpenRX Lite-UFL back" />
</p>

[![Status](https://img.shields.io/endpoint?url=https://opendrone.be/api/status/OpenRX-Lite-UFL.json)](https://github.com/OpenDrone-hw/.github/blob/main/CONTRIBUTING.md#the-life-of-a-project)
[![Shop](https://img.shields.io/badge/shop-opendrone.be-ffb700)](https://opendrone.be/products/openrx)
[![Discord](https://img.shields.io/badge/Discord-%23receivers-5865F2?logo=discord&logoColor=white)](https://discord.com/channels/1494019459822653512/1494758332903456969)
[![Video](https://img.shields.io/badge/YouTube-How%20ExpressLRS%20Receivers%20Work-FF0000?logo=youtube&logoColor=white)](https://www.youtube.com/watch?v=ssmQkRkXE84)
[![OSHWA](https://img.shields.io/badge/OSHWA-BE000031-0099b0)](https://certification.oshwa.org/be000031.html)

## Specifications

| | |
|---|---|
| Band | 2.4 GHz |
| Radio | SX1281 |
| Antenna | U.FL |
| Telemetry power | 13 dBm (20 mW) |
| Protocol | CRSF |
| MCU | ESP32-C3 |
| Input | 5 V pad |
| Firmware | ExpressLRS |
| Flashing | Betaflight passthrough or Wi-Fi |
| Dimensions | 10.0 x 11.5 mm |
| PCB | 6-layer, 1.0 mm |

Technical write-up, part list and layout constraints: [AGENTS.md](AGENTS.md).

## In the line

What pairs with what, and what is available:
[opendrone.be](https://opendrone.be).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

Hardware licensed under [CERN-OHL-S-2.0](https://ohwr.org/cern_ohl_s_v2.txt),
see [LICENSE](LICENSE).
