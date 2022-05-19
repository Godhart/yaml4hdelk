import os
from bottle import Bottle, run, SimpleTemplate, Request, static_file
import json
import yaml
import yaml4schm
from yaml4schm import load_unit, render_unit, connect, renderer, tool_adaptation, cleanup
from yaml4schm_defs import TOOL_HDELK, TOOL_D3HW
from yaml4schm_defs import RENDER_ADD_MISSING_UNITS, RENDER_ADD_MISSING_PORTS


app = Bottle()


@app.route('/')
@app.route('/index')
@app.route('/index.htm')
@app.route('/index.html')
def index():
    return "It Works!"


hdelk = SimpleTemplate("% include('hdelk_tpl.html', data=data, title=title)")
d3hw = SimpleTemplate("% include('d3hw_tpl.html', data=data, title=title)")

def render(tool, source_data, make_shell):
    load_from_file = False

    if isinstance (source_data, str):
        load_from_file = True
        path = source_data
        path_items = path.split('/')
        if len(path_items) < 2:
            return "<pre>Use following URL Format: /&lt;tool_name&gt;/show/&lt;files_domain&gt;/&lt;file_path&gt;</pre>"
        if path_items[0] == "demo":
            files_domain = "Demo"
        else:
            files_domain = os.environ.get("YAML4SCHM_FILES_DOMAIN_"+path_items[0].upper(), None)
            if files_domain is None:
                return f"<pre>Files domain '{path_items[0]}' is not defined!</pre>"
        file_path = files_domain + "/" + "/".join(path_items[1:])
    else:
        file_path = ""

    if load_from_file:
        source_string = None
        unit_data = source_data
    else:
        source_string = yaml.dump(source_data)
        unit_data = f"@{file_path}"

    if make_shell is True:
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

    if tool == TOOL_HDELK:
        tooler = hdelk
    else:
        tooler = d3hw

    return tooler.render(
        data=json.dumps(schm),
        title=data.get("attributes", {}).get("type", "Schematic"),
        display_customizations="")


@app.route('/hdelk/show/<path:path>')
def hdelk_show(path):
    tool = TOOL_HDELK

    return render(tool, path, False)


@app.route('/d3hw/show/<path:path>')
def d3hw_show(path):
    tool = TOOL_D3HW

    return render(tool, path, False)


@app.route('/hdelk/render/post', method='POST')
def hdelk_render_post():
    tool = TOOL_HDELK

    if Request.json.get("is_yaml", False) is False:
        source_data = yaml.safe_load(Request.json.get("data", "{}"))
    else:
        source_data = Request.json.get("data", {})

    return render(tool, source_data, Request.json.get("make_shell", False))


@app.route('/hdelk/render/test')
def hdelk_render_test():
    tool = TOOL_HDELK

    with open("Demo/unit3.yaml", "r") as f:
        source_data = yaml.safe_load(f)

    return render(tool, source_data, make_shell=False)


@app.route('/d3hw/render/test')
def hdelk_render_test():
    tool = TOOL_D3HW

    with open("Demo/unit3.yaml", "r") as f:
        source_data = yaml.safe_load(f)

    return render(tool, source_data, make_shell=False)


@app.route('/js/<path:path>')
def js(path):
    return static_file(path, root="Demo/html/js")


@app.route('/css/<path:path>')
def css(path):
    return static_file(path, root="Demo/html/css")


if __name__ == "__main__":
    host = os.environ.get("SERVER_HOST", "localhost")
    port = os.environ.get("SERVER_PORT", 8083)
    run(app, host=host, port=int(port), debug=True)
