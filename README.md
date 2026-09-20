# Kohler AI Bathroom Designer: Enterprise Specification Engine

A deterministic, code-compliant spatial routing and sustainability platform for architectural design. It ingests dimensional constraints, places fixtures using strict ADA and IBC compliance parameters, tracks environmental impact via Kohler's Eco-Smart tier, and compiles a paginated, deployment-ready specification PDF.

Built for the **KOHLER AI Lab Program, Track 1**.

### 🎥 Video Demonstration
**Watch the Walkthrough:** [https://youtu.be/OoWaedDzoKU](https://youtu.be/OoWaedDzoKU)

### 📁 Submission Artifacts
* **Working Model:** Full source code included in this repository.
* **Video Demonstration:** Linked above.
* **Prompts Documentation:** See `Prompts_Documentation.pdf` in the root directory.
* **Presentation Deck:** See `Kohler_Deck.pdf` in the root directory.

### 🏗 Architecture
* **Routing Engine (Python/Flask):** Processes room dimensions and applies a deterministic coordinate clamp (Track 1 safety override) to guarantee spatial safety.
* **Rendering Pipeline (Vanilla JS + SVG):** Dynamically scales vector output using `viewBox` normalization to fit any viewport perfectly without clipping.
* **State Management (Browser LocalStorage):** Transfers spatial vector data and session metrics seamlessly from the Studio Planner to the Sustainability Dashboard without database re-queries.
* **Impact & Rationale Engine:** Calculates deterministic water reduction metrics and explicitly documents architectural reasoning (e.g., ADA clearances, IBC walkways).
* **Export Pipeline (CSS / Native Browser):** Injects custom `@media print` overrides to hide navigation, force background graphics, and prevent page breaks from slicing charts during PDF compilation.

### 🎯 Scope of this Build
This build fulfills the requirements for the Track 1 functional prototype.
* **Safety Override:** To prevent generative AI spatial hallucinations during live evaluation, the raw LLM coordinate math is currently bypassed. The system uses a strict deterministic clamp to ensure perfect, code-compliant layouts. Full dynamic AI coordinate generation is staged for Track 2.
* **Data Persistence:** Database integration is bypassed in favor of local session storage to guarantee lightweight, immediate data transfer for demonstration purposes.

### ⚙️ Quickstart Instructions

**Prerequisites:** Python 3.10+, Modern Web Browser (Chrome/Edge recommended for native PDF rendering).

```bash
# 1. Clone the repository
git clone [https://github.com/poojawork102/kohler-ai-bathroom-designer.git](https://github.com/poojawork102/kohler-ai-bathroom-designer.git)
cd kohler-ai-bathroom-designer

# 2. Set up the environment
python -m venv venv
# On Windows: venv\Scripts\activate
# On Mac/Linux: source venv/bin/activate
pip install -r requirements.txt

# 3. Run the backend
python app.py

# 4. Open the application
# Navigate to http://localhost:5000 in your browser
