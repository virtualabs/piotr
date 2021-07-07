"""
Piotr command line helper.
"""

from blessings import Terminal

class OperationNotSupported(Exception):
    pass

class ModulesRegistry:
    """
    Command line modules registry.
    """

    # registered modules
    registered_modules = {}

    @staticmethod
    def register(module_name, module_class):
        if module_name not in ModulesRegistry.registered_modules:
            ModulesRegistry.registered_modules[module_name] = None
        ModulesRegistry.registered_modules[module_name] = module_class

    @staticmethod
    def has(module_name):
        return (module_name in ModulesRegistry.registered_modules)

    @staticmethod
    def get(module_name):
        if ModulesRegistry.has(module_name):
            return ModulesRegistry.registered_modules[module_name]

    @staticmethod
    def enumerate():
        sorted_modules = []
        for module in ModulesRegistry.registered_modules:
            sorted_modules.append((module, ModulesRegistry.registered_modules[module]))
        sorted_modules.sort()
        for module in sorted_modules:
            yield module

class command:
    def __init__(self, description, args_desc=None):
        self.__desc = description
        self.__args_desc = args_desc

    def __call__(self, f):
        f.desc = self.__desc
        f.command = True
        f.args_desc = self.__args_desc
        return f


class module:
    """
    Class decorator to automagically register modules into our registry.
    """
    def __init__(self, module_name, module_desc=''):
        self.module_name = module_name
        self.module_desc = module_desc

    def __call__(self, clazz):
        ModulesRegistry.register(
            self.module_name,
            clazz
        )
        clazz.module_name = self.module_name
        clazz.module_desc = self.module_desc
        return clazz

class CmdlineModule:

    def __init__(self):
        self.term = Terminal()

    def __split_padding(self, message):
        for i in range(len(message)):
            if message[i]!=' ' and message[i]!='\t':
                return (message[:i], message[i:])
        return message

    def error(self, message):
        """
        Display an error in red.
        """
        padding,message = self.__split_padding(message)
        print(padding + self.term.red + message + self.term.normal)

    def warning(self, message):
        """
        Display a warning in bold.
        """
        padding,message = self.__split_padding(message)
        print(padding + self.term.bold + message + self.term.normal)

    def important(self, message):
        """
        Display an important message.
        """
        padding,message = self.__split_padding(message)
        print(padding + self.term.magenta + message + self.term.normal)

    def title(self, message):
        padding,message = self.__split_padding(message)
        print(padding + self.term.underline + message + self.term.normal)

    def has(self, operation):
        """
        Check if class implements a given operation.
        """
        try:
            attr = getattr(self, operation)
            return (callable(attr) and hasattr(attr, 'command') and hasattr(attr, 'desc'))
        except AttributeError as error:
            return False

    def dispatch(self, operation, options):
        """
        Dispatch operation to the right method.
        """
        if self.has(operation):
            method = getattr(self, operation)
            method(options)
        else:
            print(' Unknown operation "%s"' % operation)
            self.help(options)

    @command('Shows this help')
    def help(self, options=[]):
        """
        Loop on commands.
        """
        methods = {}
        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            if callable(attr) and hasattr(attr, 'command') and hasattr(attr, 'desc'):
                methods[attr_name] = {
                    'desc': getattr(attr, 'desc'),
                    'args': getattr(attr, 'args_desc')
                }
        commands = []
        for i in methods:
            commands.append((i, methods[i]['desc'], methods[i]['args']))
        commands.sort()

        self.title(' Available commands:\n')
        for cmd in commands:
            if cmd[2] is not None:
                args_desc = ' '.join(['(%s)' % arg[1:] if arg.startswith('?') else '<%s>'%arg for arg in cmd[2]])
                cmd_line = (self.term.bold + '{command_name:<50}' + self.term.normal + '{command_desc:<50}').format(
                    command_name='  %s %s %s' % (self.module_name, cmd[0], args_desc),
                    command_desc=cmd[1]
                )
            else:
                cmd_line = (self.term.bold + '{command_name:<50}' + self.term.normal + '{command_desc:<50}').format(
                    command_name='  %s %s' % (self.module_name, cmd[0]),
                    command_desc=cmd[1]
                )
            print(cmd_line)
        print('')
