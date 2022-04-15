import os
import sys
import yaml
import json
import re

_VERSION = "1.1.0"
_USAGE = f"""
yaml4hdelk, version {_VERSION}

Run this tool like:   python {sys.argv[0]} <top_unit.yaml> [<output.html>] [<custom.js>] [no_shell]
where
    <top_unit.yaml> - path to top unit specification file in YAML format
    <output.html>   - path to output file.
                      omit "" or "-" for STDOUT output (default)
    <custom.js>     - path to file with display customizations in JS format
                      for details see section 'Modifying the Look and Feel' of HDElk tutorial
                      omit "" or "-" for no customizations (default)
    no_shell        - just type in any value to avoid generating shell around top unit
                      with shell around top unit looks same as when it's nested (or similar at least)
                      omit or "" to generate shell (default)
"""


_UNIT_KEYS = ("io", "generics", "units", "nets", "display", "attributes")
_YAML_UNIT_ALLOWED_KEYS = (*_UNIT_KEYS, "filepath")

_YAML_IO_ALLOWED_DIRS = ("in", "out", "south", "north", "west", "east")

_VIEW_NONE = "none"
_VIEW_SYMBOL = "symbol"
_VIEW_FULL = "full"
_VIEW_NESTED = "nested"

_BASE_PATH = None


def find_file(root: str, filename: str) -> str:
    """
    Looks for full path by given filename within root end under
    :param root: root to start looking from
    :param filename: specified filename
    :return: full file path
    """
    f_low = filename.lower()
    for root, dirs, files in os.walk(_BASE_PATH):
        fl = [fn.lower() for fn in files]
        for fn in (f_low, f_low+".yaml", f_low+".yml"):
            if fn in fl:
                return os.path.join(root,fn)
    return None


def guess_filepath(root: str, path: str) -> str:
    """
    Guesses full file path by given path
    :param root: root to start looking from
    :param path: specified path
    Special patterns for path:
        If path starts with @ then it's relative to _BASE_PATH
        If path is within angle braces < > then path should be a filename and it would be searched within _BASE_PATH
    :return: full file path
    """
    if path[0:1] == "@":
        if _BASE_PATH is None:
            raise ValueError("For usage of pathes, starting with @, _BASE_PATH should be specified")
        return os.path.join(_BASE_PATH + path)
    if path[0:1] == "<" and path[-1:] == ">":
        if _BASE_PATH is None:
            raise ValueError("For usage of pathes inside angle braces i.e `<>` _BASE_PATH should be specified")
        r = find_file(_BASE_PATH, path[1:-1])
        if r is None:
            raise ValueError(f"File {path} wasn't found within {_BASE_PATH}")
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
    if yaml_string is None:
        with open(filepath, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    else:
        data = yaml.safe_load(yaml_string)
    # TODO: check file exists, return stub if not

    if unit:
        if "attributes" not in data:
            data["attributes"] = {}
        if "type" not in data["attributes"]:
            data["attributes"]["type"] = \
                re.sub("\.[^.]*$", "", os.path.split(filepath)[-1])
        if "display" not in data:
            data["display"] = {}
        if "" not in data["display"]:
            data["display"][""] = {"view": "full"}

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
            source_path = guess_filepath(os.path.split(parentpath)[0], v)
            # TODO: make stub in case of error
            partial = _load(source_path)
            data = {**data, **partial}
            data["filepath"] = source_path
        elif isinstance(v, dict):
            data[k] = _source(parentpath, v)
        else:
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
            if isinstance(v, dict) and isinstance(dst[k], dict):
                _merge_nodes(v, dst[k])
            elif isinstance(v, list) and isinstance(dst[k], list):
                dst[k] += v
            else:
                dst[k] = v
        else:
            dst[k] = v


def _process_unit(data: dict, filepath: str, hierpath: str = "", display: dict = None, view: str = None):
    """
    Determines actual view options for given unit, updates nested nodes as necessary
    :param data: node with unit's definition
    :param filepath: filepath for source of this node
    :param hierpath: unit's path in unit's hierarchy
    :param display: all display rules at this level of hierarchy
    :param view: view kind for this unit. None if view kind should be determined from display rules
    :return: nothing. it changes data itself
    """
    filepath_list = [filepath]  # filepath_list is updated on every data's layer depth change

    def _filepath():
        # Returns latest seen filepath value for current data's layer
        return filepath_list[-1]

    if "filepath" in data:
        filepath_list.append(data["filepath"])

    if not all(k in _YAML_UNIT_ALLOWED_KEYS for k in data.keys()):
        raise ValueError(f"Not supported keys found in file `{_filepath()}` for {data}")

    # Add missing fields
    for k in _UNIT_KEYS:
        if k not in data:
            data[k] = {}

    # Update display information
    # First use loaded
    # Then override with externally specified
    active_display = {}
    for k, v in data["display"].items():
        active_display[hierpath+"/"+k] = v

    if display is not None:
        for k, v in display.items():
            active_display[k] = v

    # Check how this part should be displayed first
    data["display"] = this_display = _get_display(hierpath, active_display)

    if view is None:
        this_view = this_display.get("view", _VIEW_SYMBOL)
    else:
        this_view = view

    data["display"]["view"] = this_view
    if this_view == _VIEW_NONE:
        return {}

    # Check how nested part should be displayed
    nested_view = _VIEW_SYMBOL
    if this_view == _VIEW_SYMBOL:
        data["units"] = {}
        data["nets"] = {}
    elif this_view == _VIEW_FULL:
        nested_view = _VIEW_SYMBOL
    elif this_view == _VIEW_NESTED:
        nested_view = None

    nested_units = data["units"]

    remove = []
    for k, v in nested_units.items():
        if "unit" not in v:
            remove.append(k)

    # TODO: raise error if there is something to remove
    for k in remove:
        del nested_units[k]

    if "filepath" in data["units"]:
        filepath_list.append(data["units"]["filepath"])

    for k, v in nested_units.items():
        filepath_list.append(v.get("filepath", _filepath()))

        part_hierpath = hierpath + "/" + k
        if nested_view is not None:
            part_view = nested_view
        else:
            part_display = _get_display(part_hierpath, active_display)
            part_view = part_display.get("view", _VIEW_SYMBOL)

        if isinstance(v["unit"], str):
            nested_filepath = guess_filepath(os.path.split(_filepath())[0], v["unit"])
            v["unit"] = _load(nested_filepath, unit=True)
            # TODO: make stub in case of error
        else:
            nested_filepath = _filepath()

        if isinstance(v["unit"], dict):
            _process_unit(v["unit"], nested_filepath, part_hierpath, active_display, part_view)
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
            if this_display_level is None or this_display_level > display_level:
                this_display = v    # TODO: more sophisticated approach that mixes view properties from multiple matches
                this_display_level = display_level

    if this_display is None:
        this_display = {}
    return this_display


def load_unit(filepath: str, hierpath: str = "", display: dict = None, view: str = None, yaml_string: str = None) -> dict:
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
    _process_unit(data, filepath, hierpath, display, view)
    return data


def _lookup(localref: str, names: list, values: list, regex: bool = False) -> list:
    """
    Looks for given names within values
    :param localref: localref is added to the names, starting with point. If localref is empty string then starting point would be cleared
    :param names: list of names to look for within values. simple string or regex
    :param values: values to look. should be a list of 2-item tuples. Names are matched against first value in a tuple, second item of tuple is put into result in case if name matched
    :param regex: set to True if names contain regex
    :return: list with full hierarchical names for matched values
    """
    result = []
    for n in names:
        if regex:
            if n[0:2] == '\.':
                if localref != "":
                    n = localref + n
                else:
                    n = n[2:]
        else:
            if n[0:1] == '.':
                if localref != "":
                    n = localref + n
                else:
                    n = n[1:]
        for v in values:
            if regex:
                if re.match("^"+n+"$", v[0]) is not None:
                    result.append(v[1])
            else:
                if n == v[0]:
                    result.append(v[1])
    return result


def hdelk_connect(localref: str, nets: list, nodes: list) -> list:
    """
    Generated 'edges' items for hdelk
    :param localref: name for item, that is referenced relatively
    :param nets: nets specification
    :param nodes: nodes within scope
    :return: list with edges specification
    """
    result = []
    for v in nets:
        if isinstance(v, list):
            if len(v) < 2:
                raise ValueError(f"Wrong net specification: `{v}`. Expected at least two items")
            net = {"src": v[0], "dst": v[1]}
            for i in range(2, len(v)):
                if v[i] == "-regex":
                    net["srcr"] = True
                    net["dstr"] = True
                    continue
                kv = v[i].split(":", 1)
                if len(kv) != 2:
                    raise ValueError(f"Wrong net's attribute specification: `{v[i]}`. Expected format: `key:value`")
                net[kv[0]] = kv[1]
        elif not isinstance(v, dict):
            raise ValueError(f"Net should be specified as dict or list. Got: `{v}`")
        else:
            if "src" not in v and "srcr" not in v:
                raise ValueError(f"No source found in net `{v}`")
            if "dst" not in v and "dstr" not in v:
                raise ValueError(f"No destination found in net `{v}`")
            if "src" in v and "srcr" in v:
                raise ValueError(f"Should be only `src` or `srcr`, not both in net `{v}`")
            if "dst" in v and "dstr" in v:
                raise ValueError(f"Should be only `dst` or `dstr`, not both in net `{v}`")
            if "srcr" in v:
                v["src"] = v["srcr"]
                v["srcr"] = True
            if "dstr" in v:
                v["dst"] = v["dstr"]
                v["dstr"] = True
            net = v
        if isinstance(net["src"], str):
            net["src"] = [net["src"]]
        if isinstance(net["dst"], str):
            net["dst"] = [net["dst"]]
        sources = _lookup(localref, net["src"], nodes, net.get("srcr", False))
        targets = _lookup(localref, net["dst"], nodes, net.get("dstr", False))
        if len(sources) < 1 or len(targets) < 1:
            continue
        del net["src"]
        del net["dst"]
        if "srcr" in net:
            del net["srcr"]
        if "dstr" in net:
            del net["dstr"]
        for s in sources:
            for t in targets:
                result.append({"sources": [s], "targets": [t], **net})
    return result


def hdelk_render(data: dict, id: str, label: str = None, hierpath: str = "",
                 is_top: bool = None, attributes: dict = None) -> (dict, list):
    """
    Renders unit and it's subunits in HDElk format
    :param data: unit's data (in format of load_unit output)
    :param hierpath: unit's hierarchical path
    :param is_top: False if this unit isn't top
    :param attributes: customized attributes for unit
    :return:
    """
    if data["display"].get("view", _VIEW_SYMBOL) == _VIEW_NONE:
        return None, None

    result = {}
    if hierpath != "":
        result["id"] = hierpath
    if label is not None:
        result["label"] = label
    if attributes is None:
        attributes = {}
    for attrs in (data["attributes"], attributes):
        for k, v in attrs.items():
            if k not in ("id", "children", "edges", "unit", "filepath") and k not in _UNIT_KEYS:
                result[k] = v
    result["children"] = []
    result["edges"] = []

    childs = result["children"]
    edges = result["edges"]
    nodes = []  # Nodes are used to transform nets into edges
    export_nodes = []
    if is_top is True or is_top is None:
        for k, v in data["io"].items():
            port = {"id": k, "port": 1}
            for pk, pv in v.items():
                if pk not in ("id", "dir", "filepath"):
                    port[pk] = pv
            childs.append(port)
            nodes.append((k, k))
    else:
        ports = {}
        for k, v in data["io"].items():
            portside = v.get("dir", "in")
            if portside not in _YAML_IO_ALLOWED_DIRS:
                raise ValueError(f"IO port `{k}` dir value `{portside}` if none of {_YAML_IO_ALLOWED_DIRS}")
            if portside not in ports:
                ports[portside] = []
            port = {"id": k}
            for pk, pv in v.items():
                if pk not in ("dir", "id", "filepath"):
                    port[pk] = pv
            ports[portside].append(port)
            nodes.append((k, hierpath+"."+k))
            export_nodes.append((id+"."+k, hierpath+"."+k))
        for k, v in ports.items():
            result[k+"Ports"] = v

    if data["display"].get("view", _VIEW_SYMBOL) != _VIEW_SYMBOL:
        for k, v in data["units"].items():
            if "unit" in v:
                if hierpath != "":
                    part_hierpath = hierpath + "_" + k
                else:
                    part_hierpath = k
                subunit, subnodes = hdelk_render(v["unit"], k, k, part_hierpath, False, v)
                if subunit is not None:
                    childs.append(subunit)
                    node = (k, part_hierpath)
                    nodes.append(node)
                    nodes += subnodes

    result["edges"] += hdelk_connect(hierpath, data["nets"], nodes)
    for k, v in data["units"].items():
        if "nets" not in v:
            continue
        if hierpath != "":
            part_hierpath = hierpath + "_" + k
        else:
            part_hierpath = k
        result["edges"] += hdelk_connect(part_hierpath, v["nets"], nodes)

    if is_top is False:
        for k in ("children", "edges"):
            if len(result[k]) == 0:
                del result[k]

    return result, export_nodes


def hdelk_html(schm: dict, header: str = "Schematic", display_customizations: str = "") -> str:
    """
    Generates HTML with HDElk schematic
    :param schm: schematics data in hdelk_render format (actually that is content for HDElk's graph variable)
    :param header: string to be written in header of file
    :return:
    """
    result = f"""<!DOCTYPE html>
<html>
<body>

<h1>{header}</h1>

<script src="js/elk.bundled.js"></script>
<script src="js/svg.min.js"></script>
<script src="js/hdelk.js"></script>

<div id="simple_diagram"></div>

<script type="text/javascript">

    {display_customizations}

    var simple_graph = {json.dumps(schm, indent=2)}

    hdelk.layout( simple_graph, "simple_diagram" );
</script>

</body>
</html>"""
    return result


if __name__ == "__main__":
    if len(sys.argv) <= 1:
        print(_USAGE)
        exit(0)

    _BASE_PATH = os.getcwd()

    # First argument is file path
    filepath = sys.argv[1]

    # Second argument is output target
    if len(sys.argv) > 2:
        opath = sys.argv[2]
        if opath in ("", "-"):
            opath = None
    else:
        opath = None

    # Third argument is display customizations
    if len(sys.argv) > 3 and sys.argv[3] != "":
            with open(sys.argv[3], "r") as f:
                display_customizations = f.read()
    else:
        display_customizations = ""

    # Fourth argument is for strict yaml data usage
    if len(sys.argv) > 4 and sys.argv[4] != "":
        # Otherwise special shell around top unit is generated
        # to provide uniform rendering of unit neither it's top or  it's nested
        # (default behaviour)
        hunit = '''
attributes:
  type: ""
display:
  "": {view: nested}
  "U1": {view: full}
units:
  U1:
    unit: '''+filepath+'''
    label: ""
'''
    else:
        hunit = None

    filepath = guess_filepath(_BASE_PATH, filepath)
    data = load_unit(filepath, "", {}, None)
    hdata = load_unit(filepath, "", {}, None, yaml_string=hunit)
    schm, _ = hdelk_render(hdata, "", "")
    html = hdelk_html(schm, "Schematic of " + data["attributes"].get("type", filepath), display_customizations)

    if opath is None:
        print(html)
    else:
        if opath == "html":
            opath = data.get("attributes", {}).get("type", "")+".html"
            if opath != ".html":
                opath = os.path.join("Output", opath)
        with open(opath, "w", encoding="utf-8") as f:
            f.write(html)
