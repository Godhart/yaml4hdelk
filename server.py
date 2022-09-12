from typing import Tuple
import os
from bottle import Bottle, run, SimpleTemplate, request, static_file, response
import json
import yaml
import yaml4schm
from yaml4schm import load_unit, render_unit, connect, renderer, tool_adaptation, cleanup
from yaml4schm_defs import TOOL_HDELK, TOOL_D3HW
from yaml4schm_defs import RENDER_ADD_MISSING_UNITS, RENDER_ADD_MISSING_PORTS
from operators import parse_line, Expression
from server_data import new_domain, DataDomain


# TODO: REST lookup to get files by path pattern
# TODO: REST diagram     dia/<path:path>
# TODO: REST commit

# TODO: add common header to all JSON responses (server version, args etc.)
# TODO: add domains config file
# TODO: validate requests with JSON schema
# TODO: add links onto schematic items to traverse into the deep (interactive inplace or open in a new page)
# TODO: whiteboard mode

#   https://bottlepy.org/docs/dev/async.html
#   https://stackoverflow.com/questions/13318608/streaming-connection-using-python-bottle-multiprocessing-and-gevent


_VERSION = "1.4a0.0"
_VERSION_HISTORY = {
    "1.4": "added RESTful interface",
    "1.3": "supported changes in view/edit templates (svg styling)",
    "1.2": "+ live debug",
    "1.1": "+ editor mode, JSON output",
    "1.0": "Renders schematics from files on server",
}

_versions = {
    "yaml4schm_version": yaml4schm._VERSION,
    "server_version": _VERSION,
}


_DOMAINS = {}

_POST = "POST"
_GET = "GET"


def get_domains():
    if len(_DOMAINS) == 0:
        _DOMAINS["Demo"] = new_domain("Demo", "./Demo")
        env = [*os.environ.keys()]
        domain_prefix = "YAML4SCHM_FILES_DOMAIN_"
        for k in env:
            # TODO: read configs
            # TODO: create domain that corresponds to it's kind (fs, http, git)
            if k[:len(domain_prefix)] == domain_prefix:
                domain_name = k[len(domain_prefix):].lower()
                _DOMAINS[domain_name] = new_domain(
                    name=domain_name,
                    path=os.environ.get(k)
                )
    return _DOMAINS


get_domains()

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
    # TODO: remove this

    path_items = path.split('/')
    if len(path_items) < 2:
        raise ValueError(
            "<pre>Use following URL Format: /&lt;tool_name&gt;/show/&lt;files_domain&gt;/&lt;file_path&gt;</pre>")  # TODO: 404
    if "/../" in path:
        raise ValueError(
            "<pre>Hierarchy ('..' items) in the file path is not supported!<pre>")
    if path_items[0] == "demo":
        files_domain = "Demo"
    else:
        files_domain = os.environ.get(
            "YAML4SCHM_FILES_DOMAIN_"+path_items[0].upper(), None)
        if files_domain is None:
            raise ValueError(
                f"<pre>Files domain '{path_items[0]}' is not defined!</pre>")  # TODO: 404
    return files_domain, files_domain + "/" + "/".join(path_items[1:])


def build_schm(tool, source_data, make_shell, override_source_text=None, create=False):
    """Build schematic data out of YAML description"""

    print(f"build_schm(\n  tool={tool},\n  source_data={source_data},\n"
          "  make_shell={make_shell},\n  override_source_text={override_source_text})")
    load_from_file = False

    if isinstance(source_data, str):
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
                    raise ValueError(
                        f"File {source_data} is not found!")       # TODO: 404
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
                raise ValueError(
                    f"Path {source_data} is directory, not file!")  # TODO: 404
            else:
                with open(file_path, "r") as f:
                    source = f.read()
        source_string = override_source_text
        unit_data = source_data
    else:
        source_string = yaml.dump(source_data)
        # TODO: looks like file_path isn't set in case if source data isn't filepath
        unit_data = f"@{file_path}"

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
        data = load_unit(file_path, "", "", {}, None,
                         yaml_string=source_string)
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
        meta = ""
        stylesheet = ""
        static_svg = "false"
    else:
        meta = '<meta charset="utf-8">'
        stylesheet = ""
        static_svg = "false"

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
        "path": path
    }

    response.content_type = 'application/json'
    print(f"show_json(\n  tool={tool},\n  path={path})")
    if tool not in _allowed_tools:
        return _error(f"Tool '{tool}' is not supported!", common)

    try:
        _, _, schm = build_schm(tool, path, make_shell=False)
    except Exception as e:
        return _error(f"Failed due to exception {e}", common)
    return _success({"schematic": schm}, common)


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

    meta = '<meta charset="utf-8">'
    stylesheet = ''
    static_svg = "false"

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


@app.route('/<tool>/edit/<path:path>', method=_POST)
def edit(tool, path):
    """ Server-side business logic to react on changes in the editor """
    response.content_type = 'application/json'
    print(f"edit(\n  tool={tool},\n  path={path})")
    if tool not in _allowed_tools:
        return _error(f"Tool '{tool}' is not supported!", {})

    data = request.json.get("text", "{}")

    try:
        source, _, schm = build_schm(
            tool, path, make_shell=False, override_source_text=data, create=True)
    except Exception as e:
        return _error(f"Rendering schematic failed due to exception: {e}", {})

    path_items = path.split("/")
    domain = path_items[0]
    file_path = "/".join(path_items[1:])
    domain, error = _get_domain(domain)
    if error is None:
        hash = domain.get_files_hash([file_path])[file_path]
    else:
        hash = None

    return _success({"diagram": schm, "source": source, "hash": hash}, {})


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

    meta = '<meta charset="utf-8">'
    stylesheet = ''

    return tooler.render(
        yaml4schm_version=yaml4schm._VERSION,
        server_version=_VERSION,
        meta=meta,
        stylesheet=stylesheet,
        tool="live",
        editor="debug",
        file_path=subject,
        title="Expressions")


@app.route('/live/debug/<subject>', method=_POST)
def live_debug_post(subject):
    """ Server-side business logic to react on changes in the editor """
    response.content_type = 'application/json'
    print(f"live_debug_post(subject={subject})")

    data = request.json.get("text", "{}")
    result = {}

    try:
        for line in data.split("\n"):
            try:
                expr = Expression("", [0])
                parse_line(line, expr)
                units = {}
                nets = []
                output_net = expr.export(units, nets, "Top")
                result[line] = {
                    "expr": expr.as_dict(),
                    "output_net": output_net,
                    "units": units,
                    "nets": nets,
                }
            except Exception as e:
                result[line] = {
                    "ERROR": f"Parsing line failed due to exception: {e}"}
    except Exception as e:
        return _error({f"Processing expressions failed due to exception: {e}"}, {})

    s_result = yaml.dump(result)
    print(s_result)
    return _success({"diagram": s_result, "source": data, "hash": None}, {})


@app.route('/<tool>/save/<path:path>', method=_POST)
def save_by_path(tool, path):
    """ Save schematic from editor onto hosing server drive """
    response.content_type = 'application/json'
    print(f"save(\n  tool={tool},\n  path={path})")
    if tool not in _allowed_tools:
        return _error(f"Tool '{tool}' is not supported!", {})

    path_items = path.split("/")
    domain = path_items[0]
    file_path = "/".join(path_items[1:])

    domain, error = _get_domain(domain)
    if error is not None:
        return _error(error, {})

    data = {file_path: {}}
    text = request.json.get("text", None)
    if text is not None:
        data[file_path]["content"] = text
    hash = request.json.get("hash", None)
    if hash is not None:
        data[file_path]["hash"] = hash

    # Build schematics to make sure data is OK
    try:
        content, _, diagram = build_schm(
            tool, path, make_shell=False, override_source_text=text, create=True)
    except Exception as e:
        return _error(f"Schematic check failed due to exception: {e}!", {})

    _, error = _save_files(
        domain, data)
    if error is not None:
        return _error(error, {})

    update_result, error = _get_files(domain, [file_path], ["hash"])
    if error is not None:
        hash = None
    else:
        hash = update_result[file_path]["hash"]

    return _success({
        "diagram": diagram,
        "source": content,
        "hash": hash
    }, {})


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


@app.route('/rest/1.0/domains/domainsList')
def domains_list():
    """ Return list of available domains """
    response.content_type = 'application/json'
    print(f"domains_list()")

    common = {}

    return _success({"domains": sorted(get_domains().keys())}, common)


@app.route('/rest/1.0/domain/<domain>/filesList')
def files_list(domain):
    """ Return list of available files within domain """
    response.content_type = 'application/json'
    print(f"files_list({domain}, ...)")

    common = {"domain": domain}

    domain, error = _get_domain(domain)
    if error is not None:
        return _error(error, common)

    try:
        files = domain.list_files()
        return _success({"files": files}, common)
    except Exception as e:
        return _error(f"Failed due to exception: {e}", common)


@app.route('/rest/1.0/domain/<domain>/lock/<path:path>', method=_POST)
def file_lock(domain, path):
    """ Sets lock on file """
    response.content_type = 'application/json'
    do_lock = request.json.get("set", "False")
    force = request.json.get("force", "False")
    secret = request.json.get("secret", None)
    test = request.json.get("test", "False")
    print(
        f"file_lock({domain},{path},do_lock={do_lock},force={force},secret={secret},test={test})")

    if do_lock is not True and test is not True:
        return _error("Wrong parameter! Determine what you want!", common)

    if secret is None:
        return _error(f"No secret were provided!", common)

    common = {"domain": domain, "do_lock": do_lock,
              "force": force, "secret": secret, "test": test}

    domain, error = _get_domain(domain)
    if error is not None:
        return _error(error, common)

    lock, error = domain.lock(path, force, secret, dry_run=test)
    if error is not None:
        return _error(error, common)
    else:
        return _success({"lock": lock}, common)


@app.route('/rest/1.0/domain/<domain>/unlock/<path:path>', method=_POST)
def file_unlock(domain, path):
    """ Removes lock from file """
    response.content_type = 'application/json'
    secret = request.json.get("secret", None)
    force = request.json.get("force", "False")
    print(f"file_unlock({domain},{path})")

    common = {"domain": domain, "path": path, "secret": secret, "force": force}

    domain, error = _get_domain(domain)
    if error is not None:
        return _error(error, common)

    _, error = domain.unlock(path, secret, force)
    if error is not None:
        return _error(error, common)
    else:
        return _success({}, common)


@app.route('/rest/1.0/domain/<domain>/get', method=_POST)
def get_files(domain):
    """ Gets data for specified files """
    response.content_type = 'application/json'

    print(f"save_rest({domain})")

    fields = request.get("fields", [])

    common = {"domain": domain, "fields": fields}

    domain, error = _get_domain(domain)
    if error is not None:
        return _error(error, common)

    if len(fields == 0):
        return _error("fields is not provided!", common)

    files = request.json.get("filesList", None)
    if files is None:
        return _error("filesList is not provided!", common)

    result, error = _get_files(domain, files, fields)

    if error is None:
        return _success(result, common)
    else:
        return _error(error, common)


def _get_files(domain: DataDomain, files, fields):

    result = {"data": {}}

    if len(fields) > 0:
        for k in files.keys():
            file_data, error = domain.get_file(k, fields)
            if error is not None:
                result["files"][k] = {"ERROR": "Error getting file: " + error}
            else:
                result["files"][k] = {**file_data}

    return result, None


@app.route('/rest/1.0/domain/<domain>/save', method=_POST)
def save_rest(domain):
    """ Saves incoming data (multiple files), returns requested fields of saved content """
    response.content_type = 'application/json'

    print(f"save_rest({domain})")

    fields = request.get("fields", [])
    dry_run = request.get("dry_run", [])

    common = {"domain": domain, "fields": fields, "dry_run": dry_run}

    domain, error = _get_domain(domain)
    if error is not None:
        return _error(error, common)

    data = request.json.get("data", None)
    if data is None:
        return _error("No data provided!", common)

    if not isinstance(data, dict):
        return _error("Data should be a dict with file paths as keys, and content + previous hash as data + secret of unlocking locked files!", common)

    _, error = save(domain, data, dry_run)
    if error is not None:
        return _error(error, common)

    if not dry_run and len(fields) > 0:
        result, error = _get_files(domain, data.keys(), fields)
    else:
        result, error = {}, None

    if error is None:
        return _success(result, common)
    else:
        return _error(error, common)


def save(domain: DataDomain, files, dry_run=False):
    # Check content, hash, lock
    errors = []
    current_hashes = domain.get_files_hash(files.keys())
    current_locks = domain.get_files_lock(files.keys())
    for file_path, v in files.items():
        content = v.get("content", None)
        if content is None:
            errors.append(f"No file content provided for '{file_path}'!")
        else:
            if not isinstance(content, str):
                errors.append(f"Content for '{file_path}' is not a string!")

        previous_hash = v.get("hash", None)
        if previous_hash is None:
            errors.append(f"No hash provided for '{file_path}'!")
        else:
            if previous_hash != current_hashes.get(file_path, None):
                errors.append(
                    f"Content of '{file_path}' were changed on server since your last checkout."
                    " Sync your data (stash, reload, apply) before saving!")

        current_lock = current_locks.get(file_path, "")
        if current_lock is not None and current_lock != "":
            secret = v.get("secret", None)
            if secret is None:
                errors.append(
                    f"File '{file_path}' is locked but no secret were provided to unlock!")

            client_lock = domain._lock_hash(secret)
            if client_lock != current_lock:
                errors.append(
                    f"Secret for unlocking file '{file_path}' is wrong!")

    if len(errors) > 0:
        return None, "Files related errors:\n  - " + '\n  - '.join(errors)

    # Save data
    _, error = _save_files(domain, files, dry_run)
    if error is not None:
        return None, error

    return True, None


def _save_files(domain: DataDomain, files, dry_run=False):

    errors = []
    if not dry_run:
        for file_path, v in files.items():
            _, save_error = domain.save_file(file_path, v.get("content", None))
            if save_error is not None:
                errors.append(save_error)
    if len(errors) > 0:
        return None, "Files related errors:\n  - " + '\n  - '.join(errors)

    return True, None


def _get_domain(domain) -> Tuple[DataDomain, str]:
    domains = get_domains()
    if domain not in domains:
        return None, f"Domain '{domain}' is not exists!"
    return domains[domain], None


def _error(message, rest):
    return json.dumps({"ERROR": message, **rest, **_versions})


def _success(data, rest):
    return json.dumps({"SUCCESS": True, **data, **rest, **_versions})


if __name__ == "__main__":
    host = os.environ.get("SERVER_HOST", "localhost")
    port = os.environ.get("SERVER_PORT", 8083)
    run(app, host=host, port=int(port), debug=True)
