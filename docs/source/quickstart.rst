==========
Quickstart
==========

This section introduces `Piotr` and demonstrates its basic usages.

Import an example virtual device
================================

Piotr allows you to import (and export) any virtual device, you can use this
feature to install on your system *Saumil Shah*'s Damn Vulnerable ARM Router as
shown below:

.. code-block:: text

    $ wget https://github.com/virtualabs/piotr/blob/main/examples/dvar.piotr?raw=true
    $ sudo piotr device add dvar.piotr
    $ rm dvar.piotr

The Damn Vulnerable Arm Router is now available in your virtual devices, as
shown with the `device list` command:

.. code-block:: text

    $ piotr device list

    Installed devices:

      > dvar:           Damn Vulnerable ARM Router by Saumil Shah (platform: virt, cpu: -)
    
     1 device(s) available

Start an instance of Damn Vulnerable ARM Router
===============================================

Once the Damn Vulnerable ARM Router installed, you can directly launch it with
the following command:

.. code-block:: text

    $ sudo piotr device start dvar

`sudo` is required as Qemu needs some administrative rights to access the network
and forward packets from the localhost to the emulated device. You will be prompted
with a Piotr banner and will have a shell on the host
system. This is the host system, not the emulated device's. You then need to
start the services belonging to the emulated device by calling the `target-start`
command in the host shell, as shown below:

.. code-block:: text

    [Host]# target-start
    random: fast init done
    System ready
    Control Server started on port 8080


    BusyBox v1.24.2 () built-in shell (ash)

    [Guest]#

This device listens on port `8081` and `8080`, and you can check it is working
by browsing the URL `http://localhost:8080` that will show you something like
this:

**TODO: add screenshot**

In another terminal, you may check that an instance is actually running with 
the following command:

.. code-block:: text

    $ sudo piotr device running
    sudo piotr device running
    Running instances:

      Instance name                           Device                                  
    > kind_hofstadter                         Damn Vulnerable ARM Router by Saumil Shah

    1 running instance(s)

Each running instance is given a random name, unless you specify it when
starting a device. The one created here is `kind_hofstadter`, and it identifies
this instance. This may be useful if you have multiple running instances.

Listing instance active processes
=================================

Piotr provides also some specific command-line tools that may be helpful.
`piotr-ps` allows you to list all the active processes for a given instance:

.. code-block:: text

    $ sudo piotr-ps 
    PID   USER     COMMAND
        1 root     init
        2 root     [kthreadd]
        3 root     [rcu_gp]
        4 root     [rcu_par_gp]
        5 root     [kworker/0:0-eve]
        6 root     [kworker/0:0H-kb]
        7 root     [kworker/u2:0-ev]
        8 root     [mm_percpu_wq]
        9 root     [ksoftirqd/0]
       10 root     [rcu_sched]
       11 root     [rcu_bh]
       12 root     [migration/0]
       13 root     [cpuhp/0]
       14 root     [kdevtmpfs]
       15 root     [kworker/u2:1-fl]
       79 root     [kworker/0:1-eve]
      111 root     [khungtaskd]
      257 root     [oom_reaper]
      258 root     [writeback]
      260 root     [kcompactd0]
      261 root     [crypto]
      263 root     [kblockd]
      264 root     [ata_sff]
      381 root     [rpciod]
      382 root     [kworker/u3:0]
      383 root     [xprtiod]
      398 root     [kswapd0]
      469 root     [nfsiod]
      548 root     [kworker/0:1H-kb]
      647 root     [ext4-rsv-conver]
      664 root     /sbin/syslogd -n
      668 root     /sbin/klogd -n
      705 root     /sbin/dhcpcd -f /etc/dhcpcd.conf
      711 root     /usr/bin/qemu-ga -p /dev/vport0p1
      712 root     -sh
      731 root     {target-start} /bin/sh /usr/sbin/target-start
      735 root     {init.sh} /bin/sh /piotr/init.sh
      744 root     /usr/bin/miniweb
      745 root     /usr/bin/lightsrv
      746 root     sh
      767 root     /bin/ps aux


Accessing a pseudo-shell on the emulated device
===============================================

Piotr provides the `piotr-shell` utility that behaves almost like a *normal*
shell except you cannot change directory (a limitation of the current
implementation):

.. code-block:: text

    $ sudo piotr -g -i
    >> PIOTR v1.0
    >>
    >> This is an interactive pseudo-shell with limitations:
    >>   - all commands are executed from the root directory
    >>   - stderr is not captured and won't be displayed
    >>   - no commands history
    >>   - no real-time standard output, commands are executed
    >>     and results shown once done

    [Guest]#


Debugging a remote process with gdb-multiarch
=============================================

Piotr provides the `piotr-debug` utility that basically runs a `gdbserver`
inside the host system and attach it to a given PID:

.. code-block:: text

    $ sudo piotr-debug 725
    Starting gdbserver on the target instance (kind_hofstadter)
    Gdbserver is now running on instance with PID 839

Once `gdbserver` attached to the target process, you may use `gdb-multiarch`
to connect to it and remotely debug the target process. 


