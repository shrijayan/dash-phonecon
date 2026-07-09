import type {SidebarsConfig} from '@docusaurus/plugin-content-docs';

// This runs in Node.js - Don't use client-side code here (browser APIs, JSX...)

const sidebars: SidebarsConfig = {
  docsSidebar: [
    'intro',
    'architecture',
    'protocol',
    {
      type: 'category',
      label: 'Ubuntu',
      link: {type: 'doc', id: 'ubuntu/install'},
      items: ['ubuntu/first-run', 'ubuntu/bluetooth-audio', 'ubuntu/development'],
    },
    {
      type: 'category',
      label: 'Android',
      link: {type: 'doc', id: 'android/install'},
      items: ['android/permissions', 'android/development'],
    },
    {
      type: 'category',
      label: 'macOS',
      link: {type: 'doc', id: 'macos/install'},
      items: [],
    },
    'releases',
    'troubleshooting',
    'faq',
  ],
};

export default sidebars;
