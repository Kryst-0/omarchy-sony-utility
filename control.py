#!/usr/bin/python3
"""One on-demand Sony MDR session, released after a finite JSON request."""
import json
import os
from pathlib import Path
import queue
import re
import socket
import threading
import time
from protocol import UUID,Framer,encode,functions,presets,eq,build_set

class Session:
    def __init__(self,address):self.address=address;self.sock=None;self.seq=0;self.framer=Framer();self.pending=[]
    def __enter__(self):
        import dbus,dbus.service,dbus.mainloop.glib
        from gi.repository import GLib
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        self.bus=dbus.SystemBus();self.path='/org/krysto/sonyutility/p'+str(os.getpid());self.loop=GLib.MainLoop();self.received=queue.Queue()
        # Identity is verified from BlueZ before opening the proprietary channel.
        objects=dbus.Interface(self.bus.get_object('org.bluez','/'),'org.freedesktop.DBus.ObjectManager').GetManagedObjects()
        matches=[(path,i['org.bluez.Device1']) for path,i in objects.items() if 'org.bluez.Device1' in i and str(i['org.bluez.Device1'].get('Address','')).upper()==self.address.upper()]
        if len(matches)!=1:raise ValueError('Headset not found')
        device,props=matches[0]
        if str(props.get('Name','')).upper()!='WH-CH520' or not props.get('Paired') or not props.get('Connected') or UUID not in [str(u) for u in props.get('UUIDs',[])]:raise ValueError('Supported paired headset required')
        received=self.received
        class Profile(dbus.service.Object):
            @dbus.service.method('org.bluez.Profile1',in_signature='oha{sv}',out_signature='')
            def NewConnection(self,device,fd,properties):received.put(fd.take())
            @dbus.service.method('org.bluez.Profile1',in_signature='o',out_signature='')
            def RequestDisconnection(self,device):pass
            @dbus.service.method('org.bluez.Profile1',in_signature='',out_signature='')
            def Release(self):pass
        self.profile=Profile(self.bus,self.path);self.manager=dbus.Interface(self.bus.get_object('org.bluez','/org/bluez'),'org.bluez.ProfileManager1')
        self.manager.RegisterProfile(self.path,UUID,{'Role':'client','Name':'Sony Utility'})
        self.thread=threading.Thread(target=self.loop.run,daemon=True);self.thread.start()
        try:
            dbus.Interface(self.bus.get_object('org.bluez',device),'org.bluez.Device1').ConnectProfile(UUID,reply_handler=lambda:None,error_handler=lambda error:received.put(RuntimeError(str(error))))
            fd=received.get(timeout=8)
            if isinstance(fd,Exception):raise fd
            self.sock=socket.socket(fileno=fd);self.sock.settimeout(2)
            return self
        except BaseException:self.__exit__(None,None,None);raise
    def __exit__(self,*_):
        if self.sock:self.sock.close()
        if hasattr(self,'manager'):
            try:self.manager.UnregisterProfile(self.path)
            except Exception:pass
        if hasattr(self,'profile'):self.profile.remove_from_connection()
        if hasattr(self,'loop'):self.loop.quit()
        if hasattr(self,'thread'):self.thread.join(timeout=1)
    def receive(self,deadline):
        self.sock.settimeout(max(0.01,deadline-time.monotonic()))
        data=self.sock.recv(4096)
        if not data:raise OSError('Headset disconnected')
        for kind,seq,payload in self.framer.feed(data):
            if kind==1:
                self.seq=seq
                self.pending.append((kind,payload))
            else:
                self.sock.sendall(encode(1,1-seq))
                self.pending.append((kind,payload))
            if len(self.pending)>128:raise ValueError("Too many pending frames")
    def command(self,payload,kind=12):
        self.pending=[(k,p) for k,p in self.pending if k!=1]
        expected=1-self.seq
        self.sock.sendall(encode(kind,self.seq,payload))
        deadline=time.monotonic()+2
        while time.monotonic()<deadline:
            for n,(k,p) in enumerate(self.pending):
                if k==1:
                    self.pending.pop(n)
                    if self.seq!=expected:raise ValueError('Invalid ACK sequence')
                    return
            self.receive(deadline)
        raise TimeoutError('MDR acknowledgment missing')
    def request(self,payload,reply,kind=12,timeout=1.2):
        # Replies queued before this GET must not confirm this transaction.
        self.pending=[(k,p) for k,p in self.pending if not (k==kind and p.startswith(reply))]
        self.command(payload,kind)
        deadline=time.monotonic()+timeout
        while time.monotonic()<deadline:
            for n,(k,p) in enumerate(self.pending):
                if k==kind and p.startswith(reply):self.pending.pop(n);return p
            try:self.receive(deadline)
            except socket.timeout:return None
        return None


def snapshot(conn):
    hello=conn.request(b'\x00\x00',b'\x01\x00')
    if not hello or len(hello)!=8 or hello[6]!=0:raise ValueError('MDR v2 required')
    caps=conn.request(b'\x06\x00',b'\x07\x00')
    if caps is None:raise ValueError('No capabilities')
    features=functions(caps);state={};errors={}
    def read(label,request,reply,parse,kind=12):
        try:
            p=conn.request(request,reply,kind)
            if p is not None:state.update(parse(p))
        except (ValueError,TimeoutError):errors[label]='unsupported'
    if 0x50 in features:
        read('presets',b'\x50\x00\x01',b'\x51\x00',lambda p:{'presets':presets(p)})
        read('eq',b'\x56\x00',b'\x57\x00',eq)
    if 0xe2 in features:
        read('dsee',b'\xe6\x01',b'\xe7\x01',lambda p:{'dsee':bool(p[2])} if len(p)==3 and p[2] in (0,1) else {})
    if 0xe1 in features:
        read('priority',b'\xe6\x00',b'\xe7\x00',lambda p:{'priority':p[2]} if len(p)==3 and p[2] in (0,1) else {})
    read('firmware',b'\x04\x02',b'\x05\x02',lambda p:{'firmware':p[3:].decode('utf-8',errors='replace')} if len(p)>=3 and p[2]<=64 and len(p)==3+p[2] else {})
    if 0x18 in features:
        read('multipoint',b'\x12\x06',b'\x13\x06',lambda p:{'multipoint':1 in p[3:]} if len(p)>=3 and len(p)==3+p[2] else {})
    if hello[7]==0:
        c2=conn.request(b'\x06\x00',b'\x07\x00',14)
        f2=functions(c2) if c2 else set()
        voiceType=1 if 0x41 in f2 or 0x42 in f2 else 0 if 0x40 in f2 else None
        if voiceType is not None:
            read('voice',bytes([0x46,voiceType]),bytes([0x47,voiceType]),lambda p:{'voice':p[2]==0,'voiceType':voiceType} if len(p)==(4 if voiceType==1 else 3) and p[2] in (0,1) else {},14)
    return {'ok':True,'state':state,'errors':errors}


def run(request):
    if not isinstance(request,dict) or request.get('op') not in ('status','set') or request.get('transport')!='bluetooth':raise ValueError('Invalid request')
    address=request.get('address','')
    if not isinstance(address,str) or not re.fullmatch(r'(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}',address):raise ValueError('Invalid address')
    if request['op']=='set' and request.get('feature') not in ('preset','bands','dsee','priority','voice'):raise ValueError('Unsupported command')
    # Cross-process lock keeps several bar instances from holding the Sony service.
    import fcntl
    runtime=Path(os.environ.get('XDG_RUNTIME_DIR','/tmp'))
    lockpath=runtime/('sony-utility-'+str(os.getuid())+'.lock')
    fd=os.open(lockpath,os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        with Session(address) as conn:
            result=snapshot(conn)
            if request['op']=='set':
                feature=request['feature'];value=request.get('value');kind,payload,get=build_set(feature,value,result['state'])
                conn.command(payload,kind)
                # Transport ACK is not evidence that the device applied a setting.
                time.sleep(.4)
                reply=bytes([(get[0]+1)&255,get[1]])
                p=conn.request(get,reply,kind)
                if p is None:return {'ok':False,'error':'unconfirmed'}
                if feature in ('preset','bands'):actual=eq(p);result['state'].update(actual)
                elif feature=='voice':
                    actual={'voice':p[2]==0} if len(p)==(4 if result['state'].get('voiceType')==1 else 3) and p[2] in (0,1) else {}
                    result['state'].update(actual)
                else:
                    actual={feature:bool(p[2]) if feature=='dsee' else p[2]} if len(p)==3 and p[2] in (0,1) else {}
                    result['state'].update(actual)
                if actual.get(feature)!=value:return {'ok':False,'error':'unconfirmed'}
                result['sent']=feature
            return result

if __name__=='__main__':
    import sys
    try:
        if len(sys.argv)!=2 or len(sys.argv[1])>2048:raise ValueError('Invalid request')
        result=run(json.loads(sys.argv[1]))
    except Exception as exc:
        result={'ok':False,'error':'unavailable'}
        print(type(exc).__name__+': '+str(exc),file=sys.stderr)
    print(json.dumps(result,ensure_ascii=False))
