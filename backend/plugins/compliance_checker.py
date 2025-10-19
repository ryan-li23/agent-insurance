"""Compliance checking plugin for fraud detection and validation."""

import logging
from typing import Dict, Any
from datetime import datetime

from semantic_kernel.functions import kernel_function

logger = logging.getLogger(__name__)


class ComplianceCheckerPlugin:
    """
    Semantic Kernel plugin for compliance checking and fraud detection.
    
    Provides functions for:
    - Timestamp mismatch detection between EXIF data and claim dates
    - Scope creep detection (invoice items vs. claim narrative)
    - Consistency validation across evidence
    """
    
    def __init__(self):
        """Initialize compliance checker plugin."""
        logger.info("Initialized ComplianceCheckerPlugin")
    
    @kernel_function(
        name="check_compliance",
        description=(
            "Perform comprehensive compliance checks on claim evidence. "
            "Detects timestamp mismatches, scope creep, and other inconsistencies. "
            "Returns a compliance report with findings and risk flags."
        )
    )
    def check_compliance(
        self,
        claim_data: Dict[str, Any],
        evidence_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Perform comprehensive compliance checks.
        
        Args:
            claim_data: Dictionary with claim information:
                - loss_date: Date of loss (ISO format or datetime)
                - fnol_date: First notice of loss date
                - claim_description: Narrative description of claim
                - policy_type: Policy type
            evidence_data: Dictionary with evidence:
                - images: List of image metadata dicts with timestamps
                - invoices: List of invoice dicts
                - documents: List of document metadata
                
        Returns:
            Dictionary containing:
                - compliant: Overall compliance status (bool)
                - risk_level: "low", "medium", or "high"
                - findings: List of finding dicts with type, severity, description
                - timestamp_check: Results of timestamp validation
                - scope_check: Results of scope validation
                - consistency_check: Results of consistency validation
        """
        logger.info("Performing compliance checks on claim evidence")
        
        findings = []
        
        # Check timestamps
        timestamp_results = self.check_timestamp_consistency(
            claim_data=claim_data,
            evidence_data=evidence_data
        )
        findings.extend(timestamp_results.get('findings', []))
        
        # Check scope
        scope_results = self.check_scope_creep(
            claim_data=claim_data,
            evidence_data=evidence_data
        )
        findings.extend(scope_results.get('findings', []))
        
        # Check consistency
        consistency_results = self.check_evidence_consistency(
            evidence_data=evidence_data
        )
        findings.extend(consistency_results.get('findings', []))
        
        # Determine overall compliance and risk level
        high_severity_count = sum(1 for f in findings if f.get('severity') == 'high')
        medium_severity_count = sum(1 for f in findings if f.get('severity') == 'medium')
        
        if high_severity_count > 0:
            risk_level = "high"
            compliant = False
        elif medium_severity_count > 1:
            risk_level = "medium"
            compliant = False
        elif medium_severity_count == 1:
            risk_level = "medium"
            compliant = True
        else:
            risk_level = "low"
            compliant = True
        
        report = {
            'compliant': compliant,
            'risk_level': risk_level,
            'findings': findings,
            'findings_count': len(findings),
            'timestamp_check': timestamp_results,
            'scope_check': scope_results,
            'consistency_check': consistency_results
        }
        
        logger.info(
            f"Compliance check complete: compliant={compliant}, "
            f"risk_level={risk_level}, findings={len(findings)}"
        )
        
        return report
    
    @kernel_function(
        name="check_timestamp_consistency",
        description=(
            "Check for timestamp mismatches between image EXIF data and claim dates. "
            "Detects images taken before loss date or significantly after, "
            "which may indicate fraud or misrepresentation."
        )
    )
    def check_timestamp_consistency(
        self,
        claim_data: Dict[str, Any],
        evidence_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Check timestamp consistency across evidence.
        
        Args:
            claim_data: Claim information with loss_date
            evidence_data: Evidence with image timestamps
            
        Returns:
            Dictionary with timestamp check results
        """
        findings = []
        
        loss_date_str = claim_data.get('loss_date')
        if not loss_date_str:
            return {
                'status': 'skipped',
                'reason': 'No loss date provided',
                'findings': []
            }
        
        # Parse loss date
        try:
            loss_date = self._parse_date(loss_date_str)
        except Exception as e:
            logger.warning(f"Failed to parse loss date: {loss_date_str}, error: {e}")
            return {
                'status': 'error',
                'reason': f'Invalid loss date format: {loss_date_str}',
                'findings': []
            }
        
        # Check image timestamps
        images = evidence_data.get('images', [])
        missing_exif_count = 0
        
        for i, image in enumerate(images):
            image_name = image.get('image_name', f'image_{i}')
            timestamp_str = image.get('timestamp')
            
            if not timestamp_str:
                missing_exif_count += 1
                # Missing EXIF is informational only - not automatically suspicious
                findings.append({
                    'type': 'missing_exif_timestamp',
                    'severity': 'info',  # Changed from 'low' to 'info'
                    'description': (
                        f"Image '{image_name}' has no EXIF timestamp. "
                        f"This is common for processed/edited images and not inherently suspicious."
                    ),
                    'image': image_name,
                    'note': 'Consider in context with other evidence'
                })
                continue
            
            try:
                image_date = self._parse_date(timestamp_str)
                
                # Calculate time difference
                time_diff = image_date - loss_date
                days_diff = time_diff.days
                hours_diff = time_diff.total_seconds() / 3600
                
                # Check if image was taken significantly before loss date
                # Allow same day or minor differences due to timezone/clock issues
                if days_diff < -1:  # More than 1 day before
                    findings.append({
                        'type': 'timestamp_before_loss',
                        'severity': 'high',
                        'description': (
                            f"Image '{image_name}' was taken {abs(days_diff)} days "
                            f"before the reported loss date. This requires investigation."
                        ),
                        'image': image_name,
                        'image_date': timestamp_str,
                        'loss_date': loss_date_str,
                        'days_difference': abs(days_diff)
                    })
                
                # Check if image was taken on same day or shortly after (normal)
                elif -1 <= days_diff <= 7:
                    # This is normal - photos taken around the time of loss
                    # No finding needed, this is expected
                    pass
                
                # Check if image was taken significantly after loss date
                elif days_diff > 90:
                    findings.append({
                        'type': 'timestamp_long_after_loss',
                        'severity': 'medium',
                        'description': (
                            f"Image '{image_name}' was taken {days_diff} days "
                            f"after the reported loss date. May indicate pre-existing damage."
                        ),
                        'image': image_name,
                        'image_date': timestamp_str,
                        'loss_date': loss_date_str,
                        'days_difference': days_diff
                    })
                
            except Exception as e:
                logger.warning(f"Failed to parse image timestamp: {timestamp_str}, error: {e}")
                findings.append({
                    'type': 'invalid_timestamp',
                    'severity': 'info',
                    'description': f"Image '{image_name}' has invalid timestamp format",
                    'image': image_name
                })
        
        # Add summary note if all images lack EXIF
        if missing_exif_count == len(images) and len(images) > 0:
            findings.append({
                'type': 'all_images_missing_exif',
                'severity': 'low',  # Only low severity, not blocking
                'description': (
                    f"All {len(images)} images lack EXIF timestamps. "
                    f"While not inherently suspicious, consider this in context with other evidence."
                ),
                'note': 'Evaluate based on totality of evidence'
            })
        
        return {
            'status': 'completed',
            'images_checked': len(images),
            'findings': findings
        }
    
    @kernel_function(
        name="check_scope_creep",
        description=(
            "Detect scope creep by comparing invoice line items against claim narrative. "
            "Identifies work or materials that don't match the reported damage, "
            "which may indicate fraudulent billing."
        )
    )
    def check_scope_creep(
        self,
        claim_data: Dict[str, Any],
        evidence_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Check for scope creep in invoices.
        
        Args:
            claim_data: Claim information with claim_description
            evidence_data: Evidence with invoice data
            
        Returns:
            Dictionary with scope check results
        """
        findings = []
        
        claim_description = claim_data.get('claim_description', '').lower()
        if not claim_description:
            return {
                'status': 'skipped',
                'reason': 'No claim description provided',
                'findings': []
            }
        
        # Extract damage types from claim description
        damage_keywords = self._extract_damage_keywords(claim_description)
        
        # Check invoices
        invoices = evidence_data.get('invoices', [])
        for invoice in invoices:
            vendor = invoice.get('vendor', 'Unknown')
            line_items = invoice.get('line_items', [])
            
            for item in line_items:
                description = item.get('description', '').lower()
                category = item.get('category', 'other').lower()
                amount = item.get('amount', 0)
                
                # Check for unrelated work
                if self._is_unrelated_work(description, category, damage_keywords):
                    findings.append({
                        'type': 'scope_creep',
                        'severity': 'high',
                        'description': (
                            f"Invoice item '{item.get('description')}' from {vendor} "
                            f"does not match reported damage type"
                        ),
                        'vendor': vendor,
                        'item_description': item.get('description'),
                        'item_category': category,
                        'amount': amount,
                        'claim_damage_types': list(damage_keywords)
                    })
                
                # Check for excessive amounts
                # Safely format amount for display
                try:
                    amount_display = float(amount) if amount is not None else 0.0
                except (ValueError, TypeError):
                    amount_display = 0.0
                    
                if amount_display > 10000:
                    findings.append({
                        'type': 'high_value_item',
                        'severity': 'medium',
                        'description': (
                            f"High-value line item (${amount_display:.2f}) from {vendor} "
                            f"requires additional scrutiny"
                        ),
                        'vendor': vendor,
                        'item_description': item.get('description'),
                        'amount': amount
                    })
        
        return {
            'status': 'completed',
            'invoices_checked': len(invoices),
            'damage_keywords': list(damage_keywords),
            'findings': findings
        }
    
    @kernel_function(
        name="check_evidence_consistency",
        description=(
            "Check for internal consistency across all evidence. "
            "Validates that observations, invoices, and documents tell a coherent story."
        )
    )
    def check_evidence_consistency(
        self,
        evidence_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Check consistency across evidence.
        
        Args:
            evidence_data: All evidence data
            
        Returns:
            Dictionary with consistency check results
        """
        findings = []
        
        # Check for missing evidence types
        has_images = len(evidence_data.get('images', [])) > 0
        has_invoices = len(evidence_data.get('invoices', [])) > 0
        has_documents = len(evidence_data.get('documents', [])) > 0
        
        if not has_images:
            findings.append({
                'type': 'missing_evidence',
                'severity': 'medium',
                'description': 'No damage photos provided with claim'
            })
        
        if has_invoices and not has_images:
            findings.append({
                'type': 'inconsistent_evidence',
                'severity': 'high',
                'description': 'Invoices provided without supporting damage photos'
            })
        
        # Check for duplicate invoices
        invoices = evidence_data.get('invoices', [])
        invoice_numbers = [inv.get('invoice_number') for inv in invoices if inv.get('invoice_number')]
        if len(invoice_numbers) != len(set(invoice_numbers)):
            findings.append({
                'type': 'duplicate_invoices',
                'severity': 'medium',
                'description': 'Duplicate invoice numbers detected'
            })
        
        return {
            'status': 'completed',
            'has_images': has_images,
            'has_invoices': has_invoices,
            'has_documents': has_documents,
            'findings': findings
        }
    
    def _parse_date(self, date_str: str) -> datetime:
        """
        Parse date string to datetime object.
        
        Args:
            date_str: Date string in various formats
            
        Returns:
            datetime object
        """
        # Try ISO format first
        try:
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except Exception:
            pass
        
        # Try common formats
        formats = [
            "%Y-%m-%d",
            "%Y/%m/%d",
            "%m/%d/%Y",
            "%d/%m/%Y",
            "%Y-%m-%d %H:%M:%S",
            "%Y/%m/%d %H:%M:%S"
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except Exception:
                continue
        
        raise ValueError(f"Unable to parse date: {date_str}")
    
    def _extract_damage_keywords(self, description: str) -> set:
        """
        Extract damage-related keywords from claim description.
        
        Args:
            description: Claim description text
            
        Returns:
            Set of damage keywords
        """
        keywords = set()
        
        damage_patterns = {
            'water': ['water', 'flood', 'leak', 'moisture', 'wet', 'plumbing'],
            'fire': ['fire', 'smoke', 'burn', 'flame', 'soot'],
            'wind': ['wind', 'storm', 'hurricane', 'tornado', 'hail'],
            'roof': ['roof', 'shingle', 'gutter', 'flashing'],
            'structural': ['structural', 'foundation', 'wall', 'ceiling', 'floor'],
            'mold': ['mold', 'mildew', 'fungus'],
            'theft': ['theft', 'burglary', 'stolen', 'break-in'],
            'vandalism': ['vandalism', 'graffiti', 'damage'],
            'collision': ['collision', 'impact', 'crash', 'hit']
        }
        
        for category, patterns in damage_patterns.items():
            for pattern in patterns:
                if pattern in description:
                    keywords.add(category)
                    break
        
        return keywords
    
    def _is_unrelated_work(
        self,
        item_description: str,
        item_category: str,
        damage_keywords: set
    ) -> bool:
        """
        Check if invoice item is unrelated to reported damage.
        
        Args:
            item_description: Line item description
            item_category: Line item category
            damage_keywords: Set of damage keywords from claim
            
        Returns:
            True if item appears unrelated
        """
        if not damage_keywords:
            return False
        
        # Map categories to damage types
        category_damage_map = {
            'roofing': {'roof', 'wind', 'fire'},
            'plumbing': {'water'},
            'electrical': {'fire'},
            'hvac': {'fire', 'water'},
            'flooring': {'water', 'fire', 'structural'},
            'drywall': {'water', 'fire', 'structural', 'mold'},
            'painting': {'water', 'fire', 'smoke', 'mold'},
            'carpentry': {'structural', 'wind', 'water'},
            'masonry': {'structural', 'fire'},
            'cleaning': {'fire', 'smoke', 'water', 'mold'}
        }
        
        # Check if category matches damage type
        for cat, related_damages in category_damage_map.items():
            if cat in item_category or cat in item_description:
                if damage_keywords & related_damages:
                    return False
        
        # Check for suspicious unrelated items
        unrelated_patterns = [
            'upgrade', 'remodel', 'renovation', 'addition',
            'landscaping', 'pool', 'deck', 'patio',
            'appliance', 'furniture', 'electronics'
        ]
        
        for pattern in unrelated_patterns:
            if pattern in item_description:
                return True
        
        return False
