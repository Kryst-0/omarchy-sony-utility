import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from install import install
class InstallTests(unittest.TestCase):
 def test_isolated_install_is_repeatable_and_preserves_layout(self):
  with tempfile.TemporaryDirectory() as tmp:
   config=Path(tmp)/'config';shell=config/'omarchy/shell.json';shell.parent.mkdir(parents=True)
   shell.write_text(json.dumps({'version':1,'bar':{'layout':{'right':[{'id':'omarchy.audio'},{'id':'omarchy.bluetooth'}]}},'idle':{'lock':123}}))
   source=Path(__file__).resolve().parents[1]
   install(config,source);install(config,source)
   data=json.loads(shell.read_text());self.assertEqual(data['idle']['lock'],123)
   ids=[i['id'] for i in data['bar']['layout']['right']]
   self.assertEqual(ids.count('krysto.sony-utility'),1);self.assertIn('omarchy.bluetooth',ids)
   self.assertTrue(list(shell.parent.glob('shell.json.bak.sony-*')))
   self.assertTrue((config/'omarchy/plugins/krysto.sony-utility/control.py').exists())
