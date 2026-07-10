import {themes as prismThemes} from 'prism-react-renderer';
import type {Config} from '@docusaurus/types';
import type * as Preset from '@docusaurus/preset-classic';

// This runs in Node.js - Don't use client-side code here (browser APIs, JSX...)

const config: Config = {
  title: 'Dash Phone Con',
  tagline: 'Answer and control your Android phone\'s calls from your computer',
  favicon: 'img/favicon.ico',

  // Future flags, see https://docusaurus.io/docs/api/docusaurus-config#future
  future: {
    v4: true, // Improve compatibility with the upcoming Docusaurus v4
  },

  // Set the production url of your site here
  url: 'https://shrijayan.github.io',
  // Set the /<baseUrl>/ pathname under which your site is served
  // For GitHub pages deployment, it is often '/<projectName>/'
  baseUrl: '/dash-phonecon/',

  // GitHub pages deployment config.
  organizationName: 'shrijayan',
  projectName: 'dash-phonecon',
  deploymentBranch: 'gh-pages',
  trailingSlash: false,

  onBrokenLinks: 'throw',
  onBrokenAnchors: 'warn',

  headTags: [
    {
      tagName: 'link',
      attributes: {
        rel: 'sitemap',
        type: 'application/xml',
        href: '/dash-phonecon/sitemap.xml',
      },
    },
    {
      tagName: 'link',
      attributes: {
        rel: 'llms.txt',
        type: 'text/plain',
        href: '/dash-phonecon/llms.txt',
      },
    },
    {
      tagName: 'script',
      attributes: {type: 'application/ld+json'},
      innerHTML: JSON.stringify({
        '@context': 'https://schema.org',
        '@type': 'SoftwareApplication',
        name: 'Dash Phone Con',
        applicationCategory: 'UtilitiesApplication',
        operatingSystem: 'Ubuntu, macOS, Android',
        description:
          "Answer, decline, and hang up your Android phone's calls from an Ubuntu or macOS desktop over WiFi/LAN.",
        url: 'https://shrijayan.github.io/dash-phonecon/',
        offers: {'@type': 'Offer', price: '0', priceCurrency: 'USD'},
        codeRepository: 'https://github.com/shrijayan/dash-phonecon',
      }),
    },
  ],

  // Even if you don't use internationalization, you can use this field to set
  // useful metadata like html lang. For example, if your site is Chinese, you
  // may want to replace "en" with "zh-Hans".
  i18n: {
    defaultLocale: 'en',
    locales: ['en'],
  },

  presets: [
    [
      'classic',
      {
        docs: {
          sidebarPath: './sidebars.ts',
          editUrl: 'https://github.com/shrijayan/dash-phonecon/tree/main/website/',
          routeBasePath: 'docs',
        },
        blog: false,
        theme: {
          customCss: './src/css/custom.css',
        },
      } satisfies Preset.Options,
    ],
  ],

  // Emits a raw-markdown mirror of every doc (docs/foo -> docs/foo.md) so
  // AI agents/crawlers and the "Copy page as Markdown" button can fetch
  // source content directly instead of scraping rendered HTML.
  plugins: ['./plugins/llms-markdown-plugin.js'],

  clientModules: ['./src/clientModules/copyPageAsMarkdown.js'],

  themeConfig: {
    image: 'img/social-card.png',
    metadata: [
      {name: 'twitter:card', content: 'summary_large_image'},
    ],
    colorMode: {
      defaultMode: 'dark',
      respectPrefersColorScheme: true,
    },
    navbar: {
      title: 'Dash Phone Con',
      logo: {
        alt: 'Dash Phone Con Logo',
        src: 'img/logo.svg',
      },
      items: [
        {
          type: 'docSidebar',
          sidebarId: 'docsSidebar',
          position: 'left',
          label: 'Docs',
        },
        {
          to: '/docs/ubuntu/install',
          position: 'left',
          label: 'Ubuntu',
        },
        {
          to: '/docs/android/install',
          position: 'left',
          label: 'Android',
        },
        {
          to: '/docs/macos/install',
          position: 'left',
          label: 'macOS',
        },
        {
          href: 'https://github.com/shrijayan/dash-phonecon/releases/latest',
          label: 'Download latest release',
          position: 'right',
        },
        {
          href: 'https://github.com/shrijayan/dash-phonecon',
          label: 'GitHub',
          position: 'right',
        },
      ],
    },
    footer: {
      style: 'dark',
      links: [
        {
          title: 'Docs',
          items: [
            {label: 'Overview', to: '/docs/intro'},
            {label: 'Ubuntu install', to: '/docs/ubuntu/install'},
            {label: 'Android install', to: '/docs/android/install'},
            {label: 'macOS install', to: '/docs/macos/install'},
          ],
        },
        {
          title: 'Project',
          items: [
            {label: 'Architecture', to: '/docs/architecture'},
            {label: 'Protocol reference', to: '/docs/protocol'},
            {label: 'Troubleshooting', to: '/docs/troubleshooting'},
            {label: 'FAQ', to: '/docs/faq'},
          ],
        },
        {
          title: 'More',
          items: [
            {label: 'Releases', href: 'https://github.com/shrijayan/dash-phonecon/releases'},
            {label: 'Issues', href: 'https://github.com/shrijayan/dash-phonecon/issues'},
            {label: 'GitHub', href: 'https://github.com/shrijayan/dash-phonecon'},
          ],
        },
      ],
      copyright: `Copyright © ${new Date().getFullYear()} Dash Phone Con. Built with Docusaurus.`,
    },
    prism: {
      theme: prismThemes.github,
      darkTheme: prismThemes.dracula,
      additionalLanguages: ['bash', 'kotlin', 'swift', 'json', 'gradle'],
    },
  } satisfies Preset.ThemeConfig,
};

export default config;
