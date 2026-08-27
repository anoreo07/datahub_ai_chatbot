#!/usr/bin/env node
/**
 * V-DataAtlas - Automated Markdown to PDF Converter with Mermaid Rendering
 * Usage: node scripts/generate_report_pdf.js
 */
const fs = require('fs');
const path = require('path');
const puppeteer = require('puppeteer');
const { marked } = require('marked');

async function main() {
  const rootDir = path.resolve(__dirname, '..');
  const mdPath = path.join(rootDir, 'docs/V-DataAtlas_Product_Report.md');
  const outPdfPath = path.join(rootDir, 'docs/V-DataAtlas_Product_Report.pdf');
  const scratchDir = '/home/annh45/.gemini/antigravity/brain/82c3312d-6fed-466c-b0d2-b665197205e2/scratch';
  const mermaidJsPath = path.join(scratchDir, 'node_modules/mermaid/dist/mermaid.min.js');

  if (!fs.existsSync(mdPath)) {
    console.error('Markdown file not found:', mdPath);
    process.exit(1);
  }

  console.log('Reading markdown from:', mdPath);
  const mdContent = fs.readFileSync(mdPath, 'utf-8');

  // Custom renderer for marked to transform ```mermaid into <div class="mermaid">
  const renderer = new marked.Renderer();
  const originalCodeRenderer = renderer.code.bind(renderer);

  renderer.code = function(code, lang, isEscaped) {
    let text = typeof code === 'object' ? code.text : code;
    let language = typeof code === 'object' ? code.lang : lang;

    if (language === 'mermaid') {
      return `<div class="mermaid-container"><pre class="mermaid">${text}</pre></div>`;
    }
    return originalCodeRenderer(code, lang, isEscaped);
  };

  marked.setOptions({
    renderer: renderer,
    gfm: true,
    breaks: false,
  });

  console.log('Parsing Markdown to HTML...');
  const parsedHtml = marked.parse(mdContent);
  const mermaidScript = fs.existsSync(mermaidJsPath) ? fs.readFileSync(mermaidJsPath, 'utf-8') : '';

  const fullHtml = `<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="UTF-8">
  <title>V-DataAtlas Product Report</title>
  <style>
    @page {
      size: A4;
      margin: 15mm 15mm 15mm 15mm;
    }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
      font-size: 13px;
      line-height: 1.6;
      color: #111827;
      margin: 0;
      padding: 0;
    }
    h1 {
      font-size: 22px;
      font-weight: 700;
      color: #0f172a;
      border-bottom: 2px solid #0f172a;
      padding-bottom: 8px;
      margin-top: 24px;
      margin-bottom: 12px;
      page-break-after: avoid;
    }
    h2 {
      font-size: 17px;
      font-weight: 700;
      color: #1e293b;
      border-bottom: 1px solid #cbd5e1;
      padding-bottom: 6px;
      margin-top: 28px;
      margin-bottom: 10px;
      page-break-after: avoid;
    }
    h3 {
      font-size: 14px;
      font-weight: 600;
      color: #334155;
      margin-top: 18px;
      margin-bottom: 8px;
      page-break-after: avoid;
    }
    h4 {
      font-size: 13px;
      font-weight: 600;
      color: #475569;
      margin-top: 14px;
      margin-bottom: 6px;
      page-break-after: avoid;
    }
    p, ul, ol {
      margin-top: 6px;
      margin-bottom: 8px;
    }
    li {
      margin-bottom: 4px;
    }
    hr {
      border: 0;
      border-top: 1px solid #e2e8f0;
      margin: 18px 0;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      margin: 12px 0;
      font-size: 12px;
      page-break-inside: auto;
    }
    tr {
      page-break-inside: avoid;
      page-break-after: auto;
    }
    th, td {
      border: 1px solid #94a3b8;
      padding: 6px 10px;
      text-align: left;
      vertical-align: top;
    }
    th {
      background-color: #f1f5f9;
      color: #0f172a;
      font-weight: 600;
    }
    pre {
      background-color: #f8fafc;
      border: 1px solid #e2e8f0;
      border-radius: 4px;
      padding: 10px;
      overflow-x: auto;
      font-family: "JetBrains Mono", Consolas, "Courier New", monospace;
      font-size: 11.5px;
      page-break-inside: avoid;
    }
    code {
      font-family: "JetBrains Mono", Consolas, "Courier New", monospace;
      font-size: 11.5px;
      background-color: #f1f5f9;
      padding: 1px 4px;
      border-radius: 3px;
      color: #0f172a;
    }
    pre code {
      background-color: transparent;
      padding: 0;
      border-radius: 0;
    }
    blockquote {
      margin: 10px 0;
      padding: 6px 12px;
      border-left: 4px solid #3b82f6;
      background-color: #f8fafc;
      color: #334155;
    }
    a {
      color: #2563eb;
      text-decoration: none;
    }
    a:hover {
      text-decoration: underline;
    }
    .mermaid-container {
      display: flex;
      justify-content: center;
      align-items: center;
      margin: 18px 0;
      padding: 12px;
      background-color: #ffffff;
      border: 1px solid #e2e8f0;
      border-radius: 6px;
      page-break-inside: avoid;
      text-align: center;
    }
    .mermaid svg {
      max-width: 100%;
      height: auto;
    }
  </style>
  <script>
    ${mermaidScript}
  </script>
</head>
<body>
  ${parsedHtml}
  <script>
    mermaid.initialize({
      startOnLoad: true,
      theme: 'default',
      securityLevel: 'loose',
      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif',
      flowchart: {
        useMaxWidth: true,
        htmlLabels: true,
        curve: 'basis'
      },
      sequence: {
        useMaxWidth: true,
        showSequenceNumbers: true
      },
      er: {
        useMaxWidth: true
      }
    });
  </script>
</body>
</html>`;

  console.log('Launching Puppeteer headless browser...');
  const browser = await puppeteer.launch({
    headless: 'new',
    args: [
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--disable-dev-shm-usage',
      '--disable-gpu',
      '--font-render-hinting=none'
    ]
  });

  const page = await browser.newPage();
  console.log('Setting HTML content in page...');
  await page.setContent(fullHtml, { waitUntil: 'networkidle0' });

  console.log('Rendering Mermaid diagrams...');
  await page.evaluate(async () => {
    if (window.mermaid) {
      await window.mermaid.run();
    }
  });

  await new Promise(r => setTimeout(r, 2000));

  const svgCount = await page.evaluate(() => {
    return document.querySelectorAll('.mermaid svg').length;
  });
  console.log(`Successfully rendered ${svgCount} Mermaid SVG diagrams in page!`);

  console.log('Writing PDF to disk...');
  await page.pdf({
    path: outPdfPath,
    format: 'A4',
    margin: {
      top: '15mm',
      right: '15mm',
      bottom: '15mm',
      left: '15mm',
    },
    printBackground: true,
    displayHeaderFooter: true,
    headerTemplate: '<div></div>',
    footerTemplate: `
      <div style="width: 100%; font-size: 9px; color: #64748b; text-align: center; padding-top: 5px; font-family: sans-serif;">
        <span>V-DataAtlas Technical Product Report</span> &nbsp;|&nbsp; 
        <span>Trang <span class="pageNumber"></span> / <span class="totalPages"></span></span>
      </div>
    `,
  });

  await browser.close();
  console.log('PDF generated successfully at:', outPdfPath);
}

main().catch(err => {
  console.error('Error generating PDF:', err);
  process.exit(1);
});
