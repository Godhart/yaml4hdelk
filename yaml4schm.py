import copy
import os
import yaml
import json
import re
import argparse
from yaml4schm_defs import *
from operators import Expression, parse_line

_SKIP_TODO        = True
_IGNORE_UNCERTAIN = True

_VERSION = "2.1a0.0"
_VERSION_HISTORY = {
    "2.1": "Basic support for operators (though work and checks still WIP)",
    "2.0": "Refactored v1. Works as standalone app and as a part of server (server.py)",
}
_INFO = f"""
yaml4schm, version {_VERSION}

Provides generation of HTML with hardware schematic from textual description
in YAML format.
Uses HDElk or d3-schematic tools to generate graphics
"""
# TODO: recursion protection
# TODO: add custom styles
# TODO: intermediate nets for expressions

_ROOT_PATH = None


def find_file(root: str, filename: str) -> str or None:
    """
    Looks for full path by given filename within root and under
    :param root: root to start looking from
    :param filename: specified filename
    :return: full file path if found otherwise None
    """
    f_low = filename.lower()
    for root, dirs, files in os.walk(_ROOT_PATH):
        fl = [fn.lower() for fn in files]
        for fn in (f_low, f_low+".yaml", f_low+".yml"):
            if fn in fl:
                return os.path.join(root, fn)
    return None


def guess_filepath(root: str, path: str) -> str:
    """
    Guesses full file path by given path
    :param root: root to start looking from
    :param path: specified path
    Special patterns for path:
        If path starts with @ then it's relative to _ROOT_PATH
        If path is within angle braces < > then path should be a filename and it would be searched within _ROOT_PATH
    :return: full file path
    """
    if path[0:1] == "@":
        if _ROOT_PATH is None:
            raise ValueError("For usage of paths, starting with `@`, a root path should be specified")
        return os.path.join(_ROOT_PATH, path[1:])
    if path[0:1] == "<" and path[-1:] == ">":
        if _ROOT_PATH is None:
            raise ValueError("For usage of paths inside angle braces, i.e `<`,`>`, a root path should be specified")
        r = find_file(_ROOT_PATH, path[1:-1])
        if r is None:
            raise ValueError(f"File {path} wasn't found within {_ROOT_PATH}")
        return r
    return os.path.join(root, path)  # TODO: more sophisticated guessing like libs looking (i.e "lib:unit") etc


def _load(filepath: str, unit: bool = False, yaml_string: str = None) -> dict:
    """
    Loads data from given yaml file
    Processes special nodes like "source" and "merge"
    :param filepath: file path
    :param unit: loaded data is unit definition, otherwise it's treated just as structure text (YAML format)
    :param yaml_string: if set then data is loaded from yaml_string, filepath is used as root path when referencing to other files
    :return: loaded data
    """
    # TODO: input filter to separate data from it's surroundings
    if yaml_string is None:
        with open(filepath, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    else:
        data = yaml.safe_load(yaml_string)
    # TODO: check file exists, return stub if not

    data[A_FILEPATH] = filepath

    if unit:
        _check_allowed(data, YAML_UNIT_ALLOWED, filepath, "-", "main")

        if "attributes" not in data:
            data["attributes"] = {}
        if "type" not in data["attributes"]:
            data["attributes"]["type"] = \
                re.sub("\.[^.]*$", "", os.path.split(filepath)[-1])
        if "display" not in data:
            data["display"] = {}
        if "" not in data["display"]:
            data["display"][""] = {"view": VIEW_FULL}

    # Process "source" nodes
    data = _source(filepath, data)

    # Process "merge" nodes
    _merge(data)
    return data


def _source(parentpath: str, node: dict):
    """
    Processes "source" nodes - loads data from external file into node, that hosts "source" node
    Filepath if determined by value of "source" node
    Data in file should be a dict
    :param parentpath: filepath of node's source
    :param node: node that should be processed
    :return: alternate node version
    """
    data = {}
    for k, v in node.items():
        if k == "source":
            # Load data
            source_path = guess_filepath(os.path.split(parentpath)[0], v)
            # TODO: make stub in case of error
            partial = _load(source_path)
            # Merge loaded data
            data = {**data, **partial}
            # Take a note that data were loaded and from where
            # NOTE: could cause a problem in case of multiple source ops in a row (in a merge for example)
            data[A_FILEPATH] = source_path
        elif isinstance(v, dict):
            # Recurse if nested node is a dict
            data[k] = _source(parentpath, v)
        else:
            # Otherwise keep previous value
            data[k] = v
    return data


def _merge(node: dict):
    """
    Processes "merge" nodes - merges data from "merge" node into it's host then removes "merge" node
    "merge" node should be a list of items to merge into host
    :param node: node to process
    :return: nothing. it changes node itself
    """
    if "merge" in node:
        for m in node["merge"]:
            _merge_nodes(m, node)
        del node["merge"]
    for k, v in node.items():
        if isinstance(v, dict):
            _merge(v)


def _merge_nodes(src: dict, dst: dict):
    """
    Does actual merging for _merge
    :param src: items to be merged
    :param dst: host node
    :return: nothing. it changes dst
    """
    for k, v in src.items():
        if k in dst:
            if v is None:
                del dst[k]
            elif isinstance(v, dict) and isinstance(dst[k], dict):
                _merge_nodes(v, dst[k])
            elif isinstance(v, list) and isinstance(dst[k], list):
                dst[k] += v
            else:
                dst[k] = v
        else:
            dst[k] = v


def _rndr(data: dict, key: str, default=None):
    if RNDR in data and key in data[RNDR]:
        return data[RNDR][key]
    elif default is not None:
        if RNDR not in data:
            data[RNDR] = {}
        data[RNDR][key] = default
        return default
    return None


def _rndr_set(data: dict, key: str, value) -> None:
    if RNDR not in data:
        data[RNDR] = {}
    data[RNDR][key] = value


def _check_allowed(data: dict, allowed: dict, filepath: str, hierpath: str, section: str):
    violations = [str(k) for k in data.keys() if k not in allowed]
    if len(violations) > 0:
        raise ValueError(f"Not supported keys found for unit `{hierpath}` {section}, file source `{filepath}`\n"
                         f"    keys: {', '.join(violations)}")
    violations = [f"{k}: {v}" for k, v in data.items() if allowed[k] is not None and v not in allowed[k]]
    if len(violations) > 0:
        raise ValueError(f"Not supported values found for unit `{hierpath}` {section}, file source `{filepath}`\n"
                         f"    keys-values: {', '.join(violations)}")


def _check_all_allowed(data: list, allowed: dict, filepath: str, hierpath: str, section: str):
    for d in data:
        if isinstance(d, dict):  # TODO: ? for nets only ?
            _check_allowed(d, allowed, filepath, hierpath, section)


def _next_hierpath(hierpath, k):
    return _ext_id(hierpath) + k


def _next_localpath(localpath, k):
    if localpath == "":
        return k
    else:
        return _next_hierpath(localpath, k)


def _process_unit_instance(data: dict, filepath: str, hierpath: str = "", localpath: str = "", display: dict = None, view: str = None,
                           dig: bool = False, dig_depth: int = -1):
    """
    Determines actual view options for given unit, updates nested units as necessary
    :param data: node with unit's definition
    :param filepath: filepath for source of this node
    :param hierpath: unit's path in whole hierarchy
    :param localpath: unit's path with reference to file
    :param display: all display rules at this level of hierarchy
    :param view: view kind for this unit. None if view kind should be determined from display rules
    :param dig: dig further into unit's instance content even if unit would be displayed as symbol
    :param dig_depth: credits for digging. when reached to zero then digging stopped. reduced with every outer file load
    :return: nothing. it changes data itself
    """

    # Init filepath list
    filepath_list = [filepath]  # filepath_list is updated on every data's layer depth change

    def _filepath():
        """Returns latest seen filepath value for current data's layer"""
        return filepath_list[-1]

    if A_FILEPATH in data:
        filepath_list.append(data[A_FILEPATH])

    # Add missing fields
    for k in YAML_UNIT_KEYS:
        if k not in data:
            if k != "nets":
                data[k] = {}
            else:
                data[k] = []

    data[A_LOCALPATH] = localpath

    # Sanity check
    _check_allowed(data, {**YAML_UNIT_ALLOWED}, _filepath(), hierpath, "main")

    _check_allowed(data["attributes"], YAML_UNIT_ATTRIBUTES_ALLOWED, _filepath(), hierpath, "attributes")

    _check_all_allowed(list(data["io"].values()), YAML_IO_ALLOWED, _filepath(), hierpath, "I/O")

    _check_all_allowed(data["nets"], YAML_NET_ALLOWED, _filepath(), hierpath, "nets")

    # Update display information
    ## First use loaded
    active_display = {}
    for k, v in data["display"].items():
        active_display[_next_hierpath(hierpath, k)] = v

    ## Then override with externally specified
    if display is not None:
        for k, v in display.items():
            active_display[k] = v

    # Check how this part should be displayed before doing anything else
    data["display"] = this_display = _get_display(hierpath, active_display)

    if view is None:
        this_view = this_display.get("view", VIEW_SYMBOL)
    else:
        this_view = view

    data["display"]["view"] = this_view
    if this_view == VIEW_NONE:
        return {}

    # Check how nested parts should be displayed
    nested_view = VIEW_SYMBOL           # By default - as SYMBOL
    if this_view == VIEW_SYMBOL:        # If current view is SYMBOL and no dig specified - don't recurse further
        # If this unit's view is SYMBOL
        # and digging is not allowed or there is no more credits for dig_depth (it's not zero)
        # then drop nested units
        if not dig or dig_depth == 0:
            data["units"] = {}
            data["nets"] = []
            data["operators"] = {}
    elif this_view == VIEW_FULL:        # In FULL view nested units are displayed as SYMBOLS
        nested_view = VIEW_SYMBOL
    elif this_view == VIEW_NESTED:      # In NESTED view nested units are displayed according to their own view settings
        nested_view = None

    # Process operators
    op_units = {}
    if "operators" in data:
        for target, expression in data["operators"].items():
            # print(f"Parsing expression `{expression}` for target `{target}`")
            expr = Expression("", [0])
            parse_line(expression, expr)
            output_net = expr.export(op_units, [], "") #! # TODO: hierpath)
            # print(f"expression result: \n  Output net: {output_net}\n  Units: {op_units}")
            net_data = [output_net, target]
            if "nets" not in data:
                data["nets"] = []
            data["nets"].append(net_data)

    nested_units = data["units"]

    # Remove malformed nested units
    remove = []
    for k, v in nested_units.items():
        if "unit" not in v:
            remove.append(k)

    # TODO: raise error if there is something to remove
    for k in remove:
        del nested_units[k]

    for k, v in nested_units.items():
        # Process instance specific operators
        if "operators" in v:
            for target, expression in v["operators"].items():
                # print(f"Parsing expression `{expression}` for target `{target}`")
                expr = Expression("", [0], relative_path=k)
                parse_line(expression, expr)
                output_net = expr.export(op_units, [], "") #! # TODO: hierpath)
                # print(f"expression result: \n  Output net: {output_net}\n  Units: {op_units}")
                net_data = [output_net, target]
                if "nets" not in v:
                    v["nets"] = []
                v["nets"].append(net_data)

    if len(op_units) > 0:
        if "units" not in data:
            data["units"] = {}
        data["units"] = {**data["units"], **op_units}
        nested_units = data["units"]

    if A_FILEPATH in data:
        # Reset local path for nested units if this unit were loaded
        units_local_path = ""
    else:
        # Otherwise - update as necessary
        units_local_path = localpath

    # If units were loaded from outer file then update filepath_list
    if A_FILEPATH in data["units"]:
        filepath_list.append(data["units"][A_FILEPATH])
        # units_local_path = ""   # TODO: ? is this should affect local path ?

    # Process nested units
    for k, v in nested_units.items():
        filepath_list.append(v.get(A_FILEPATH, _filepath()))

        part_hierpath = _next_hierpath(hierpath, k)
        part_localpath = _next_localpath(units_local_path, k)

        _check_allowed(v,  YAML_UNIT_INSTANCE_ALLOWED, filepath, part_hierpath, hierpath+"/units")

        if nested_view is not None:
            # If view for nested units is already defined - use it
            part_view = nested_view
        else:
            # Otherwise - get view according to unit hierarchical path
            part_display = _get_display(part_hierpath, active_display)  # TODO: also load display from instance
            part_view = part_display.get("view", VIEW_SYMBOL)

        if isinstance(v["unit"], str):
            loaded = True   # loaded = True if unit were loaded from outer file
            nested_filepath = guess_filepath(os.path.split(_filepath())[0], v["unit"])
            v["unit"] = _load(nested_filepath, unit=True)
            # TODO: make stub in case of error
        else:
            loaded = False  # loaded = False if unit were explicitly described within it's hosting unit data
            nested_filepath = _filepath()

        _check_allowed(v["unit"],  YAML_UNIT_ALLOWED, filepath, part_hierpath, hierpath+"/units/"+k)

        if isinstance(v["unit"], dict):
            _process_unit_instance(
                v["unit"], nested_filepath, part_hierpath, part_localpath, active_display, part_view,
                dig,
                # If this unit were loaded and digging is active - reduce dig_depth
                [dig_depth, max(dig_depth-1, 0)][dig and loaded and dig_depth > 0]
                )
        else:
            raise ValueError(
                f"Unit instance should be a dict or string with path to description file! Got: {type(v['unit'])}")

        filepath_list = filepath_list[:-1]


def _get_display(hierpath: str, display: dict) -> dict:
    """
    Looks for display rules for specified unit
    :param hierpath: unit's hierarchical path
    :param display: display rules
    :return: dict with display rules for specified unit
    """
    if hierpath == "":
        hierpath = "/"
    this_display = None
    this_display_level = None
    for k, v in display.items():
        if re.match("^"+k+"$", hierpath) is not None:
            display_level = sum(c == "/" for c in k)
            if this_display_level is None \
            or this_display_level > display_level:  # Settings from higher levels of hierarchy are prior
                this_display = v    # TODO: more sophisticated approach that mixes view properties from multiple matches
                this_display_level = display_level

    if this_display is None:
        this_display = {}
    return this_display


def load_unit(filepath: str, hierpath: str = "", localpath: str = "", display: dict = None, view: str = None, yaml_string: str = None) -> dict:
    """
    Loads part/schematic description from yaml file
    :param filepath: path to file with data
    :param hierpath: path of this part in hierarchy
    :param display: display settings
    :param view: override view from display
    :param yaml_string: if set then data is loaded from yaml_string, filepath is used as root path when referencing to other files
    :return: schematic description
    """
    data = _load(filepath, unit=True, yaml_string=yaml_string)
    _process_unit_instance(data, filepath, hierpath, localpath, display, view,
                           dig=True, dig_depth=100)  # TODO: define whether to dig or not and how deep
    return data


def _to_target(data: dict, target: dict, exclude: list or tuple) -> None:
    """
    Transfers values from data dict into target dict
    Values are merged with existing (non dict values from data are replacing old values in target)
    :param data: source of values
    :param target: target to set values into
    :param exclude: list of keys with values that shouldn't be transferred
    :return:
    """
    for k in data.keys():
        if k not in exclude:
            if k not in target or not isinstance(target[k], dict):
                if data[k] is not None:
                    # Apply value to target if value isn data is not None
                    target[k] = data[k]
                elif k in target:
                    # Remove value from target if value in data is None
                    del target[k]
            else:
                # If both target and data values are dict - recurse (this way data is merged)
                _to_target(data[k], target[k], [])


def _map_attribute(node: dict, keys: list or tuple, value) -> None:
    """
    Recursion worker for _map_attributes function
    :param node: current node
    :param keys: list with fields names in hierarchical order.
    if only one key left then value is applied to node's field with key's name
    otherwise recursed into node's field with first key's name (if node's field exist then it should be a dict)
    :param value: value to set
    :return: nothing, changes data in place
    """
    assert len(keys) > 0, "Something went wrong"

    if len(keys) == 1:
        node[keys[0]] = value
    else:
        if isinstance(keys[0], (list, tuple)):
            assert all(isinstance(k, (list, tuple)) for k in keys), "Something went wrong"
            for k in keys:
                _map_attribute(node, k, value)
        else:
            if keys[0] not in node:
                node[keys[0]] = {}
            _map_attribute(node[keys[0]], keys[1:], value)


def _map_attributes(data: dict, attributes: dict, keys_map: dict) -> None:
    """
    Applies values from attributes dict into target (data)
    keys_map is used to determine to which field of data dict value from attributes field should be applied
    :param data: target data to apply attributes
    :param attributes: attributes to be mapped onto data
    :param keys_map: dict with attribute name as key, and list of hierarchical chain of fields in value
    :return: nothing, changes data in place
    """
    for k, v in attributes.items():
        if k in keys_map:
            _map_attribute(data, keys_map[k], v)


def _copy_keys(source: dict, target: dict) -> None:
    """
    Copy keys specified in COPY_KEYS from source to target
    :param source: source
    :param target: target
    :return:
    """
    for k in COPY_KEYS:
        if k in source:
            target[k] = source[k]


def render_unit(tool: str, data: dict, hierpath: str = "",
                is_top: bool = None, custom: dict = None
                ) -> dict:
    """
    Renders unit and it's subunits in tool's format description
    :param tool: name of tool to determine proper format description
    :param data: unit's data (in format of load_unit output)
    :param hierpath: unit's parent hierarchical path
    :param is_top: False if this unit isn't top
    :param custom: customized attributes for unit
    :return: rendered unit as dict
    """
    # Get custom options
    if custom is None:
        custom = {}
    else:
        custom = copy.deepcopy(custom)

    # Display information
    display = data["display"]

    # Init result with defaults
    result = copy.deepcopy(UNIT_DEFAULTS[tool])

    # Get initial unit's attributes
    attributes = copy.deepcopy(data["attributes"])
    _copy_keys(data, attributes)

    # Update with custom attributes
    _to_target(custom, attributes, YAML_UNIT_KEYS)

    # Reflect attributes into result
    _map_attributes(result, attributes, YAML_UNIT_ATTRIBUTES_REMAP[tool])

    # Set unit's ID (do it after attributes mapping so attributes won't override ID)
    if hierpath == "":
        hierpath = "/"

    result["id"] = hierpath

    # Skip hidden
    hide = _rndr(result, "unit_hide")
    if hide is not None and (hide is True or tool in hide):
        # NOTE: hide could be a bool or list/string with tools list in which item should be hidden
        hide = True

    if display.get("view", VIEW_SYMBOL) == VIEW_NONE or hide:
        # TODO: create stubs for all nested units and ports and set them to be hidden
        _rndr_set(result, "hidden", True)
        return result

    if tool == TOOL_D3HW and display.get("view", VIEW_SYMBOL) == VIEW_SYMBOL:
        _rndr_set(result, "hide_content", True)

    childs = result["children"] = []
    _rndr_set(result, "is_unit", True)

    # Add ports
    for k, v in data["io"].items():
        _add_port(tool, result, hierpath+"."+k, k, v, reverse=hierpath == "/")

    # Add subunits
    if True:
        for k, v in data["units"].items():
            if "unit" in v:
                part_hierpath = _next_hierpath(hierpath, k)
                if tool == TOOL_HDELK and data["display"].get("view", VIEW_SYMBOL) == VIEW_SYMBOL:
                    pass  # TODO: create stubs for all nested units and set them to be hidden
                if "nets" in v:
                    _check_all_allowed(v["nets"], YAML_NET_ALLOWED, "TODO: get filepath by hierarchy", part_hierpath, "nets")
                    # TODO: make sure at least one endpoint is referred to this unit (contains . in the beginning)
                subunit = render_unit(tool, v["unit"], part_hierpath, False, v)
                if subunit is not None:
                    childs.append(subunit)
                    # Add instance specific nets
                    if "nets" in v:
                        nets = _rndr(subunit, "outer_nets", [])
                        for net_data in v["nets"]:
                            net = _net(tool, net_data)
                            _rndr_set(net, "unit_id", result["id"])
                            nets.append(net)

    # Add unit's own nets
    if "nets" in data:
        nets = _rndr(result, "my_nets", [])
        for net_data in data["nets"]:
            net = _net(tool, net_data)
            _rndr_set(net, "unit_id", result["id"])
            # Append net to list
            nets.append(net)

    if len(childs) == 0:
        del result["children"]

    return result


def _net(tool, net_data):
    net = copy.deepcopy(NET_DEFAULTS[tool])
    attributes = {}
    # If net is specified as list - convert it to dict first
    if isinstance(net_data, list):
        if "-regex" in net_data:
            suffix = "r"
        else:
            suffix = ""
        net_dict = {
            "src" + suffix: net_data[0],
            "dst" + suffix: net_data[1],
        }
        for attr in net_data[2:]:
            if attr[0] == "-":
                continue
            k, v = attr.split(":", 1)
            net_dict[k] = v
        net_data = net_dict
    # Get attributes
    _to_target(net_data, attributes, YAML_NET_KEYS)
    # Map attributes into result
    _map_attributes(net, attributes, YAML_NET_REMAP[tool])
    return net


def _ext_id(id):
    """
    Extends id with / symbol if necessary
    :param id: id to extend
    :return: extended id
    """
    if id[-1:] != "/":
        return id + "/"
    return id


def _add_to_scope(scope: dict, item: dict, root=False, port=False) -> None:
    """
    Adds item to the scope. Item should be a part of it's scope or it's root
    :param scope: scope into which add item
    :param item: item to add
    :param root: True if this item is a root of the scope
    :param port: True if this item is a root's port
    :return:
    """
    # Get id for scope
    if not root:
        root_id = _ext_id(scope["root"]["id"])
        # Make sure item is part of scope's root
        assert root_id == item["id"][:len(root_id)], "Something went wrong"
    else:
        root_id = scope["root"]["id"]
        if not port:
            # Make sure item is actually root of the scope
            assert root_id == item["id"], "Something went wrong"
        else:
            # Make sure item is root's port
            #  assert root_id+"." == item["id"][:len(root_id)+1], "Something went wrong"
            pass  # TODO: return assertion logic, but don't fail if it's port of an top (which is unit, not port)

    # Add item to scope with it's local id
    scope["items"][item["id"][len(root_id):]] = item


def _scope_data(unit: dict, scopes: dict, scope: dict or None):
    """
    Flattens and extracts data into single level dicts
    :param unit: data with rendered units
    :param scopes: all scopes
    :param scope: current scope
    :return: scope for specified unit
    """
    next_scope = None

    # Init scope (now it's always for every unit)
    if True:
    # TODO: remove
    #  scope is None or _rndr(unit, A_FILEPATH) is not None:
    #  Also in case if data were loaded from file - scope should be changed
        next_scope = {"root": unit, "items": {}, "scopes": {}}
        if scope is not None:
            scope["scopes"][unit["id"]] = next_scope
        scopes[unit["id"]] = next_scope

    # Add unit to initial scope
    if scope is not None:
        _add_to_scope(scope, unit)
        for port in unit.get("ports", []):
            _add_to_scope(scope, port)

    # If there is local scope for this unit then
    if next_scope is not None:
        # Switch scope
        scope = next_scope
        is_root = True
        # Add unit again but this time to the local scope
        _add_to_scope(scope, unit, root=is_root)
        for port in unit.get("ports", []):
            _add_to_scope(scope, port, root=is_root, port=True)

    for u in unit.get("children", []):
        _scope_data(u, scopes, scope)

    return scope


def _find_item_in_scope(scope, id, recurse=None, me=None, regex=False, want_list=False):
    # TODO: add reference unit to look for item relative to this unit, not to scope's root
    """
    Looks for item within scope by it's id
    :param scope: scope in which to start looking for
    :param id: ID of item to look for. Absolute (starts with /) or localized to the scope
    :param recurse: True to look within nested scopes, False to avoid recursion (for regexes)
    :param me: item to refer if id starts with .
    :param regex: True if id is regex
    :param want_list: If True then list is returned for non regex
    :return: scope in which item were found, local id of the item to the scope, found item or None
    or None, None, None in case if specified id is out of this scope and subscopes (in case of recursion)
    for regex id of if list wanted - returned list, containing such tuples
    """
    if id[:1] == "." or (regex and id[:2] == r"\."):
        assert me is not None, "Self reference, but me is not specified!"
        assert me in scope["items"].values(), "Self reference, but me is not in scope!"
        id = me["id"]+id
        if me == scope["root"]:
            local_id = id[len(scope["root"]["id"]):]
        else:
            local_id = id[len(_ext_id(scope["root"]["id"])):]
    elif id[:1] == "/":
        # Translate id into localized to scope id if necessary

        # But first check if it's within this scope
        if id[:len(_ext_id(scope["root"]["id"]))] != _ext_id(scope["root"]["id"]):
            if False:
                pass    # TODO: not sure about this check
            else:
                if regex or want_list:
                    return []
                else:
                    return None, None, None
        local_id = id[len(_ext_id(scope["root"]["id"])):]
    else:
        # Translate localized back into full (will be required on recursion)
        local_id = id
        id = _ext_id(scope["root"]["id"]) + id

    # Look for it within items
    if not regex:
        found = scope["items"].get(local_id, None)
    else:
        found = [v for v in scope["items"].values() if re.match(f"^{id}$", v["id"]) is not None]

    # If not found or it's regex search - try to recurse into nested scopes
    nested = []
    if (found is None and recurse is True) or (regex and recurse is not False):
        for k, s in scope["scopes"].items():
            r = _find_item_in_scope(s, id, recurse, None, regex, want_list)
            if not regex:
                # If it's not regex search and something is found - then return result
                if want_list and len(r) > 0 \
                or not want_list and r[0] is not None:
                    return r
            else:
                nested += r

    if not regex:
        # Return result if there were no recursion and it's not regex search
        if found is None:
            if not want_list:
                return None, None, None
            else:
                return []
        else:
            r = [(scope, local_id, found)]
            if not want_list:
                return r[0]
            else:
                return r
    else:
        # If this is regex search - join
        return [(scope, local_id, item) for item in found if item is not None] + nested


def _walk_endpoints(scope, allow_regex=False, recurse=False, want_net=False):
    """
    Generator that walks thru net's endpoints of units in the scope
    :param scope: scope of interest
    :param allow_regex: if True then regex endpoints are also returned
    :param recurse: if True then is recursed into nested scopes
    :param want_net: if True then whole net specification is returned
    :return: hosting scope of endpoint, unit for which net is specified, endpoint kind, endpoint name
    """
    for unit in list(scope["items"].values()):
        # NOTE: during endpoints walking scope items could be updated
        # so need to fix them in a list in the beginning of walk

        # Skip non units
        if not _rndr(unit, "is_unit"):
            continue

        ep_lookup = (NET_SRC, NET_DST)
        if allow_regex:
            ep_lookup = ep_lookup + (NET_SRCR, NET_DSTR)

        nets = []
        my_nets = _rndr(unit, "my_nets")
        outer_nets = _rndr(unit, "outer_nets")
        scope_change = _rndr(unit, A_FILEPATH) is not None

        if unit == scope["root"] or not scope_change:
            # My nets are in cluded for root and for nested units as long as they are within file's scope
            if my_nets is not None:
                nets += my_nets
        if unit != scope["root"]:
            # Only outer nets for non-root are included
            if outer_nets is not None:
                nets += outer_nets

        if len(nets) > 0:
            for net in nets:
                nr = net.get(RNDR, {})
                if not want_net:
                    # Return by endpoint
                    for ep in ep_lookup:
                        value = nr.get(ep, None)
                        if value is None:
                            continue
                        if isinstance(value, str):
                            value = (value, )
                        for v in value:
                            yield scope, unit, ep, v
                else:
                    if allow_regex or (NET_SRC in net and NET_DST in nr):
                        yield scope, unit, "net", net
    if recurse:
        for s in scope["scopes"].values():
            _walk_endpoints(s, allow_regex, recurse, want_net)  # TODO: why recursion doesn't works


def _add_missing_units(tool, scope, recurse) -> None:
    """
    Walk thru scope nets, add units to scope if referred units are not found
    (non regex src/dst of nets are used)
    :param tool: target rendering tool
    :param scope:
    :param recurse: True to recurse into nested scopes
    :return:
    """
    for _, _, _, ep in _walk_endpoints(scope, allow_regex=False):
        # Skip references to self's ports
        if ep[0] == ".":    # TODO: externalPorts are starting with . and they are treated as units
            continue
        # Change references to root's ports
        # TODO: make it clear what is root in which cases (units are described within single file, units are loaded)
        if ep[0:2] == "/.":
            ep = ep[1:]
        id = re.sub(r"\..*", "", ep)    # Extract unit path from endpoint
        _, _, unit = _find_item_in_scope(scope, id, True)
        # Add unit if it wasn't found
        if unit is None:
            # Init result with defaults
            missing = copy.deepcopy(UNIT_DEFAULTS[tool])
            # Get initial unit's attributes
            attributes = {"name": id, A_MISSING: True}
            # Reflect attributes into result
            _map_attributes(missing, attributes, YAML_UNIT_ATTRIBUTES_REMAP[tool])
            missing["id"] = _ext_id(scope["root"]["id"]) + id
            # To the root of the scope
            if "children" not in scope["root"]:
                scope["root"]["children"] = []
            scope["root"]["children"].append(missing)
            # To the scope
            scope["items"][id] = missing  # TODO: use add to scope?
    if recurse:
        for s in scope["scopes"].values():
            _add_missing_units(tool, s, recurse)


def _add_port(tool, unit, port_id, port_name, port_custom, reverse=False):
    """ Creates port and adds it to unit
    :param tool: target rendering tool
    :param unit: port's hosting unit
    :param port_id: id for new port
    :param port_name: name for new port
    :param port_custom: custom settings for port
    :param reverse: if True then direction is reversed (required for top unit's ports)
    :return:
    """
    if tool in (TOOL_HDELK, TOOL_D3HW) and unit["id"] == "/":
        port = copy.deepcopy(UNIT_DEFAULTS[tool])
        attributes = {"name": port_name}
        _to_target(port_custom, attributes, YAML_UNIT_KEYS + YAML_IO_KEYS)  # Exclude keys both of UNIT and IO
        _pin_attrs_to_name(tool, attributes)
        port_name = attributes["name"]
        _map_attributes(port, attributes,
                        YAML_UNIT_ATTRIBUTES_REMAP[tool])  # Use UNIT's attributes mapping, not IO's
        for k in ("children", "edges"):
            if k in port:
                del port[k]

        port["id"] = port_id
        _rndr_set(port, "is_port", True)

        if tool == TOOL_HDELK:
            port["port"] = 1
        else:
            port["hwMeta"]["isExternalPort"] = True

            port_pin = copy.deepcopy(IO_DEFAULTS[tool])
            port["ports"].append(port_pin)
            port_pin["hwMeta"]["name"] = port_name
            port_pin["id"] = port_id + "-port_pin"
            if "dir" in attributes:
                port_pin["direction"] = attributes["dir"]
            if reverse:
                _rndr_set(port_pin, "pin_reverse", True)

            # TODO: recurse and childs into top port if there is any

        if "children" not in unit:
            unit["children"] = []
        unit["children"].append(port)
    else:
        port = copy.deepcopy(IO_DEFAULTS[tool])
        attributes = {"name": port_name}
        _to_target(port_custom, attributes, YAML_IO_KEYS)
        _pin_attrs_to_name(tool, attributes)
        port_name = attributes["name"]
        _map_attributes(port, attributes, YAML_IO_REMAP[tool])
        port["id"] = port_id
        if reverse:
            _rndr_set(port, "pin_reverse", True)
        if "ports" not in unit:
            unit["ports"] = []
        unit["ports"].append(port)
    return port


def _pin_attrs_to_name(tool, attributes):
    """
    Translates port attributes like inversion, clock, edge into starting symbol of pin name
    :param attributes:
    :return:
    """
    if attributes.get("inv", False) is True:
        if PIN_INV_PREFIX is not None and attributes["name"][:len(PIN_INV_PREFIX)] != PIN_INV_PREFIX:
            attributes["name"] = PIN_INV_PREFIX + attributes["name"]
        if PIN_INV_SUFFIX is not None and attributes["name"][-len(PIN_INV_SUFFIX):] != PIN_INV_SUFFIX:
            attributes["name"] += PIN_INV_SUFFIX
    if tool == TOOL_D3HW:
        if attributes.get("clk", False) is True \
        or attributes.get("gate", False) is True:
            if (PIN_INV_PREFIX is None or attributes["name"][:len(PIN_INV_PREFIX)] == PIN_INV_PREFIX) \
            and (PIN_INV_SUFFIX is None or attributes["name"][-len(PIN_INV_SUFFIX):] == PIN_INV_SUFFIX):
                if attributes.get("clk", False) is True:
                    attributes["name"] = attributes["name"] + PIN_CLK_FALL
                else:
                    attributes["name"] = attributes["name"] + PIN_GATE_LOW
            else:
                if attributes.get("clk", False) is True:
                    attributes["name"] = attributes["name"] + PIN_CLK_RISE
                else:
                    attributes["name"] = attributes["name"] + PIN_GATE_HIGH


def _add_missing_ports(tool, scope, traverse, recurse) -> None:
    """
    Walk thru scope nets, add units to scope if referred units are not found
    (non regex src/dst of nets are used)
    :param tool: schematic rendering tool
    :param scope:
    :param traverse: True to look for missing ports within nested scopes
    :param recurse: True to recurse into nested scopes
    :return:
    """
    for _, ref_unit, ep_kind, ep in _walk_endpoints(scope, allow_regex=False):
        if ep[0] == ".":
            # If it's short from (without unit specification)
            # take id straight from the unit fow which endpoint is specified
            unit = ref_unit
            if ref_unit == scope["root"]:
                local_id = ""
            else:
                root_id = _ext_id(scope["root"]["id"])
                assert ref_unit["id"][len(root_id)-1:len(root_id)] == "/", "Something went wrong"
                local_id = ref_unit["id"][len(root_id):]
            name = ep[1:]
            port_id = ref_unit["id"] + ep
            port_local_id = local_id + ep
            s = scope
        elif "." in ep:  # Endpoint is port (it could be unit and this is out of interest here)
            # Otherwise look for specified unit
            unit_id = re.sub(r"\..*", "", ep)   # Extract unit path from endpoint
            s, local_id, unit = _find_item_in_scope(scope, unit_id, traverse)
            # Skip if specified unit is not found
            if unit is None:
                continue
            name = ep[len(_ext_id(unit_id)):]
            port_id = unit["id"] + ep[len(unit_id):]
            port_local_id = local_id + ep[len(unit_id):]
        else:
            continue

        # Add port if it wasn't found
        if port_local_id not in s["items"]:
            attributes = {
                A_MISSING: True,
                "dir": ["in", "out"][(ep_kind == NET_SRC)
                                     ^ (unit["id"] == "//")],
                # TODO: reverse direction if net endpoint is nested unit's port
            }
            port = _add_port(tool, unit, port_id, name, attributes)
            s["items"][port_local_id] = port

    if recurse:
        for s in scope["scopes"].values():
            _add_missing_ports(tool, s, traverse, recurse)


def _connect_net(tool, scope, unit, net_data):
        net = copy.deepcopy(net_data)
        v = net.get(RNDR, {})
        autoname = True
        if NET_SRC not in v and NET_SRCR not in v:
            raise ValueError(f"No source found in net `{net}`")
        if NET_DST not in v and NET_DSTR not in v:
            raise ValueError(f"No destination found in net `{net}`")
        if NET_SRC in v and NET_SRCR in v:
            raise ValueError(f"Should be only `{NET_SRC}` or `{NET_SRCR}`, not both in net `{net}`")
        if NET_DST in v and NET_DSTR in v:
            raise ValueError(f"Should be only `{NET_DST}` or `{NET_DSTR}`, not both in net `{net}`")
        if NET_SRCR in v:
            v[NET_SRC] = v[NET_SRCR]
            v[NET_SRCR] = True
        else:
            v[NET_SRCR] = False
        if NET_DSTR in v:
            v[NET_DST] = v[NET_DSTR]
            v[NET_DSTR] = True
        else:
            v[NET_DSTR] = False
        if tool != TOOL_D3HW or "name" in net_data["hwMeta"] and net_data["hwMeta"]["name"] is not None:
            autoname = False

        if isinstance(v[NET_SRC], str):
            v[NET_SRC] = [v[NET_SRC]]
        if isinstance(v[NET_DST], str):
            v[NET_DST] = [v[NET_DST]]

        sources = []
        for ep in v[NET_SRC]:
            if ep[:1] == "/":
                ep = _ext_id(scope["root"]["id"])+ep[1:]
            sources += _find_item_in_scope(scope, id=ep, recurse=False, me=unit, regex=v[NET_SRCR], want_list=True)
            # NOTE: nets traversing not works, so recursion is turned off

        targets = []
        for ep in v[NET_DST]:
            if ep[:1] == "/":
                ep = _ext_id(scope["root"]["id"])+ep[1:]
            targets += _find_item_in_scope(scope, id=ep, recurse=False, me=unit, regex=v[NET_DSTR], want_list=True)
            # NOTE: nets traversing not works, so recursion is turned off

        # TODO: avoid hidden

        if len(sources) < 1 or len(targets) < 1:
            return

        root = scope["root"]
        net_id = f'{_ext_id(root["id"])}:{v[NET_SRC]}:{v[NET_DST]}'

        src = []
        trg = []
        src_name = None
        trg_name = None
        for _, _, source in sources:
            src_name = _rndr(source, "name")
            if tool != TOOL_D3HW or _rndr(source, "is_port") is not True:
                # Common case
                src.append([re.sub(r"\..*", "", source["id"]), source["id"]])
            else:
                # Case for top's ports for D3HW
                src.append([source["id"], source["id"]+"-port_pin"])

            for _, _, target in targets:
                trg_name = _rndr(target, "name")
                if tool != TOOL_D3HW or _rndr(target, "is_port") is not True:
                    # Common case
                    trg.append([re.sub(r"\..*", "", target["id"]), target["id"]])
                else:
                    # Case for top's ports for D3HW
                    trg.append([target["id"], target["id"]+"-port_pin"])

        if len(src) == 0 or len(trg) == 0:
            return

        # TODO: increase net references on ports (required to use auto_hide later)

        # "_nets_" is a dict to gather all merge all nets with same sources into one
        if "_nets_" not in root:
            root["_nets_"] = {}
        nets = root["_nets_"]

        # key is sorted sources list
        net_key = tuple([tuple(v) for v in sorted(src)])

        if net_key not in nets:
            # init net data
            nets[net_key] = {"sources": src, "targets": [], **net}

            if tool == TOOL_D3HW:
                # add id
                nets[net_key]["id"] = net_id
                # autoname net if this is D3HW
                if autoname and (len(src) == 1 or len(trg) == 1):
                    home_unit = _rndr(net_data, "unit_id")
                    if len(src) == 1:
                        # By default - if there is single source pin then it's name is used to name the net
                        name = src_name
                        name_id = re.sub(r"-port_pin$", "", src[0][1])
                        if len(trg) == 1:
                            # If there is single target pin then it's name should be used
                            # if it's root's pin for it's scope
                            alt_name = trg_name
                            alt_id = re.sub(r"-port_pin$", "", trg[0][1])
                        else:
                            alt_name = None
                            alt_id = None
                        if alt_name is not None \
                            and name_id[len(home_unit):len(home_unit) + 1] != "." \
                            and alt_id[len(home_unit):len(home_unit) + 1] == ".":
                            # This is case when single target pin is scope's root's pin
                            name = alt_name
                            name_id = alt_id
                    else:
                        # If there is multiple sources pins and single target pin
                        # then target pin's name is used to name the net
                        name = trg_name
                        name_id = re.sub(r"-pin_port$", "", trg[0][1])
                    if home_unit is not None:
                        name_id = name_id[len(home_unit):]
                    name_id = re.sub(r"\..*$", "", name_id)
                    if name_id[:1] == "/":
                        name_id = name_id[1:]
                    if name[-1] in (PIN_GATE_HIGH, PIN_GATE_LOW, PIN_CLK_RISE, PIN_CLK_FALL):
                        name = name[:-1]
                    if len(name_id) > 0:
                        name = name_id + "." + name
                    # if name[:1] == ".":
                    #     name = name[1:]
                    nets[net_key]["hwMeta"]["name"] = name
        else:
            pass

        nets[net_key]["targets"] += trg


def _nets_to_edges(tool, unit):

    for v in unit.get("_nets_", {}).values():
        if "edges" not in unit:
            unit["edges"] = []

        if tool == TOOL_D3HW:
            unit["edges"].append(v)

        if tool == TOOL_HDELK:
            for _, sid in v["sources"]:
                for _, tid in v["targets"]:
                    unit["edges"].append({
                        **v,
                        "sources": [sid],
                        "targets": [tid],
                    })
    for u in unit.get("children", []):
        _nets_to_edges(tool, u)


def connect(tool: str, top_unit: dict, options: tuple or list) -> None:
    """
    Generates 'edges' items
    :param tool: name of tool
    :param top_unit: data with rendered units
    :param options: nodes within scope
    :return: nothing - data is modified just in place
    """
    options = (RENDER_ADD_MISSING_PORTS, RENDER_ADD_MISSING_UNITS)

    # Build scopes
    _scopes = {}
    top_scope = _scope_data(top_unit, _scopes, None)

    # Walk thru nets, add missing units
    if RENDER_ADD_MISSING_UNITS in options:
        _add_missing_units(tool, top_scope, recurse=True)

    # Walt thru nets, add missing ports if necessary
    if RENDER_ADD_MISSING_PORTS in options:
        _add_missing_ports(tool, top_scope, traverse=True, recurse=True)

    # Walk thru nets again - connect as necessary
    _connect_nets(tool, top_scope)

    # Transforms nets data into edges
    _nets_to_edges(tool, top_unit)


def _connect_nets(tool, starting_scope):
    for scope, unit, _, net_data in _walk_endpoints(starting_scope, allow_regex=True, recurse=False, want_net=True):
        # TODO: skip hidden
        _connect_net(tool, scope, unit, net_data)

    for scope in starting_scope.get("scopes").values():
        # TODO: skip hidden
        _connect_nets(tool, scope)


def cleanup(data):
    if isinstance(data, list):
        for d in data:
            cleanup(d)
    elif isinstance(data, dict):
        keys = list(data.keys())
        for k in keys:
            if k[:1] == "_" and k[-1:] == "_":
                del data[k]
        for v in data.values():
            cleanup(v)


def renderer(tool, data):
    # TODO: check/update display
    # TODO: remove hidden
    # TODO: hideNC, autohide
    # TODO: color, highlight, bus
    # TODO: color missing
    # TODO: hide empty
    pass


def tool_adaptation(tool, data):

    if tool == TOOL_HDELK:
        hdelk_adaptation(data)
    if tool == TOOL_D3HW:
        d3hw_adaptation(data)


def _hdelk_portGroups(data):
    # Translate ports into port specific groups
    hdelk_ports = {}
    ports = data.get("ports", [])
    for p in ports:
        ports_group = p.get(RNDR, {}).get("pin_dir", "in")+"Ports"
        side = p.get(RNDR, {}).get("pin_side", None)
        if side is not None:
            ports_group = side + "Ports"
        if ports_group not in hdelk_ports:
            hdelk_ports[ports_group] = []
        hdelk_ports[ports_group].append(p)
    for k, v in hdelk_ports.items():
        data[k] = hdelk_ports[k]
    if "ports" in data:
        del data["ports"]

    for c in data.get("children", []):
        _hdelk_portGroups(c)


def hdelk_adaptation(data):
    _hdelk_portGroups(data)


def _d3hw_adaptation_unit(unit):
    """
    set some default values
    :param unit:
    :return:
    """
    if "hwMeta" not in unit:
        unit["hwMeta"] = {}
    if "name" not in unit["hwMeta"]:
        unit["hwMeta"]["name"] = unit["id"]
        u_type = _rndr(unit, "type")
        if u_type is not None:
            unit["hwMeta"]["name"] += ":" + u_type
    for u in unit.get("children", []):
        _d3hw_adaptation_unit(u)


def _d3hw_hide_content(unit):

    if _rndr(unit, "hide_content"):
        if "children" in unit:
            unit["_children"] = unit["children"]
            del unit["children"]
        if "edges" in unit:
            unit["_edges"] = unit["edges"]
            del unit["edges"]

    for u in unit.get("children", []):
        _d3hw_hide_content(u)


def _d3hw_adaptation_port(unit):
    """
    transform values for side and direction
    set port index
    :param unit:
    :return:
    """
    index_auto_step = 1000
    index = {
        "WEST": -index_auto_step,
        "EAST": index_auto_step,
        "NORTH": index_auto_step,
        "SOUTH": -index_auto_step
    }
    for p in unit.get("ports", []):
        if "direction" in p and p["direction"] == "in":
            p["direction"] = "INPUT"
        elif "direction" in p:
            p["direction"] = "OUTPUT"
        else:
            p["direction"] = "INPUT"

        if _rndr(p, "pin_reverse"):
            if p["direction"] == "INPUT":
                p["direction"] = "OUTPUT"
            else:
                p["direction"] = "INPUT"

        props = p.get("properties", None)
        if props is None:
            props = p["properties"] = {}
        if "side" in props:
            props["side"] = props["side"].upper()
        else:
            if p["direction"] == "INPUT":
                props["side"] = "WEST"
            else:
                props["side"] = "EAST"
        side = props["side"]
        if "index" not in props:
            props["index"] = index[side]
            if index[side] > 0:
                index[side] += index_auto_step
            else:
                index[side] -= index_auto_step
        else:
            if side in ("WEST", "SOUTH"):
                props["index"] = -props["index"]

    for u in unit.get("children", []):
        _d3hw_adaptation_port(u)


def _d3hw_id_map(item, id_map, id_counter, is_unit):
    """
    Assigns numeric ID for each unit, port and edge
    Fills in string ID to numeric ID map
    Replaces string ID with numeric
    Sets maxID for unit meta
    :param item: unit, port or edge
    :param id_map: dict with mapping string ids to numeric ids
    :param id_counter: list with single item - id counter (list is used to 'pass by ref')
    :param is_unit: True if item is unit, otherwise False
    :return:
    """
    id_map[item["id"]] = id_counter[0]
    DEBUG = 0
    item["id"] = str(id_counter[0]) + ["", ":" + item["id"]][DEBUG]
    id_counter[0] += 1
    if not is_unit:
        return

    for i in item.get("ports", []):
        _d3hw_id_map(i, id_map, id_counter, is_unit=False)

    for i in item.get("edges", []):
        _d3hw_id_map(i, id_map, id_counter, is_unit=False)

    for i in item.get("children", []):
        _d3hw_id_map(i, id_map, id_counter, is_unit=True)

    item["hwMeta"]["maxId"] = id_counter[0]


def _d3hw_id_sub(item, id_map, is_unit):
    """
    Replaces string ID in strings with numeric ID
    - in edges sources and targets
    :param item: unit, port or edge
    :param id_map: dict with mapping string ids to numeric ids
    :param is_unit: True if item is unit, otherwise False
    :return:
    """
    if not is_unit:
        return

    DEBUG = 0
    for e in item.get("edges", []):
        for eps in ("sources", "targets"):
            for ep in e[eps]:
                for i in range(0, len(ep)):
                    ep[i] = str(id_map[ep[i]]) + ["", ":" + ep[i]][DEBUG]

    for u in item.get("children", []):
        _d3hw_id_sub(u, id_map, is_unit=True)


def d3hw_adaptation(data):
    _d3hw_adaptation_unit(data)
    _d3hw_adaptation_port(data)
    id_map = {}
    id_counter = [0]
    _d3hw_id_map(data, id_map, id_counter, is_unit=True)
    _d3hw_id_sub(data, id_map, is_unit=True)
    _d3hw_hide_content(data)


def tool_html(tool: str, schm: dict, header: str = "Schematic", display_customizations: str = "") -> str:
    """
    Generates HTML with schematic using specified tool
    :param tool: tool to be used for schematic drawing
    :param schm: schematics data in tool_render format
    :param header: string to be written in header of file
    :return: whole HTML page content as string
    """
    if tool == TOOL_D3HW:
        return d3hw_html(schm, header, display_customizations)
    if tool == TOOL_HDELK:
        return hdelk_html(schm, header, display_customizations)
    return f"""<!DOCTYPE html>
<html>
    Not supported tool {tool}!
<body>
</body>
</html>"""


def hdelk_html(schm: dict, header: str = "Schematic", display_customizations: str = "") -> str:
    """
    Generates HTML with schematic using HDElk
    :param schm: schematics data in tool_render format (actually that is content for HDElk's graph variable)
    :param header: string to be written in header of file
    :return: whole HTML page content as string
    """
    result = f"""<!DOCTYPE html>
<html>
<body>

<h1>{header}</h1>

<script src="./js/hdelk/elk.bundled.js"></script>
<script src="./js/hdelk/svg.min.js"></script>
<script src="./js/hdelk/hdelk.js"></script>

<div id="simple_diagram"></div>

<script type="text/javascript">

    {display_customizations}

    var simple_graph = {json.dumps(schm, indent=2)}

    hdelk.layout( simple_graph, "simple_diagram" );
</script>

</body>
</html>"""
    return result


def d3hw_html(schm: dict, header: str = "Schematic", display_customizations: str = "") -> str:
    """
    Generates HTML with schematic using D3-HWSchematic
    :param schm: schematics data in tool_render format (actually that is content for D3-Hardware's graph variable)
    :param header: string to be written in header of file
    :return: whole HTML page content as string
    """

    result = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>{header}</title>
  <script type="text/javascript" src="./js/d3hw/d3.js"></script>
  <!-- <script type="text/javascript" src="./js/d3hw/d3.min.js"></script>  -->
  <script type="text/javascript" src="./js/d3hw/elk.bundled.js"></script>
  <script type="text/javascript" src="./js/d3hw/d3-hwschematic.js"></script>
  <link href="./css/d3/d3-hwschematic.css" rel="stylesheet">
  <style>
  	body {{
	   margin: 0;
    }}
  </style>
</head>
<body>
    <svg id="scheme-placeholder"></svg>
    <script>
        // schematic rendering script

        function viewport() {{
          var e = window,
            a = 'inner';
          if (!('innerWidth' in window)) {{
            a = 'client';
            e = document.documentElement || document.body;
          }}
          return {{
            width: e[a + 'Width'],
            height: e[a + 'Height']
          }}
        }}

        var width = viewport().width,
            height = viewport().height;

        var svg = d3.select("#scheme-placeholder")
            .attr("width", width)
            .attr("height", height);

        var orig = document.body.onresize;
        document.body.onresize = function(ev) {{
            if (orig)
        	    orig(ev);

            var w = viewport();
            svg.attr("width", w.width);
			      svg.attr("height", w.height);
        }}

        var hwSchematic = new d3.HwSchematic(svg);
        var zoom = d3.zoom();
        zoom.on("zoom", function applyTransform(ev) {{
        	hwSchematic.root.attr("transform", ev.transform)
        }});

        // disable zoom on doubleclick
        // because it interferes with component expanding/collapsing
        svg.call(zoom)
           .on("dblclick.zoom", null)

    </script>
    <script>
          function displayContents() {{
            var graph = {json.dumps(schm, indent=2)};
            if (graph.hwMeta && graph.hwMeta.name)
                 document.title = graph.hwMeta.name; // #TODO: use proper field for title
            // load the data and render the elements
            hwSchematic.bindData(graph);
          }}

          displayContents();
    </script>
</body>
</html>
"""
    return result


if __name__ == "__main__":
    _SKIP_TODO = False
    _IGNORE_UNCERTAIN = False

    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--version",
                        action="version",
                        version=_VERSION,
                        help="Print version of this tool")
    parser.add_argument("-i", "--info",
                        action="version",
                        version=_INFO,
                        help="Print short info about this tool")
    parser.add_argument("source_path",
                        default="",
                        help="Path to top unit description file (YAML expected)",
                        type=str)
    parser.add_argument("output_path",
                        default="",
                        help="Path to output file. "
                             "If '-' or empty string is specified then result is printed to STDOUT,\n"
                             "if '@' is first char then output path = <output_path after @>/<source_file_name>.<format>",
                        type=str)
    parser.add_argument("-t", "--tool",
                        choices=(TOOL_HDELK, TOOL_D3HW),
                        default=TOOL_D3HW,
                        dest="tool",
                        help="Target rendering tool",
                        type=str
                        )
    parser.add_argument("-f", "--format",
                        choices=("HTML", "JSON"),
                        default="HTML",
                        dest="format",
                        help="Output format",
                        type=str)
    parser.add_argument("-r", "--root",
                        default=os.getcwd(),
                        dest="root",
                        help="Root path for units description files lookup",
                        type=str)
    parser.add_argument("--hdelk_custom",
                        default="",
                        dest="hdelk_custom",
                        help="HDELk customizations file path",
                        type=str)
    parser.add_argument("-s", "--shell",
                        action="store_true",
                        dest="shell",
                        help="If specified then shell (aka box) is generated for top unit "
                             "and it would look same as nested units")
    args = parser.parse_args()
    filepath = args.source_path
    opath = args.output_path
    if opath in ("", "-"):
        opath = None
    oformat = args.format
    _ROOT_PATH = args.root
    display_customizations = args.hdelk_custom

    if args.shell:
        # Special shell around top unit is generated
        # to provide uniform rendering of unit neither it's top or  it's nested
        # (default behavior)
        hunit = '''
attributes:
  type: ""
display:
  "": {view: nested}
  "/": {view: full}
units:
  "/":
    unit: '@'''+filepath+''''
    name: ""
'''
    else:
        hunit = None

    filepath = guess_filepath(_ROOT_PATH, filepath)
    data = load_unit(filepath, "", "", {}, None)
    hdata = load_unit(filepath, "", "", {}, None, yaml_string=hunit)
    tool = args.tool
    schm = render_unit(tool, hdata, "", is_top=True, custom=hdata)
    connect(tool, schm, (RENDER_ADD_MISSING_UNITS, RENDER_ADD_MISSING_PORTS))
    renderer(tool, schm)
    tool_adaptation(tool, schm)
    cleanup(schm)
    if oformat == "HTML":
        result = tool_html(tool, schm, "Schematic of " + data["attributes"].get("type", filepath), display_customizations)
    else:
        result = json.dumps(schm, indent=2)

    if opath is None or opath == "":
        print(result)
    else:
        if opath[:1] == "@":
            opath = opath[1:]
            if opath == "":
                opath = "./"
            opath = os.path.join(
                opath,
                re.sub(r"\.[^.]+$", "", os.path.split(filepath)[1])  # Remove initial file extension
                +"."+oformat.lower()                                 # Add target format extension
            )
        with open(opath, "w", encoding="utf-8") as f:
            f.write(result)
