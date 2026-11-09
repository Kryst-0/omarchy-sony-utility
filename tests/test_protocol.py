import sys
from pathlib import Path
import socket
import unittest
import tempfile
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from protocol import Framer,encode,functions,presets,eq,build_set
import control

class FramingTests(unittest.TestCase):
 def test_captured_sony_handshake_frame(self):
  # MDR v2 handshake payload recorded publicly for WH-CH520; no feature claims.
  frame=encode(12,0,bytes.fromhex('0100030010010000'))
  self.assertEqual(Framer().feed(frame),[(12,0,bytes.fromhex('0100030010010000'))])
 def test_fragmentation_and_marker_escape(self):
  wire=encode(14,1,b'\x3c\x3d\x3e');f=Framer();result=[]
  for b in wire:result+=f.feed(bytes([b]))
  self.assertEqual(result,[(14,1,b'\x3c\x3d\x3e')])
 def test_checksum_rejected(self):
  wire=bytearray(encode(12,0,b'\x56\0'));wire[-2]^=1
  with self.assertRaises(ValueError):Framer().feed(wire)
 def test_length_and_oversize_rejected(self):
  with self.assertRaises(ValueError):Framer().feed(b'\x3e'+b'x'*17000)
  with self.assertRaises(ValueError):Framer().feed(bytes.fromhex('3e0c000000000200003c'))
 def test_capabilities_bounds(self):
  self.assertEqual(functions(bytes.fromhex('0700035000e100e200')),{0x50,0xe1,0xe2})
  with self.assertRaises(ValueError):functions(bytes.fromhex('07000250'))
 def test_eq_native_wire(self):
  data=eq(bytes.fromhex('5700a006000a0b0c0d14'))
  self.assertEqual(data,{'preset':160,'bands':[-10,0,1,2,3,10]})
  state={**data,'presets':[{'value':160,'name':'Custom'}]}
  self.assertEqual(build_set('bands',data['bands'],state)[1],bytes.fromhex('5800a006000a0b0c0d14'))
 def test_eq_invalid_layout(self):
  for data in [bytes.fromhex('5700a0010a'),bytes.fromhex('5700a006151414141414')]:
   with self.assertRaises(ValueError):eq(data)
 def test_only_advertised_presets(self):
  with self.assertRaises(ValueError):build_set('preset',17,{'presets':[{'value':0,'name':'Off'}]})
 def test_edit_bands_requires_custom(self):
  with self.assertRaises(ValueError):build_set('bands',[0]*6,{'preset':0,'bands':[0]*6,'presets':[{'value':0}]})
 def test_boolean_enums(self):
  self.assertEqual(build_set('dsee',True,{'dsee':False})[1],bytes.fromhex('e80101'))
  self.assertEqual(build_set('voice',True,{'voice':False,'voiceType':1})[:2],(14,bytes.fromhex('480100')))
 def test_no_anc_reset_firmware_or_raw(self):
  for feature in ('anc','firmware','raw','pair','reset','multipoint','poweroff'):
   with self.assertRaises(ValueError):build_set(feature,1,{})
 def test_markup_preset_is_data(self):
  label=b'<img src="https://example.invalid">'
  data=presets(bytes([0x51,0,6,20,1,160,len(label)])+label)
  self.assertEqual(data[0]['name'],label.decode())
 def test_truncated_preset(self):
  with self.assertRaises(ValueError):presets(bytes.fromhex('5100061401a00641'))

class FakeSession:
 def __init__(self,address=None):self.commands=[]
 def __enter__(self):return self
 def __exit__(self,*args):pass
 def request(self,payload,reply,kind=12,timeout=1.2):
  return {b'\0\0':bytes.fromhex('0100030010010001'),b'\x06\0':bytes.fromhex('0700035000e100e200'),b'\x50\0\x01':bytes.fromhex('510006140200034f6666a006437573746f6d'),b'\x56\0':bytes.fromhex('570000060a0a0a0a0a0a'),b'\xe6\1':bytes.fromhex('e70100'),b'\xe6\0':bytes.fromhex('e70001'),b'\x04\2':bytes.fromhex('050205312e302e30')}.get(payload)
 def command(self,payload,kind=12):self.commands.append((kind,payload))

class SessionTests(unittest.TestCase):
 def test_supported_feature_snapshot(self):
  s=control.snapshot(FakeSession())
  self.assertEqual(s['state']['bands'],[0]*6);self.assertFalse(s['state']['dsee']);self.assertEqual(s['state']['priority'],1)
  self.assertNotIn('voice',s['state']);self.assertNotIn('anc',s['state'])
 def test_ack_alone_never_confirms_set(self):
  with tempfile.TemporaryDirectory() as tmp, patch.dict(control.os.environ,{'XDG_RUNTIME_DIR':tmp}), patch.object(control,'Session',FakeSession),patch.object(control.time,'sleep'):
   result=control.run({'op':'set','transport':'bluetooth','address':'00:11:22:33:44:55','feature':'dsee','value':True})
  self.assertFalse(result['ok']);self.assertEqual(result['error'],'unconfirmed')
 def test_wrong_transport_or_feature_rejected(self):
  with self.assertRaises(ValueError):control.run({'op':'status','transport':'usb'})
  with self.assertRaises(ValueError):control.run({'op':'set','transport':'bluetooth','address':'00:11:22:33:44:55','feature':'reset'})
 def test_corrupt_stream_not_acked(self):
  s=control.Session('00:11:22:33:44:55')
  from unittest.mock import Mock
  s.sock=Mock();s.sock.recv.return_value=bytes.fromhex('3e0c0000000000003c')
  with self.assertRaises(ValueError):s.receive(control.time.monotonic()+1)
  s.sock.sendall.assert_not_called()
if __name__=='__main__':unittest.main()
