renderLigandScene({
  proteinOpacity: 1,
  ligandOpacity: 1,
});

structure
  .component({ selector: proteinSelector, ref: "protein-component" })
  .tooltip({ text: "REPLACE_PROTEIN_TOOLTIP" });
