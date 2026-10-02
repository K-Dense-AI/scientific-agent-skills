"""Scientific adapter for RMBase v3.0's observed public request contracts."""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from pathlib import Path

from datasets import Datasets
from parsers import gene_sites, json_rows, modification_detail, validate_bed
from transport import BASE, RMBaseError, Transport, utc_now

CATALOG = json.loads((Path(__file__).resolve().parents[1] / "references" / "catalog.json").read_text(encoding="utf-8"))
MOD_TYPES = {
    "m6a": "m6A", "m1a": "m1A", "m5c": "m5C", "m7g": "m7G",
    "pseudo": "Pseudo", "nm": "Nm", "rnaediting": "RNA-editing",
    "ac4c": "ac4C", "othermod": "otherMod",
}
GENE_TYPES = {"m6a", "m1a", "m5c", "m7g", "pseudo", "nm", "editing", "other"}
ENDPOINTS = {
    "enzyme": ("getEnzymeRes.php", ("writerName", "writerID")),
    "snorna": ("getsnoRNARes.php", ("snoName", "guideModNum")),
    "cluster": ("getCluster.php", ("clusterID", "geneID")),
    "motif": ("getOtherMotif.php", ("modType", "motifID", "motifSeq")),
    "motif-datasets": ("getMotifRes.php", ("GSMAccession",)),
    "rbp": ("getModRBPRes.php", ("rbpSiteID", "rbpName")),
    "mirna": ("getModMirTarRes.php", ("mirTarRand", "mirRNAName")),
    "variant": ("getModVarRes.php", ()),
}


def identifier(value, label="identifier"):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.:+-]{0,159}", value) or value.lower() == "all":
        raise RMBaseError("invalid_identifier", f"Provide a single explicit {label}; wildcards and unbounded queries are not supported.")
    return value


def context(module, assembly, species=None):
    choices = CATALOG["modules"][module]["assemblies"]
    if assembly not in choices:
        raise RMBaseError("invalid_assembly", f"Assembly {assembly!r} is not offered for {module}; use catalog.")
    ctx = choices[assembly]
    if species is not None and species != ctx["species"]:
        raise RMBaseError("species_assembly_mismatch", "Species and genome assembly do not match the RMBase catalogue.")
    return ctx


def option(value, allowed, label):
    if value not in allowed:
        raise RMBaseError("invalid_option", f"Unsupported {label}; use catalog for the exact RMBase choices.", choices=sorted(allowed))
    return value


class Client:
    def __init__(self, transport=None, assembly="hg38", species=None, limit=50, offset=0):
        if not 1 <= limit <= 500 or not 0 <= offset <= 1_000_000:
            raise RMBaseError("invalid_page", "Limit must be 1–500; offset must be 0–1000000.")
        self.http = transport or Transport()
        self.assembly, self.species = assembly, species
        self.limit, self.offset = limit, offset
        self.datasets = Datasets(self.http)

    def _params(self, module):
        ctx = context(module, self.assembly, self.species)
        return {"assembly": self.assembly, "genome": ctx["species"]}, ctx

    def result(self, command, rows, query, mode="REMOTE_QUERY", *, warnings=(), assembly=True):
        rows = sorted(rows, key=lambda row: json.dumps(row, sort_keys=True, ensure_ascii=True))
        selected = rows[self.offset:self.offset + self.limit]
        total = len(rows)
        notes = list(warnings)
        if self.offset or total > self.limit:
            notes.append("Output is a local slice of the fetched response; this is not server-side pagination.")
        if not rows:
            notes.append("No records in this RMBase query does not demonstrate biological absence.")
        if any(s.get("transport") == "http" for s in self.http.sources):
            notes.append("The observed public service uses unencrypted HTTP; transport authenticity is not guaranteed.")
        return {
            "schema_version": "1.0", "status": "ok" if rows else "no_records", "command": command,
            "query": query, "records": selected,
            "pagination": {"kind": "local", "total_records": total, "returned_records": len(selected),
                           "offset": self.offset, "limit": self.limit,
                           "complete": self.offset == 0 and len(selected) == total,
                           "next_offset": self.offset + len(selected) if self.offset + len(selected) < total else None},
            "provenance": {"rmbase_version": "3.0", "queried_at": utc_now(), "access_mode": mode,
                           "genome_assembly": self.assembly if assembly else None,
                           "species": context("gene", self.assembly, self.species)["species"] if assembly else "Homo sapiens",
                           "sources": list(self.http.sources),
                           "database_publication": {"pmid": "37956310", "doi": "10.1093/nar/gkad1070"}},
            "warnings": notes,
        }

    def gene(self, name, mode="genename", source="auto", modification=None):
        identifier(name, "gene symbol or versioned ID")
        params, _ = self._params("gene")
        option(mode, ("genename", "geneid", "transcript"), "identifier mode")
        option(source, ("auto", "remote", "local"), "source")
        kind = "trans" if mode == "transcript" else "genes"
        local = source == "local" or (source == "auto" and self.datasets.available(self.assembly, kind))
        if mode == "transcript" and not local:
            raise RMBaseError("dataset_required", "Transcript lookup uses the official transcript archive; run sync --kind trans.", 6)
        if local:
            rows = self.datasets.query(name, self.assembly, mode, kind)
            access = "LOCAL_DATASET"
        else:
            params.update(mode=mode, genename=name)
            raw = self.http.request("ajaxFiles/getModGeneRes.php", params, "POST")
            rows = json_rows(raw, ("geneName", "geneID", "totalNum"))
            # Protect exact-match semantics if the website starts returning partial matches.
            field = "geneName" if mode == "genename" else "geneID"
            rows = [r for r in rows if r[field] == name]
            access = "REMOTE_QUERY"
        if modification:
            option(modification, GENE_TYPES, "gene modification category")
            if len(rows) > 1:
                raise RMBaseError("ambiguous_gene", "Multiple gene records match; select a versioned gene ID.")
            if rows:
                gene = rows[0]
                if local:
                    rows = [{"modID": mid, "geneID": gene["geneID"], "geneName": gene["geneName"],
                             "modification_category": modification} for mid in gene[modification + "List"]]
                else:
                    detail = {"db": "rmbase3_modgene", "table": self.assembly + "_modgene",
                              "modType": modification, "gene": gene["geneName"], "geneid": gene["geneID"]}
                    if gene.get(modification + "Num") == 0:
                        rows = []
                    else:
                        rows = gene_sites(self.http.request("modgenedetailresult.php", detail))
                        if len(rows) != gene.get(modification + "Num"):
                            raise RMBaseError("count_mismatch", "Gene summary and detail counts disagree; do not claim completeness.", 4)
                    access = "HTML_ADAPTER"
        return self.result("gene", rows, {"gene": name, "identifier_mode": mode, "modification": modification, "source": source}, access,
                           warnings=["Gene-associated RNA modifications are distinct from the encoded protein's writer/reader/eraser activity."])

    def modification(self, mod_id, mod_type):
        identifier(mod_id, "RMBase modification ID")
        option(mod_type, MOD_TYPES, "modification type")
        self._params(mod_type)
        if not re.fullmatch(r"[A-Za-z0-9'-]+_site_[0-9]+", mod_id):
            raise RMBaseError("invalid_modification_id", "Use the exact RMBase *_site_<number> ID from a query.")
        if mod_type != "othermod" and not mod_id.startswith(MOD_TYPES[mod_type] + "_site_"):
            raise RMBaseError("modification_type_mismatch", "Modification ID prefix and selected modification type disagree.")
        table = f"{self.assembly}_{mod_type}base_modsite"
        if self.assembly == "hg38" and mod_type == "rnaediting":
            table += "_all"
        params = {"db": f"rmbase3_{mod_type}base", "table": table, "modID": mod_id}
        rows = modification_detail(self.http.request("detailModResult.php", params), mod_id)
        return self.result("modification", rows, {"modification_id": mod_id, "modification_type": mod_type}, "HTML_ADAPTER",
                           warnings=["Coordinates are retained as displayed by RMBase; no genome build conversion is performed."])

    def sites(self, mod_type, cell, minimum=1, maximum=1000):
        option(mod_type, MOD_TYPES, "modification type")
        params, ctx = self._params(mod_type)
        option(cell, ctx["options"], "cell/tissue")
        params.update(modtype=mod_type, celltype=cell)
        route = "getmodSiteRes.php"
        if mod_type == "m6a":
            if not 1 <= minimum <= maximum <= 1000:
                raise RMBaseError("invalid_support", "Support must satisfy 1 <= min <= max <= 1000.")
            params.update(minval=minimum, maxval=maximum)
            route = "getm6ASiteRes.php"
        elif minimum != 1 or maximum != 1000:
            raise RMBaseError("unsupported_filter", "Support filters are only sent by the m6A website form.")
        rows = json_rows(self.http.request("ajaxFiles/" + route, params, "POST"), ("modID", "modType"))
        return self.result("sites", rows, params, warnings=["The site returns the full filtered array; a small output limit does not reduce its response size."])

    def lookup(self, module, value=None, *, category=None, subtype=None, support=1):
        params, ctx = self._params(module)
        endpoint, fields = ENDPOINTS[module]
        if module == "snorna" and value:
            identifier(value, "snoRNA")
        if module == "enzyme":
            params["methylname"] = option(value, ctx["options"], "enzyme")
        elif module in {"cluster", "motif"}:
            params["cluster"] = option(value, ctx["options"], "modification")
        elif module == "rbp":
            params.update(rbptype=option(category, ctx["options"], "RBP category"), rbpname=identifier(value, "RBP"))
            if not 1 <= support <= 1000:
                raise RMBaseError("invalid_support", "RBP support must be 1–1000.")
            params.update(minval=support, maxval=1000)
        elif module == "mirna":
            params.update(rnaname=option(category, ctx["options"], "target RNA category"), targetname=identifier(value, "miRNA"))
        elif module == "variant":
            params.update(varname=option(category, ctx["options"], "variant kind"),
                          mycancer=option(subtype, ("know", "unknow"), "variant evidence category"),
                          cancername=identifier(value, "cancer label"))
        rows = json_rows(self.http.request("ajaxFiles/" + endpoint, params, "POST"), fields)
        if module == "snorna" and value:
            rows = [r for r in rows if r["snoName"] == value]
        if module == "variant" and rows:
            required = "snpID" if category == "snp" else "modSNVID"
            if any(required not in r for r in rows):
                raise RMBaseError("schema_changed", "Variant record fields changed.", 4)
        return self.result(module, rows, params,
                           warnings=["Only the website's documented form filters are sent; additional filtering may be local."])

    def colocalization(self, cell, histone, modification):
        if self.assembly != "hg38" or self.species not in (None, "Homo sapiens"):
            raise RMBaseError("invalid_assembly", "The audited co-localization menu covers human data only.")
        cells = CATALOG["colocalization"]["Homo sapiens"][0]
        option(cell, cells, "cell")
        option(histone, cells[cell][0], "histone mark")
        option(modification, cells[cell][0][histone].split("、"), "RNA modification")
        params = {"cell": cell, "histone": histone, "rnamod": modification}
        rows = json_rows(self.http.request("ajaxFiles/getHistone.new.php", params, "POST"), ("modType", "cell"))
        return self.result("colocalization", rows, params, warnings=["Co-localization/correlation does not demonstrate causation."])

    def cancer(self, gene, section="DIFF"):
        identifier(gene, "RMP gene symbol")
        option(section, ("DIFF", "SCNA", "CNV"), "RMP section")
        if self.assembly != "hg38" or self.species not in (None, "Homo sapiens"):
            raise RMBaseError("invalid_assembly", "RMP cancer queries cover human TCGA data.")
        raw = self.http.request("ajaxFiles/getCancerRes.RBP.table.php", {"rbp": gene, "datatype": "Counts"}, "POST")
        outer = json_rows(raw, clean_html=False)
        matches = [row[section] for row in outer if section in row]
        if len(matches) != 1 or not isinstance(matches[0], str):
            raise RMBaseError("schema_changed", "Expected a named nested JSON RMP section.", 4)
        rows = json_rows(matches[0])
        return self.result("cancer", rows, {"gene": gene, "section": section, "datatype": "Counts"}, assembly=False,
                           warnings=["TCGA coordinate assembly is not declared by this endpoint; do not merge these coordinates with hg38 sites.",
                                     "RMP/TCGA data are research associations, not clinical conclusions."])

    def submit(self, tool, path, *, public_data=False):
        """One submission only. Successful task/result schemas remain unverified."""
        option(tool, ("annotation", "metagene", "gene-tool"), "analysis tool")
        if not public_data:
            raise RMBaseError("public_data_required", "Uploads use public HTTP. Supply --public-data only for data authorized for public transmission.")
        ctx = context("tools", self.assembly, self.species)
        path = Path(path)
        if path.stat().st_size >= 2_000_000:
            raise RMBaseError("invalid_upload", "Input must be smaller than 2 MB.")
        data = path.read_bytes()
        fields = {"group": ctx["group"], "genome": ctx["species"], "Species": self.assembly, "bedTextArea": ""}
        if tool == "gene-tool":
            try:
                ids = data.decode("utf-8-sig").splitlines()
            except UnicodeDecodeError as exc:
                raise RMBaseError("invalid_upload", "Gene IDs must be UTF-8 text.") from exc
            if not ids:
                raise RMBaseError("invalid_upload", "Gene list is empty.")
            for entry in ids:
                identifier(entry, "gene ID")
            fields.update(tooltype="modgene", rbp="Gene Case", bedTextArea="Input ID List")
            route = "/cgi-bin/runModgenetool.pl"
        else:
            validate_bed(data)
            route = "/cgi-bin/runModAnno.pl" if tool == "annotation" else "/cgi-bin/runModMeta.pl"
        boundary = "rmbase-" + uuid.uuid4().hex
        chunks = [f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode() for k, v in fields.items()]
        chunks.append(f'--{boundary}\r\nContent-Disposition: form-data; name="bedInputFile"; filename="input.txt"\r\nContent-Type: text/plain\r\n\r\n'.encode() + data + f'\r\n--{boundary}--\r\n'.encode())
        raw = self.http.request(route, method="POST", body=b"".join(chunks),
                                content_type="multipart/form-data; boundary=" + boundary, cache=False, retry=False)
        raise RMBaseError("unverified_task_response", "The server accepted a request, but its task lifecycle is unverified. Do not automatically resubmit or claim completion.", 7,
                          endpoint=BASE.split("/rmbase/")[0] + route,
                          response_sha256=hashlib.sha256(raw).hexdigest(), response_bytes=len(raw))

    def task(self, task_id):
        identifier(task_id, "task ID")
        raise RMBaseError("task_lifecycle_unverified", "All three analysis CGI endpoints returned HTTP 503 during audit. No successful task/status/result contract was available; no request was sent.", 7)


def catalog(module=None, assembly=None):
    if module:
        option(module, CATALOG["modules"], "module")
        result = CATALOG["modules"][module]
        if assembly:
            return {"module": module, "assembly": assembly, **context(module, assembly), "source": result["source"]}
        return {"module": module, **result}
    return {"audit_date": CATALOG["audit_date"], "modules": sorted(CATALOG["modules"]),
            "assemblies": CATALOG["modules"]["gene"]["assemblies"],
            "analysis_status": "All three public CGI submission endpoints returned 503; task lifecycle unverified."}
