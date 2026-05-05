/**
 * Onlook configuration for Rain Workshop IDE.
 *
 * This config enables visual editing of React projects by mapping
 * Workshop nodes to actual source files and components.
 *
 * @see https://onlook.dev/docs/configuration
 */

/** @type {import('onlook').OnlookConfig} */
const config = {
  // The root directory of generated projects that Onlook will edit
  projectRoot: "./.workshop-sandbox",

  // Mapping from Workshop node types to file paths / templates
  nodeMapping: {
    page: {
      dir: "src/app",
      template: "page.tsx",
    },
    component: {
      dir: "src/components",
      template: "component.tsx",
    },
    function: {
      dir: "src/lib",
      template: "function.ts",
    },
  },

  // Framework detection
  framework: "nextjs",

  // Enable visual editing overlays on the preview iframe
  visualEditing: {
    enabled: true,
    selectorMode: "data-oid",
    overlayHotkey: "alt",
  },

  // Component registry — maps Onlook-detected components to Workshop nodes
  components: {
    registryPath: ".onlook/components.json",
  },

  // Tailwind CSS support
  styling: {
    framework: "tailwind",
    configPath: "tailwind.config.ts",
  },

  // Auto-sync: push changes from visual editor back to Ground Truth
  sync: {
    onSave: "ground-truth",
    debounceMs: 500,
  },
};

export default config;
