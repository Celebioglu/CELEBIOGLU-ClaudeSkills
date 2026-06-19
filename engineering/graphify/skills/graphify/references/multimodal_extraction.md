# Multimodal Extraction — Reference

## What "Multimodal" Means for graphify

graphify handles inputs beyond code files:

| Input type | Extraction method | Where it runs |
|-----------|------------------|---------------|
| Code (25 langs) | `ast_extractor.py` regex / tree-sitter | Local Python, stdlib |
| Markdown / docs | `graph_builder.py` heading hierarchy | Local Python, stdlib |
| JSON / YAML / TOML | `graph_builder.py` key extraction | Local Python, stdlib |
| Images / screenshots / diagrams | Claude multimodal inference | Claude model context |
| PDF documents | `pdfminer.six` text → then Claude | Local + Claude context |
| Audio files | Whisper local transcription → Claude | Local CPU (no cloud API) |
| Video files | Whisper local transcription + frame sampling → Claude | Local CPU |

The Python scripts handle deterministic extraction. Claude itself handles semantic understanding of multimodal inputs — concepts and relationships extracted from images/audio are fed back to `graph_builder.py` as additional node/edge JSON.

## Foundational Sources

**1. Radford et al. (2022) — "Robust Speech Recognition via Large-Scale Weak Supervision" (Whisper)**  
*OpenAI Technical Report / arXiv:2212.04356*  
Whisper is a seq2seq transformer trained on 680k hours of web audio. Key properties: multilingual (99 languages), runs on CPU, handles noisy audio. For graphify: `pip install openai-whisper` (no API key required — inference is local). Use `whisper <file> --model base` for speed or `--model medium` for accuracy. Output: timestamped transcript that graphify then parses for concept mentions.

**2. Anthropic Claude API Documentation — Vision**  
*docs.anthropic.com/claude/docs/vision*  
Claude processes images natively when passed as base64 or URL in the messages array. For graphify sessions: attach whiteboard photos, architecture diagrams, screenshots, or scanned PDFs directly to the Claude conversation. Claude extracts entities (box labels, arrow descriptions) and relationships (connection labels) and expresses them as structured text that `graph_builder.py` can parse.

**3. Liu et al. (2023) — "Visual Instruction Tuning" (LLaVA)**  
*NeurIPS 2023 / arXiv:2304.08485*  
Visual instruction tuning connects image encoders to LLMs, enabling the model to answer questions about images. The key finding: diagram-understanding capability generalizes from natural images to technical diagrams (UML, architecture boxes-and-arrows, flowcharts) without task-specific training. This is why Claude can extract graph nodes and edges from whiteboard photos without a specialized diagramming model.

**4. Lohr (2023) — "How to Read a Technical Diagram"**  
*IEEE Spectrum / ACM Queue cross-post*  
Documents the conventions used in common software architecture diagrams: C4 model (Context/Container/Component/Code), UML class diagrams, sequence diagrams, ERDs, flowcharts. graphify uses these conventions to guide Claude extraction: "identify boxes as nodes, arrows as edges, dashed lines as dependency edges, solid lines as containment or call edges."

**5. PDFMiner — Python PDF Parser**  
*github.com/pdfminer/pdfminer.six*  
`pdfminer.six` extracts text from PDFs preserving layout (column order, table structure). Installation: `pip install pdfminer.six`. For graphify: pipe PDF text through `graph_builder.py`'s markdown-heading parser (PDFs often have title/section structure that maps to h1/h2 heading hierarchy). For complex PDFs (mathematical notation, scanned images), pass directly to Claude multimodal.

**6. Zhu et al. (2015) — "Aligning Books and Movies"**  
*ICCV 2015*  
Demonstrates that narrative alignment across media (book text ↔ movie scene) can be done by matching semantic concepts across modalities. For graphify: the same principle applies when aligning a code comment mentioning "UserService" with a whiteboard box labeled "User Svc" — they are the same conceptual node. Matching by normalized label overlap (stemming + fuzzy match) is the practical implementation.

**7. Schuhmann et al. (2022) — "LAION-5B: An Open Large-Scale Dataset for Training Next Generation Image-Text Models"**  
*NeurIPS 2022*  
Shows that image-text alignment at scale (5.85B pairs) produces robust cross-modal representations. Practical implication for graphify: Claude's image understanding is robust to: low-resolution photos, handwritten text, partial diagrams, diagrams in non-English languages, photos of physical whiteboards under non-ideal lighting.

## Workflow: Multimodal graphify Session

```
1. Gather inputs: code dir, PDFs, screenshots, recordings
2. Run ast_extractor.py on code → entities.json
3. Run graph_builder.py entities.json --scan ./docs → graph.json (merges Markdown/YAML)
4. For each image/PDF: paste into Claude chat and ask:
     "Extract entities (node type + name) and relationships (source, target, relation)
      from this diagram as JSON matching the format:
      { 'nodes': [{'id':..., 'label':..., 'type':...}],
        'edges': [{'source':..., 'target':..., 'relation':...}] }"
5. Append Claude's JSON output to a file: extra_nodes.json
6. Re-run graph_builder.py with --merge extra_nodes.json to unify all sources
7. Run graph_renderer.py --format summary for the combined insight report
```

## Audio/Video: Whisper Integration

```bash
# Install (CPU-only, ~1GB model download for 'base')
pip install openai-whisper

# Transcribe a meeting recording or design session video
whisper design-session.mp4 --model base --output_format json > transcript.json

# The transcript is plain text — feed it to graph_builder.py as a markdown file
# (wrap it in ## headings by speaker segment if available)
```

Whisper supports: mp3, mp4, mpeg, mpga, m4a, wav, webm. The `base` model runs on any CPU in ~1x real-time. Use `medium` for better accuracy on accented speech or domain-specific terminology.

## Hard Rules

- **Never send code to a cloud transcription service** without security review — use Whisper locally.
- **Images are not stored by graphify** — they exist only in the Claude conversation context window.
- **Claude multimodal extraction is not deterministic** — re-running the same image may yield slightly different node/edge lists. Lock the output to `extra_nodes.json` once reviewed.
- **PDF scans (raster images embedded in PDF)** require multimodal Claude, not pdfminer — pdfminer only extracts selectable text.
