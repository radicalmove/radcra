# Sphere artwork source and provenance

The Sphere Store artwork is generated entirely from first-party project code. `scripts/generate-store-assets.py` composes the geometric Sphere mark produced by `scripts/generate-extension-icons.py`, the Sphere name, and the descriptive text “Course Review App”. The mark uses the approved deep navy/blue ramp and a restrained white comment cue; it is not derived from the CUBE artwork. No university, Google, marketplace, stock, or third-party artwork is included.

Generation uses Pillow with high-resolution rendering and Lanczos downsampling. Typography uses only the bundled `DejaVuSans-Bold.ttf`; the generator stops if that exact repository asset is missing and never falls back to an environment font.

The font is DejaVu Fonts 2.37, obtained from the [upstream 2.37 release](https://github.com/dejavu-fonts/dejavu-fonts/releases/tag/version_2_37). Its SHA-256 is `e6476c1b80502924294eed40894c5b18e06c181444ca953e5334262df9c27724`. Redistribution is permitted under the DejaVu Fonts license included as `DEJAVU-LICENSE.txt` in this directory.

Recreate the sources from the repository root (the explicit output names are part of the Store asset contract):

```sh
python3 scripts/generate-extension-icons.py --output-directory extension/public/icons
python3 scripts/generate-store-assets.py --output store-assets/sphere-promo-440x280.png
```
