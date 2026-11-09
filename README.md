# Sony Utility — WH-CH520

A separate Omarchy / Quickshell bar plugin, styled like JBL Utility and Razer
Utility. Bluetooth only. No account, server, cloud connection, software EQ or
background daemon. The icon appears only when connected WH-CH520 headphones are
the system's default output. Choose the output in Omarchy's normal audio panel.

## Install on your friend's Omarchy desktop

Extract the archive, open a terminal in the `sony-utility` directory, then run:

```sh
/usr/bin/python3 install.py
```

The installer validates the plugin, backs up existing configuration, copies the
files to `$XDG_CONFIG_HOME/omarchy/plugins/krysto.sony-utility` (normally
`~/.config/omarchy/plugins/krysto.sony-utility`), adds one bar entry and restarts
the shell. It does not restart audio. Repeat installation is safe and does not
create a second icon. `--no-reload` skips the shell restart.

Requires a recent Omarchy shell with `qs.Ui`, Quickshell Bluetooth and PipeWire,
`/usr/bin/python3`, Python D-Bus/PyGObject, BlueZ, and `timeout`. These are available
on the Omarchy system used to prepare this plugin. It is not a Windows or macOS
plugin. No administrator privileges or additional Python environment are needed.

Pair WH-CH520 through the normal Bluetooth panel and select them as the default
audio output. Close Sony Sound Connect on the phone while using these controls;
the proprietary control channel may be held by another client. The widget reads
settings only when opened or refreshed, and releases the channel afterward.

## Controls

- BlueZ battery, output volume, mute, rotating Sony phrases.
- Native EQ: presets advertised by the headphones; five bands plus Clear Bass
  when that six-value layout is returned. Select a supported Custom preset to
  edit the sliders. Changes are sent to the headset, not to a PipeWire filter.
- DSEE and sound quality / connection stability priority when reported.
- Voice guidance on/off when advertised on MDR v2 table 2 and read successfully.
- Firmware version and multipoint status, when reported.

The last two rows are informational. Multipoint changes, voice-language packages,
firmware updates and 360 Reality Audio setup remain in Sony Sound Connect. There
are no ANC/Ambient controls: WH-CH520 has no such hardware.

Changes require capability discovery, a valid current reading, a protocol ACK,
and a delayed matching GET. A transport ACK alone is never displayed as a
successful setting change. Presets not advertised by the device cannot be sent.
Unknown layouts, malformed data and readback mismatches leave controls unavailable.
Custom sliders update after release and a short debounce. There is no automatic
write retry. Each helper request has a 35-second outer timeout and a cross-process
lock. Device names and capabilities are not trusted as rich text or shell code.

## Validation and limits

**No WH-CH520 was physically available for this build.** These controls are an
implementation of published Sony MDR v2 schemas, not a claim of testing on your
friend's headphones. They need a live device check. Errors can be retried with
the panel's refresh button; unsupported controls stay hidden.

Validation covers framed/fragmented streams, checksum/length validation, capability
bounds, native EQ encoding, preset allowlists, boolean enum differences, refused
writes, failed readback, source changes, and untrusted labels. The framing test
uses the public CH520 handshake payload; all feature sessions are synthetic.

```sh
/usr/bin/python3 -m unittest discover -s tests -v
QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME= QT_QUICK_CONTROLS_STYLE=Basic /usr/lib/qt6/bin/qmltestrunner -input tests/tst_model.qml
omarchy plugin validate .
```

Remove using `omarchy plugin remove krysto.sony-utility`.
See `PROTOCOL-SOURCES.md` for protocol references and exact source revision.

## Install

```sh
omarchy plugin add https://github.com/Kryst-0/omarchy-sony-utility.git --enable
```

## Remove

```sh
omarchy plugin remove krysto.sony-utility
```
