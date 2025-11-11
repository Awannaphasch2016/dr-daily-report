You are a code generator. Read the following Visualization Intent Contract (VIC) JSON and produce a runnable visualization using the specified library. 
- If library == altair/plotly/bokeh: generate a single Python file that:
  1) loads data from VIC.data.source,
  2) applies VIC.transform if present,
  3) builds the chart per VIC.view.encodings and VIC.view.mark,
  4) enables interactions per VIC.interactions,
  5) writes a self-contained HTML to VIC.output.path.
- If library == d3: generate index.html + script.js (+ styles.css if needed) that:
  1) loads VIC.data.source (csv/json) client-side,
  2) creates the chart per VIC.view.encodings and VIC.view.mark,
  3) enables interactions per VIC.interactions (zoom/hover/brush),
  4) writes instructions to run via a simple static server (e.g., python -m http.server).

Also print any dependency install commands and a short “How to run” section.

Here is the VIC JSON:
<PASTE THE JSON HERE>
