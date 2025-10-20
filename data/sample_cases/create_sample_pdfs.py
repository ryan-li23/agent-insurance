"""
Script to generate sample PDF files for test cases.
Creates FNOL forms and invoices as PDFs that can be processed by Nova Pro.
"""

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
import os


def create_fnol_case_a():
    """Create FNOL PDF for Case A - Burst Pipe"""
    os.makedirs("case_a", exist_ok=True)
    doc = SimpleDocTemplate("case_a/fnol.pdf", pagesize=letter)
    story = []
    styles = getSampleStyleSheet()
    
    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=colors.HexColor('#003366'),
        spaceAfter=30,
        alignment=TA_CENTER
    )
    story.append(Paragraph("FIRST NOTICE OF LOSS", title_style))
    story.append(Spacer(1, 0.2*inch))
    
    # Policy Information Table
    policy_data = [
        ['Policy Number:', 'HO3-2024-001234'],
        ['Insured Name:', 'John Smith'],
        ['Property Address:', '123 Maple Street, Springfield, IL 62701'],
        ['Date of Loss:', '10/10/2024'],
        ['Time of Loss:', '02:30 AM'],
        ['Date Reported:', '10/10/2024']
    ]
    
    policy_table = Table(policy_data, colWidths=[2*inch, 4*inch])
    policy_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(policy_table)
    story.append(Spacer(1, 0.3*inch))
    
    # Loss Description
    story.append(Paragraph("<b>LOSS DESCRIPTION:</b>", styles['Heading2']))
    story.append(Spacer(1, 0.1*inch))
    
    loss_desc = """On October 10, 2024, at approximately 2:30 AM, I was awakened by the sound of rushing water. 
    Upon investigation, I discovered that a pipe had burst in the upstairs bathroom. Water was flooding the bathroom 
    floor and leaking through the ceiling into the kitchen below.<br/><br/>
    
    I immediately shut off the main water valve and called an emergency plumber. The plumber arrived at 4:00 AM 
    and confirmed that a copper pipe behind the bathroom wall had frozen and burst due to the recent cold snap 
    (temperatures dropped to 15°F overnight)."""
    
    story.append(Paragraph(loss_desc, styles['Normal']))
    story.append(Spacer(1, 0.2*inch))
    
    # Damage Observed
    story.append(Paragraph("<b>DAMAGE OBSERVED:</b>", styles['Heading2']))
    story.append(Spacer(1, 0.1*inch))
    
    damage_list = """
    • Bathroom: Significant water damage to drywall, flooring (tile), and vanity cabinet<br/>
    • Kitchen: Water damage to ceiling drywall, light fixture damaged, water pooling on floor<br/>
    • Estimated affected area: Approximately 200 square feet
    """
    story.append(Paragraph(damage_list, styles['Normal']))
    story.append(Spacer(1, 0.2*inch))
    
    # Immediate Actions
    story.append(Paragraph("<b>IMMEDIATE ACTIONS TAKEN:</b>", styles['Heading2']))
    story.append(Spacer(1, 0.1*inch))
    
    actions = """
    • Shut off main water valve<br/>
    • Called emergency plumber (arrived 4:00 AM)<br/>
    • Placed buckets to catch dripping water<br/>
    • Moved furniture and belongings away from affected areas<br/>
    • Contacted insurance company
    """
    story.append(Paragraph(actions, styles['Normal']))
    story.append(Spacer(1, 0.2*inch))
    
    # Cause and Contact
    story.append(Paragraph("<b>CAUSE OF LOSS:</b>", styles['Heading2']))
    story.append(Paragraph("Sudden and accidental discharge of water due to frozen and burst pipe.", styles['Normal']))
    story.append(Spacer(1, 0.2*inch))
    
    story.append(Paragraph("<b>CONTACT INFORMATION:</b>", styles['Heading2']))
    contact = "Phone: (217) 555-0123<br/>Email: john.smith@email.com"
    story.append(Paragraph(contact, styles['Normal']))
    
    doc.build(story)
    print("Created case_a/fnol.pdf")


def create_invoice_case_a():
    """Create invoice PDF for Case A"""
    doc = SimpleDocTemplate("case_a/invoice.pdf", pagesize=letter)
    story = []
    styles = getSampleStyleSheet()
    
    # Company Header
    header_style = ParagraphStyle('Header', parent=styles['Normal'], fontSize=14, textColor=colors.HexColor('#003366'))
    story.append(Paragraph("<b>RAPID RESTORATION SERVICES</b>", header_style))
    story.append(Paragraph("456 Commerce Drive, Springfield, IL 62702", styles['Normal']))
    story.append(Paragraph("Phone: (217) 555-9876 | License #: IL-REST-2024-5678", styles['Normal']))
    story.append(Spacer(1, 0.3*inch))
    
    # Invoice Title
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=16, alignment=TA_CENTER)
    story.append(Paragraph("<b>INVOICE</b>", title_style))
    story.append(Spacer(1, 0.2*inch))
    
    # Invoice Details
    invoice_info = [
        ['Invoice Number:', 'INV-2024-1234'],
        ['Invoice Date:', '10/15/2024'],
        ['Customer:', 'John Smith'],
        ['Property:', '123 Maple Street, Springfield, IL 62701'],
        ['Insurance Claim:', 'HO3-2024-001234']
    ]
    
    info_table = Table(invoice_info, colWidths=[2*inch, 4*inch])
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 0.3*inch))
    
    # Line Items
    story.append(Paragraph("<b>SERVICES PROVIDED:</b>", styles['Heading2']))
    story.append(Spacer(1, 0.1*inch))
    
    line_items = [
        ['Description', 'Quantity', 'Unit Price', 'Total'],
        ['Emergency plumbing repair - burst pipe', '1', '$450.00', '$450.00'],
        ['Water extraction and drying services', '1', '$800.00', '$800.00'],
        ['Bathroom drywall removal and replacement', '50 sq ft', '$8.00', '$400.00'],
        ['Kitchen ceiling drywall repair', '30 sq ft', '$8.00', '$240.00'],
        ['Bathroom tile flooring repair', '25 sq ft', '$15.00', '$375.00'],
        ['Paint and finishing (2 rooms)', '1', '$600.00', '$600.00'],
        ['Vanity cabinet replacement', '1', '$350.00', '$350.00'],
        ['Kitchen light fixture replacement', '1', '$125.00', '$125.00'],
        ['', '', '<b>Subtotal:</b>', '<b>$3,340.00</b>'],
        ['', '', '<b>Tax (6.25%):</b>', '<b>$208.75</b>'],
        ['', '', '<b>TOTAL:</b>', '<b>$3,548.75</b>']
    ]
    
    items_table = Table(line_items, colWidths=[3*inch, 1*inch, 1.2*inch, 1.2*inch])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -4), 1, colors.black),
        ('LINEABOVE', (2, -3), (-1, -3), 2, colors.black),
        ('LINEABOVE', (2, -1), (-1, -1), 2, colors.black),
        ('ALIGN', (2, -3), (-1, -1), 'RIGHT'),
    ]))
    story.append(items_table)
    story.append(Spacer(1, 0.3*inch))
    
    # Payment Terms
    story.append(Paragraph("<b>PAYMENT TERMS:</b> Due upon receipt", styles['Normal']))
    story.append(Paragraph("<b>NOTES:</b> All work completed per industry standards. Materials and labor warranty: 1 year.", styles['Normal']))
    
    doc.build(story)
    print("Created case_a/invoice.pdf")


def create_fnol_case_b():
    """Create FNOL PDF for Case B - Seepage Suspicion"""
    os.makedirs("case_b", exist_ok=True)
    doc = SimpleDocTemplate("case_b/fnol.pdf", pagesize=letter)
    story = []
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'], fontSize=16, 
                                 textColor=colors.HexColor('#003366'), spaceAfter=30, alignment=TA_CENTER)
    story.append(Paragraph("FIRST NOTICE OF LOSS", title_style))
    story.append(Spacer(1, 0.2*inch))
    
    policy_data = [
        ['Policy Number:', 'HO3-2024-005678'],
        ['Insured Name:', 'Sarah Johnson'],
        ['Property Address:', '789 Oak Avenue, Springfield, IL 62703'],
        ['Date of Loss:', '09/15/2024'],
        ['Time of Loss:', 'Unknown - discovered 6:00 PM'],
        ['Date Reported:', '09/20/2024']
    ]
    
    policy_table = Table(policy_data, colWidths=[2*inch, 4*inch])
    policy_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    story.append(policy_table)
    story.append(Spacer(1, 0.3*inch))
    
    story.append(Paragraph("<b>LOSS DESCRIPTION:</b>", styles['Heading2']))
    story.append(Spacer(1, 0.1*inch))
    
    loss_desc = """On September 20, 2024, I discovered water staining and dampness on the basement wall near the 
    foundation. The affected area shows discoloration extending approximately 4 feet up from the floor along a 
    10-foot section of the east wall.<br/><br/>
    
    I'm not sure when this started, but I noticed a musty smell in the basement about 2-3 weeks ago. The staining 
    appears to have been developing over time. There was heavy rainfall in the area during the week of September 8-15."""
    
    story.append(Paragraph(loss_desc, styles['Normal']))
    story.append(Spacer(1, 0.2*inch))
    
    story.append(Paragraph("<b>DAMAGE OBSERVED:</b>", styles['Heading2']))
    damage_list = """
    • Basement wall: Water staining and dampness on drywall (approximately 40 square feet)<br/>
    • Basement floor: Carpet shows moisture damage and discoloration<br/>
    • Musty odor present in basement<br/>
    • Some stored items affected by moisture
    """
    story.append(Paragraph(damage_list, styles['Normal']))
    story.append(Spacer(1, 0.2*inch))
    
    story.append(Paragraph("<b>POSSIBLE CAUSE:</b>", styles['Heading2']))
    story.append(Paragraph("Unknown. Could be related to recent heavy rainfall or possible foundation issue.", styles['Normal']))
    story.append(Spacer(1, 0.2*inch))
    
    story.append(Paragraph("<b>CONTACT INFORMATION:</b>", styles['Heading2']))
    contact = "Phone: (217) 555-4567<br/>Email: sarah.johnson@email.com"
    story.append(Paragraph(contact, styles['Normal']))
    
    doc.build(story)
    print("Created case_b/fnol.pdf")


def create_invoice_case_b():
    """Create invoice PDF for Case B"""
    doc = SimpleDocTemplate("case_b/invoice.pdf", pagesize=letter)
    story = []
    styles = getSampleStyleSheet()
    
    header_style = ParagraphStyle('Header', parent=styles['Normal'], fontSize=14, textColor=colors.HexColor('#003366'))
    story.append(Paragraph("<b>BASEMENT SOLUTIONS INC.</b>", header_style))
    story.append(Paragraph("321 Industrial Parkway, Springfield, IL 62704", styles['Normal']))
    story.append(Paragraph("Phone: (217) 555-3344 | License #: IL-BASE-2024-9012", styles['Normal']))
    story.append(Spacer(1, 0.3*inch))
    
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=16, alignment=TA_CENTER)
    story.append(Paragraph("<b>ESTIMATE / INVOICE</b>", title_style))
    story.append(Spacer(1, 0.2*inch))
    
    invoice_info = [
        ['Invoice Number:', 'EST-2024-5678'],
        ['Date:', '09/25/2024'],
        ['Customer:', 'Sarah Johnson'],
        ['Property:', '789 Oak Avenue, Springfield, IL 62703'],
        ['Insurance Claim:', 'HO3-2024-005678']
    ]
    
    info_table = Table(invoice_info, colWidths=[2*inch, 4*inch])
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 0.3*inch))
    
    story.append(Paragraph("<b>SERVICES PROVIDED:</b>", styles['Heading2']))
    story.append(Spacer(1, 0.1*inch))
    
    line_items = [
        ['Description', 'Quantity', 'Unit Price', 'Total'],
        ['Moisture inspection and assessment', '1', '$200.00', '$200.00'],
        ['Basement wall drywall removal', '40 sq ft', '$6.00', '$240.00'],
        ['Carpet removal and disposal', '100 sq ft', '$3.00', '$300.00'],
        ['Dehumidification and drying (5 days)', '1', '$500.00', '$500.00'],
        ['Foundation sealing (interior)', '10 ft', '$45.00', '$450.00'],
        ['Drywall replacement and finishing', '40 sq ft', '$8.00', '$320.00'],
        ['Paint and waterproof coating', '40 sq ft', '$5.00', '$200.00'],
        ['', '', '<b>Subtotal:</b>', '<b>$2,210.00</b>'],
        ['', '', '<b>Tax (6.25%):</b>', '<b>$138.13</b>'],
        ['', '', '<b>TOTAL:</b>', '<b>$2,348.13</b>']
    ]
    
    items_table = Table(line_items, colWidths=[3*inch, 1*inch, 1.2*inch, 1.2*inch])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -4), 1, colors.black),
        ('LINEABOVE', (2, -3), (-1, -3), 2, colors.black),
        ('LINEABOVE', (2, -1), (-1, -1), 2, colors.black),
        ('ALIGN', (2, -3), (-1, -1), 'RIGHT'),
    ]))
    story.append(items_table)
    story.append(Spacer(1, 0.3*inch))
    
    story.append(Paragraph("<b>NOTES:</b> Foundation sealing addresses current moisture intrusion. " +
                          "Recommend exterior drainage evaluation for long-term solution.", styles['Normal']))
    
    doc.build(story)
    print("Created case_b/invoice.pdf")


def create_fnol_case_c():
    """Create FNOL PDF for Case C - Auto Collision"""
    os.makedirs("case_c", exist_ok=True)
    doc = SimpleDocTemplate("case_c/fnol.pdf", pagesize=letter)
    story = []
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'], fontSize=16,
                                 textColor=colors.HexColor('#003366'), spaceAfter=30, alignment=TA_CENTER)
    story.append(Paragraph("FIRST NOTICE OF LOSS - AUTO COLLISION", title_style))
    story.append(Spacer(1, 0.2*inch))
    
    policy_data = [
        ['Policy Number:', 'AUTO-2024-009876'],
        ['Insured Name:', 'Michael Chen'],
        ['Vehicle:', '2022 Honda Accord, VIN: 1HGCV1F3XNA123456'],
        ['Date of Loss:', '10/05/2024'],
        ['Time of Loss:', '3:45 PM'],
        ['Date Reported:', '10/05/2024'],
        ['Location:', 'Intersection of Main St & 5th Ave, Springfield, IL']
    ]
    
    policy_table = Table(policy_data, colWidths=[2*inch, 4*inch])
    policy_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    story.append(policy_table)
    story.append(Spacer(1, 0.3*inch))
    
    story.append(Paragraph("<b>ACCIDENT DESCRIPTION:</b>", styles['Heading2']))
    story.append(Spacer(1, 0.1*inch))
    
    loss_desc = """On October 5, 2024, at approximately 3:45 PM, I was driving eastbound on Main Street approaching 
    the intersection with 5th Avenue. The traffic light was green for my direction. As I entered the intersection, 
    another vehicle (2019 Ford F-150, driver: Robert Williams) ran the red light traveling northbound on 5th Avenue 
    and struck the front passenger side of my vehicle.<br/><br/>
    
    The impact caused significant damage to the front right quarter panel, door, and wheel assembly of my vehicle. 
    The airbags did not deploy. Both vehicles were towed from the scene. Police report #SPD-2024-10-1234 was filed."""
    
    story.append(Paragraph(loss_desc, styles['Normal']))
    story.append(Spacer(1, 0.2*inch))
    
    story.append(Paragraph("<b>DAMAGE TO INSURED VEHICLE:</b>", styles['Heading2']))
    damage_list = """
    • Front right quarter panel: Severe impact damage, crumpled<br/>
    • Front right door: Dented, door frame bent, will not open<br/>
    • Front right wheel: Bent rim, tire damaged<br/>
    • Front right suspension: Possible damage to control arm and strut<br/>
    • Headlight assembly: Broken
    """
    story.append(Paragraph(damage_list, styles['Normal']))
    story.append(Spacer(1, 0.2*inch))
    
    story.append(Paragraph("<b>OTHER PARTY INFORMATION:</b>", styles['Heading2']))
    other_party = """
    Driver: Robert Williams<br/>
    Vehicle: 2019 Ford F-150, License: IL ABC-1234<br/>
    Insurance: State Farm, Policy #: 123-456-789<br/>
    Phone: (217) 555-7890
    """
    story.append(Paragraph(other_party, styles['Normal']))
    story.append(Spacer(1, 0.2*inch))
    
    story.append(Paragraph("<b>WITNESSES:</b>", styles['Heading2']))
    story.append(Paragraph("Pedestrian at corner: Jennifer Martinez, (217) 555-2468", styles['Normal']))
    story.append(Spacer(1, 0.2*inch))
    
    story.append(Paragraph("<b>INJURIES:</b>", styles['Heading2']))
    story.append(Paragraph("Minor soreness, declined ambulance transport. Will monitor for symptoms.", styles['Normal']))
    story.append(Spacer(1, 0.2*inch))
    
    story.append(Paragraph("<b>CONTACT INFORMATION:</b>", styles['Heading2']))
    contact = "Phone: (217) 555-8901<br/>Email: michael.chen@email.com"
    story.append(Paragraph(contact, styles['Normal']))
    
    doc.build(story)
    print("Created case_c/fnol.pdf")


def create_invoice_case_c():
    """Create invoice PDF for Case C"""
    doc = SimpleDocTemplate("case_c/invoice.pdf", pagesize=letter)
    story = []
    styles = getSampleStyleSheet()
    
    header_style = ParagraphStyle('Header', parent=styles['Normal'], fontSize=14, textColor=colors.HexColor('#003366'))
    story.append(Paragraph("<b>PRECISION AUTO BODY & REPAIR</b>", header_style))
    story.append(Paragraph("555 Auto Plaza Drive, Springfield, IL 62705", styles['Normal']))
    story.append(Paragraph("Phone: (217) 555-AUTO | License #: IL-AUTO-2024-7788", styles['Normal']))
    story.append(Spacer(1, 0.3*inch))
    
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=16, alignment=TA_CENTER)
    story.append(Paragraph("<b>REPAIR ESTIMATE</b>", title_style))
    story.append(Spacer(1, 0.2*inch))
    
    invoice_info = [
        ['Estimate Number:', 'EST-2024-9876'],
        ['Date:', '10/08/2024'],
        ['Customer:', 'Michael Chen'],
        ['Vehicle:', '2022 Honda Accord'],
        ['VIN:', '1HGCV1F3XNA123456'],
        ['Insurance Claim:', 'AUTO-2024-009876']
    ]
    
    info_table = Table(invoice_info, colWidths=[2*inch, 4*inch])
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 0.3*inch))
    
    story.append(Paragraph("<b>REPAIR ITEMS:</b>", styles['Heading2']))
    story.append(Spacer(1, 0.1*inch))
    
    line_items = [
        ['Description', 'Quantity', 'Unit Price', 'Total'],
        ['Front right quarter panel (OEM)', '1', '$850.00', '$850.00'],
        ['Front right door assembly (OEM)', '1', '$1,200.00', '$1,200.00'],
        ['Front right wheel rim (OEM)', '1', '$320.00', '$320.00'],
        ['Front right tire replacement', '1', '$180.00', '$180.00'],
        ['Headlight assembly (OEM)', '1', '$450.00', '$450.00'],
        ['Control arm replacement', '1', '$280.00', '$280.00'],
        ['Strut assembly replacement', '1', '$380.00', '$380.00'],
        ['Paint and color matching (3 panels)', '1', '$1,800.00', '$1,800.00'],
        ['Frame alignment and inspection', '1', '$400.00', '$400.00'],
        ['Labor - body work and assembly', '28 hrs', '$95.00', '$2,660.00'],
        ['Diagnostic and teardown', '1', '$250.00', '$250.00'],
        ['', '', '<b>Subtotal:</b>', '<b>$8,770.00</b>'],
        ['', '', '<b>Tax (6.25%):</b>', '<b>$548.13</b>'],
        ['', '', '<b>TOTAL:</b>', '<b>$9,318.13</b>']
    ]
    
    items_table = Table(line_items, colWidths=[3*inch, 1*inch, 1.2*inch, 1.2*inch])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -4), 1, colors.black),
        ('LINEABOVE', (2, -3), (-1, -3), 2, colors.black),
        ('LINEABOVE', (2, -1), (-1, -1), 2, colors.black),
        ('ALIGN', (2, -3), (-1, -1), 'RIGHT'),
    ]))
    story.append(items_table)
    story.append(Spacer(1, 0.3*inch))
    
    story.append(Paragraph("<b>NOTES:</b> All OEM parts used. Estimated repair time: 7-10 business days. " +
                          "Supplemental estimate may be required upon teardown if additional damage discovered.", 
                          styles['Normal']))
    
    doc.build(story)
    print("Created case_c/invoice.pdf")


if __name__ == "__main__":
    print("Generating sample case PDF files...")
    print("\nCase A - Burst Pipe:")
    create_fnol_case_a()
    create_invoice_case_a()
    
    print("\nCase B - Seepage:")
    create_fnol_case_b()
    create_invoice_case_b()
    
    print("\nCase C - Auto Collision:")
    create_fnol_case_c()
    create_invoice_case_c()
    
    print("\n✓ All PDF files created successfully!")
    print("\nNote: You still need to add photo files to each case directory:")
    print("  - case_a/photo_*.jpg (bathroom/kitchen water damage)")
    print("  - case_b/photo_*.jpg (basement wall staining)")
    print("  - case_c/photo_*.jpg (vehicle collision damage)")
