"""Script to create sample policy documents for testing."""

import sys
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def create_ho3_policy(output_path: str):
    """
    Create a sample HO-3 (Homeowners) policy document.
    
    Args:
        output_path: Path where PDF will be saved
    """
    doc = SimpleDocTemplate(output_path, pagesize=letter)
    story = []
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        textColor='darkblue',
        spaceAfter=30,
        alignment=TA_CENTER
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor='darkblue',
        spaceAfter=12,
        spaceBefore=12
    )
    
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['BodyText'],
        fontSize=10,
        alignment=TA_JUSTIFY,
        spaceAfter=12
    )
    
    # Title
    story.append(Paragraph("HOMEOWNERS INSURANCE POLICY", title_style))
    story.append(Paragraph("HO-3 Special Form", styles['Heading2']))
    story.append(Spacer(1, 0.2*inch))
    
    # Policy Information
    story.append(Paragraph("POLICY NUMBER: HO3-2024-001234", body_style))
    story.append(Paragraph("EFFECTIVE DATE: January 1, 2024", body_style))
    story.append(Spacer(1, 0.3*inch))
    
    # Section I - Property Coverages
    story.append(Paragraph("SECTION I - PROPERTY COVERAGES", heading_style))
    
    story.append(Paragraph("COVERAGE A - Dwelling", styles['Heading3']))
    story.append(Paragraph(
        "We cover the dwelling on the residence premises shown in the Declarations, including structures "
        "attached to the dwelling, and materials and supplies located on or next to the residence premises "
        "used to construct, alter or repair the dwelling or other structures on the residence premises.",
        body_style
    ))
    
    story.append(Paragraph("COVERAGE B - Other Structures", styles['Heading3']))
    story.append(Paragraph(
        "We cover other structures on the residence premises set apart from the dwelling by clear space. "
        "This includes structures connected to the dwelling by only a fence, utility line, or similar connection. "
        "This coverage is 10% of the limit of liability that applies to Coverage A.",
        body_style
    ))
    
    story.append(Paragraph("COVERAGE C - Personal Property", styles['Heading3']))
    story.append(Paragraph(
        "We cover personal property owned or used by an insured while it is anywhere in the world. "
        "At your request, we will cover personal property owned by others while the property is on the part "
        "of the residence premises occupied by an insured. This coverage is 50% of the limit of liability "
        "that applies to Coverage A.",
        body_style
    ))
    
    story.append(Paragraph("COVERAGE D - Loss of Use", styles['Heading3']))
    story.append(Paragraph(
        "The limit of liability for Coverage D is the total limit for the coverages in 1. Additional Living "
        "Expense, 2. Fair Rental Value, and 3. Civil Authority Prohibits Use below. This coverage is 30% "
        "of the limit of liability that applies to Coverage A.",
        body_style
    ))
    
    story.append(PageBreak())
    
    # Section I - Perils Insured Against
    story.append(Paragraph("SECTION I - PERILS INSURED AGAINST", heading_style))
    
    story.append(Paragraph("COVERAGE A - DWELLING and COVERAGE B - OTHER STRUCTURES", styles['Heading3']))
    story.append(Paragraph(
        "We insure against risk of direct physical loss to property described in Coverages A and B.",
        body_style
    ))
    
    story.append(Paragraph("We do not insure, however, for loss:", body_style))
    
    exclusions = [
        "1. Excluded under Section I - Exclusions;",
        "2. Involving collapse, except as provided in Section I - Additional Coverage - Collapse;",
        "3. Caused by:",
        "   a. Freezing of a plumbing, heating, air conditioning or automatic fire protective sprinkler system "
        "or of a household appliance, or by discharge, leakage or overflow from within the system or appliance "
        "caused by freezing. This exclusion applies only while the dwelling is vacant, unoccupied or being constructed;",
        "   b. Freezing, thawing, pressure or weight of water or ice, whether driven by wind or not, to a:",
        "      (1) Fence, pavement, patio or swimming pool;",
        "      (2) Footing, foundation, bulkhead, wall, or any other structure or device that supports all or part "
        "of a building, or other structure;",
        "      (3) Retaining wall or bulkhead that does not support all or part of a building or other structure;",
        "   c. Theft in or to a dwelling under construction, or of materials and supplies for use in the construction "
        "until the dwelling is finished and occupied;",
        "   d. Vandalism and malicious mischief, and any ensuing loss caused by any intentional and wrongful act "
        "committed in the course of the vandalism or malicious mischief, if the dwelling has been vacant for more "
        "than 60 consecutive days immediately before the loss."
    ]
    
    for exclusion in exclusions:
        story.append(Paragraph(exclusion, body_style))
    
    story.append(PageBreak())
    
    # Section I - Exclusions
    story.append(Paragraph("SECTION I - EXCLUSIONS", heading_style))
    
    story.append(Paragraph(
        "We do not insure for loss caused directly or indirectly by any of the following. Such loss is excluded "
        "regardless of any other cause or event contributing concurrently or in any sequence to the loss.",
        body_style
    ))
    
    major_exclusions = [
        ("1. Ordinance or Law", 
         "Ordinance Or Law means any ordinance or law requiring or regulating the construction, demolition, "
         "remodeling, renovation or repair of property, including removal of any resulting debris."),
        
        ("2. Earth Movement",
         "Earth Movement means earthquake including land shock waves or tremors before, during or after a volcanic "
         "eruption; landslide; mudslide; mudflow; earth sinking, rising or shifting; mine subsidence; or any other "
         "earth movement including earth sinking, rising or shifting caused by human activity."),
        
        ("3. Water Damage",
         "Water Damage means: a. Flood, surface water, waves, tidal water, overflow of a body of water, or spray "
         "from any of these, whether or not driven by wind; b. Water or water-borne material which backs up through "
         "sewers or drains or which overflows or is discharged from a sump, sump pump or related equipment; or "
         "c. Water or water-borne material below the surface of the ground, including water which exerts pressure "
         "on or seeps or leaks through a building, sidewalk, driveway, foundation, swimming pool or other structure."),
        
        ("4. Power Failure",
         "Power Failure means the failure of power or other utility service if the failure takes place off the "
         "residence premises. But if the failure results in a loss, from a Peril Insured Against on the residence "
         "premises, we will pay for the loss caused by that peril."),
        
        ("5. Neglect",
         "Neglect means neglect of an insured to use all reasonable means to save and preserve property at and "
         "after the time of a loss."),
        
        ("6. War",
         "War includes the following and any consequence of any of the following: a. Undeclared war, civil war, "
         "insurrection, rebellion or revolution; b. Warlike act by a military force or military personnel; or "
         "c. Destruction, seizure or use for a military purpose."),
        
        ("7. Nuclear Hazard",
         "Nuclear Hazard means any nuclear reaction, radiation, or radioactive contamination, all whether controlled "
         "or uncontrolled or however caused, or any consequence of any of these."),
        
        ("8. Intentional Loss",
         "Intentional Loss means any loss arising out of any act an insured commits or conspires to commit with "
         "the intent to cause a loss.")
    ]
    
    for title, description in major_exclusions:
        story.append(Paragraph(title, styles['Heading3']))
        story.append(Paragraph(description, body_style))
    
    story.append(PageBreak())
    
    # Section I - Conditions
    story.append(Paragraph("SECTION I - CONDITIONS", heading_style))
    
    story.append(Paragraph("A. Insurable Interest and Limit of Liability", styles['Heading3']))
    story.append(Paragraph(
        "Even if more than one person has an insurable interest in the property covered, we will not be liable "
        "in any one loss: 1. To an insured for more than the amount of such insured's interest at the time of loss; or "
        "2. For more than the applicable limit of liability.",
        body_style
    ))
    
    story.append(Paragraph("B. Duties After Loss", styles['Heading3']))
    story.append(Paragraph(
        "In case of a loss to covered property, we have no duty to provide coverage under this policy if the failure "
        "to comply with the following duties is prejudicial to us. These duties must be performed either by you, "
        "an insured or a representative of either:",
        body_style
    ))
    
    duties = [
        "1. Give prompt notice to us or our agent;",
        "2. Notify the police in case of loss by theft;",
        "3. Notify the credit card or electronic fund transfer card company in case of loss under Credit Card, "
        "Electronic Fund Transfer Card or Forgery and Counterfeit Money coverage;",
        "4. Protect the property from further damage. If repairs to the property are required, you must make "
        "reasonable and necessary repairs to protect the property;",
        "5. Cooperate with us in the investigation of a claim;",
        "6. Prepare an inventory of damaged personal property showing the quantity, description, actual cash value "
        "and amount of loss;",
        "7. As often as we reasonably require: a. Show the damaged property; b. Provide us with records and documents "
        "we request and permit us to make copies; and c. Submit to examination under oath;",
        "8. Send to us, within 60 days after our request, your signed, sworn proof of loss which sets forth, to the "
        "best of your knowledge and belief: a. The time and cause of loss; b. The interests of the insured and all "
        "others in the property involved and all liens on the property; c. Other insurance which may cover the loss; "
        "d. Changes in title or occupancy of the property during the term of the policy; e. Specifications of damaged "
        "buildings and detailed repair estimates; f. The inventory of damaged personal property; g. Receipts for "
        "additional living expenses incurred and records that support the fair rental value loss; and h. Evidence or "
        "affidavit that supports a claim under Credit Card, Electronic Fund Transfer Card or Forgery and Counterfeit "
        "Money coverage."
    ]
    
    for duty in duties:
        story.append(Paragraph(duty, body_style))
    
    story.append(PageBreak())
    
    # Additional Coverage - Water Backup
    story.append(Paragraph("ADDITIONAL COVERAGE - WATER BACKUP OF SEWERS AND DRAINS", heading_style))
    story.append(Paragraph(
        "We will pay for direct physical loss to property covered under Coverage A, Coverage B and Coverage C caused "
        "by water or waterborne material which backs up through sewers or drains or which overflows or is discharged "
        "from a sump, sump pump or related equipment. The most we will pay under this Additional Coverage for any one "
        "loss is $10,000.",
        body_style
    ))
    
    story.append(Paragraph(
        "This Additional Coverage does not increase the limit of liability applying to the damaged property.",
        body_style
    ))
    
    # Burst Pipe Coverage
    story.append(Paragraph("COVERAGE FOR BURST PIPES", heading_style))
    story.append(Paragraph(
        "We cover sudden and accidental discharge or leakage of water or steam as the direct result of the breaking "
        "apart or cracking of a plumbing, heating, air conditioning or automatic fire protective sprinkler system or "
        "household appliance. This includes the cost to tear out and replace any part of a building necessary to "
        "repair the system or appliance from which the water or steam escaped.",
        body_style
    ))
    
    story.append(Paragraph(
        "We do not cover loss: 1. On the residence premises if the dwelling has been vacant for more than 60 "
        "consecutive days immediately before the loss; 2. To the system or appliance from which the water or steam "
        "escaped; 3. Caused by or resulting from freezing; or 4. On the residence premises caused by accidental "
        "discharge or leakage which occurs off the residence premises.",
        body_style
    ))
    
    # Build PDF
    doc.build(story)
    print(f"Created HO-3 policy document: {output_path}")


def create_pap_policy(output_path: str):
    """
    Create a sample PAP (Personal Auto Policy) document.
    
    Args:
        output_path: Path where PDF will be saved
    """
    doc = SimpleDocTemplate(output_path, pagesize=letter)
    story = []
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        textColor='darkblue',
        spaceAfter=30,
        alignment=TA_CENTER
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor='darkblue',
        spaceAfter=12,
        spaceBefore=12
    )
    
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['BodyText'],
        fontSize=10,
        alignment=TA_JUSTIFY,
        spaceAfter=12
    )
    
    # Title
    story.append(Paragraph("PERSONAL AUTO POLICY", title_style))
    story.append(Paragraph("PAP Standard Form", styles['Heading2']))
    story.append(Spacer(1, 0.2*inch))
    
    # Policy Information
    story.append(Paragraph("POLICY NUMBER: PAP-2024-567890", body_style))
    story.append(Paragraph("EFFECTIVE DATE: January 1, 2024", body_style))
    story.append(Spacer(1, 0.3*inch))
    
    # Agreement and Definitions
    story.append(Paragraph("AGREEMENT AND DEFINITIONS", heading_style))
    story.append(Paragraph(
        "In return for payment of the premium and subject to all the terms of this policy, we agree with you as follows:",
        body_style
    ))
    
    story.append(Paragraph("DEFINITIONS", styles['Heading3']))
    
    definitions = [
        ("A. You and Your", "mean the named insured shown in the Declarations and the spouse if a resident of the same household."),
        ("B. We, Us and Our", "mean the Company providing this insurance."),
        ("C. Bodily Injury", "means bodily harm, sickness or disease, including death that results."),
        ("D. Business", "includes trade, profession or occupation."),
        ("E. Family Member", "means a person related to you by blood, marriage or adoption who is a resident of your household."),
        ("F. Occupying", "means in, upon, getting in, on, out or off."),
        ("G. Property Damage", "means physical injury to, destruction of or loss of use of tangible property."),
        ("H. Trailer", "means a vehicle designed to be pulled by a private passenger auto, pickup or van."),
        ("I. Your Covered Auto", "means any vehicle shown in the Declarations, a newly acquired auto, a trailer you own, or a temporary substitute auto.")
    ]
    
    for term, definition in definitions:
        story.append(Paragraph(f"<b>{term}</b>: {definition}", body_style))
    
    story.append(PageBreak())
    
    # Part A - Liability Coverage
    story.append(Paragraph("PART A - LIABILITY COVERAGE", heading_style))
    
    story.append(Paragraph("INSURING AGREEMENT", styles['Heading3']))
    story.append(Paragraph(
        "A. We will pay damages for bodily injury or property damage for which any insured becomes legally responsible "
        "because of an auto accident. Damages include prejudgment interest awarded against the insured. We will settle "
        "or defend, as we consider appropriate, any claim or suit asking for these damages. In addition to our limit of "
        "liability, we will pay all defense costs we incur. Our duty to settle or defend ends when our limit of liability "
        "for this coverage has been exhausted by payment of judgments or settlements. We have no duty to defend any suit "
        "or settle any claim for bodily injury or property damage not covered under this policy.",
        body_style
    ))
    
    story.append(Paragraph("B. Insured as used in this Part means:", body_style))
    insureds = [
        "1. You or any family member for the ownership, maintenance or use of any auto or trailer.",
        "2. Any person using your covered auto.",
        "3. For your covered auto, any person or organization but only with respect to legal responsibility for acts "
        "or omissions of a person for whom coverage is afforded under this Part.",
        "4. For any auto or trailer, other than your covered auto, any other person or organization but only with "
        "respect to legal responsibility for acts or omissions of you or any family member for whom coverage is "
        "afforded under this Part."
    ]
    
    for insured in insureds:
        story.append(Paragraph(insured, body_style))
    
    story.append(PageBreak())
    
    # Part A - Exclusions
    story.append(Paragraph("EXCLUSIONS", styles['Heading3']))
    story.append(Paragraph("A. We do not provide Liability Coverage for any insured:", body_style))
    
    exclusions = [
        "1. Who intentionally causes bodily injury or property damage.",
        "2. For property damage to property owned or being transported by that insured.",
        "3. For property damage to property rented to, used by or in the care of that insured.",
        "4. For bodily injury to an employee of that insured during the course of employment.",
        "5. For that insured's liability arising out of the ownership or operation of a vehicle while it is being "
        "used as a public or livery conveyance.",
        "6. While employed or otherwise engaged in the business of selling, repairing, servicing, storing or parking "
        "vehicles designed for use mainly on public highways.",
        "7. Maintaining or using any vehicle while that person is employed or otherwise engaged in any business "
        "(other than farming or ranching) not described in Exclusion A.6.",
        "8. Using a vehicle without a reasonable belief that that person is entitled to do so.",
        "9. For bodily injury or property damage for which that insured is an insured under a nuclear energy liability policy."
    ]
    
    for exclusion in exclusions:
        story.append(Paragraph(exclusion, body_style))
    
    story.append(PageBreak())
    
    # Part D - Coverage for Damage to Your Auto
    story.append(Paragraph("PART D - COVERAGE FOR DAMAGE TO YOUR AUTO", heading_style))
    
    story.append(Paragraph("INSURING AGREEMENT", styles['Heading3']))
    story.append(Paragraph(
        "A. We will pay for direct and accidental loss to your covered auto or any non-owned auto, including their "
        "equipment, minus any applicable deductible shown in the Declarations. If loss to more than one your covered "
        "auto or non-owned auto results from the same collision, only the highest applicable deductible will apply. "
        "We will pay for loss to your covered auto caused by:",
        body_style
    ))
    
    story.append(Paragraph("1. Other than collision only if the Declarations indicate that Other Than Collision "
                          "Coverage is provided for that auto.", body_style))
    story.append(Paragraph("2. Collision only if the Declarations indicate that Collision Coverage is provided for "
                          "that auto.", body_style))
    
    story.append(Paragraph(
        "If there is a loss to a non-owned auto, we will provide the broadest coverage applicable to any your covered auto "
        "shown in the Declarations.",
        body_style
    ))
    
    story.append(Paragraph("TRANSPORTATION EXPENSES", styles['Heading3']))
    story.append(Paragraph(
        "A. In addition, we will pay, without application of a deductible, up to $30 per day to a maximum of $900 for:",
        body_style
    ))
    
    transport_expenses = [
        "1. Temporary transportation expenses not exceeding the amount stated above incurred by you in the event of a "
        "loss to your covered auto. We will pay for such expenses if the loss is caused by:",
        "   a. Other than collision only if the Declarations indicate that Other Than Collision Coverage is provided "
        "for that auto.",
        "   b. Collision only if the Declarations indicate that Collision Coverage is provided for that auto.",
        "2. Expenses for which you become legally responsible in the event of loss to a non-owned auto. We will pay "
        "for such expenses if the loss is caused by:",
        "   a. Other than collision only if the Declarations indicate that Other Than Collision Coverage is provided "
        "for any your covered auto.",
        "   b. Collision only if the Declarations indicate that Collision Coverage is provided for any your covered auto."
    ]
    
    for expense in transport_expenses:
        story.append(Paragraph(expense, body_style))
    
    story.append(PageBreak())
    
    # Part D - Exclusions
    story.append(Paragraph("EXCLUSIONS", styles['Heading3']))
    story.append(Paragraph("We will not pay for:", body_style))
    
    part_d_exclusions = [
        "1. Loss to your covered auto or any non-owned auto which occurs while it is being used as a public or livery "
        "conveyance.",
        "2. Damage due and confined to wear and tear, freezing, mechanical or electrical breakdown or failure, or road "
        "damage to tires.",
        "3. Loss due to or as a consequence of radioactive contamination, discharge of any nuclear weapon, nuclear "
        "reaction, radiation, or radioactive contamination.",
        "4. Loss to any electronic equipment designed for the reproduction of sound, including any accessories used with "
        "such equipment.",
        "5. Loss to tapes, records, discs or other media used with equipment described in Exclusion 4.",
        "6. A total loss to your covered auto or any non-owned auto due to destruction or confiscation by governmental "
        "or civil authorities.",
        "7. Loss to a non-owned auto when used by you or any family member without a reasonable belief that you or that "
        "family member are entitled to do so.",
        "8. Loss to equipment designed or used for the detection or location of radar or laser.",
        "9. Loss to any custom furnishings or equipment in or upon any pickup or van.",
        "10. Loss to any non-owned auto being maintained or used by any person while employed or otherwise engaged in "
        "the business of selling, repairing, servicing, storing or parking vehicles designed for use on public highways."
    ]
    
    for exclusion in part_d_exclusions:
        story.append(Paragraph(exclusion, body_style))
    
    story.append(PageBreak())
    
    # Part D - Limit of Liability
    story.append(Paragraph("LIMIT OF LIABILITY", styles['Heading3']))
    story.append(Paragraph(
        "A. Our limit of liability for loss will be the lesser of the:",
        body_style
    ))
    
    limits = [
        "1. Actual cash value of the stolen or damaged property; or",
        "2. Amount necessary to repair or replace the property with other property of like kind and quality.",
        "",
        "However, the most we will pay for loss to:",
        "",
        "1. Any non-owned auto which is a trailer is $1,500.",
        "2. Electronic equipment that reproduces, receives or transmits audio, visual or data signals, which is not "
        "designed solely for the reproduction of sound and accessories used with such equipment, is $1,000."
    ]
    
    for limit in limits:
        if limit:
            story.append(Paragraph(limit, body_style))
        else:
            story.append(Spacer(1, 0.1*inch))
    
    story.append(Paragraph(
        "B. An adjustment for depreciation and physical condition will be made in determining actual cash value in the "
        "event of a total loss.",
        body_style
    ))
    
    story.append(Paragraph(
        "C. If a repair or replacement results in better than like kind or quality, we will not pay for the amount of "
        "the betterment.",
        body_style
    ))
    
    # Build PDF
    doc.build(story)
    print(f"Created PAP policy document: {output_path}")


def main():
    """Main entry point."""
    # Ensure data/policies directory exists
    policies_dir = Path("data/policies")
    policies_dir.mkdir(parents=True, exist_ok=True)
    
    print("Creating sample policy documents...")
    print()
    
    # Create HO-3 policy
    ho3_path = policies_dir / "HO3_specimen_policy.pdf"
    create_ho3_policy(str(ho3_path))
    
    # Create PAP policy
    pap_path = policies_dir / "PAP_specimen_policy.pdf"
    create_pap_policy(str(pap_path))
    
    print()
    print("=" * 60)
    print("Sample policy documents created successfully!")
    print("=" * 60)
    print(f"HO-3 Policy: {ho3_path}")
    print(f"PAP Policy: {pap_path}")
    print()
    print("You can now run the index builder:")
    print("  python backend/storage/build_index.py")


if __name__ == "__main__":
    main()
