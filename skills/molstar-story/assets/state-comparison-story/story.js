const Colors = {
  reference: "#2B6CB0",
  mobile: "#D97706",
  referenceChangeCarbon: "#2563EB",
  mobileChangeCarbon: "#DC2626",
  ligandCarbon: "#7C3AED",
  pocketCarbon: "#168A78",
  motion: "#B42318",
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

const referenceReceptorSelector = REPLACE_REFERENCE_RECEPTOR_SELECTOR_JSON;
const mobileReceptorSelector = REPLACE_MOBILE_RECEPTOR_SELECTOR_JSON;
const mobileLigandSelector = REPLACE_MOBILE_LIGAND_SELECTOR_JSON;
const mobilePocketSelector = REPLACE_MOBILE_POCKET_SELECTOR_ARRAY_JSON;
const referenceChangedSelector = REPLACE_REFERENCE_CHANGED_SELECTOR_ARRAY_JSON;
const mobileChangedSelector = REPLACE_MOBILE_CHANGED_SELECTOR_ARRAY_JSON;
const motionVectors = REPLACE_MOTION_VECTOR_ARRAY_JSON;

const reference = builder
  .download({ url: "reference.pdb" })
  .parse({ format: "pdb" })
  .modelStructure({});

const mobile = builder
  .download({ url: "mobile_aligned.pdb" })
  .parse({ format: "pdb" })
  .modelStructure({});

const flatRepresentation = {
  molstar_representation_params: { ignoreLight: true },
};

builder.canvas({
  background_color: "#F7F8FA",
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

function showCartoon(structure, selector, color, opacity, tooltip, refPrefix) {
  const component = structure.component({
    selector,
    ref: `${refPrefix}-component`,
  });
  const representation = component
    .representation({
      type: "cartoon",
      ref: `${refPrefix}-cartoon`,
      custom: flatRepresentation,
    })
    .color({ color, ref: `${refPrefix}-color` });
  representation.opacity({ opacity, ref: `${refPrefix}-opacity` });
  component.tooltip({ text: tooltip });
  return component;
}

function showReference(opacity = 1) {
  return showCartoon(
    reference,
    referenceReceptorSelector,
    Colors.reference,
    opacity,
    "REPLACE_REFERENCE_TOOLTIP",
    "reference-receptor",
  );
}

function showMobile(opacity = 1) {
  return showCartoon(
    mobile,
    mobileReceptorSelector,
    Colors.mobile,
    opacity,
    "REPLACE_MOBILE_TOOLTIP",
    "mobile-receptor",
  );
}

function showLigand(opacity = 1) {
  const component = mobile.component({
    selector: mobileLigandSelector,
    ref: "mobile-ligand-component",
  });
  component
    .representation({
      type: "ball_and_stick",
      ref: "mobile-ligand-sticks",
      custom: flatRepresentation,
    })
    .color({ ...elementColoring(Colors.ligandCarbon), ref: "mobile-ligand-color" })
    .opacity({ opacity, ref: "mobile-ligand-opacity" });
  component.tooltip({ text: "REPLACE_LIGAND_TOOLTIP" });
  return component;
}

function showPocket(opacity = 1) {
  const component = mobile.component({
    selector: mobilePocketSelector,
    ref: "mobile-pocket-component",
  });
  component
    .representation({
      type: "ball_and_stick",
      ref: "mobile-pocket-sticks",
      custom: flatRepresentation,
    })
    .color({ ...elementColoring(Colors.pocketCarbon), ref: "mobile-pocket-color" })
    .opacity({ opacity, ref: "mobile-pocket-opacity" });
  component.tooltip({ text: "REPLACE_POCKET_TOOLTIP" });
  return component;
}

function showChangedResidues(opacity = 1) {
  reference
    .component({
      selector: referenceChangedSelector,
      ref: "reference-changed-component",
    })
    .representation({
      type: "ball_and_stick",
      ref: "reference-changed-sticks",
      custom: flatRepresentation,
    })
    .color({
      ...elementColoring(Colors.referenceChangeCarbon),
      ref: "reference-changed-color",
    })
    .opacity({ opacity, ref: "reference-changed-opacity" });
  mobile
    .component({
      selector: mobileChangedSelector,
      ref: "mobile-changed-component",
    })
    .representation({
      type: "ball_and_stick",
      ref: "mobile-changed-sticks",
      custom: flatRepresentation,
    })
    .color({
      ...elementColoring(Colors.mobileChangeCarbon),
      ref: "mobile-changed-color",
    })
    .opacity({ opacity, ref: "mobile-changed-opacity" });
}

function showMotionVectors(opacity = 1, labelOpacity = 1) {
  const primitives = builder.primitives({
    ref: "motion-vectors",
    opacity,
    label_background_color: "#FFFFFF",
    label_opacity: labelOpacity,
  });
  for (const vector of motionVectors) {
    primitives.arrow({
      start: vector.start,
      end: vector.end,
      tube_radius: 0.16,
      color: Colors.motion,
    });
    primitives.label({
      position: vector.labelPosition ?? vector.end,
      text: vector.label,
      label_color: Colors.motion,
      label_size: 1.7,
    });
  }
}

function renderComparisonScene({
  referenceOpacity,
  mobileOpacity,
  ligandOpacity = 0,
  pocketOpacity = 0,
  changedOpacity = 0,
  motionOpacity = 0,
  motionLabelOpacity = 0,
}) {
  // Keep recurring refs stable, but use opaque primary evidence in scene files.
  showReference(referenceOpacity);
  showMobile(mobileOpacity);
  showLigand(ligandOpacity);
  showPocket(pocketOpacity);
  showChangedResidues(changedOpacity);
  showMotionVectors(motionOpacity, motionLabelOpacity);
}
