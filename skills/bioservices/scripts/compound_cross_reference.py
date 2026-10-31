#!/usr/bin/env python3
"""
Compound Cross-Database Search

This script searches for a compound by name and retrieves identifiers
from multiple databases:
- KEGG Compound
- ChEBI
- ChEMBL (via UniChem)
- Basic compound properties

Usage:
    python compound_cross_reference.py COMPOUND_NAME [--output FILE]

Examples:
    python compound_cross_reference.py Geldanamycin
    python compound_cross_reference.py "Adenosine triphosphate"
    python compound_cross_reference.py Aspirin --output aspirin_info.txt
"""

import sys
import argparse
from urllib.parse import quote
from bioservices import KEGG, UniChem, ChEBI, ChEMBL


def search_kegg_compound(compound_name):
    """Search KEGG for compound by name."""
    print(f"\n{'='*70}")
    print("STEP 1: KEGG Compound Search")
    print(f"{'='*70}")

    k = KEGG()
    k.services.url = "https://rest.kegg.jp"

    print(f"Searching KEGG for: {compound_name}")

    try:
        results = k.services.http_get("find/compound/" + quote(compound_name, safe=""), frmt="txt")

        if not isinstance(results, str):
            raise ValueError(f"KEGG search failed: {results!r}")
        if not results.strip():
            print(f"[FAIL] No results found in KEGG")
            return k, None

        # Parse results
        lines = results.strip().split("\n")
        print(f"[OK] Found {len(lines)} result(s):\n")

        for i, line in enumerate(lines[:5], 1):
            parts = line.split("\t")
            kegg_id = parts[0]
            description = parts[1] if len(parts) > 1 else "No description"
            print(f"  {i}. {kegg_id}: {description}")

        exact_matches = [line for line in lines if len(line.split("\t", 1)) == 2
                         and compound_name.casefold() in {
                             name.strip().casefold() for name in line.split("\t", 1)[1].split(";")}]
        if len(exact_matches) == 1:
            lines = exact_matches
        if len(lines) > 1:
            print("[SKIP] Ambiguous compound name; refine the query before mapping")
            return k, None

        # Use the unique result
        first_result = lines[0].split("\t")
        kegg_id = first_result[0].replace("cpd:", "")

        print(f"\nUsing: {kegg_id}")

        return k, kegg_id

    except Exception as e:
        print(f"[FAIL] Error: {e}")
        return k, None


def get_kegg_info(kegg, kegg_id):
    """Retrieve detailed KEGG compound information."""
    print(f"\n{'='*70}")
    print("STEP 2: KEGG Compound Details")
    print(f"{'='*70}")

    try:
        print(f"Retrieving KEGG entry for {kegg_id}...")

        entry = kegg.get(f"cpd:{kegg_id}")

        if not entry:
            print("[FAIL] Failed to retrieve entry")
            return None

        # Parse entry
        compound_info = {
            'kegg_id': kegg_id,
            'name': None,
            'formula': None,
            'exact_mass': None,
            'mol_weight': None,
            'chebi_id': None,
            'chebi_ids': [],
            'pathways': []
        }

        current_section = None

        for line in entry.split("\n"):
            # KEGG field names start in column 1 and their continuation lines are
            # indented. A new field therefore ends any multi-line section --
            # without this reset, the indented DBLINKS lines that follow PATHWAY
            # would be collected as pathways.
            if line and not line.startswith(" "):
                current_section = None

            if line.startswith("NAME"):
                compound_info['name'] = line.replace("NAME", "").strip().rstrip(";")

            elif line.startswith("FORMULA"):
                compound_info['formula'] = line.replace("FORMULA", "").strip()

            elif line.startswith("EXACT_MASS"):
                compound_info['exact_mass'] = line.replace("EXACT_MASS", "").strip()

            elif line.startswith("MOL_WEIGHT"):
                compound_info['mol_weight'] = line.replace("MOL_WEIGHT", "").strip()

            elif "ChEBI:" in line:
                parts = line.split("ChEBI:")
                if len(parts) > 1:
                    for identifier in parts[1].strip().split():
                        if identifier not in compound_info['chebi_ids']:
                            compound_info['chebi_ids'].append(identifier)

            elif line.startswith("PATHWAY"):
                current_section = "pathway"
                pathway = line.replace("PATHWAY", "").strip()
                if pathway:
                    compound_info['pathways'].append(pathway)

            elif current_section == "pathway" and line.startswith("            "):
                pathway = line.strip()
                if pathway:
                    compound_info['pathways'].append(pathway)

            elif line.startswith(" ") and not line.startswith("            "):
                current_section = None

        # A KEGG entry can link distinct protonation or structural forms.
        # Preserve every candidate; the legacy singular field is unique only.
        if len(compound_info['chebi_ids']) == 1:
            compound_info['chebi_id'] = compound_info['chebi_ids'][0]
        elif compound_info['chebi_ids']:
            print("[SKIP] Multiple ChEBI cross-references; review structures before mapping: "
                  + ", ".join(compound_info['chebi_ids']))

        # Display information
        print(f"\n[OK] KEGG Compound Information:")
        print(f"  ID: {compound_info['kegg_id']}")
        print(f"  Name: {compound_info['name']}")
        print(f"  Formula: {compound_info['formula']}")
        print(f"  Exact Mass: {compound_info['exact_mass']}")
        print(f"  Molecular Weight: {compound_info['mol_weight']}")

        if compound_info['chebi_id']:
            print(f"  ChEBI ID: {compound_info['chebi_id']}")

        if compound_info['pathways']:
            print(f"  Pathways: {len(compound_info['pathways'])} found")

        return compound_info

    except Exception as e:
        print(f"[FAIL] Error: {e}")
        return None


def get_chembl_id(kegg_id, chebi_id=None):
    """Resolve a KEGG entry's ChEBI cross-reference with UniChem 2.

    KEGG is not a supported UniChem 2 source. Preserve the original KEGG ID
    for provenance and use only the ChEBI ID recorded in that KEGG entry.
    """
    print(f"\n{'='*70}")
    print("STEP 3: ChEMBL Mapping (via UniChem)")
    print(f"{'='*70}")
    if not chebi_id:
        print(f"[SKIP] KEGG:{kegg_id} has no unique ChEBI cross-reference; mapping unavailable")
        return None
    chebi_id = str(chebi_id)
    if not chebi_id.startswith("CHEBI:"):
        chebi_id = f"CHEBI:{chebi_id}"
    try:
        response = UniChem().get_compounds(chebi_id, "chebi")
        identifiers = sorted({
            source["compoundId"]
            for match in response.get("compounds", [])
            for source in match.get("sources", [])
            if source.get("shortName") == "chembl" and source.get("compoundId")
        })
        if len(identifiers) == 1:
            print(f"[OK] {chebi_id} -> ChEMBL ID: {identifiers[0]}")
            return identifiers[0]
        if identifiers:
            print(f"[SKIP] Ambiguous ChEMBL mappings: {', '.join(identifiers)}; review structures")
        else:
            print("[SKIP] No ChEMBL mapping returned; this does not prove absence")
    except Exception as error:
        print(f"[FAIL] UniChem lookup failed: {error}")
    return None


def get_chebi_info(chebi_id):
    """Retrieve ChEBI compound information."""
    print(f"\n{'='*70}")
    print("STEP 4: ChEBI Details")
    print(f"{'='*70}")

    if not chebi_id:
        print("[SKIP] No ChEBI ID available")
        return None

    try:
        c = ChEBI()

        print(f"Retrieving ChEBI entry for {chebi_id}...")

        # Ensure proper format
        if not chebi_id.startswith("CHEBI:"):
            chebi_id = f"CHEBI:{chebi_id}"

        entity = c.getCompleteEntity(chebi_id)

        if entity:
            print(f"\n[OK] ChEBI Information:")
            print(f"  ID: {entity.chebiId}")
            print(f"  Name: {entity.chebiAsciiName}")

            if hasattr(entity, 'formula') and entity.formula:
                print(f"  Formula: {entity.formula}")

            if hasattr(entity, 'mass') and entity.mass:
                print(f"  Mass: {entity.mass}")

            if hasattr(entity, 'charge') and entity.charge:
                print(f"  Charge: {entity.charge}")

            return {
                'chebi_id': entity.chebiId,
                'name': entity.chebiAsciiName,
                'formula': entity.formula if hasattr(entity, 'formula') else None,
                'mass': entity.mass if hasattr(entity, 'mass') else None
            }
        else:
            print("[FAIL] Failed to retrieve ChEBI entry")
            return None

    except Exception as e:
        print(f"[FAIL] Error: {e}")
        return None


def get_chembl_info(chembl_id):
    """Retrieve ChEMBL compound information."""
    print(f"\n{'='*70}")
    print("STEP 5: ChEMBL Details")
    print(f"{'='*70}")

    if not chembl_id:
        print("[SKIP] No ChEMBL ID available")
        return None

    try:
        c = ChEMBL()

        print(f"Retrieving ChEMBL entry for {chembl_id}...")

        # `get_compound_by_chemblId` was a pre-1.6 name; current releases expose
        # the same lookup as `get_molecule`.
        compound = c.get_molecule(chembl_id)

        if compound:
            print(f"\n[OK] ChEMBL Information:")
            print(f"  ID: {chembl_id}")

            if 'pref_name' in compound and compound['pref_name']:
                print(f"  Preferred Name: {compound['pref_name']}")

            if 'molecule_properties' in compound:
                props = compound['molecule_properties'] or {}

                if 'full_mwt' in props:
                    print(f"  Molecular Weight: {props['full_mwt']}")

                if 'alogp' in props:
                    print(f"  LogP: {props['alogp']}")

                if 'hba' in props:
                    print(f"  H-Bond Acceptors: {props['hba']}")

                if 'hbd' in props:
                    print(f"  H-Bond Donors: {props['hbd']}")

            if 'molecule_structures' in compound:
                structs = compound['molecule_structures'] or {}

                if isinstance(structs.get('canonical_smiles'), str):
                    smiles = structs['canonical_smiles']
                    print(f"  SMILES: {smiles[:60]}{'...' if len(smiles) > 60 else ''}")

            return compound
        else:
            print("[FAIL] Failed to retrieve ChEMBL entry")
            return None

    except Exception as e:
        print(f"[FAIL] Error: {e}")
        return None


def save_results(compound_name, kegg_info, chembl_id, output_file):
    """Save results to file."""
    print(f"\n{'='*70}")
    print(f"Saving results to {output_file}")
    print(f"{'='*70}")

    with open(output_file, 'w') as f:
        f.write("=" * 70 + "\n")
        f.write(f"Compound Cross-Reference Report: {compound_name}\n")
        f.write("=" * 70 + "\n\n")

        # KEGG information
        if kegg_info:
            f.write("KEGG Compound\n")
            f.write("-" * 70 + "\n")
            f.write(f"ID: {kegg_info['kegg_id']}\n")
            f.write(f"Name: {kegg_info['name']}\n")
            f.write(f"Formula: {kegg_info['formula']}\n")
            f.write(f"Exact Mass: {kegg_info['exact_mass']}\n")
            f.write(f"Molecular Weight: {kegg_info['mol_weight']}\n")
            f.write(f"Pathways: {len(kegg_info['pathways'])} found\n")
            f.write("\n")

        # Database IDs
        f.write("Cross-Database Identifiers\n")
        f.write("-" * 70 + "\n")
        if kegg_info:
            f.write(f"KEGG: {kegg_info['kegg_id']}\n")
            if kegg_info['chebi_id']:
                f.write(f"ChEBI: {kegg_info['chebi_id']}\n")
            elif kegg_info.get('chebi_ids'):
                f.write("ChEBI candidates (unresolved): "
                        + ", ".join(kegg_info['chebi_ids']) + "\n")
        if chembl_id:
            f.write(f"ChEMBL: {chembl_id}\n")
        f.write("\n")

    print(f"[OK] Results saved")


def main():
    """Main workflow."""
    parser = argparse.ArgumentParser(
        description="Search compound across multiple databases",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python compound_cross_reference.py Geldanamycin
  python compound_cross_reference.py "Adenosine triphosphate"
  python compound_cross_reference.py Aspirin --output aspirin_info.txt
        """
    )
    parser.add_argument("compound", help="Compound name to search")
    parser.add_argument("--output", default=None,
                       help="Output file for results (optional)")

    args = parser.parse_args()

    print("=" * 70)
    print("BIOSERVICES: Compound Cross-Database Search")
    print("=" * 70)

    # Step 1: Search KEGG
    kegg, kegg_id = search_kegg_compound(args.compound)
    if not kegg_id:
        print("\n[FAIL] Failed to find compound. Exiting.")
        sys.exit(1)

    # Step 2: Get KEGG details
    kegg_info = get_kegg_info(kegg, kegg_id)

    # Step 3: Map to ChEMBL
    chembl_id = get_chembl_id(kegg_id, (kegg_info or {}).get("chebi_id"))

    # Step 4: Get ChEBI details
    chebi_info = None
    if kegg_info and kegg_info['chebi_id']:
        chebi_info = get_chebi_info(kegg_info['chebi_id'])

    # Step 5: Get ChEMBL details
    chembl_info = None
    if chembl_id:
        chembl_info = get_chembl_info(chembl_id)

    # Summary
    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")
    print(f"  Compound: {args.compound}")
    if kegg_info:
        print(f"  KEGG ID: {kegg_info['kegg_id']}")
        if kegg_info['chebi_id']:
            print(f"  ChEBI ID: {kegg_info['chebi_id']}")
    if chembl_id:
        print(f"  ChEMBL ID: {chembl_id}")
    print(f"{'='*70}")

    # Save to file if requested
    if args.output:
        save_results(args.compound, kegg_info, chembl_id, args.output)


if __name__ == "__main__":
    main()
