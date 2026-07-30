"""
pma_houdini — the Houdini-side half of the Creative Module.

Import this from a shelf tool or hython script. Do NOT import it from
plain Python outside Houdini — `extractor.extract_scene` imports `hou`,
which only exists inside a running Houdini process.
"""
