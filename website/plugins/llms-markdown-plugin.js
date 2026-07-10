// Docusaurus plugin: writes a raw-markdown mirror of every doc page into the
// build output (e.g. build/docs/intro.html -> build/docs/intro.md), so the
// "Copy page as Markdown" button (see src/clientModules/copyPageAsMarkdown.ts)
// and AI agents/crawlers can fetch the source content directly instead of
// scraping rendered HTML.
const fs = require('fs');
const path = require('path');

/** @returns {import('@docusaurus/types').Plugin} */
module.exports = function llmsMarkdownPlugin() {
  return {
    name: 'llms-markdown-plugin',
    async postBuild({outDir, siteDir}) {
      const docsDir = path.join(siteDir, 'docs');
      const files = walk(docsDir).filter((f) => f.endsWith('.mdx') || f.endsWith('.md'));

      for (const file of files) {
        const raw = fs.readFileSync(file, 'utf8');
        const {frontmatter, body} = splitFrontmatter(raw);
        const relative = path.relative(docsDir, file).replace(/\.mdx?$/, '');
        // intro.mdx declares slug: /intro, which Docusaurus resolves to
        // docs/intro — same as its file path, so no special-casing needed.
        const outPath = path.join(outDir, 'docs', `${relative}.md`);
        fs.mkdirSync(path.dirname(outPath), {recursive: true});
        const trimmedBody = body.trim();
        // Skip the frontmatter title if the body already opens with its own
        // top-level heading (every doc in this repo does) to avoid a
        // duplicate title line in the markdown mirror.
        const needsTitle = frontmatter.title && !/^#\s/.test(trimmedBody);
        const title = needsTitle ? `# ${frontmatter.title}\n\n` : '';
        fs.writeFileSync(outPath, title + trimmedBody + '\n');
      }
    },
  };
};

function walk(dir) {
  return fs.readdirSync(dir, {withFileTypes: true}).flatMap((entry) => {
    const full = path.join(dir, entry.name);
    return entry.isDirectory() ? walk(full) : [full];
  });
}

function splitFrontmatter(raw) {
  const match = raw.match(/^---\n([\s\S]*?)\n---\n?([\s\S]*)$/);
  if (!match) return {frontmatter: {}, body: raw};
  const [, fm, body] = match;
  const frontmatter = {};
  for (const line of fm.split('\n')) {
    const m = line.match(/^(\w+):\s*(.*)$/);
    if (m) frontmatter[m[1]] = m[2].replace(/^["']|["']$/g, '');
  }
  return {frontmatter, body};
}
