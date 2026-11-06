#
# partcad-openusd-nvidia, 2026
#
# Licensed under Apache License, Version 2.0.
#
"""Tests of the NVIDIA plugin, with NVIDIA's bucket answered from a table.

The bucket lists itself as S3 does - ListObjectsV2, a folder ('delimiter=/')
and a page at a time - and its folders are laid out as
omniverse-content-production's are, with made-up layers in them. Nothing here
touches the network.
"""

import base64
import importlib.util
import io
import os
import re
import runpy
import urllib.parse
import zipfile

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_PLUGIN = os.path.join(_HERE, "nvidia_repo.py")
_SPEC = importlib.util.spec_from_file_location("nvidia_repo_under_test", _PLUGIN)
plugin = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(plugin)
ua = plugin.ua


def _usda(text=""):
    return ("#usda 1.0\n" + text).encode()


SIMREADY = "Assets/simready_content/"
FILES = {
    "Assets/ArchVis/Industrial/Pallets/Pallet_A1.usd": _usda("( subLayers = [@./Textures/T_Pallet.png@] )\n"),
    "Assets/ArchVis/Industrial/Pallets/Textures/T_Pallet.png": b"png",
    "Assets/ArchVis/Industrial/Pallets/Textures/.thumbs/256x256/T_Pallet.png.auto.png": b"small png",
    "Assets/ArchVis/Industrial/Pallets/.thumbs/256x256/Pallet_A1.usd.png": b"png",
    "Assets/ArchVis/Industrial/Racks/Rack_A1.usd": _usda(),
    "Assets/ArchVis/Industrial/Shelves/Rack_A1.usd": _usda(),
    "Assets/ArchVis/Industrial/Shelves/Materials/Steel.usda": _usda(),
    "Assets/ArchVis/Industrial/Shelves/Materials/Textures/T_Steel.png": b"png",
    SIMREADY
    + "common_assets/props/pallet_a01/pallet_a01.usd": _usda(
        "( subLayers = [@../../../materials/physics/physics_metal.usda@] )\n"
    ),
    SIMREADY + "common_assets/props/pallet_a01/pallet_a01.usda": _usda(),
    SIMREADY + "common_assets/props/pallet_a01/pallet_a01_base.usd": _usda(),
    SIMREADY + "common_assets/props/pallet_a01/textures/T_pallet.png": b"png",
    SIMREADY + "common_assets/props/crate_a02/crate_a02.usd": _usda(),
    SIMREADY + "common_assets/props/crate_a02/textures/T_crate.png": b"png",
    SIMREADY + "materials/physics/physics_metal.usda": _usda(),
    "Samples/OldAttic/Attic_NVIDIA.usd": _usda(),
    "Samples/OldAttic/Props/Chair.usd": _usda(),
}


def _listing(prefix, after=None, page=2):
    """One page of the folder 'prefix': its files, then its subfolders, as S3 answers 'delimiter=/'."""
    below = [k[len(prefix) :] for k in FILES if k.startswith(prefix)]
    entries = sorted(prefix + k for k in below if "/" not in k)
    entries += sorted({prefix + k.split("/")[0] + "/" for k in below if "/" in k})
    start = entries.index(after) + 1 if after else 0
    chunk = entries[start : start + page]
    more = start + page < len(entries)
    body = "<ListBucketResult><IsTruncated>%s</IsTruncated>" % ("true" if more else "false")
    for entry in chunk:
        if entry.endswith("/"):
            body += "<CommonPrefixes><Prefix>%s</Prefix></CommonPrefixes>" % entry
        else:
            body += "<Contents><Key>%s</Key><Size>%d</Size></Contents>" % (entry, len(FILES[entry]))
    if more:
        body += "<NextContinuationToken>%s</NextContinuationToken>" % chunk[-1]
    return (body + "</ListBucketResult>").encode()


class Wire:
    def __init__(self):
        self.asked = []

    def __call__(self, url, headers=None, method=None, timeout=120):
        self.asked.append(url)
        if url.startswith(plugin.BUCKET + "?"):
            query = urllib.parse.parse_qs(url.split("?", 1)[1])
            assert query["delimiter"] == ["/"], "the bucket is listed a folder at a time"
            return ua.Response(200, {}, _listing(query["prefix"][0], query.get("continuation-token", [None])[0]), url)
        path = urllib.parse.unquote(url[len(plugin.BUCKET) :])
        if path in FILES:
            return ua.Response(200, {}, FILES[path], url)
        return ua.Response(404, {}, b"", url)


@pytest.fixture
def nvidia(tmp_path, monkeypatch):
    monkeypatch.setenv("PARTCAD_OPENUSD_NVIDIA_CACHE", str(tmp_path))

    def make(**parameters):
        made = plugin.Nvidia({"parameters": parameters})
        made.http.request = Wire()
        return made

    return make


def test_a_child_package_per_kind_of_asset(nvidia):
    assert nvidia().get("deps") == sorted(plugin.COLLECTIONS)


def test_every_layer_of_archvis_is_a_prop_and_a_shared_name_is_told_apart(nvidia):
    parts = nvidia().get("archvis-industrial/objects/part")
    assert sorted(parts) == ["Pallet_A1", "Racks_Rack_A1", "Shelves_Rack_A1"]
    assert parts["Pallet_A1"]["license"] == "LicenseRef-NVIDIA-Omniverse-License-Agreement"


def _listed(made):
    return sorted(urllib.parse.parse_qs(url.split("?", 1)[1])["prefix"][0] for url in made.http.request.asked
                  if "?" in url)  # fmt: skip


def test_the_listing_is_read_a_folder_and_a_page_at_a_time_and_kept(nvidia):
    made = nvidia()
    made.get("archvis-industrial/objects/part")
    assert all("?" in url for url in made.http.request.asked), "listing downloads no file"
    # The folders of what an asset is made of are not listed.
    assert set(_listed(made)) == {
        "Assets/ArchVis/Industrial/",
        "Assets/ArchVis/Industrial/Pallets/",
        "Assets/ArchVis/Industrial/Racks/",
        "Assets/ArchVis/Industrial/Shelves/",
    }
    assert len(_listed(made)) > 4, "a page at a time"
    again = nvidia()
    again.get("archvis-industrial/objects/part")
    assert again.http.request.asked == []


def test_simready_is_listed_from_its_folder_of_props_alone(nvidia):
    made = nvidia()
    assert sorted(made.get("simready/objects/part")) == ["crate_a02", "pallet_a01"]
    assert set(_listed(made)) == {SIMREADY + "common_assets/props/"}
    assert made.get("simready/search/part?q=crate")
    assert set(_listed(made)) == {SIMREADY + "common_assets/props/"}


def test_a_simready_prop_is_its_folder_and_reaches_the_materials_beside_it(nvidia):
    made = nvidia()
    data = base64.b64decode(made.get("simready/files/pallet_a01.usdz"))
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        assert z.namelist() == ["common_assets/props/pallet_a01/pallet_a01.usd", "materials/physics/physics_metal.usda"]


def test_a_texture_s_thumbnail_stands_in_for_it_and_the_whole_of_it_only_when_asked(nvidia):
    looked = base64.b64decode(nvidia().get("archvis-industrial/files/Pallet_A1.usdz"))
    with zipfile.ZipFile(io.BytesIO(looked)) as z:
        assert z.namelist() == ["Pallet_A1.usd", "Textures/T_Pallet.png"]
        # Omniverse's 256-pixel thumbnail of it, under its name.
        assert z.read("Textures/T_Pallet.png") == b"small png"
    bare = base64.b64decode(nvidia(looks=False).get("archvis-industrial/files/Pallet_A1.bare.usdz"))
    with zipfile.ZipFile(io.BytesIO(bare)) as z:
        assert z.namelist() == ["Pallet_A1.usd"]
    textured = base64.b64decode(nvidia(textures=True).get("archvis-industrial/files/Pallet_A1.textured.usdz"))
    with zipfile.ZipFile(io.BytesIO(textured)) as z:
        assert z.namelist() == ["Pallet_A1.usd", "Textures/T_Pallet.png"]
        assert z.read("Textures/T_Pallet.png") == b"png"


def test_the_samples_are_the_scenes_and_listing_them_asks_nothing(nvidia):
    made = nvidia()
    assert sorted(made.get("samples/objects/part")) == sorted(plugin.SCENES)
    assert made.http.request.asked == []


def test_the_plugin_is_named_as_the_package_declares_it():
    with open(os.path.join(_HERE, "partcad.yaml")) as f:
        text = f.read()
    name = re.search(r"^name: (\S+)", text, re.M).group(1)
    assert re.search(r"^  nvidia_repo:\n    type: basic\n    path: nvidia_repo.py", text, re.M)
    assert plugin.Nvidia.PLUGIN == name + ":nvidia_repo"


def test_partcad_runs_it_and_reads_the_answer_from_output(tmp_path, monkeypatch):
    monkeypatch.setenv("PARTCAD_OPENUSD_NVIDIA_CACHE", str(tmp_path))
    result = runpy.run_path(_PLUGIN, init_globals={"request": {"key": "meta", "parameters": {}}}, run_name="get")
    assert result["output"]["result"]["manufacturable"] is False
