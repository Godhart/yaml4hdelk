# YAML4SCHM
A helper tool to produce schematics
with [HDElk](https://davidthings.github.io/hdelk/)
or [d3-hwschematic](https://https://github.com/Nic30/d3-hwschematic).

Tool transforms schematic text (YAML) description into rendering tool
compatible format then creates HTML to view the result.

YAML-based schematic description is designed to be compact, human friendly and
reuse friendly.

Examples of YAML-based description and corresponding HTML output for each tool
are in `Demo` folder.

> NOTE: `d3-hwschematic` provides interactive schematic view, not just static
> image.

# Key benefits:
* Schematic as a code
* YAML (is better for humans than JSON in an original tool)
* Schematics could be organized into multiple files and then used
  * as separate units
  * as a part of another schematic
* Multiple files allows code reuse and making complex schematics simple
* Regexes for simplified multipoint connections description such as
  CLOCK, RESET, CE etc.
* Control view of schematic
  * View control can be separated from schematic description
  * Multiple views for same schematic
  * Control visibility of schematics items
    * Expand/collapse schematics for nested units
    * Hide specified units
    * Hide specified ports
    * Hide specified nets
  * Colorize items
  * Use regexes to specify items
  * Collapse schematic into structural preview (comming soon)
* Faster entry than graphics editor
  * Sketch 'mode' to capture ideas
  * No pixel hunting / placement / routing / alignment involved
    (but you'll have to grant results of automatic placement/routing)
* Version control and changes review friendly
* Place any sort of comments along schematic description as you require -
  no need to wipe them off before printing
* Along with original tool you'll get unification for schematics representation
  (though someone may find it's boring), so updating schematics after styles
  change is easy
* More than picture with `d3-hwschematic`

# Current state

Works:
* Schematic entry works
* View control works in basic
* Both tools are supported in basic

To be done:
* Complete support for rendering tools features
* Unit's parameters (aka generics) specification
* Arrays indications / generation
* View specification
  * Highlighting
  * Hiding
  * Conditioning (via tool params)
* Collapsing into structural view
