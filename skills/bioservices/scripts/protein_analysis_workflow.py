#!/usr/bin/env python3
"""
Complete Protein Analysis Workflow

This script performs a comprehensive protein analysis pipeline:
1. UniProt search and identifier retrieval
2. FASTA sequence retrieval
3. BLAST similarity search
4. KEGG pathway discovery
5. STRING association lookup
6. GO annotation retrieval

Usage:
    export NCBI_EMAIL=you@lab.org
    python protein_analysis_workflow.py PROTEIN_NAME [EMAIL] [--skip-blast]

Examples:
    python protein_analysis_workflow.py ZAP70_HUMAN
    python protein_analysis_workflow.py P43403 user@example.com --skip-blast

Note: BLAST searches can take several minutes. Use --skip-blast to skip this step.
Email is read from NCBI_EMAIL when the optional EMAIL argument is omitted.
"""

import os
import re
import sys
import time
import argparse
from bioservices import UniProt, KEGG, NCBIblast, QuickGO, STRING
from batch_id_converter import mapping_to_lists

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def resolve_ncbi_email(cli_email=None):
    """Return a validated EMBL-EBI BLAST contact email from CLI or NCBI_EMAIL."""
    email = (cli_email or os.environ.get("NCBI_EMAIL", "")).strip()
    if email and _EMAIL_RE.match(email):
        return email
    return None


def search_protein(query):
    """Search UniProt for protein and retrieve basic information."""
    print(f"\n{'='*70}")
    print("STEP 1: UniProt Search")
    print(f"{'='*70}")

    u = UniProt(verbose=False)

    print(f"Searching for: {query}")

    # Try direct retrieval first (if query looks like accession)
    if re.fullmatch(r"[A-Z0-9]{6}|[A-Z0-9]{10}", query):
        try:
            entry = u.retrieve(query, frmt="json")
            if isinstance(entry, dict) and entry.get("primaryAccession"):
                uniprot_id = entry["primaryAccession"]
                print(f"[OK] Found UniProt entry: {uniprot_id}")
                return u, uniprot_id
        except:
            pass

    # Otherwise search
    results = u.search(query, frmt="tsv", columns="accession,gene_names,organism_name,length,protein_name", limit=5, size=5)

    if not isinstance(results, str) or not results.strip():
        print("[FAIL] Search failed or returned no results")
        return u, None

    lines = results.strip().split("\n")
    if len(lines) < 2:
        print("[FAIL] No entries found")
        return u, None

    # Display results
    print(f"\n[OK] Found {len(lines)-1} result(s):")
    for i, line in enumerate(lines[1:], 1):
        fields = line.split("\t")
        print(f"  {i}. {fields[0]} - {fields[1]} ({fields[2]})")

    # Use first result
    first_entry = lines[1].split("\t")
    uniprot_id = first_entry[0]
    gene_names = first_entry[1] if len(first_entry) > 1 else "N/A"
    organism = first_entry[2] if len(first_entry) > 2 else "N/A"
    length = first_entry[3] if len(first_entry) > 3 else "N/A"
    protein_name = first_entry[4] if len(first_entry) > 4 else "N/A"

    print(f"\nUsing first result:")
    print(f"  UniProt ID: {uniprot_id}")
    print(f"  Gene names: {gene_names}")
    print(f"  Organism: {organism}")
    print(f"  Length: {length} aa")
    print(f"  Protein: {protein_name}")

    return u, uniprot_id


def retrieve_sequence(uniprot, uniprot_id):
    """Retrieve FASTA sequence for protein."""
    print(f"\n{'='*70}")
    print("STEP 2: FASTA Sequence Retrieval")
    print(f"{'='*70}")

    try:
        sequence = uniprot.retrieve(uniprot_id, frmt="fasta")

        if isinstance(sequence, str) and sequence.startswith(">"):
            # Extract sequence only (remove header)
            lines = sequence.strip().split("\n")
            header = lines[0]
            seq_only = "".join(lines[1:])

            print(f"[OK] Retrieved sequence:")
            print(f"  Header: {header}")
            print(f"  Length: {len(seq_only)} residues")
            print(f"  First 60 residues: {seq_only[:60]}...")

            return seq_only
        else:
            print("[FAIL] Failed to retrieve sequence")
            return None

    except Exception as e:
        print(f"[FAIL] Error: {e}")
        return None


def run_blast(sequence, email, skip=False):
    """Run BLAST similarity search."""
    print(f"\n{'='*70}")
    print("STEP 3: BLAST Similarity Search")
    print(f"{'='*70}")

    if skip:
        print("[SKIP] Skipped (--skip-blast flag)")
        return None

    if not email:
        print("[SKIP] Skipped (set NCBI_EMAIL or pass email for BLAST)")
        return None

    try:
        print(f"Submitting BLASTP job...")
        print(f"  Database: uniprotkb")
        print(f"  Sequence length: {len(sequence)} aa")

        s = NCBIblast(verbose=False)
        s.services.url = "https://www.ebi.ac.uk/Tools/services/rest/ncbiblast"

        jobid = s.run(
            program="blastp",
            sequence=sequence,
            stype="protein",
            database="uniprotkb",
            email=email
        )

        if not isinstance(jobid, str) or not jobid.startswith("ncbiblast-"):
            raise ValueError(f"Invalid BLAST job response: {jobid!r}")
        print(f"[OK] Job submitted: {jobid}")
        print(f"  Waiting for completion...")

        # Poll for completion
        max_wait = 300  # 5 minutes
        start_time = time.time()

        while time.time() - start_time < max_wait:
            status = s.get_status(jobid)
            elapsed = int(time.time() - start_time)
            print(f"  Status: {status} (elapsed: {elapsed}s)", end="\r")

            if status == "FINISHED":
                print(f"\n[OK] BLAST completed in {elapsed}s")

                # Retrieve results
                results = s.get_result(jobid, "out")

                # Parse and display summary
                lines = results.split("\n")
                print(f"\n  Results preview:")
                for line in lines[:20]:
                    if line.strip():
                        print(f"    {line}")

                return results

            elif status in {"ERROR", "FAILURE", "NOT_FOUND"}:
                print(f"\n[FAIL] BLAST job failed")
                return None

            time.sleep(5)

        print(f"\n[FAIL] Timeout after {max_wait}s")
        return None

    except Exception as e:
        print(f"[FAIL] Error: {e}")
        return None


def discover_pathways(uniprot, kegg, uniprot_id):
    """Discover KEGG pathways for protein."""
    print(f"\n{'='*70}")
    print("STEP 4: KEGG Pathway Discovery")
    print(f"{'='*70}")

    try:
        # Map UniProt → KEGG
        print(f"Mapping {uniprot_id} to KEGG...")
        kegg_mapping = mapping_to_lists(uniprot.mapping(
            fr="UniProtKB_AC-ID", to="KEGG", query=uniprot_id))
        kegg_ids = kegg_mapping.get(uniprot_id) or []
        if not kegg_ids:
            print("[SKIP] No KEGG mapping returned")
            return []
        pathway_info = {}
        for kegg_id in kegg_ids:
            organism, gene_id = kegg_id.split(":", 1)
            found = kegg.get_pathway_by_gene(gene_id, organism)
            if found is None:
                continue
            if not isinstance(found, dict):
                raise ValueError("Unexpected KEGG PATHWAY response")
            pathway_info.update(found)
        for pathway_id, name in pathway_info.items():
            print(f"  {pathway_id}: {name}")
        return list(pathway_info.items())

    except Exception as e:
        print(f"[FAIL] Error: {e}")
        return []


def find_interactions(protein_query, taxon_id=None):
    """Return up to ten STRING associations, retaining scores and stable IDs."""
    if taxon_id is None:
        print("[SKIP] STRING lookup needs the protein's verified taxonomy ID")
        return []
    try:
        results = STRING(verbose=False).get_interaction_partners(
            protein_query, species=taxon_id, required_score=700, limit=10,
            caller_identity="scientific-agent-skills-bioservices")
        if not isinstance(results, list):
            raise ValueError("Unexpected STRING response")
        print(f"[OK] {len(results)} STRING associations (not necessarily physical binding)")
        return results
    except Exception as error:
        print(f"[FAIL] STRING lookup: {error}")
        return []


def get_go_annotations(uniprot_id, max_pages=1000):
    """Fetch all QuickGO pages and group distinct positive terms by aspect.

    NOT-qualified annotations are not positive assertions. Evidence and complete
    raw records should be retained separately for downstream enrichment.
    """
    if type(max_pages) is not int or max_pages < 1:
        raise ValueError("max_pages must be a positive integer")
    g = QuickGO(verbose=False)
    aspects = {"P": [], "F": [], "C": []}
    aspect_codes = {"biological_process": "P", "molecular_function": "F",
                    "cellular_component": "C"}
    expected_total = None
    for page in range(1, max_pages + 1):
        payload = g.Annotation(geneProductId=f"UniProtKB:{uniprot_id}",
                               includeFields="goName", limit=100, page=page)
        if not isinstance(payload, dict) or not isinstance(payload.get("results"), list):
            raise ValueError("QuickGO lookup failed; annotations are incomplete")
        page_info = payload.get("pageInfo")
        if not isinstance(page_info, dict):
            raise ValueError("QuickGO response lacks pagination metadata")
        total_pages = page_info.get("total")
        if type(total_pages) is not int or not 0 <= total_pages <= max_pages:
            raise ValueError("QuickGO page total is invalid or exceeds max_pages; annotations are incomplete")
        current = page_info.get("current", page)
        if type(current) is not int or current != page:
            raise ValueError("QuickGO returned the wrong page; annotations are incomplete")
        if expected_total is not None and total_pages != expected_total:
            raise ValueError("QuickGO page total changed; rerun to obtain complete annotations")
        expected_total = total_pages
        if total_pages == 0 and payload["results"]:
            raise ValueError("QuickGO zero-page response contains results")
        for record in payload["results"]:
            if "NOT" in str(record.get("qualifier", "")).split("|"):
                continue
            aspect = aspect_codes.get(record.get("goAspect"))
            term = (record.get("goId"), record.get("goName", ""))
            if aspect and term[0] and term not in aspects[aspect]:
                aspects[aspect].append(term)
        if page >= total_pages:
            break
    print(f"[OK] {sum(map(len, aspects.values()))} distinct positive GO terms")
    return aspects


def main():
    """Main workflow."""
    parser = argparse.ArgumentParser(
        description="Complete protein analysis workflow using BioServices",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  export NCBI_EMAIL=you@lab.org
  python protein_analysis_workflow.py ZAP70_HUMAN
  python protein_analysis_workflow.py P43403 user@example.com --skip-blast
        """
    )
    parser.add_argument("protein", help="Protein name or UniProt ID")
    parser.add_argument(
        "email",
        nargs="?",
        default=None,
        help="EMBL-EBI BLAST contact email (optional if NCBI_EMAIL is set)",
    )
    parser.add_argument("--skip-blast", action="store_true",
                       help="Skip BLAST search (faster)")

    args = parser.parse_args()

    print("=" * 70)
    print("BIOSERVICES: Complete Protein Analysis Workflow")
    print("=" * 70)

    # Step 1: Search protein
    uniprot, uniprot_id = search_protein(args.protein)
    if not uniprot_id:
        print("\n[FAIL] Failed to find protein. Exiting.")
        sys.exit(1)

    # Step 2: Retrieve sequence
    sequence = retrieve_sequence(uniprot, uniprot_id)
    if not sequence:
        print("\n[WARN] Warning: Could not retrieve sequence")

    # Step 3: BLAST search
    ncbi_email = resolve_ncbi_email(args.email)
    blast_results = None
    if sequence:
        blast_results = run_blast(sequence, ncbi_email, args.skip_blast)

    # Step 4: Pathway discovery
    kegg = KEGG()
    kegg.services.url = "https://rest.kegg.jp"
    pathways = discover_pathways(uniprot, kegg, uniprot_id)

    # Step 5: Interaction mapping
    entry = uniprot.retrieve(uniprot_id, frmt="json")
    taxon_id = entry.get("organism", {}).get("taxonId") if isinstance(entry, dict) else None
    interactions = find_interactions(uniprot_id, taxon_id)

    # Step 6: GO annotations
    try:
        go_terms = get_go_annotations(uniprot_id)
    except Exception as error:
        print(f"[FAIL] {error}")
        go_terms = None

    # Summary
    print(f"\n{'='*70}")
    print("WORKFLOW SUMMARY")
    print(f"{'='*70}")
    print(f"  Protein: {args.protein}")
    print(f"  UniProt ID: {uniprot_id}")
    print(f"  Sequence: {'[OK]' if sequence else '[FAIL]'}")
    print(f"  BLAST: {'[OK]' if blast_results else '[SKIP/FAIL]'}")
    print(f"  Pathways: {len(pathways)} found")
    print(f"  Interactions: {len(interactions)} found")
    print(f"  GO terms: {sum(map(len, go_terms.values())) if go_terms is not None else 'unavailable'}")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
