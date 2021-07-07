Piotr: Pythonic IoT exploitation and Research
=============================================


Introduction to Piotr
---------------------

Piotr is an emulation helper for Qemu that provides a convenient way to
create, share and run virtual IoT devices. It only supports the ARM Architecture
at the moment.

Piotr is heavily inspired from @therealsaumil's `ARM-X framework <https://github.com/therealsaumil/armx>`_ and keeps the
same approach: emulated devices run inside an emulated host that provides
all the tools you may need and creates a fake environment for them. This
approach allows remote debugging with gdbserver or fridaserver, provides a
steady platform for vulnerability research, exploitation and training.

Moreover, Piotr is able to package any emulated device into a single file that
may be shared and imported by other users, thus sharing its kernel, DTB file or
even its host filesystem. This way, it is possible to create new emulated
devices based upon existing ones, and to improve all of them by simply changing
a single file (kernel, host filesystem, etc.).


How does Piotr work ?
---------------------

Piotr stores everything it needs inside a specific user directory called `.piotr`,
located in the user's home directory. This directory stores all the kernels, dtb
files, host filesystems and emulated devices.

Each emulated device is stored in a specific subdirectory of your `.piotr/devices`
directory, and must contain at least:

 * a *config.yaml* file containing the device's qemu configuration in a readable way
 * a root filesystem with correct permissions and groups and users

When Piotr is asked to emulate a specific device, it loads its *config.yaml* file,
parses it and creates a Qemu emulated device with the corresponding specifications.

This emulated device can then be driven by Piotr's helper tools in order to:

 * list or kill running processes
 * dynamically configure network interfaces
 * debug any process running on the emulated device
 * ...


Reference documentation
-----------------------

Piotr's reference documentation is available on `Read The Docs <https://piotr.readthedocs.io/>`_.
If you want to start using Piotr as soon as possible, we recommend you to read our `Quickstart guide <https://piotr.readthedocs.io/en/latest/quickstart.html>`_ !


License
-------

Piotr is released under the MIT license, see LICENSE for more information.