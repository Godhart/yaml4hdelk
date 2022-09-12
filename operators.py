"""
Parse operators string

String like 'value1 and value2 or (value3 and mux(@clk, %cke, #rst, $select, value4, value 5 and (value6 or value 7)) )'
where and, or - simple operators (also xor, not, nand, nor, nxor, +, -, *, /, **, srl, sra, sll, sla )
mux - units with single output (also dmx, fd, fdr, fds, fdc, fdp, ram, ld, ldp, lde)
"""
import re
import copy

# TODO: recursion protection?
# TODO: freestyle unit description where units and nets are mixed
# TODO: autonaming output nets by operator instance itself
# TODO: buffer op


NEG = "~"   # TODO: replaces "~" with NEG in the code
KIND_OP = "op"
KIND_UNIT = "unit"
KIND_FMS = "fsm"
KIND_PORT = "port"
TYPE_ASSIGN = "assign"
DUMMY_TOKEN = "_dummy_token_"
WHITESPACES = (" ", "\t")


operators = [
    "and", "or", "xor", "nand", "nor", "nxor",
    "&&",  "||", "^",   NEG+"&" ,  NEG+"|",  NEG+"^",
    "srl", "sra", "sll", "sla",  "ror", "rol",
    "&",    # Concatenation into BUS
    "+", "-", "*", "/", "**",
    "=", "==", ">", ">=", "<", "<=",
    "eq", "ne", "gt", "ge", "lt", "le",
]

OP_MAP = {
    "and"   : "AND",
    "or"    : "OR",
    "xor"   : "XOR",
    "nand"  : "NAND",
    "nor"   : "NOR",
    "nxor"  : "NXOR",

    "&&"    : "AND",
    "||"    : "OR",
    "^"     : "XOR",
    "~&"    : "NAND",
    "~|"    : "NOR",
    "~^"    : "NXOR",

    "srl"   : "SRL",
    "sra"   : "SRA",
    "sll"   : "SLL",
    "sla"   : "SLA",
    "ror"   : "ROR",
    "rol"   : "ROL",

    ">>"    : "SRL",
    "<<"    : "SLL",

    "$>"    : "SRA",
    "$<"    : "SLA",

    "@>"    : "ROR",
    "@<"    : "ROL",

    "&"     : "CONCAT",
    "con"   : "CONCAT",

    "+"     : "ADD",
    "-"     : "SUB",
    "*"     : "MUL",
    "/"     : "DIV",

    "add"   : "ADD",
    "sub"   : "SUB",
    "mul"   : "MUL",
    "div"   : "DIV",

    "="     : "EQ",
    "=="    : "EQ",
    "!="    : "NE",
    ">"     : "GT",
    ">="    : "GE",
    "<"     : "LT",
    "<="    : "LE",

    "eq"    : "EQ",
    "ne"    : "NE",
    "gt"    : "GT",
    "ge"    : "GE",
    "lt"    : "LT",
    "le"    : "LE",
}

_COMB_IO = {"input": lambda X: f"I{X}", "output": lambda X: "Y"}
_SHIFT_IO = {"input": lambda X: f"{('IN', 'SHIFT')[X]}", "output": lambda X: "OUT"}
_COMP_IO = {"input": lambda X: f"{('A', 'B')[X]}", "output": lambda X: "O"}
def _comb_ports_count(ports):
    if isinstance(ports, int):
        return ports
    result = 0
    for k in ports:
        if k[:1]=='I':
            result += 1
    return result

OP = {
    "AND"   : {**_COMB_IO, "name": lambda ports: f"AND{_comb_ports_count(ports)}"},
    "OR"    : {**_COMB_IO, "name": lambda ports: f"OR{_comb_ports_count(ports)}"},
    "XOR"   : {**_COMB_IO, "name": lambda ports: f"XOR{_comb_ports_count(ports)}"},
    "NAND"  : {**_COMB_IO, "name": lambda ports: f"NAND{_comb_ports_count(ports)}"},
    "NOR"   : {**_COMB_IO, "name": lambda ports: f"NOR{_comb_ports_count(ports)}"},
    "NXOR"  : {**_COMB_IO, "name": lambda ports: f"NXOR{_comb_ports_count(ports)}"},

    "SRL"   : {**_SHIFT_IO, "name": lambda ports: f"SRL"},
    "SRA"   : {**_SHIFT_IO, "name": lambda ports: f"SRA"},
    "SLL"   : {**_SHIFT_IO, "name": lambda ports: f"SLL"},
    "SLA"   : {**_SHIFT_IO, "name": lambda ports: f"SLA"},
    "ROR"   : {**_SHIFT_IO, "name": lambda ports: f"ROR"},
    "ROL"   : {**_SHIFT_IO, "name": lambda ports: f"ROL"},

    "CONCAT": {"input": lambda X: f"I{X}", "output": lambda X: "O", "name": lambda ports: f"CONCAT"},

    "ADD"   : {**_COMP_IO, "name": lambda ports: f"ADD{_comb_ports_count(ports)}"},
    "SUB"   : {**_COMP_IO, "name": lambda ports: f"SUB{_comb_ports_count(ports)}"},
    "MUL"   : {**_COMP_IO, "name": lambda ports: f"MUL{_comb_ports_count(ports)}"},
    "DIV"   : {**_COMP_IO, "name": lambda ports: f"DIV"},
    "EQ"    : {**_COMP_IO, "name": lambda ports: f"EQ"},
    "NE"    : {**_COMP_IO, "name": lambda ports: f"NE"},
    "GT"    : {**_COMP_IO, "name": lambda ports: f"GT"},
    "GE"    : {**_COMP_IO, "name": lambda ports: f"GE"},
    "LT"    : {**_COMP_IO, "name": lambda ports: f"LT"},
    "LE"    : {**_COMP_IO, "name": lambda ports: f"LE"},
}

_FD_IO = {
    "input" : lambda X: f"{['D'][X]}",
    "@"     : lambda X: "CLK",
    "#"     : lambda X: "R",
    "%"     : lambda X: "CE",
    "output": lambda ports_dict: "Q"}

def _get_slice_output(ports_dict):
    for p in ports_dict.values():
        if p[0][:1] == "o":
            return ports_dict[p][0]

UNIT = {**OP,
    "FD"    :   {**_FD_IO, "name": lambda ports: f"FD"},
    "MUX"   :   {"input": lambda X: f"I{X}", "$": lambda X: "S", "output": lambda X: "O", "name": lambda ports: f"MUX{_comb_ports_count(ports)}"},
    "RAM"   :   {**_FD_IO, "$": lambda X: "A", "name": lambda ports: f"RAM"},
    "LD"    :   {**_FD_IO, "@": lambda X: "G", "#": lambda X: "CLR", "%": lambda X: "LE", "name": lambda ports: f"LD"},
    "CNT"   :   {"output": lambda X: "Q", "@": lambda X: "C", "#": lambda X: "R", "%": lambda X: "CE", "name": lambda ports: f"CNT"},
    "BBOX"  :   {**_FD_IO, "input": lambda X: f"I{X}", "output": lambda X: "O", "name": lambda ports: f"BBOX"},
    "NOT"   :   {"input": lambda X: "I", "output": lambda X: "O", "name": lambda ports: f"NOT"},
    "SLICE" :   {"input": lambda X: f"{X}", "output": lambda ports_dict: _get_slice_output(ports_dict), "name": lambda ports: f"SLICE"},
}

cooperators = [ ] # TODO: ["+", "-"], ["*", "/"]

# TODO: operands amount limits (low and high) for operators

units = [
    "FD", "RAM", "LD", "MUX", "CNT", "BBOX",
    "NOT",
    "AND", "OR", "XOR", "NAND", "NOR", "NXOR",
    "SRL", "SRA", "SLL", "SLA", "ROR", "ROL",
    "CONCAT", "SLICE",
    "ADD", "SUB", "MUL", "DIV",
    "EQ", "NE", "GT", "GE", "LT", "LE",
]

special = ["fsm", "code", ] # TODO: chain for chaining heterogenous operators by order


class Unit(object):
    def __init__(self, unit_type, ports):
        self.unit_type = unit_type
        self.ports = ports
        # TODO: check ports content depending on unit type


def token_kind(token):
    if token in units or token[0:1] == NEG and token[1:] in units:
        return KIND_UNIT
    elif token == KIND_FMS:
        return KIND_FMS
    else:
        return KIND_OP


class PrettyPrinter(object):
    def __str__(self):
        lines = [self.__class__.__name__ + ':']
        for key, val in vars(self).items():
            lines += '{}: {}'.format(key, val).split('\n')
        return '\n    '.join(lines)


class Expression(PrettyPrinter):

    def __init__(self, current_token, pos, port=False, parent=None, relative_path="/"):
        # Store token that were on creation (for debug purposes)
        self._initial_token = current_token
        self._start_pos = pos[0]
        self._parent = parent
        self._level = 0
        self._relative_path = relative_path

        # True if token is port assignment expression
        self._port = port

        # If kind is KIND_OP then content is expression with one or more operands.
        # Multiple operands are joined with op token
        # Operands could be a signal names or a units (in this case unit's output used)
        # Same op should be used for joining all operands
        # - operands are stored into tokens
        # - op (if there more than one operand) is stored in self._type
        # - expression can be with inversion modifier

        # If kind is KIND_UNIT then it's port map
        #   and it's content is one or more port assignment expressions separated with ','
        # Each port assignment expression is of KIND_OP kind
        # - Port assignment expressions would be stored into tokens
        # - Unit name would be stored in self._type
        # - Unit can be with inversion modifier

        # If kind is KIND_PORT (port assignment expression) then content is same as with KIND_OP
        # But modifier in this case contains not only inversion, but also target port name or special char

        # TODO:
        # If kind is KIND_CHAIN then it's chained expressions
        # - consequent operands with same op are joined into one operation
        # - in case if op is changed then new operation is started,
        #   output of previous operation is used as first operand for new operation
        # - operations are stored into tokens, each with kind KIND_OP

        if not port:
            # Kind of expression - op / unit / fsm
            self._kind = token_kind(current_token)

            # Expression modifier (negative)
            self._modifier = ""
            if current_token[:1] == NEG:
                self._modifier = NEG
                current_token = current_token[1:]

            # Type of op / unit
            self._type = (None, current_token)[self._kind == KIND_UNIT]
        else:
            self._kind = KIND_PORT
            self._modifier = current_token
            self._type = None

        # Op's operands / port assignment expressions / chained expressions
        self._tokens = []

        # Current port expression
        self._port_assignment = None

        # True if next token is expected to be operator
        self._expected_operator = False

    @property
    def kind(self):
        return self._kind

    @property
    def type(self):
        return self._type

    @property
    def relative_path(self):
        return self._relative_path

    @property
    def port(self):
        return self._port

    @property
    def modifier(self):
        return self._modifier

    @property
    def tokens(self):
        return copy.deepcopy(self._tokens)

    @property
    def level(self):
        if self._parent is None:
            return 0
        else:
            return self._parent.level + 1

    def __repr__(self):
        return self.__str__()

    # def __str__(self):
    #     indent = " "*4*self.level
    #     return (
    #         f"\n{indent}Expression(_initial_token={self._initial_token}, _start_pos={self._start_pos}"
    #         f"\n{indent}kind={self.kind}, type={self.type}, port={self.port},"
    #         f"\n{indent}modifier={self.modifier}, tokens=\n{self.tokens}\n)"
    #     )

    def as_dict(self):
        return {"Expression": {
            "_initial_token": self._initial_token,
            "_start_pos": self._start_pos,
            "kind": self.kind,
            "type": self.type,
            "port": self.port,
            "modifier": self.modifier,
            "tokens": self.tokens,
            "level": self.level
        }}

    def process_token(self, line, pos, token, dry_run=False, last=False, close_port=False):
        if self.kind == KIND_OP or self.kind == KIND_PORT:
            if self._expected_operator:
                if token == "":
                    if last:
                        assert "#A4 Shouldn't be here"
                    else:
                        assert "#A5 Shouldn't be here"
                else:
                    # At this moment operation operator is expected
                    if self._type is None:
                        # If this is a first operator occurrence - store it
                        if token not in operators:
                            raise ValueError(f"#01 Unexpected token '{token}' at position {pos[0]-len(token)} on line '{line}'! Operator expected")
                        if not dry_run:
                            self._type = token
                            self._expected_operator = not self._expected_operator
                    else:
                        # Otherwise - check that following operators are of same kind
                        if token != self._type:
                            raise ValueError(f"#02 Unexpected token '{token}' at position {pos[0]-len(token)} on line '{line}'! Operator '{self._type}' expected")
                        if not dry_run:
                            self._expected_operator = not self._expected_operator
            else:
                # Otherwise - append token into operands list
                if token == "":
                    if last:
                        assert "#A6 Shouldn't be here"
                    else:
                        assert "#A7 Shouldn't be here"
                else:
                    # TODO: It's enough checks in parse_line?
                    if not dry_run:
                        if isinstance(token, str):
                            if token[:1] == "~":
                                modifier = "~"
                                token = token[1:]
                            else:
                                modifier = ""
                            if token[:1] == ".":
                                token = self._relative_path + token
                            e_token = Expression(modifier, pos, False, self, relative_path=self._relative_path)
                            e_token._tokens.append(token)
                            e_token._type = TYPE_ASSIGN
                            token = e_token
                        self._tokens.append(token)
                        self._expected_operator = not self._expected_operator
            if last:
                # Expression just ended
                if len(self._tokens) == 0:
                    raise ValueError(f"#03 At least one signal or unit is expected at position {self._start_pos} on line '{line}'")
                if len(self._tokens) == 1:
                    if self._type is None:
                        self._type = TYPE_ASSIGN
                    else:
                        raise ValueError(f"#20 At least two operands is required for op, stared at position {self._start_pos} on line '{line}'")

        elif self.kind == KIND_UNIT:
            expression = True   # expression is True if token contains assignment expression

            if self._port_assignment is None:
                # If didn't created port assignment expression yet - do it now
                if token[-1:] in ("@", "#", "$", "%", ":"):
                    # If token ends with one of this chars - then it's port name or special port char
                    if not dry_run:
                        self._port_assignment = Expression(token, pos, port=True, relative_path=self._relative_path)
                    expression = False  # No expressions in token in this case
                elif token != "":
                    # Otherwise if token is not empty - it's first token for anonymous (aka default) port assignment expression
                    # Create port assignment expression then few lines later add token into it
                    if not dry_run:
                        self._port_assignment = Expression("", pos, port=True, relative_path=self._relative_path)
                else:
                    # Empty token
                    if close_port or last:
                        # Could be if this is port assignment expression closing (on ',' char or if it's end of whole port map)
                        if last:
                            # Empty tokens are allowed only if this is empty space after trailing ',' char in port map
                            # Port assignment expression isn't created in this case
                            expression = False  # Also there is no expressions in token in this case
                        else:
                            raise ValueError(f"#04 At least one operand is required for port assignment, closed at position {pos[0]} on line '{line}'")
                    else:
                        assert False, "#A1 Shouldn't be here"

            if expression:
                # If token contains expression then process it
                self._port_assignment.process_token(line, pos, token, dry_run, last = (last or close_port))

            if close_port or last:
                # When port assignment expression ended - add it in self's tokens list
                # and prepare for next port assignment (by cleaning up current)
                if self._port_assignment is not None:
                    if len(self._port_assignment._tokens) == 0:
                        # Error is possible in case if port name / special port char is specified but no assignment expression given
                        # In other case there won't be expression at all ot it'll contains assignment
                        raise ValueError(f"#05 At least one operand is required for port assignment, started at position {self._port_assignment._start_pos} on line '{line}'")
                    else:
                        if not dry_run:
                            self._tokens.append(self._port_assignment)
                            self._port_assignment = None
                else:
                    pass

            if last:
                # In case if this is end of port map - ensure there is at least one port assignment
                if len(self._tokens) == 0:
                    raise ValueError(f"#06 At least one port assignment should be in unit's port map, started at position {self._start_pos} on line '{line}'")
        else:
            raise NotImplementedError(f"#07 Expressions other than general operation, port map and port expression are not supported yet!")
        return True

    @staticmethod
    def _name_suffix(joint, inputs):
        items = [re.subn(r"\W","__", item)[0] for item in inputs]
        return joint.join(items)

    def export(self, units, nets, name_prefix=""):
        """Returns output net name, updates units and nets as necessary"""
        if self._kind == KIND_OP or self._kind == KIND_PORT:
            if self._type == TYPE_ASSIGN:
                if isinstance(self._tokens[0], str):
                    input_net = self._tokens[0]
                else:
                    input_net = self._tokens[0].export(units, nets, name_prefix)

                if "~" not in self._modifier:
                    output_net = input_net
                else:
                    unit_name = f"{name_prefix}U_{self._name_suffix('',input_net)}_inv"
                    if unit_name not in units:
                        units[unit_name]={
                            "name": UNIT["NOT"]["name"](1),
                            "unit": "<NOT>",
                        }
                        netz = units[unit_name]["nets"] = []
                        netz.append([input_net, f".I"])
                    output_net = f"{unit_name}.O"
            else:   # It's op
                inputs = []
                for t in self._tokens:
                    inputs.append(t.export(units, nets, name_prefix))
                name_suffix = self._name_suffix(f"_{self._type}_", inputs)
                unit_name = f"{name_prefix}U_{name_suffix}"
                op = OP_MAP[self._type]
                if unit_name not in units: # NOTE: With this redundant units are not instantiated
                    units[unit_name] = {
                        "name": OP[op]["name"](len(inputs)),
                        "unit": f"<{op}>".upper(),
                    }
                    netz = units[unit_name]["nets"] = []
                    for i in range(0, len(inputs)):
                        netz.append([inputs[i], f".{OP[op]['input'](i)}"])
                output_net = f"{unit_name}.{OP[op]['output'](None)}"
            if self._kind == KIND_OP:
                return output_net
            else:
                return [self._modifier, output_net]

        elif self._kind == KIND_UNIT:
            if self._type not in UNIT:
                raise ValueError(f"Unit '{self._type}' is not defined!")
            unit = UNIT[self._type]
            port_map = []
            for t in self._tokens:
                port_map.append(t.export(units, nets, name_prefix))

            # Get actual port names for each port
            anonymous_idx = 0   # Index for anonymous port map (default input)
            inputs = {} # Ports of unit itself
            add_fd = {} # Ports for additional output FD if required
            for ip in port_map:
                _fd = False
                if ip[0] == "":
                    ip[0] = unit["input"](anonymous_idx)
                    anonymous_idx += 1
                elif ip[0] in ("@", "#", "%"):
                    if "@" not in unit:
                        ip[0] = _FD_IO[ip[0]](0)
                        add_fd["__".join(ip)] = ip
                        _fd = True
                    else:
                        ip[0] = unit[ip[0]](None)
                elif ip[0] == "$":
                    if "$" not in unit:
                        raise ValueError(f"Input '$' is not defined for unit '{self._type}'")
                    else:
                        ip[0] = unit[ip[0]](None)
                elif ip[0][-1] == ":":
                    ip[0] = ip[0][:-1]
                if not _fd:
                    inputs["__".join(ip)] = ip

            # Add unit and connect it's ports
            name_suffix = f"{self._type}___{self._name_suffix('___',inputs.keys())}"
            unit_name = f"{name_prefix}U_{name_suffix}"
            if unit_name not in units:  # NOTE: With this redundant units are not instantiated
                units[unit_name] = {
                    "name": unit["name"]([v[0] for v in inputs.values()]),
                    "unit": f"<{self._type}>".upper(),
                }
                netz = units[unit_name]["nets"] = []
                for v in inputs.values():
                    netz.append([v[1], f".{v[0]}"])
            output_net = f"{unit_name}.{unit['output'](inputs)}"


            # Add output Flip-Flop if required
            if len(add_fd) > 0:
                name_suffix += f"__FD___{self._name_suffix('___',add_fd.keys())}"
                unit_name = f"{name_prefix}U_{name_suffix}"
                if unit_name not in units:  # NOTE: With this redundant units are not instantiated
                    units[unit_name] = {
                        "name": UNIT["FD"]["name"](1),
                        "unit": "<FD>",
                    }
                    netz = units[unit_name]["nets"] = []
                    for v in add_fd.values():
                        netz.append([v[1], f".{v[0]}"])
                    # Connect unit's output with flip-flop's input
                    netz.append([output_net, f".{_FD_IO['input'](0)}"])
                # Now output net is flip-flop's output
                output_net = f"{unit_name}.{_FD_IO['output'](add_fd)}"

            # Add inversion if required
            if "~" in self._modifier:
                name_suffix += "__inv"
                unit_name = f"{name_prefix}U_{name_suffix}"
                if unit_name not in units:
                    units[unit_name]={
                        "name": UNIT["NOT"]["name"](1),
                        "unit": "<NOT>",
                    }
                    netz = units[unit_name]["nets"] = []
                    netz.append([output_net, f".I"])
                output_net = f"{unit_name}.O"

            return output_net
        else:
            raise NotImplementedError(f"Export for {self._kind} is not implemented yet!")



def allowed_token_char(token, char, is_port):
    more = ""
    if token == "" and is_port:
        # @#$& for first port char
        more += "@#$%"
    if token == "" or token in ("@", "#", "$", "%") or token[-1:] == ":":
        # for first char NEG or char after @#$% is allowed
        # also NEG allowed after : (port name separator)
        more += NEG
    if re.match(r"^[A-Za-z0-9_./"+more+"]$", char) is None:
        # Allow alphanumerics with underscore, dots (port name delimiter) and hierarchy delimiters
        if char == ":" and is_port and re.match(r"^\w+$", token) is not None:
            # Also allow single ':' after alphanumerics if this is port assignment expression
            pass
        else:
            return False
    if char == "/" and "." in token:
        # no / after dot
        return False

    return True


def parse_line(line, expression, pos=None, level=0, relative_path=""):
    assert pos is not None or level==0, "#A2 Unexpected to have a pos at level 0"
    if pos is None:
        pos = [0]
    quoted = None
    escape = False
    current_token = ""
    closed_token = False

    is_unit = expression.kind == KIND_UNIT
    while pos[0] < len(line):
        char = line[pos[0]]
        add_char = None
        pos[0] += 1
        if quoted is not None:
            #############
            # Quoted line
            raise NotImplementedError("#08 Quoted strings are not implemented yet!")
            if escape:
                # TODO: check that escape sequence is OK
                escape = False
                add_char = char
            else:
                if char == "\\":
                    escape = True
                elif char == quoted:
                    quoted = None
                else:
                    add_char = char
        elif escape:
            #############
            # Escape char
            raise NotImplementedError("#09 Escape sequences are not implemented yet!")
            # TODO: check that escape sequence is OK
            escape = False
            add_char = char
        else: # not quoted and not escape
            #################
            # Open quoted
            if char in ('"', "'"):
                raise NotImplementedError("#10 Quoted strings are not implemented yet!")
                quoted = char
            #################
            # Opening bracket for nested expressions
            elif char == "(":
                if current_token in ("", NEG) \
                or token_kind(current_token) == KIND_UNIT:
                # Empty token could be if this is a nested expression
                    if expression.process_token(line, pos, DUMMY_TOKEN, dry_run=True):
                        nested = Expression(current_token, pos, relative_path=relative_path)
                        parse_line(line, nested, pos, level+1, relative_path)
                        expression.process_token(line, pos, nested)
                        current_token = ""; closed_token = False
                else:
                    # TODO: if level==0 then port map for arbitrary unit / fsm / code
                    raise ValueError(f"#11 Unsupported token '{current_token}' at position {pos[0]-len(current_token)} on line '{line}'!")

            elif token_kind(current_token) == KIND_UNIT and \
                ((closed_token is True  and char not in WHITESPACES) or
                 (closed_token is False and not allowed_token_char(current_token, char, is_unit))
                ):
            #################
            # Check no more tokens between unit and opening bracket if there were whitespace between
                # If token is closed - don't allow any char except whitespace and opening brace
                raise ValueError(f"#12 Ports/KIND_FMS specification for unit '{current_token}' expected at position {pos[0]} on line '{line}'! I.e. '(' char, not `{char}`")
            #################
            # Closing bracket
            elif char == ")":
                if level != 0:
                    expression.process_token(line, pos, current_token, last=True)
                    current_token = ""; closed_token = False
                    return
                else:
                    raise ValueError(f"#13 Unexpected '{char}' char at position {pos[0]} on line '{line}'!")
            ##################
            # Port map
            elif char in ("@", "#", "$", "%"):
                if current_token == "":
                    # Port assignment expression with special port char
                    expression.process_token(line, pos, char)
                    current_token = ""; closed_token = False
                else:
                    raise ValueError(f"#14 Unexpected '{char}' char at position {pos[0]} on line '{line}'!")
            elif char == ":":
                if re.match(r"^\w+$", current_token) is not None:
                    # Port assignment expression with port name
                    expression.process_token(line, pos, current_token+char)
                    current_token = ""; closed_token = False
                else:
                    raise ValueError(f"#15 Unexpected '{char}' char at position {pos[0]} on line '{line}'!")
            ####################
            # Port map delimiter
            elif char == ",":
                if expression.kind == KIND_UNIT:
                    expression.process_token(line, pos, current_token, close_port=True)
                    current_token = ""; closed_token = False
                else:
                    raise ValueError(f"#16 Unexpected '{char}' char at position {pos[0]} on line '{line}'!")
            ############
            # Whitespace
            elif char in WHITESPACES:
                if current_token != "":
                    # Allow whitespaces between unit name and opening bracket
                    if token_kind(current_token) == KIND_UNIT:
                        # skip whitespaces BUT mark that token is closed and no more chars before opening bracket allowed
                        closed_token = True
                    else:
                        expression.process_token(line, pos, current_token)
                        current_token = ""; closed_token = False
            #############
            # Common chars are added into current token
            elif allowed_token_char(current_token, char, is_unit):
                if not closed_token:
                    add_char = char
                else:
                    assert False, "#A3 This should be already covered by `raise ValueError(f\"Ports/KIND_FMS specification for unit...`"
            else:
                raise ValueError(f"#17 Unsupported char at position {pos} in line {line}!")

            if add_char is not None:
                current_token += add_char

    if level != 0:
        raise ValueError(f"#18 Unexpected end of line '{line}'! Nesting level={level}")

    if quoted is not None:
        raise ValueError(f"#19 Not closed quotation on line '{line}'! Check following quote: `{quoted}{current_token}`")

    # Process last token
    expression.process_token(line, pos, current_token, last=True)
    current_token = ""; closed_token = False

_TESTS = {
    "complex_test1": r"a or ~b or ~MUX(z, ~x, $~select, @~clk, #rst, %ce)",
    "complex_test2": r"/.a or ~/b/c/d.e or ~MUX(z, ~x, $~select, @~clk, #rst, %ce)",
    "test-all": r"""
io:
  A: {}
  B: {}
  AorB: {dir: out}
  2b: {}
units:
  U1: {unit: <OR>, nets: [[/.A, .I0], [/.B, .I1]]}
  U2: {unit: <XOR>, nets: [[.Y, /.NestedOps]], operators: {.I0: /.A and /.B, .I1": ~/.Z}}
nets:
  - [U1.O, .AorB]
operators:
  "OP.I0": U1.O or B.X or /.Y or ~/.Z or ~MUX(/.A, /.B, $/.SELECT, @/.CLK, %/.CE)
  "OP.I1": (U1.O or B.X or /.Y or ~/.Z or ~MUX(/.A, /.B, $/.SELECT, @/.CLK, %/.CE)) and /.Y and ~MUX(/.A, /.B, $/.SELECT)
  ".QUESTION": /.2b or ~/.2b
"""
}
