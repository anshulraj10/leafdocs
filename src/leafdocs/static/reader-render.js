// Client-side rendering for the reader view. reader.html loads the KaTeX and
// mermaid vendor scripts only on pages that need them, so each part below
// runs only when its library is present.
(function () {
  // Math: arithmatex (generic mode) wraps TeX in \( \) or \[ \] inside
  // .arithmatex elements. Render only there, never the whole page.
  if (window.renderMathInElement) {
    document.querySelectorAll('.arithmatex').forEach(function (el) {
      window.renderMathInElement(el, {
        delimiters: [
          { left: '\\(', right: '\\)', display: false },
          { left: '\\[', right: '\\]', display: true },
        ],
        throwOnError: false,
      });
    });
  }

  // Diagrams: fenced_code emits <pre><code class="language-mermaid">.
  // Copy the source as text (never as HTML) into the <pre class="mermaid">
  // element mermaid expects.
  if (window.mermaid) {
    document.querySelectorAll('pre > code.language-mermaid').forEach(function (code) {
      var pre = document.createElement('pre');
      pre.className = 'mermaid';
      pre.textContent = code.textContent;
      code.parentElement.replaceWith(pre);
    });

    // Theme colors come from the palette variables in base.html
    var css = getComputedStyle(document.documentElement);
    var color = function (name) { return css.getPropertyValue(name).trim(); };

    window.mermaid.initialize({
      startOnLoad: false,
      securityLevel: 'strict',
      theme: 'base',
      themeVariables: {
        darkMode: true,
        background: color('--bg'),
        fontFamily: color('--font-ui'),
        textColor: color('--text'),
        primaryColor: color('--surface'),
        primaryTextColor: color('--text'),
        primaryBorderColor: color('--accent'),
        secondaryColor: color('--tag-bg'),
        secondaryTextColor: color('--tag-text'),
        secondaryBorderColor: color('--accent-dim'),
        tertiaryColor: color('--bg'),
        tertiaryTextColor: color('--text'),
        tertiaryBorderColor: color('--border'),
        lineColor: color('--muted'),
        edgeLabelBackground: color('--surface'),
        noteBkgColor: color('--surface'),
        noteTextColor: color('--text'),
        noteBorderColor: color('--border'),
      },
    });
    window.mermaid.run({ querySelector: 'pre.mermaid' });
  }
})();
