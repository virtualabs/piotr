"""
Piotr Qemu guest agent client.
"""
from base64 import b64decode
from time import sleep
from piotr.qemu import QemuGuestEnum
from piotr.util.qemu.agent import QemuGuestAgentClient

class QemuGuestNotFound(Exception):
    pass

class QemuGuest:

    def __init__(self, name):
        self.name = name

        # Enumerate guests and search for the one Specified
        instance = QemuGuestEnum.getInstanceByName(name)
        if instance is not None:
            self.pid = instance['pid']
            self.guest = instance['guest']
            if instance['agent'] is not None:
                self.agent = QemuGuestAgentClient(instance['agent'])
            else:
                self.agent = None
        else:
            raise QemuGuestNotFound()


    def run_command(self, command, args, wait=True):
        """
        Run a command in guest, wait and return the result.
        """
        if self.agent is not None:
            result = self.agent.exec(command, args, capture=True)
            if result is None:
                return None

            if 'pid' in result:
                pid = result['pid']
                if wait:
                    exited = False
                    while not exited:
                        status = self.agent.exec_status(pid)
                        exited = status['exited']
                    if 'out-data' in status:
                        return b64decode(status['out-data'])
                    else:
                        return b''
                else:
                    return pid
            else:
                return None
