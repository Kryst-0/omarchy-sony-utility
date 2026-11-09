function bluetoothDevice(devices, output) {
  var sink = String(output || "").toLowerCase()
  for (var i=0;i<devices.length;i++) {
    var d=devices[i]
    if (!d || !d.connected || String(d.name || d.deviceName || "").toUpperCase() !== "WH-CH520") continue
    var address=String(d.address || "").replace(/:/g,"_").toLowerCase()
    if(address && sink.indexOf(address)>=0) return d
  }
  return null
}
function validState(s) {
  if(!s || typeof s!=="object") return ({})
  var out={}
  if(Array.isArray(s.presets)) out.presets=s.presets.slice(0,32).filter(p=>p && Number.isInteger(p.value) && p.value>=0 && p.value<=255 && typeof p.name==="string" && p.name.length<=96)
  if(Number.isInteger(s.preset) && s.preset>=0 && s.preset<=255) out.preset=s.preset
  if(Array.isArray(s.bands) && s.bands.length===6 && s.bands.every(v=>Number.isInteger(v) && v>=-10 && v<=10)) out.bands=s.bands
  if(typeof s.dsee==="boolean") out.dsee=s.dsee
  if(typeof s.voice==="boolean") out.voice=s.voice
  if(s.priority===0 || s.priority===1) out.priority=s.priority
  if(typeof s.multipoint==="boolean") out.multipoint=s.multipoint
  if(typeof s.firmware==="string" && s.firmware.length<=64) out.firmware=s.firmware
  return out
}
