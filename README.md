# NVIDIA's Omniverse sample content for PartCAD

Serves the sample content NVIDIA publishes for Omniverse - the "Example Assets"
[openusd.org's Downloads page](https://openusd.org/release/dl_downloads.html) links to, which NVIDIA
offers as [downloadable asset packs](https://docs.omniverse.nvidia.com/usd/latest/usd_content_samples/downloadable_packs.html)
and keeps, unzipped, in its public bucket `omniverse-content-production` - as PartCAD parts,
published as `//pub/collection/openusd/nvidia/assets`:

| Package | What it is | Parts |
| --- | --- | --- |
| `assets/archvis-commercial` | The ArchVis commercial props | 82: chairs, tables, ... (`Boat`, `Steam`, ...) |
| `assets/archvis-industrial` | The ArchVis industrial props | 75: pallets, racks, shelves, containers (`Pallet_A1`, `Cardbox_A1`, ...) |
| `assets/archvis-residential` | The ArchVis residential props | 507: appliances, furniture, ... (`fridge`, `stove`, `CeilingFan`, ...) |
| `assets/simready` | The SimReady props, made for simulation | about 1000 (`aluminumpallet_a01`, ...) |
| `assets/marbles` | The Marbles demo's standalone assets | 116 (`A_chute`, `A_marble`, ...) |
| `assets/samples` | The sample scenes | `OldAttic`, `Marbles`, `Astronaut`, `EuclidVR` |

```shell
pc list parts //pub/collection/openusd/nvidia/assets/archvis-industrial
pc search parts -P '//pub/collection/openusd/nvidia/assets...' -k pallet
pc inspect //pub/collection/openusd/nvidia/assets/archvis-industrial:Pallet_A1
pc render -t png --style shaded //pub/collection/openusd/nvidia/assets/simready:aluminumpallet_a01
```

A part is named as its file is; a name two folders share is told apart by its folder's.

**NVIDIA's terms.** NVIDIA publishes this content under the
[NVIDIA Omniverse License Agreement](https://docs.omniverse.nvidia.com/platform/latest/common/NVIDIA_Omniverse_License_Agreement.html),
which every pack's own licence file points to; it is not an open licence. Read it before you use
what you build from this for anything. (A copy of the SimReady props is also published under CC BY 4.0,
on Hugging Face as `nvidia/simready-assets`; it is not what this package serves.)

**No geometry is vendored.** Every asset is fetched from NVIDIA's bucket the first time a part of it is
built, and kept by PartCAD from then on.

**Nothing here is manufacturable.** These are props and scenes made to be rendered and simulated; the
package says `manufacturable: false`, and so does the plugin of what it serves.

Requires PartCAD 0.9.6 or newer: the first release whose `//builtin` has the `usd` part type.

## Listing, searching, building

**Listing and searching download no asset.** `pc list parts` and `pc search parts` are answered from
NVIDIA's bucket's listings, read a folder at a time: a package's folder and the folders its assets are
in, never the tens of thousands of textures and materials beside them. The thousand SimReady props are
one listing of their folder, two requests; the ArchVis and Marbles packages a few dozen to a hundred
small ones. What a part is made of is fetched when the part is built - by `pc inspect`, `pc render`,
`pc export`, or an assembly that places it - and then only that asset's own files, and kept.

`pc search parts -k <words>` is answered by the plugin, from the same catalog: a part matches when
every word is in its name, its description, its author, its tags or its package's name, and the ones
whose name matches come first. Each package answers with at most 20, or what `--limit` says (up to
100); search a package and every one below it with `-P '<package>...'`.

## What a part is

Every part here is `type: usd`: PartCAD's own part type for OpenUSD, in its `//builtin`, which reads a
stage with Pixar's USD library (`usd-core`), installed into the sandbox that builds the part and
nowhere else. The plugin's part is the file, and the part type makes the shape of it.

- **The file.** A part's file is a USDZ package of the asset, which the plugin makes when the part is
  built. An asset published as a `.usdz` is served as it is. One published as `.usd`, `.usda` or
  `.usdc` layers is a root layer that names others by relative path - sublayers, references,
  payloads - and the plugin follows those names (in a text layer its `@asset paths@`, in a binary one
  its token table) and packs the root and everything it reaches into a USDZ, root first, as the format
  wants it. Of the files that are not layers, it carries what the part's look is read from (the
  plugin's `looks`): the shaders the layers name, and the images of the colour, roughness and
  metalness - a smaller copy of each where the source keeps one, else each of up to 8 MB - and not
  the normal, height or occlusion maps. `textures` carries every one, as it is. A file an asset names
  that the source does not have is reported, and the asset is served without it.
- **The shape.** What is built is the stage's default prim - what a reference to the asset brings
  in - and every mesh it shows: through native instancing and point instancers, of the purpose asked
  for, visible ones only, in millimetres (by the stage's `metersPerUnit`) with Z up. A cube, sphere,
  cylinder, cone or capsule is meshed; curves, points and volumes are not surfaces, and are left out
  and counted. Up to 20 000 triangles, each triangle is a face, and two that share an edge share it:
  the part is drawn as lines, written to STEP, and made the solid it bounds where it closes. Past
  that, the triangles of each look are one mesh: fast at any size, drawn shaded (`pc render --style
  shaded`) and written as STL, 3MF or glTF, but with no edges for a line drawing. The part is a
  surface as USD describes it - what a renderer draws - and PartCAD says so when it is not a solid.
- **The look.** Each face is in the colour, roughness and metalness its material says - the material
  bound to its mesh, or to the subset of its faces - and as see-through: a colour a texture gives is
  read off the image where the face lies on it. `UsdPreviewSurface`, MaterialX and NVIDIA's OmniPBR,
  OmniGlass and OmniSurface are read, an MDL preset calling one included; a face with no material, or
  none of those, is in its `displayColor`. Each is stated under PartCAD's `usd` convention by the
  material's name, so a package of yours can claim one with a colour, material or finish of its own
  (`ids: {usd: Ceramic}`); one nothing claims is drawn as the stage says, and is display-only. A shaded
  `pc render` draws the roughness and metalness too.
- **The size.** It is what the asset says it is, by its `metersPerUnit`: an asset authored in the
  wrong units comes out as large, or as small, as it says.
- **The other reader.** `reader=cadmpeg` reads the same file with cadmpeg instead, PartCAD's
  converter for CAD formats, which reads USD from its 0.6.8 release on: what a render shows, at the
  stage's static values. It does no point instancer (the City Set's buildings, the chess set's pawns
  are left out), no `purpose` but `render` and no `time` but `default`, and a prim it reads as an
  exact surface (a cube, a sphere) is counted and left out rather than meshed. It is there as a
  second opinion and a fallback; `usd-core` is the reader to use.

Every part takes the part type's parameters, in its name (`King;purpose=proxy`) or in the `with` of
an enrich of it:

| Parameter | Default | What it is |
| --- | --- | --- |
| `reader` | `usd-core` | What reads the stage: `usd-core`, or `cadmpeg` (see above). |
| `prim` | the default prim | Build only what is under this prim; `/` is the whole stage. |
| `purpose` | `render` | `render`: what a final render draws; `proxy`: the stand-ins a viewer draws; `all`: both, and guides. |
| `surface` | `auto` | `faces`: a face per triangle; `mesh`: a mesh per colour; `auto`: `faces` up to 20 000 triangles. |
| `time` | `default` | The time code to read animated geometry at, skinning a character to it. `default` is what a viewer opens the stage at (its start time code, else its earliest sample), unposed. |
| `maxTriangles` | 5000000 | The most triangles the part may be: a scene of more is refused, saying so. |

PartCAD's own documentation of the part type is
[the `usd` part type](https://partcad.readthedocs.io/en/latest/config_parts.html#usd-files).

The materials are NVIDIA's MDL, which is left out with the textures: a part is drawn in the colour a
layer gives, where it gives one. A SimReady prop's file also holds the studio its thumbnail was
rendered in, beside the prop; that is not the prop's default prim, and is not built.

## Parameters of the plugin

| Parameter | Default | What it is |
| --- | --- | --- |
| `looks` | `true` | Whether a part's USDZ carries what its look is read from: its MDL presets, and its colour and ORM (occlusion, roughness, metalness) textures, each as the 256-pixel thumbnail NVIDIA's bucket keeps of it - 40 to 90 KB, where the texture is up to 28 MB. PartCAD colours each face from them. |
| `textures` | `false` | Whether a part's USDZ carries every texture its layers name, each as it is, at full size: to open it complete in another USD application. |
| `max_size_mb` | `512` | The most a part's USDZ may be, in MB. An asset found to be larger is refused, saying so, before the rest of it is fetched. |

Each is yours to set without touching this package, in your own `~/.partcad/config.yaml` under
`parameters`, by the plugin's name (`//pub/collection/openusd/nvidia:nvidia_repo`), or in a package of
your own, as an enrich of the plugin and a package it serves.

## Caching

The plugin keeps what NVIDIA's bucket answered under `~/.cache/partcad-openusd-nvidia/` (or
`$PARTCAD_OPENUSD_NVIDIA_CACHE`): each folder's listing for a week, and each file for good. A listing
that cannot be refreshed is answered from the one kept. Delete the directory to start over. PartCAD
keeps every answer the plugin gives, files included.

Every request says what it is: `User-Agent: Mozilla/5.0 (compatible; PartCAD-openusd-nvidia/<version>;
+https://github.com/partcad/partcad-collection-openusd-nvidia)`.

## Status

Run against NVIDIA's bucket: listing all six packages - 1816 parts - took 266 folder listings (525
KB) and no file: the 1032 SimReady props two requests, the 507 ArchVis residential props 110. An
ArchVis pallet (1204 by 800 by 209 mm, a Euro pallet), a SimReady pallet (1222 by 1016 by 136 mm), a
Marbles chute and the Astronaut scene were fetched, packed and read back by the part type with
usd-core 26.11.

Drawn in their looks (`pc render --style shaded`), from the 256-pixel thumbnails that stand in for
their textures: the ArchVis pallet and path light, the SimReady aluminium pallet (its MDL preset's
albedo and ORM textures), the Marbles mug, bucket, glass jar and marble (DDS textures), and the
Astronaut, on a backdrop whose texture is projected rather than laid by UVs and is drawn in its mean.

Through PartCAD's own `usd` part type, run from the change that adds it to `//builtin` before its
release, with all six `partcad-collection-openusd-*` packages in one workspace: `pc list packages -r`
listed their 17 packages, and `pc search parts -P '<workspace>...'` answered across all of them in
about two seconds, each collection searching its own catalog. `pc info` built the SimReady pallet with
`usd-core` and the ArchVis pallet with `cadmpeg` (1204 by 800 by 209 mm, as `usd-core` reads it), and
`pc render -t png --style shaded` drew the SimReady one.

NVIDIA's robots for Isaac Sim are in the same bucket's listing, but their folders hold only
thumbnails there, so they are not served.

## Layout

| Path | Purpose |
| --- | --- |
| `partcad.yaml` | `//pub/collection/openusd/nvidia`; the `assets` external dependency and the `nvidia_repo` repository that serves it. |
| `nvidia_repo.py` | The repository plugin: where NVIDIA keeps its content. |
| `usd_assets.py` | What every OpenUSD collection plugin shares, byte for byte: following a USD asset's layers, packing a USDZ, reading remote archives, buckets and listings a piece at a time, searching a catalog, the keys PartCAD asks. |
| `shared.sha256` | The digests of the shared files and their tests. They are the same in every `partcad-collection-openusd-*` repository - pixar, usd-wg, apple, nvidia, aswf-dpel and disney-moana - and a test fails when one here differs: change them in all of them. |
| `test_*.py` | The tests. Nothing in them touches the network. |

```shell
python -m pytest
```

When what the plugin answers changes - here or in `usd_assets.py` - raise `CACHE_VERSION` in
`nvidia_repo.py`: PartCAD keys everything it caches of this package on it, and an unchanged version
is answered from what it cached before.

## Licensing

The code here is Apache-2.0 (`LICENSE`). The content is NVIDIA's, under the NVIDIA Omniverse License
Agreement. Nothing of it is in this repository.
