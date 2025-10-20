# Sample Insurance Claims Cases

This directory contains three sample insurance claims cases for testing the multi-agent claims processing system. Each case is designed to test different aspects of the system's capabilities.

## Case Structure

Each case directory contains:
- **fnol.pdf** - First Notice of Loss form (filled out by policyholder)
- **invoice.pdf** - Repair estimate or invoice from contractor
- **photo_*.jpg** - Photos documenting the damage

## Test Cases

### Case A: Burst Pipe (Clear Coverage)
**Directory:** `case_a/`
**Policy:** HO3-2024-001234
**Scenario:** Sudden and accidental water damage from frozen burst pipe

**Expected Outcome:** Quick approval
- Clear coverage under standard homeowners policy
- Sudden and accidental event
- Well-documented damage
- Reasonable repair costs ($3,548.75)

**Files:**
- `fnol.pdf` - Detailed loss report with timeline
- `invoice.pdf` - Itemized repair estimate from Rapid Restoration Services
- 4 photos showing bathroom and kitchen water damage

**Testing Focus:**
- FNOL parsing and key-value extraction
- Policy retrieval and coverage verification
- Straightforward approval workflow
- Requirements: 11.1, 11.5

---

### Case B: Seepage Suspicion (Multi-Round Debate)
**Directory:** `case_b/`
**Policy:** HO3-2024-005678
**Scenario:** Basement water damage with unclear cause (seepage vs. sudden event)

**Expected Outcome:** Partial coverage after debate
- Ambiguous cause (gradual seepage vs. sudden water intrusion)
- Should trigger multi-round agent debate
- Partial coverage decision likely
- May require additional investigation

**Files:**
- `fnol.pdf` - Loss report with uncertain timeline and cause
- `invoice.pdf` - Estimate from Basement Solutions Inc. ($2,348.13)
- 3 photos showing basement wall staining and moisture

**Testing Focus:**
- Handling ambiguous claims
- Multi-agent debate and reasoning
- Partial coverage decisions
- Evidence evaluation
- Requirements: 11.1, 11.5

---

### Case C: Auto Collision with Scope Dispute (Fraud Detection)
**Directory:** `case_c/`
**Policy:** AUTO-2024-009876
**Scenario:** Vehicle collision with high repair estimate

**Expected Outcome:** Partial coverage with fraud concerns
- Clear liability (other driver ran red light)
- High repair estimate ($9,318.13) may trigger fraud review
- Possible scope dispute on repair items
- Should test compliance checking

**Files:**
- `fnol.pdf` - Detailed accident report with witness information
- `invoice.pdf` - Comprehensive repair estimate from Precision Auto Body
- 5 photos showing vehicle damage and accident scene

**Testing Focus:**
- Auto claims processing
- High-value claim review
- Fraud detection patterns
- Scope of repair validation
- Compliance checking
- Requirements: 11.1, 11.5

---

## Usage

These sample cases are used by the test suite and can be processed through the claims system:

```python
# Example: Process a sample case
from backend.orchestration.supervisor import ClaimsSupervisor

supervisor = ClaimsSupervisor()
result = supervisor.process_claim(
    fnol_path="data/sample_cases/case_a/fnol.pdf",
    photos=["data/sample_cases/case_a/photo_1_bathroom_flooding.jpg", ...],
    invoice_path="data/sample_cases/case_a/invoice.pdf"
)
```

## Generating Sample Files

The PDF and photo files were generated using:
- `create_sample_pdfs.py` - Generates FNOL and invoice PDFs using reportlab
- `create_sample_photos.py` - Generates placeholder photo images using Pillow

To regenerate:
```bash
python create_sample_pdfs.py
python create_sample_photos.py
```

## Notes

- All PDFs are properly formatted for Nova Pro document analysis
- Photos are placeholder images with text labels for testing
- Policy numbers reference sample policies in `data/policies/`
- All personal information is fictional
- Amounts and details are realistic but not based on real claims
