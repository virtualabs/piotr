"""
Basic command parser.
"""

def parse_command(command_line):
    """
    Parse command and returns argv.
    """
    argv = []
    string_marker=None
    in_arg = False
    in_str = False
    acc = ''
    escaped = False
    i=0
    while i<len(command_line):
        if command_line[i]!=' ':
            if not in_arg:
                in_arg = True

            # If escape character met in string, continue.
            if in_str and command_line[i] == '\\':
                escaped = True
                acc = acc + '\\'
            else:
                # Consider string markers only if not escaped
                if not escaped:
                    if string_marker is None:
                        if command_line[i] == '"':
                            string_marker = '"'
                            in_str = True
                        elif command_line[i] == "'":
                            string_marker = "'"
                            in_str = True
                    elif command_line == string_marker:
                        in_str = False
                        string_marker = None
                else:
                    escaped = False
                acc = acc + command_line[i]
        else:
            if not in_str:
                in_arg = False
                argv.append(acc)
                acc = ''
            else:
                acc = acc + command_line[i]
        i += 1

    if len(acc) > 0:
        argv.append(acc)

    return argv
