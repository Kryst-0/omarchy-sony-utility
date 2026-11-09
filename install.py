#!/usr/bin/python3
"""Install Sony Utility for the current Omarchy user; no system packages or root."""
import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import shutil
import subprocess

def install(config,source):
    config=Path(config);source=Path(source)
    manifest=json.loads((source/'manifest.json').read_text())
    plugin_id=manifest['id']
    if plugin_id!='krysto.sony-utility':raise ValueError('Unexpected plugin ID')
    shell=config/'omarchy/shell.json'
    data=json.loads(shell.read_text()) if shell.exists() else {'version':1}
    if not isinstance(data,dict):raise ValueError('Invalid shell configuration')
    layout=data.setdefault('bar',{}).setdefault('layout',{})
    # Omitted sections continue to use Omarchy defaults. Fetch the stock right
    # section before adding the first local override, so existing widgets stay.
    if 'right' not in layout:
        defaults=Path('/usr/share/omarchy/config/omarchy/shell.json')
        try:layout['right']=json.loads(defaults.read_text())['bar']['layout']['right']
        except (OSError,ValueError,KeyError):raise ValueError('Cannot find the default bar layout; configure bar.layout.right first')
    items=layout['right']
    if not isinstance(items,list):raise ValueError('Invalid right bar section')
    if not any(isinstance(item,dict) and item.get('id')==plugin_id for item in items):
        index=next((i for i,item in enumerate(items) if item.get('id')=='omarchy.audio'),len(items))
        items.insert(index,{'id':plugin_id})
    destination=config/'omarchy/plugins'/plugin_id
    stamp=datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    if destination.exists():
        backup=config/'omarchy/backups/sony-utility'/stamp
        backup.parent.mkdir(parents=True,exist_ok=True)
        shutil.copytree(destination,backup)
    destination.mkdir(parents=True,exist_ok=True)
    for name in ('Panel.qml','DeviceModel.js','HeadphonesIcon.qml','control.py','protocol.py','manifest.json','README.md','LICENSE','PROTOCOL-SOURCES.md'):
        shutil.copy2(source/name,destination/name)
    shutil.copytree(source/'i18n',destination/'i18n',dirs_exist_ok=True)
    shell.parent.mkdir(parents=True,exist_ok=True)
    if shell.exists():shutil.copy2(shell,shell.with_name('shell.json.bak.sony-'+stamp))
    temporary=shell.with_name('shell.json.sony-tmp')
    temporary.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    temporary.replace(shell)
    return destination

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--no-reload',action='store_true',help='install without restarting the shell')
    args=parser.parse_args()
    try:
        import dbus
        from gi.repository import GLib
        source=Path(__file__).resolve().parent
        subprocess.run(['omarchy','plugin','validate',str(source)],check=True)
        config=Path(os.environ.get('XDG_CONFIG_HOME',Path.home()/'.config'))
        destination=install(config,source)
        if not args.no_reload:subprocess.run(['omarchy','restart','shell'],check=True)
        print('Sony Utility installed:',destination)
    except Exception as exc:
        parser.exit(1,'Installation failed: '+str(exc)+'\n')
