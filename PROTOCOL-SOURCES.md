# Protocol references

Implementation and tests were written independently from the following public
protocol schemas and observations. No third-party runtime implementation is
bundled.

- Sony official WH-CH520 app features:
  https://helpguide.sony.net/mdr/2958/v1/en/contents/TP1000776844.html
- SonyHeadphonesClient / libmdr, MIT, revision
  `2edf09098db27642c89e533bf86c0a6b162f6ad4`:
  https://github.com/mos9527/SonyHeadphonesClient
  - `libmdr/include/mdr/Generated/ProtocolV2.hpp`: ACK, enable/disable, voice enums.
  - `ProtocolV2T1.hpp`: capabilities, equalizer presets and six-value parameters,
    DSEE, audio priority, firmware and device-special-mode status.
  - `ProtocolV2T2.hpp`: voice guidance parameter shapes.
  - `libmdr/src/HeadphonesV2.cpp`: native EQ write semantics.
- Public MDR framing and WH-CH520 handshake observations:
  https://github.com/ncr/omarchy-headphones/blob/main/PROTOCOL.md
  `01 00 03 00 10 01 00 00` is the CH520 handshake payload used by the codec test.

The protocol is proprietary; these sources do not establish live compatibility
of this new plugin with a particular WH-CH520 firmware. No feature reply from a
different Sony model is presented as a CH520 capture. Test capability and EQ
payloads are synthetic fixtures for the schemas.
