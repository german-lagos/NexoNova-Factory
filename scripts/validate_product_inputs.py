"""Read-only P3 preparation validation; does not generate or execute product code."""
import argparse
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from factory.product_contracts import validate_bundle, verify_source, require_material_ready


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pilot", required=True, help="Explicit directory containing the three input contracts")
    parser.add_argument("--require-ready", action="store_true")
    args = parser.parse_args(argv)
    try:
        pilot = Path(args.pilot)
        order, spec, manifest = [json.loads((pilot / name).read_text()) for name in
                                 ("work-order.json", "corporate-site.json", "source-manifest.json")]
        validate_bundle(order, spec, manifest)
        registry = json.loads((ROOT / "config/sources.json").read_text())
        if registry["format"] != "nexonova.source-registry.v1":
            raise ValueError("Unknown source registry version")
        entry = registry["sources"][manifest["source_id"]]
        if entry["access"] != "read-only" or entry["expected_tree_hash"] != manifest["tree_hash"]:
            raise ValueError("Source authorization/hash mismatch")
        source = ROOT / entry["relative_to_factory"]
        verify_source(source, manifest)
        if args.require_ready:
            require_material_ready(spec, manifest)
        print("product_inputs=valid; source=verified; generation=not-authorized")
        return 0
    except (OSError, ValueError, KeyError, TypeError):
        # Do not echo source content or potential private values from invalid contracts.
        print("product_inputs=blocked; inspect contracts, source integrity and material decisions", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
