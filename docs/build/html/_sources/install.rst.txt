Setup instructions
==================

Requirements
------------

Piotr requires `qemu-system-arm` (Full ARM system emulation) in order to work
correctly, therefore you must install it before using `Piotr`.

Ubuntu/Debian
~~~~~~~~~~~~~

.. code-block:: text

    $ apt install qemu-system-arm

Fedora
~~~~~~

.. code-block:: text

    $ dnf install qemu-system-arm

ArchLinux
~~~~~~~~~

.. code-block:: text

    $ pacman -S qemu-system-arm



Install Piotr with pip
----------------------

You can use `pip` to install Piotr, as shown below:

.. code-block:: text

    $ pip install piotr

Install from Github
-------------------

If you want to install the latest version of Piotr from the Github repository,
run the following commands:

.. code-block:: text

    $ git clone https://github.com/virtualabs/piotr.git
    $ cd piotr
    $ python setup.py install

Additional tools and packages
-----------------------------

`Avatar2` and `gdb-multiarch` are required if you want to debug a process inside a virtual device from
Python. Note that if `Avatar2` is not installed, there is no need to install `gdb-multiarch`.