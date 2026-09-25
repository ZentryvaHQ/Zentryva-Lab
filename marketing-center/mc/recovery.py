"""Temporary local shadow checkpoint adapter, not a shared job scheduler.

Only pure bundled stages are replayed. The OS lock is released after a crash.
Command Center owns scheduling, provider cancellation, and automatic retries.
"""
import json
import os
from pathlib import Path
import tempfile
import time
from .core import digest

class Journal:
    def __init__(self, directory, max_attempts=3, deadline_seconds=60, control=None):
        self.directory=Path(directory)
        self.max_attempts=max_attempts
        self.deadline_seconds=deadline_seconds
        self.handle=None
        self.control=control

    def __enter__(self):
        self.directory.mkdir(parents=True,exist_ok=True)
        self.handle=(self.directory/'writer.lock').open('a+b')
        self.handle.seek(0,2)
        if self.handle.tell()==0:
            self.handle.write(b'0');self.handle.flush()
        self.handle.seek(0)
        try:
            if os.name=='nt':
                import msvcrt
                msvcrt.locking(self.handle.fileno(),msvcrt.LK_NBLCK,1)
            else:
                import fcntl
                fcntl.flock(self.handle.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        except OSError:
            self.handle.close();self.handle=None
            raise ValueError('Shadow run already has an active writer') from None
        self.deadline=time.monotonic()+self.deadline_seconds
        return self

    def __exit__(self,*args):
        if self.handle:
            self.handle.close();self.handle=None

    def _save(self,path,value):
        descriptor,name=tempfile.mkstemp(prefix='.writing-',dir=self.directory)
        try:
            with os.fdopen(descriptor,'w',encoding='utf-8') as stream:
                json.dump(value,stream,allow_nan=False)
                stream.flush();os.fsync(stream.fileno())
            os.replace(name,path)
        finally:
            if os.path.exists(name):os.unlink(name)

    def call(self,key,operation):
        if self.handle is None:raise ValueError('Checkpoint writer lock required')
        if self.control: self.control()
        if time.monotonic()>=self.deadline:raise ValueError('Shadow execution deadline reached')
        identity=digest(key)
        path=self.directory/('step-'+identity+'.json')
        old=json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
        if old and (old.get('identity')!=identity or old.get('checksum')!=digest({k:v for k,v in old.items() if k!='checksum'})):
            raise ValueError('Checkpoint integrity failed')
        if old.get('state')=='COMPLETE':return old['result']
        attempts=old.get('attempts',0)+1
        if attempts>self.max_attempts:raise ValueError('Shadow retry budget exhausted; diagnosis required')
        def save(state,**fields):
            item=dict(identity=identity,state=state,attempts=attempts,**fields)
            item['checksum']=digest(item);self._save(path,item)
        save('RUNNING')
        try:
            result=operation()
            if time.monotonic()>=self.deadline:raise TimeoutError()
            save('COMPLETE',result=result)
        except Exception:
            save('FAILED',error='STAGE_FAILED',retry_owner='Command Center or explicit local rerun')
            raise ValueError('Shadow stage failed; sanitized checkpoint preserved') from None
        # Preserve successful pure-stage work before observing a new pause.
        if self.control: self.control()
        return result

    def operation(self,registry,module,operation,*args):
        registry._ready(module)
        identity=[registry.tenant_id,registry.snapshot(),module,operation,args]
        return self.call(identity,lambda:registry.call(module,operation,*args))
