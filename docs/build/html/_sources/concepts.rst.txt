===============
What is Piotr ?
===============

Piotr is a framework designed to create, run, instrument and share virtual
devices. It is designed for trainers and security researchers in order to provide
an easy way to virtualize an existing device and instrument it with Piotr's API
to automate an analysis or to automatically exploit a vulnerability.

Piotr uses Qemu as its emulation core, and especially Qemu's full system emulation
for the ARM architecture. It is the only supported architecture so far, but others
may be supported in the future depending on Qemu capabilities and evolution.

Piotr is quite similar to Saumil Shah's ARM-X emulation environment, but differs
in many ways:

* its architecture is simpler than ARM-X, with no network connection required
* it is really easy to install (even for trainees)
* it provides a convenient way to define virtual devices
* it provides specific tools and a Python API to interact with running virtual devices

Emulation approach
==================

Piotr follows the same model `ARM-X` previously introduced, relying on a Linux
host system that will be used to bootstrap the target environment. The target
system runs in a chroot-ed environment inside the host system, thus allowing
to debug its processes, access its filesystem without any restriction, etc.

The target device filesystem is mounted over 9P which is a file sharing protocol
that does not require any network connection and that is handled by the Linux
kernel. No need to host a *samba* server, it works out of the box on any Linux
computer.

Virtual devices are defined by a set of files, including a YAML configuration
file that tells Piotr how to emulate this device and many more options that may
be used to define its behavior.

Virtual device components
=========================

A virtual device is defined by the following components:

* A linux kernel compatible with the original device system
* An optional DTB (*Device-tree block*) file that specifies the internal components and how they are interconnected
* Two filesystems: one for the host and another one for the target device
* A set of scripts that will be used by Piotr to launch the target inside the emulated host system

Piotr manages separately the following components:

* virtual devices definitions (including configuration file, root filesystem and more)
* Host linux kernels that are used by the emulated host system and provides all the required tools to analyse the target system
* Host root filesystems

A stock host Linux kernel and host root filesystem is included in Piotr and automatically installed.
These linux kernel and root filesystem provides multiple tools and are designed to automate as much
tasks as possible.

Anyway, you may design your own root filesystems or kernels with your own tools and configuration, and install them with Piotr.
By doing so, multiple virtual devices may rely on them avoiding redundancy. These kernels and filesystems will
be automatically added to exported virtual devices, and installed during importation.

Piotr for training
==================

As a trainer, I often needed a way to share a virtual device with my trainees. Installing
Qemu, configuring it and running a virtual device on a Linux system is far from straightforward,
and many trainees had a hard time launching a single virtual device. 

Piotr provides a convenient way to export and import virtual devices that will make your life
easier. Just make trainees install piotr on their systems, share the virtual device packaged file
with them and let them import and run it. That's no more difficult than that, and it saves time.

Piotr API
=========

Piotr, as a Python-based framework, provides a Python module to interact with a running
virtual device and automate various tasks: create and enumerate processes, access its 
filesystem, or attach a gdbserver to a specific PID. This could be interesting if you
want to automate some specific tasks, instruments a virtual device or even automate
the exploitation of a vulnerability.

