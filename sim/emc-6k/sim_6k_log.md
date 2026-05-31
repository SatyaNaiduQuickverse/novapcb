# Sim 6k EMC/RF Coupling Run Log


## Gate 1: Buck SW → IMU SPI1 trace coupling
- Coupled C ≈ 7.8 fF (worst-case 5mm sep, 1mm×1mm overlap)
- Z_coupled @ 1.8MHz: 11348160 Ω
- Induced V on SPI1 (1pF receiver): ~0.03 mV (well below 100mV SPI noise margin)
- VERDICT Gate 1: PASS — coupling negligible

## Gate 2: DShot edge coupling to Mauch ADC sense
- DShot300 edge rate: 660 V/μs
- Mauch RC filter cutoff: 1592 Hz
- DShot fundamental at 1/333ns = 3 MHz — 1800x above 1.6kHz cutoff
- Attenuation > 65 dB → coupled noise <10 μV at ADC
- VERDICT Gate 2: PASS — RC filter rejects DShot noise to <ADC LSB
