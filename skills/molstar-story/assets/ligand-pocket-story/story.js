const Colors = {
  protein: "#647386",
  ligandCarbon: "#C98616",
  pocketCarbon: "#258F83",
  evidenceCarbon: "#B8427A",
};

function hexColorToNumber(color) {
  return parseInt(color.substring(1), 16);
}

function elementColoring(carbonColor) {
  return {
    custom: {
      molstar_color_theme_name: "element-symbol",
      molstar_color_theme_params: {
        carbonColor: {
          name: "uniform",
          params: { value: hexColorToNumber(carbonColor) },
        },
      },
    },
  };
}

const proteinSelector = REPLACE_PROTEIN_SELECTOR_JSON;
const ligandSelector = REPLACE_LIGAND_SELECTOR_JSON;
const pocketResidues = REPLACE_POCKET_SELECTOR_ARRAY_JSON;
const decisionResidues = REPLACE_DECISION_SELECTOR_ARRAY_JSON;

const structure = builder
  .download({ url: "REPLACE_COORDINATE_BASENAME" })
  .parse({ format: "REPLACE_PDB_OR_MMCIF_FORMAT" })
  .modelStructure({});

const flatRepresentation = {
  molstar_representation_params: { ignoreLight: true },
};

builder.canvas({
  background_color: "#f7f8fa",
  custom: {
    molstar_postprocessing: {
      enable_outline: true,
      enable_ssao: false,
      enable_bloom: false,
      enable_shadow: false,
      enable_dof: false,
      enable_fog: false,
    },
  },
});

function showProtein(opacity = 1) {
  const representation = structure
    .component({ selector: proteinSelector, ref: "protein-component" })
    .representation({
      type: "cartoon",
      ref: "protein-cartoon",
      custom: flatRepresentation,
    })
    .color({ color: Colors.protein, ref: "protein-color" });
  representation.opacity({ opacity, ref: "protein-opacity" });
  return representation;
}

function showLigand(opacity = 1) {
  const component = structure.component({
    selector: ligandSelector,
    ref: "ligand-component",
  });
  component
    .representation({
      type: "ball_and_stick",
      ref: "ligand-sticks",
      custom: flatRepresentation,
    })
    .color({ ...elementColoring(Colors.ligandCarbon), ref: "ligand-color" })
    .opacity({ opacity, ref: "ligand-opacity" });
  component.tooltip({ text: "REPLACE_LIGAND_TOOLTIP" });
  return component;
}

function showResidueZone(selector, carbonColor, tooltip, refPrefix, opacity = 1) {
  const component = structure.component({
    selector,
    ref: `${refPrefix}-component`,
  });
  component
    .representation({
      type: "ball_and_stick",
      ref: `${refPrefix}-sticks`,
      custom: flatRepresentation,
    })
    .color({ ...elementColoring(carbonColor), ref: `${refPrefix}-color` })
    .opacity({ opacity, ref: `${refPrefix}-opacity` });
  component.tooltip({ text: tooltip });
  return component;
}

function renderLigandScene({
  proteinOpacity,
  ligandOpacity = 1,
  pocketOpacity = 0,
  decisionOpacity = 0,
}) {
  showProtein(proteinOpacity);
  showLigand(ligandOpacity);
  showResidueZone(
    pocketResidues,
    Colors.pocketCarbon,
    "REPLACE_POCKET_TOOLTIP",
    "pocket-zone",
    pocketOpacity,
  );
  showResidueZone(
    decisionResidues,
    Colors.evidenceCarbon,
    "REPLACE_DECISION_TOOLTIP",
    "decision-zone",
    decisionOpacity,
  );
}
