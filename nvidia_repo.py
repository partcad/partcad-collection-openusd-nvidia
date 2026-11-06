#
# partcad-openusd-nvidia, 2026
#
# Licensed under Apache License, Version 2.0.
#
"""A PartCAD 'basic' repository plugin that serves NVIDIA's Omniverse sample content as parts.

Published as ``//pub/collection/openusd/nvidia/assets``. The content is what
NVIDIA publishes for Omniverse in its public bucket,
omniverse-content-production - the same files its downloadable asset packs
zip up - which openusd.org's Downloads page links to as NVIDIA's "Example
Assets":

    archvis-commercial    the ArchVis commercial props: furniture for offices,
                          conference rooms, ...
    archvis-industrial    the ArchVis industrial props: pallets, racks,
                          shelves, containers, ...
    archvis-residential   the ArchVis residential props
    simready              the SimReady props: made for simulation
    marbles               the Marbles demo's standalone assets
    samples               the sample scenes: the Old Attic, the Marbles, the
                          Astronaut, EuclidVR

A part per asset, named as its file is (a name two folders share is told
apart by its folder's). Each is ``type: usd``, built by PartCAD's own part
type of that name from a USDZ the plugin packs of the asset's own layers (see
usd_assets.py). Listing a package reads the bucket's listings a folder at a
time - the package's folder and the folders its assets are in, never the
textures and materials beside them - and the plugin keeps them for a week, so
listing and searching download no asset. Building one reads its own layers.

Materials are NVIDIA's MDL, which is left out with the textures: PartCAD builds
a part's geometry, and draws it in the colour a layer gives, where it gives one.

PartCAD runs this script once per key (via runpy) with the key in
``request["key"]``; the answer goes in ``output``.
"""

import importlib.util
import os
import posixpath
import sys

# When this plugin's answers stopped meaning what they meant before. PartCAD
# keys everything it caches of this package on it, so raise it with any change
# to what is answered - here, or in usd_assets.py.
#
# v1: ArchVis, SimReady, Marbles and the sample scenes, as PartCAD 'usd' parts.
CACHE_VERSION = 1


def _shared():
    """usd_assets.py, beside this script, under a name of this plugin's own."""
    name = "_partcad_openusd_nvidia_usd_assets"
    if name not in sys.modules:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "usd_assets.py")
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return sys.modules[name]


ua = _shared()

BUCKET = "https://omniverse-content-production.s3-us-west-2.amazonaws.com/"
DOCS = "https://docs.omniverse.nvidia.com/usd/latest/usd_content_samples/"
TERMS = "https://docs.omniverse.nvidia.com/platform/latest/common/NVIDIA_Omniverse_License_Agreement.html"

# Each child package: the folder of the bucket it is, what it is, and how its
# assets are found there, which is also what listing it costs (see 'found'):
#
#   'every'    every layer under the folder, but in the folders of what assets
#              are made of: the folder is walked a folder at a time, past those
#   'named'    the same walk, and only '<name>/<name>.usd', a folder an asset
#   'folders'  a folder per asset, '<name>/<name>.usd', from one listing of the
#              folder's subfolders alone: a thousand SimReady props are two
#              requests, where their files are tens of thousands of textures
#   'scenes'   the scenes in SCENES, which listing costs nothing
COLLECTIONS = {
    "archvis-commercial": ("Assets/ArchVis/Commercial/", "NVIDIA's ArchVis commercial props.", "every"),
    "archvis-industrial": ("Assets/ArchVis/Industrial/", "NVIDIA's ArchVis industrial props.", "every"),
    "archvis-residential": ("Assets/ArchVis/Residential/", "NVIDIA's ArchVis residential props.", "every"),
    "simready": (
        "Assets/simready_content/common_assets/props/",
        "NVIDIA's SimReady props, made for simulation.",
        "folders",
    ),
    "marbles": ("Samples/Marbles/assets/standalone/", "The standalone assets of NVIDIA's Marbles demo.", "named"),
    "samples": ("Samples/", "NVIDIA's sample scenes.", "scenes"),
}

# Which of an asset's encodings is taken, when a folder has it in several.
_ENCODINGS = (".usd", ".usdc", ".usda", ".usdz")

# The folders no asset is in: what assets are made of.
_NOT_ASSETS = {".thumbs", "textures", "materials", "subusds", "sublayers", "props_ref"}


def _not_assets(folder):
    return folder.lower() in _NOT_ASSETS or folder.startswith(".")


# The sample scenes, by the layer each is opened by.
SCENES = {
    "OldAttic": ("OldAttic/Attic_NVIDIA.usd", "The Old Attic: an attic full of props."),
    "Marbles": ("Marbles/Marbles_Assets.usd", "The Marbles demo's room and everything in it."),
    "Astronaut": ("Astronaut/Astronaut.usd", "An astronaut."),
    "EuclidVR": ("EuclidVR/EuclidVR_Stage.usd", "The EuclidVR stage."),
}


def found(listing, prefix, how):
    """{name: path} of the assets under 'prefix' of 'listing'.

    'every': every layer not in a folder of what assets are made of;
    'named': '<name>/<name>.usd', a folder per asset.
    """
    paths = []
    for path in sorted(listing):
        if not path.startswith(prefix) or posixpath.splitext(path)[1].lower() not in (
            ".usd",
            ".usda",
            ".usdc",
            ".usdz",
        ):
            continue
        parts = path[len(prefix) :].split("/")
        if any(part.lower() in _NOT_ASSETS or part.startswith(".") for part in parts[:-1]):
            continue
        stem = posixpath.splitext(parts[-1])[0]
        if how == "named" and not (len(parts) >= 2 and parts[-2] == stem):
            continue
        paths.append((stem, parts, path))
    # One layer of a name to a folder: the same asset in two encodings is one.
    first = {}
    for stem, parts, path in paths:
        key = (posixpath.dirname(path), stem)
        rank = _ENCODINGS.index(posixpath.splitext(path)[1].lower())
        if key not in first or rank < first[key][0]:
            first[key] = (rank, stem, parts, path)
    paths = sorted((entry[1:] for entry in first.values()), key=lambda entry: entry[2])
    stems = {}
    for stem, _, _ in paths:
        stems[stem] = stems.get(stem, 0) + 1
    named = {}
    for stem, parts, path in paths:
        # A name two folders share is told apart by its folder's.
        name = stem if stems[stem] == 1 or len(parts) < 2 else "%s_%s" % (parts[-2], stem)
        named.setdefault(ua.safe_id(name), path)
    return named


class Nvidia(ua.Source):
    NAME = "openusd-nvidia"
    TITLE = "NVIDIA"
    URL = DOCS + "downloadable_packs.html"
    DESC = (
        "NVIDIA's Omniverse sample content: the ArchVis props, the SimReady props, the Marbles assets and the "
        "sample scenes, a child package each and a part per asset."
    )
    LICENSE = "LicenseRef-NVIDIA-Omniverse-License-Agreement"
    VERSION = CACHE_VERSION
    REPOSITORY = "partcad-collection-openusd-nvidia"
    PLUGIN = "//pub/collection/openusd/nvidia:nvidia_repo"

    def collections(self):
        return {name: ua.Collection(name, desc, self.URL) for name, (_, desc, _) in COLLECTIONS.items()}

    def store(self):
        # The tree is the bucket, read a folder at a time: a layer that names a
        # file in another folder - a SimReady prop's physics material - finds
        # it where it is, and nothing lists more of the bucket than that.
        return ua.S3Store(self.http, BUCKET)

    def assets(self, collection):
        if collection not in COLLECTIONS:
            return {}
        prefix, _, how = COLLECTIONS[collection]
        store = self.store()
        if how == "scenes":
            paths = {name: prefix + path for name, (path, _) in SCENES.items()}
        elif how == "folders":
            paths = {ua.safe_id(name): "%s%s/%s.usd" % (prefix, name, name) for name in store.folder(prefix)[1]}
        else:
            paths = found(store.walk(prefix, skip=_not_assets), prefix, how)
        assets = {}
        for name, path in paths.items():
            desc = SCENES[name][1] if how == "scenes" else "%s, of NVIDIA's %s." % (
                name.replace("_", " "), COLLECTIONS[collection][1].split("NVIDIA's ", 1)[1].rstrip(".")
            )  # fmt: skip
            assets[name] = ua.Asset(name, store, path, desc=desc, url=BUCKET + posixpath.dirname(path) + "/",
                                    author="NVIDIA")  # fmt: skip
        return assets


def get(key):
    return ua.serve(Nvidia(globals().get("request")), key)


# Last, so that everything above is defined when PartCAD runs this.
if __name__ == "get":
    output = {"result": get(request["key"])}  # noqa: F821 - injected by the runtime
else:
    output = {}
