"""
Logging module.
"""
import logging

class Logger:
    """
    Logger helper.
    """

    loggers = {}
    level = logging.WARNING

    def __init__(self, logger):
        self.__level = Logger.level
        self.__logger = logging.getLogger(logger)

        # set formatter
        #formatter = logging.Formatter('[%(name)s] - %(levelname)s - %(message)s')
        formatter = logging.Formatter('[%(levelname)s] %(message)s')
        self.__channel = logging.StreamHandler()
        self.__channel.setLevel(self.__level)
        self.__channel.setFormatter(formatter)
        self.__logger.addHandler(self.__channel)

    def __getattr__(self, attr):
        if hasattr(self.__logger, attr):
            return getattr(self.__logger, attr)
        else:
            raise AttributeError()

    def setLevel_(self, level):
        print("set level to %d" % level)
        self.__level = level
        self.__logger.setLevel(level)

    @staticmethod
    def setLevel(level):
        """
        Set loggers level.

        @param  level   int     Logging level
        """
        Logger.level = level
        for i in Logger.loggers.keys():
            Logger.loggers[i].setLevel_(Logger.level)

    @staticmethod
    def single(loggerName):
        """
        Get logger singleton based on module name.

        @param string   loggerName  Module name
        @return object  Logger instance.
        """
        if loggerName not in Logger.loggers:
            Logger.loggers[loggerName] = Logger(loggerName)
        return Logger.loggers[loggerName]


def warning(module, message):
    Logger.single(module).warning(message)

def error(module, message):
    Logger.single(module).error(message)

def info(module, message):
    Logger.single(module).info(message)

def debug(module, message):
    Logger.single(module).debug(message)
