import os
from bottle import Bottle, run, SimpleTemplate, request, static_file, response
import hashlib
import json
import yaml
import yaml4schm
from yaml4schm import load_unit, render_unit, connect, renderer, tool_adaptation, cleanup
from yaml4schm_defs import TOOL_HDELK, TOOL_D3HW
from yaml4schm_defs import RENDER_ADD_MISSING_UNITS, RENDER_ADD_MISSING_PORTS
from operators import parse_line, Expression
from helpers import prints


# TODO: add links to traverse into the deep
# TODO: whiteboard mode
#   https://bottlepy.org/docs/dev/async.html
#   https://stackoverflow.com/questions/13318608/streaming-connection-using-python-bottle-multiprocessing-and-gevent


_VERSION = "1.3b0.0"
_VERSION_HISTORY = {
    "1.3": "supported changes in view/edit templates (svg styling)",
    "1.2": "+ live debug",
    "1.1": "+ editor mode, JSON output",
    "1.0": "Renders schematics from files on server",
}


reload_template = os.environ.get("RELOAD_TEMPLATE", "FALSE").upper() == "TRUE"


app = Bottle()


@app.route('/')
@app.route('/index')
@app.route('/index.htm')
@app.route('/index.html')
def index():
    return "It Works!"


_allowed_tools = (TOOL_D3HW, TOOL_HDELK)


VIEW = "view"
EDIT = "edit"

templates = {
    TOOL_HDELK: {
        VIEW:   r"% include('hdelk_view_tpl.html', data=data,"
                r" yaml4schm_version=yaml4schm_version, server_version=server_version,"
                r" meta=meta,"
                r" svg_style=svg_style,"
                r" title=title, display_customizations=display_customizations)",
        EDIT:   r"% rebase('hdelk_edit_tpl.html',"
                r" yaml4schm_version=yaml4schm_version, server_version=server_version,"
                r" meta=meta,"
                r" svg_style=svg_style,"
                r" title=title, display_customizations=display_customizations)"+"\n"
                r"% include('editor_tpl.html', tool=tool, editor=editor, file_path=file_path)"
    },
    TOOL_D3HW: {
        VIEW:   r"% include('d3hw_view_tpl.html', data=data,"
                r" yaml4schm_version=yaml4schm_version, server_version=server_version,"
                r" meta=meta,"
                r" svg_style=svg_style,"
                r" title=title, static_svg=static_svg, stylesheet=stylesheet)",
        EDIT:   r"% rebase('d3hw_edit_tpl.html',"
                r" yaml4schm_version=yaml4schm_version, server_version=server_version,"
                r" meta=meta,"
                r" svg_style=svg_style,"
                r" title=title, static_svg=static_svg, stylesheet=stylesheet)"+"\n"
                r"% include('editor_tpl.html', tool=tool, editor=editor, file_path=file_path)"
    },
}


def _file_content(file_path):
    with open(file_path, "r") as f:
        return f.read()


svg_style = {
    TOOL_HDELK: "",
    TOOL_D3HW: _file_content("Demo/html/css/d3/d3-hwschematic.css")
}

renderers = {}
for _tool in templates:
    renderers[_tool] = {}
    for _view in templates[_tool]:
        renderers[_tool][_view] = SimpleTemplate(templates[_tool][_view])


def _internal_path(path):
    """Convert URL path into the path on the hosting server"""

    path_items = path.split('/')
    if len(path_items) < 2:
        raise ValueError("<pre>Use following URL Format: /&lt;tool_name&gt;/show/&lt;files_domain&gt;/&lt;file_path&gt;</pre>")  # TODO: 404
    if "/../" in path:
        raise ValueError("<pre>Hierarchy ('..' items) in the file path is not supported!<pre>")
    if path_items[0] == "demo":
        files_domain = "Demo"
    else:
        files_domain = os.environ.get("YAML4SCHM_FILES_DOMAIN_"+path_items[0].upper(), None)
        if files_domain is None:
            raise ValueError(f"<pre>Files domain '{path_items[0]}' is not defined!</pre>")  # TODO: 404
    return files_domain, files_domain + "/" + "/".join(path_items[1:])


def build_schm(tool, source_data, make_shell, override_source_text=None, create=False):
    """Build schematic data out of YAML description"""

    print(f"build_schm(\n  tool={tool},\n  source_data={source_data},\n"
    "  make_shell={make_shell},\n  override_source_text={override_source_text})")
    load_from_file = False

    if isinstance (source_data, str):
        load_from_file = True
        path = source_data
        files_domain, file_path = _internal_path(path)
    else:
        file_path = ""

    if load_from_file:
        if override_source_text is not None:
            source = override_source_text
        else:
            if not os.path.exists(file_path):
                if not create:
                    raise ValueError(f"File {source_data} is not found!")       # TODO: 404
                else:
                    source = override_source_text = \
r"""# You are about to create a new file
# This is a text for a welcome-stub
# Just replace it with your diagram description
# Check the URL for typos if it's not what you are intended to do
# Read the docs TODO: <https://url.for.docs> if not sure what to do
nets:
  - [   CREATE_NEW_FILE.NO,    CHECK.URL,                      name:TYPO       ]
  - [   CREATE_NEW_FILE.YES,   KNOW_WHAT_TO_DO,                name:NEW_FILE   ]
  - [   KNOW_WHAT_TO_DO.YES,   YOUR_IMAGINATION.IDEAS,         name:DO_IT      ]
  - [   KNOW_WHAT_TO_DO.NO,    [THE_DOCS.READ, EXAMPLES.VIEW], name:GET_IT     ]
  - [   THE_DOCS.GOT_IDEA,     YOUR_IMAGINATION.IDEAS,         name:DO_IT      ]
  - [   EXAMPLES.GOT_IDEA,     YOUR_IMAGINATION.IDEAS,         name:DO_IT      ]
"""
            elif not os.path.isfile(file_path):
                raise ValueError(f"Path {source_data} is directory, not file!") # TODO: 404
            else:
                with open(file_path, "r") as f:
                    source = f.read()
        source_string = override_source_text
        unit_data = source_data
    else:
        source_string = yaml.dump(source_data)
        unit_data = f"@{file_path}"  # TODO: looks like file_path isn't set in case if source data isn't filepath

    if make_shell is True and override_source_text is None:
        hunit = yaml.dump({
            "attributes": {"type": ""},
            "display": {
                "": {"view": "nested"},
                "/": {"view": "full"}
            },
            "units": {"/": {"unit": unit_data, "name": ""}}
        })
    else:
        hunit = None

    old_root = yaml4schm._ROOT_PATH
    yaml4schm._ROOT_PATH = files_domain
    try:
        data = load_unit(file_path, "", "", {}, None, yaml_string=source_string)
        if hunit is not None:
            hdata = load_unit(file_path, "", "", {}, None, yaml_string=hunit)
        else:
            hdata = data
    except Exception as e:
        yaml4schm._ROOT_PATH = old_root
        raise e

    schm = render_unit(tool, hdata, "", is_top=True, custom=hdata)
    connect(tool, schm, (RENDER_ADD_MISSING_UNITS, RENDER_ADD_MISSING_PORTS))
    renderer(tool, schm)
    tool_adaptation(tool, schm)
    cleanup(schm)
    return source, data, schm


def render(tool, source_data, make_shell, draw_only=False, title=""):
    """Render schematic into the HTML page"""

    print(f"render(\n  tool={tool},\n  source_data={source_data},\n  make_shell={make_shell},\n  draw_ony={draw_only})\n"
          f"  title={title}")
    try:
        _, data, schm = build_schm(tool, source_data, make_shell)
    except Exception as e:
        return f"Schematic rendering failed due to exception: {e}"

    if reload_template:
        tooler = SimpleTemplate(templates[tool][VIEW])
    else:
        tooler = renderers[tool][VIEW]

    if draw_only:
        meta=""
        stylesheet=""
        static_svg="false"
    else:
        meta='<meta charset="utf-8">'
        stylesheet=""
        static_svg="false"

    return tooler.render(
        yaml4schm_version=yaml4schm._VERSION,
        server_version=_VERSION,
        data=json.dumps(schm),
        title=f"{title}",
        static_svg=static_svg,
        meta=meta,
        svg_style=svg_style[tool],
        stylesheet=stylesheet,
        display_customizations="")


@app.route('/<tool>/show/<path:path>')
def show(tool, path):
    """Page with schematic to view in browser"""

    print(f"show(\n  tool={tool},\n  path={path})")
    if tool not in _allowed_tools:
        return f"Tool '{tool}' isn't supported!"

    return render(tool, path, make_shell=False, title=path)


@app.route('/<tool>/draw/<path:path>')
def draw(tool, path):
    """
    Page with schematic that can be rendered by Devdoc-Swissknife
    Some tags that affect this are dropped
    """

    print(f"draw(\n  tool={tool},\n  path={path})")
    if tool not in _allowed_tools:
        return f"Tool '{tool}' isn't supported!"

    return render(tool, path, make_shell=False, draw_only=True, title=path)


@app.route('/<tool>/json/<path:path>')
def show_json(tool, path):
    """ Completely built schematic in JSON format """

    common = {
        "tool": tool,
        "path": path,
        "yaml4schm_version": yaml4schm._VERSION,
        "server_version": _VERSION,
    }

    response.content_type = 'application/json'
    print(f"show_json(\n  tool={tool},\n  path={path})")
    if tool not in _allowed_tools:
        return json.dumps(
            {"ERROR": f"Tool '{tool}' is not supported!", **common})

    try:
        _, _, schm = build_schm(tool, path, make_shell=False)
    except Exception as e:
        return json.dumps(
            {"ERROR": f"Failed due to exception {e}", **common})
    return json.dumps({"SUCCESS": True, "schematic": schm, **common})


@app.route('/<tool>/edit/<path:path>', method="GET")
def editor(tool, path):
    """ Schematic editor page """
    print(f"editor(\n  tool={tool},\n  path={path})")
    if tool not in _allowed_tools:
        return f"Tool '{tool}' isn't supported!"

    if reload_template:
        tooler = SimpleTemplate(templates[tool][EDIT])
    else:
        tooler = renderers[tool][EDIT]

    meta='<meta charset="utf-8">'
    stylesheet=''
    static_svg="false"

    return tooler.render(
        yaml4schm_version=yaml4schm._VERSION,
        server_version=_VERSION,
        file_path=path,
        tool=tool,
        editor="edit",
        title="Editing: "+path,
        static_svg=static_svg,
        meta=meta,
        svg_style=svg_style[tool],
        stylesheet=stylesheet,
        display_customizations="")


@app.route('/<tool>/edit/<path:path>', method="POST")
def edit(tool, path):
    """ Server-side business logic to react on changes in the editor """
    response.content_type = 'application/json'
    print(f"edit(\n  tool={tool},\n  path={path})")
    if tool not in _allowed_tools:
        return json.dumps({"ERROR": f"Tool '{tool}' is not supported!"})

    data = request.json.get("text", "{}")

    try:
        source, _, schm = build_schm(tool, path, make_shell=False, override_source_text=data, create=True)
    except Exception as e:
        return json.dumps({"ERROR": f"Rendering schematic failed due to exception: {e}"})

    _, file_path = _internal_path(path)
    if os.path.exists(file_path):
        with open(file_path, "rb") as f:
            hash = hashlib.md5(f.read()).hexdigest()
    else:
        hash = None

    return json.dumps({"SUCCESS": True, "diagram": schm, "source": source, "hash": hash})


@app.route('/live/debug/<subject>', method="GET")
def live_debug_get(subject):
    """ Live debug editor page """
    print(f"live_debug({subject})")

    sub = "func"
    tooler = SimpleTemplate(
        r"% rebase('live_dbg_tpl.html',"
        r" yaml4schm_version=yaml4schm_version, server_version=server_version,"
        r" meta=meta,"
        r" title=title)"+"\n"
        r"% include('editor_tpl.html', tool=tool, editor=editor, file_path=file_path)"
    )

    meta='<meta charset="utf-8">'
    stylesheet=''

    return tooler.render(
        yaml4schm_version=yaml4schm._VERSION,
        server_version=_VERSION,
        meta=meta,
        stylesheet=stylesheet,
        tool="live",
        editor="debug",
        file_path=subject,
        title="Expressions")


@app.route('/live/debug/<subject>', method="POST")
def live_debug_post(subject):
    """ Server-side business logic to react on changes in the editor """
    response.content_type = 'application/json'
    print(f"live_debug_post(subject={subject})")

    data = request.json.get("text", "{}")
    result = {}

    if True: #try:
        for line in data.split("\n"):
            if True: #try:
                expr = Expression("", [0])
                parse_line(line, expr)
                units = {}
                nets = []
                output_net = expr.export(units, nets, "Top")
                result[line] =  {
                    "expr" : expr.as_dict(),
                    "output_net": output_net,
                    "units": units,
                    "nets": nets,
                }
            else: #except Exception as e:
                result[line] = {"ERROR": f"Parsing line failed due to exception: {e}"}
    else: #except Exception as e:
        return json.dumps({"ERROR": f"Processing expressions failed due to exception: {e}"})

    s_result = yaml.dump(result)
    print(s_result)
    return json.dumps({"SUCCESS": True, "diagram": s_result, "source": data, "hash": None})


@app.route('/<tool>/save/<path:path>', method="POST")
def save(tool, path):
    """ Save schematic from editor onto hosing server drive """
    response.content_type = 'application/json'
    print(f"save(\n  tool={tool},\n  path={path})")
    if tool not in _allowed_tools:
        return json.dumps({"ERROR": f"Tool '{tool}' is not supported!"})

    data = request.json.get("text", None)
    if data is None:
        return json.dumps({"ERROR": f"Source text is missing!"})

    # Build schematics to make sure data is OK
    try:
        source, _, schm = build_schm(tool, path, make_shell=False, override_source_text=data, create=True)
    except Exception as e:
        return json.dumps({"ERROR": f"Schematic check failed due to exception: {e}!"})

    # Check there were no changes since editor were opened
    _, file_path = _internal_path(path)
    if os.path.exists(file_path):
        with open(file_path, "rb") as f:
            hash = hashlib.md5(f.read()).hexdigest()
    else:
        hash = None

    last_hash = request.json.get("hash", None)
    if hash != last_hash:
        return json.dumps({"ERROR": f"File '{path}' were changed since last checkout.\nPlease save your work to offline file then update page and merge your changes."})

    with open(file_path, "w") as f:
        f.write(data)

    with open(file_path, "rb") as f:
        hash = hashlib.md5(f.read()).hexdigest()

    return json.dumps({"SUCCESS": True, "diagram": schm, "source": source, "hash": hash})


@app.route('/<tool>/test')
def test(tool):
    """ Renders simple test page with predefined schematic """

    if tool not in _allowed_tools:
        return f"Tool '{tool}' isn't supported!"

    return render(tool, "demo/unit3.yaml", make_shell=False, title="Test")


@app.route('/js/<path:path>')
def js(path):
    """ Static Javascript Files """

    return static_file(path, root="Demo/html/js")


@app.route('/css/<path:path>')
def css(path):
    """ Static CSS Files """

    return static_file(path, root="Demo/html/css")


@app.route('/monaco/<path:path>')
def monaco(path):
    """ Static TTF Files """

    return static_file(path, root="Demo/html/monaco")


if __name__ == "__main__":
    host = os.environ.get("SERVER_HOST", "localhost")
    port = os.environ.get("SERVER_PORT", 8083)
    run(app, host=host, port=int(port), debug=True)
