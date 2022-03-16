# YAML4HDElk
A helper tool to produce schematics with [HDElk](https://davidthings.github.io/hdelk/)

Schematics are described via YAML files then rendered with tool into HTML

Examples of YAML files and HTML output are in `Demo` folder

# Key benefits:
* Schematic description is separated from HTML
* YAML (is better than JSON in an original tool)
* Schematics could be described via separate files and then reused
  * as separate units
  * as a part of another schematic
* Regexes for connections description such as CLOCK, RESET, CE etc.
* Control view of schematic
  * Hide unnecessary items
  * Control visibility of schematics for nested units as deep as you need
  * View control can be separated from schematic
  * Multiple views for same schematic
* Faster entry than graphics editors
* Version control and changes review friendly

# Current state

Works:
* Schematic entry works
* View control works in basic

To be done:
* Highlighting specification (should work but could be better)
* Parameters specification
* Arrays indications
