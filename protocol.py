"""Bounded Sony MDR v2 table 1/2 codec. Independently implemented from libmdr schemas.
No ANC, firmware, pairing, reset, poweroff or raw-command API.
"""
import struct

UUID='956c7b26-d49a-4ba8-b03f-b17d393cb6e2'

def encode(kind,seq,payload=b''):
    if kind not in (1,12,14) or seq not in (0,1) or len(payload)>4096: raise ValueError('Invalid frame')
    body=bytes([kind,seq])+struct.pack('>I',len(payload))+bytes(payload)
    body+=bytes([sum(body)&255])
    return b'\x3e'+b''.join(bytes([0x3d,b&0xef]) if b in (0x3c,0x3d,0x3e) else bytes([b]) for b in body)+b'\x3c'

class Framer:
    def __init__(self):self.buffer=b''
    def feed(self,data):
        self.buffer+=bytes(data)
        if len(self.buffer)>16384: self.buffer=b'';raise ValueError('Oversized stream')
        result=[]
        while True:
            start=self.buffer.find(b'\x3e')
            if start<0:self.buffer=b'';break
            self.buffer=self.buffer[start:]
            end=self.buffer.find(b'\x3c',1)
            if end<0:break
            encoded,self.buffer=self.buffer[1:end],self.buffer[end+1:]
            body=bytearray();i=0
            while i<len(encoded):
                b=encoded[i];i+=1
                if b==0x3d:
                    if i==len(encoded) or encoded[i] not in (0x2c,0x2d,0x2e): raise ValueError('Invalid escape')
                    b=encoded[i]|0x10;i+=1
                body.append(b)
            if len(body)<7: raise ValueError('Short frame')
            kind,seq=body[:2];length=int.from_bytes(body[2:6],'big')
            if kind not in (1,12,14) or seq not in (0,1) or length>4096 or len(body)!=7+length or sum(body[:-1])&255!=body[-1]:raise ValueError('Invalid frame')
            result.append((kind,seq,bytes(body[6:-1])))
        return result

def functions(payload):
    if len(payload)<3 or payload[:2]!=b'\x07\x00' or len(payload)!=3+2*payload[2]:raise ValueError('Invalid capabilities')
    return set(payload[3::2])

def presets(payload):
    if len(payload)<5 or payload[:2]!=b'\x51\x00' or payload[2]>32 or payload[3]>127 or payload[4]>32:raise ValueError('Invalid EQ capability')
    out=[];pos=5
    for _ in range(payload[4]):
        if pos+2>len(payload):raise ValueError('Truncated preset')
        value,size=payload[pos:pos+2];pos+=2
        if size>96 or pos+size>len(payload):raise ValueError('Invalid label')
        name=payload[pos:pos+size].decode('utf-8',errors='replace');pos+=size
        if any(p['value']==value for p in out):raise ValueError('Duplicate preset')
        out.append({'value':value,'name':name})
    if pos!=len(payload):raise ValueError('Trailing preset data')
    return out

def eq(payload):
    if len(payload)<4 or payload[0] not in (0x57,0x59) or payload[1]!=0:raise ValueError('Invalid EQ')
    n=payload[3]
    if n not in (0,6) or len(payload)!=4+n or any(v>20 for v in payload[4:]):raise ValueError('Unsupported EQ layout')
    out={'preset':payload[2]}
    if n==6:out['bands']=[v-10 for v in payload[4:]]
    return out

def build_set(feature,value,state):
    if feature=='preset' and type(value) is int and value in [p['value'] for p in state.get('presets',[])]:
        return 12,bytes([0x58,0,value,0]),bytes([0x56,0])
    if feature=='bands' and isinstance(value,list) and len(value)==6 and all(type(v) is int and -10<=v<=10 for v in value) and 'bands' in state and state.get('preset') in (0xa0,0xa1,0xa2) and state['preset'] in [p['value'] for p in state.get('presets',[])]:
        return 12,bytes([0x58,0,state['preset'],6])+bytes(v+10 for v in value),bytes([0x56,0])
    if feature=='dsee' and type(value) is bool and 'dsee' in state:
        return 12,bytes([0xe8,1,int(value)]),bytes([0xe6,1])
    if feature=='priority' and type(value) is int and value in (0,1) and 'priority' in state:
        return 12,bytes([0xe8,0,value]),bytes([0xe6,0])
    if feature=='voice' and type(value) is bool and 'voice' in state and state.get('voiceType') in (0,1):
        t=state['voiceType'];return 14,bytes([0x48,t,0 if value else 1]),bytes([0x46,t])
    raise ValueError('Unsupported setting')
