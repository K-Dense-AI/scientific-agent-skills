"""Input safety, actual local statistics, plotting, and released API transports."""
from __future__ import annotations

import argparse
import importlib
import json
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest
import skill_contract

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "pathway-enrichment"
sys.path.insert(0, str(SKILL_ROOT / "scripts"))
pd = pytest.importorskip("pandas")
np = pytest.importorskip("numpy")
gp = pytest.importorskip("gseapy")
import run_enrichment as runner
from scipy.stats import hypergeom

CliHelpTests = skill_contract.cli.help_test_case(SKILL_ROOT)


def write(tmp_path, name, text):
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


@pytest.mark.parametrize("organism,genes", [("human", ["TP53", "C11orf95"]), ("mouse", ["Trp53", "H2-Ab1"]), ("fly", ["dpp", "Hh"]), ("human", ["7157", "001"])] )
def test_identifiers_preserved(organism, genes):
    assert runner._clean_symbols([" " + g + " " for g in genes], organism) == genes


def test_list_cleanup_only_deduplicates_exact_ids():
    assert runner._clean_symbols([None, "", "TP53", "tp53", "TP53"], "human") == ["TP53", "tp53"]


@pytest.mark.parametrize("filename,text", [("list.txt", "TP53\nBRCA1\n"), ("list.csv", "gene,val\nTP53,1\nBRCA1,2\n"), ("list.tsv", "gene\tval\nTP53\t1\nBRCA1\t2\n")])
def test_gene_list_formats(tmp_path, filename, text):
    assert runner._read_gene_list(write(tmp_path, filename, text)) == ["TP53", "BRCA1"]


@pytest.mark.parametrize("sep,header", [(s,h) for s in [",", "\t"] for h in [True,False]])
def test_rank_file_formats(tmp_path, sep, header):
    text = ((f"gene{sep}score\n" if header else "") + f"DOWN{sep}-2\nUP{sep}5\n")
    rank = runner._read_rnk(write(tmp_path,"input.rnk",text),"human")
    assert rank.to_dict() == {"UP":5.,"DOWN":-2.}
    assert rank.index.tolist() == ["UP", "DOWN"]


@pytest.mark.parametrize("text,match", [("A,1\nA,2\n", "Duplicate"), ("A,inf\nB,2\n", "finite"), (",1\nB,2\n", "identifiers"), ("A,garbage\nB,2\n", "Unable"), ("A,0\nB,0\n", "nonzero"), ("A,1\n", "two genes"), ("A\nB\n", "two columns")])
def test_invalid_ranks_rejected(tmp_path,text,match):
    with pytest.raises(ValueError,match=match):
        runner._read_rnk(write(tmp_path,"input.rnk",text),"human")


def test_missing_statistics_warn_and_ties_preserve_order(tmp_path):
    with pytest.warns(UserWarning):
        rank = runner._read_rnk(write(tmp_path,"input.rnk","Z,2\nA,2\nM,\nB,-1\n"),"human")
    assert rank.index.tolist() == ["Z","A","B"]


def test_wald_preferred(tmp_path):
    rank = runner._build_rank_from_deseq2(write(tmp_path,"de.csv","gene,stat,log2FoldChange,pvalue\nA,-3,1,0.01\nB,2,-1,0.01\n"),"human")
    assert rank.to_dict() == {"B":2.,"A":-3.}


def test_signed_fallback_and_zero_floor(tmp_path):
    with pytest.warns(UserWarning,match="Zero p-values"):
        rank = runner._build_rank_from_deseq2(write(tmp_path,"de.csv","gene,LOG2FOLDCHANGE,PVALUE\nA,2,0\nB,-1,0.01\n"),"human")
    assert rank.to_dict() == {"A":300.,"B":-2.}


@pytest.mark.parametrize("p", ["-0.1","1.1","inf"])
def test_invalid_pvalues_rejected(tmp_path,p):
    with pytest.raises(ValueError,match="p-values"):
        runner._build_rank_from_deseq2(write(tmp_path,"de.csv",f"gene,log2FoldChange,pvalue\nA,2,{p}\nB,-1,0.01\n"),"human")


def test_nonhuman_needs_explicit_library():
    with pytest.raises(ValueError,match="Nonhuman"):
        runner._validate_libraries(None,"mouse")


def test_invalid_remote_library_not_silently_skipped(monkeypatch):
    monkeypatch.setattr(gp,"get_library_name",lambda organism:["valid"])
    with pytest.raises(ValueError,match="Unavailable"):
        runner._validate_libraries(["valid","missing"],"human")


def test_offline_library_validation_no_network(tmp_path,monkeypatch):
    monkeypatch.setattr(gp,"get_library_name",Mock(side_effect=AssertionError("network")))
    path=write(tmp_path,"test.gmt","SET\tna\tA\tB\n")
    assert runner._validate_libraries([str(path)],"human") == [str(path)]


def ora_args(tmp_path, background):
    genes=write(tmp_path,"hits.txt","A\nB\n")
    gmt=write(tmp_path,"sets.gmt","MATCH\tna\tA\tB\tC\tOUTSIDE\nZERO\tna\tH\tI\n")
    bg=write(tmp_path,"background.txt",background) if background is not None else None
    return argparse.Namespace(genes=str(genes),libraries=[str(gmt)],background=str(bg) if bg else None, organism="human",fdr=0.05)


def test_local_ora_exact_universe_and_positive_overlap_family(tmp_path):
    args=ora_args(tmp_path,"\n".join("ABCDEFGHIJ"))
    res,sig,col=runner.run_ora(args)
    assert res.Term.tolist()==["MATCH"]  # zero-overlap terms are omitted upstream
    assert res.Overlap.iloc[0]=="2/3"      # OUTSIDE cannot enlarge set size
    assert float(res["P-value"].iloc[0])==pytest.approx(hypergeom.sf(1,10,3,2))
    assert float(res["Adjusted P-value"].iloc[0])==pytest.approx(res["P-value"].iloc[0])
    assert float(res["Odds Ratio"].iloc[0])==pytest.approx((2.5*7.5)/(1.5*0.5))
    assert args.input_summary["background_genes"]==10


@pytest.mark.parametrize("background", [None,"A\nC\n",""])
def test_ora_background_missing_or_incomplete_rejected(tmp_path,background):
    with pytest.raises(ValueError,match="background|Background"):
        runner.run_ora(ora_args(tmp_path,background))


def fixture_rank():
    return pd.Series(np.linspace(4,-4,40),index=[f"G{i}" for i in range(40)])


def fixture_sets():
    return {"TOP":[f"G{i}" for i in range(8)],"BOTTOM":[f"G{i}" for i in range(32,40)],"MIXED":[f"G{i}" for i in range(0,40,5)]}


def test_native_prerank_direction_reproducibility_and_multilevel():
    common=dict(rnk=fixture_rank(),gene_sets=fixture_sets(),min_size=3,max_size=20,seed=123,threads=1,outdir=None,permutation_num=100)
    a=gp.prerank(**common,method="permutation").res2d.set_index("Term")
    b=gp.prerank(**common,method="permutation").res2d.set_index("Term")
    pd.testing.assert_frame_equal(a,b)
    assert a.loc["TOP","NES"]>0>a.loc["BOTTOM","NES"]
    assert a["NOM p-val"].astype(float).between(0,1).all()
    # Extreme synthetic sets can have zero exceedances; zero is finite-resolution output.
    c=gp.prerank(**common,method="multilevel",sample_size=101).res2d
    assert "log2err" in c and "FWER p-val" not in c
    from scipy.stats import false_discovery_control
    np.testing.assert_allclose(c["FDR q-val"].astype(float),false_discovery_control(c["NOM p-val"].astype(float)))


def test_helper_passes_organism_and_preserves_tie_order(tmp_path,monkeypatch):
    path=write(tmp_path,"ranks.tsv","gene\tscore\nZ\t1\nA\t1\nB\t-1\n")
    result=Mock(res2d=pd.DataFrame({"Term":["T"],"FDR q-val":[0.03]}))
    fn=Mock(return_value=result);monkeypatch.setattr(gp,"prerank",fn)
    args=argparse.Namespace(deseq2=None,rnk=str(path),organism="mouse",libraries=["mouse.gmt"],min_size=1,max_size=20,permutations=100,seed=1,threads=1,fdr=0.05)
    with pytest.warns(UserWarning,match="tied"):
        runner.run_gsea(args)
    assert fn.call_args.kwargs["organism"]=="mouse"
    assert fn.call_args.kwargs["ascending"] is None
    assert fn.call_args.kwargs["method"]=="permutation"
    assert fn.call_args.kwargs["rnk"].index.tolist()==["Z","A","B"]


def test_native_matrix_scoring_and_plots(tmp_path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    expr=pd.DataFrame(np.random.default_rng(1).normal(size=(40,14)),index=fixture_rank().index)
    expr.iloc[:8,:7]+=3
    common=dict(data=expr,gene_sets=fixture_sets(),min_size=3,max_size=20,threads=1,outdir=None)
    g=gp.gsea(**common,cls=["A"]*7+["B"]*7,permutation_num=30,permutation_type="phenotype",seed=123)
    ss=gp.ssgsea(**common,permutation_num=0)
    gs=gp.gsva(**common,kcdf="Gaussian")
    assert ss.res2d.pivot(index="Term",columns="Name",values="NES").shape==(3,14)
    assert len(gs.res2d)==42
    ora=gp.enrich(gene_list=["G0","G1","G2"],gene_sets=fixture_sets(),background=fixture_rank().index.tolist(),outdir=None)
    gp.barplot(ora.results,ofname=str(tmp_path/"bar.png"))
    assert (tmp_path/"bar.png").stat().st_size>1000
    pre=gp.prerank(rnk=fixture_rank(),gene_sets=fixture_sets(),min_size=3,max_size=20,threads=1,outdir=None,permutation_num=100)
    nodes,edges=gp.enrichment_map(pre.res2d,column="FDR q-val",cutoff=1.0)
    assert isinstance(nodes,pd.DataFrame) and {"src_idx","targ_idx"}<=set(edges.columns)
    for col,df in [("FDR q-val",pre.res2d)]:
        ax=gp.dotplot(df,column=col,cutoff=1.0,show_ring=True)
        ax.get_figure().savefig(tmp_path/"dot.png");plt.close(ax.get_figure())
    term=pre.res2d.Term.iloc[0]
    gp.gseaplot(term=term,rank_metric=pre.ranking,ofname=str(tmp_path/"running.png"),**pre.results[term])
    assert (tmp_path/"running.png").stat().st_size>1000
    gp.gseaplot2(terms=[term],hits=[pre.results[term]["hits"]],RESs=[pre.results[term]["RES"]],rank_metric=pre.ranking,ofname=str(tmp_path/"running2.png"))
    gp.heatmap(expr.iloc[:5],ofname=str(tmp_path/"heatmap.png"))
    plt.close("all")


def response(data=None,text=None):
    return Mock(ok=True,status_code=200,text=json.dumps(data) if text is None else text,json=lambda:data,raise_for_status=lambda:None)


def test_actual_speedrichr_transport_with_custom_background(monkeypatch):
    session=Mock()
    session.get.return_value=response({"statistics":[{"libraryName":"LIB"}]})
    session.post.side_effect=[response({"userListId":123,"shortId":"demo"}),response({"backgroundid":"bg"}),response({"LIB":[[1,"TERM",0.01,2.,9.,["TP53"],0.02,0.,0.]]})]
    monkeypatch.setattr(importlib.import_module("gseapy.enrichr"),"retry",lambda:session)
    enr=gp.enrichr(gene_list=["TP53"],gene_sets="LIB",background=["TP53","BRCA1"],outdir=None)
    calls=session.post.call_args_list
    assert [c.args[0] for c in calls]==["https://maayanlab.cloud/speedrichr/api/"+p for p in ["addList","addbackground","backgroundenrich"]]
    assert calls[0].kwargs["files"]["list"]==(None,"TP53")
    assert set(calls[1].kwargs["data"]["background"].splitlines())=={"TP53","BRCA1"}
    assert calls[2].kwargs["data"]=={"userListId":123,"backgroundid":"bg","backgroundType":"LIB"}
    assert enr.results.Genes.tolist()==["TP53"]
    assert "Overlap" not in enr.results


def test_actual_standard_enrichr_export_transport(monkeypatch):
    session=Mock()
    session.post.return_value=response({"userListId":123,"shortId":"demo"})
    session.get.side_effect=[response({"statistics":[{"libraryName":"LIB"}]}),response(text="Term\tOverlap\tP-value\tAdjusted P-value\tGenes\nTERM\t1/3\t0.01\t0.02\tTP53\n")]
    monkeypatch.setattr(importlib.import_module("gseapy.enrichr"),"retry",lambda:session)
    enr=gp.enrichr(gene_list=["TP53"],gene_sets="LIB",outdir=None)
    assert session.post.call_args.args[0]=="https://maayanlab.cloud/Enrichr/addList"
    assert session.get.call_args.args[0]=="https://maayanlab.cloud/Enrichr/export"
    assert session.get.call_args.kwargs["params"]=={"userListId":123,"filename":"temp","backgroundType":"LIB"}
    assert enr.results.Overlap.tolist()==["1/3"]


def test_cli_local_results_metadata_and_no_stale_plot(tmp_path):
    args=ora_args(tmp_path,"\n".join("ABCDEFGHIJ"))
    out=tmp_path/"output"
    cmd=[sys.executable,str(SKILL_ROOT/"scripts/run_enrichment.py"),"ora","--genes",args.genes,"--background",args.background,"--libraries",*args.libraries,"--outdir",str(out)]
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE="1",MPLBACKEND="Agg")
    first=subprocess.run(cmd,capture_output=True,text=True,env=env)
    assert first.returncode==0,first.stderr
    meta=json.loads((out/"ora_metadata.json").read_text())
    assert meta["significant"]==0 and meta["dotplot_written"] is False
    assert len(meta["input_sha256"])==3
    assert not (out/"ora_dotplot.png").exists()
    second=subprocess.run(cmd,capture_output=True,text=True,env=env)
    assert second.returncode!=0 and "fresh directory" in second.stderr
