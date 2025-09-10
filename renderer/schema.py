#!/usr/bin/env python3
"""
calm.profile report schema and field mapping
defines all template fields and converts camelCase to snake_case
"""

from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

# Template field definitions in snake_case
TEMPLATE_FIELDS = {
    # Basic metadata
    "company_name": str,
    "assessment_date": str,
    "report_id": str,
    "assessment_id": str,
    "completion_date": str,
    "customer_email": str,
    # Archetype data
    "archetype_primary": str,
    "archetype_confidence": float,
    "archetype_tagline": str,
    "archetype_mix_primary": float,
    "archetype_mix_secondary": float,
    "archetype_mix_tertiary": float,
    "archetype_mix_quaternary": float,
    "archetype_secondary": str,
    "archetype_tertiary": str,
    "archetype_quaternary": str,
    # Axis scores
    "axis_structure": int,
    "axis_collaboration": int,
    "axis_scope": int,
    "axis_tempo": int,
    # Metrics
    "overhead_percentage": float,
    "annual_cost": float,
    "weekly_cost": float,
    "hours_lost_ppw": float,
    # Context data
    "team_size": int,
    "meeting_load": str,
    "hourly_rate": float,
    "platform": str,
    # Recommendations (rice scores)
    "r1_title": str,
    "r1_description": str,
    "r1_effort": str,
    "r1_impact": str,
    "r1_timeline": str,
    "r1_rice": int,
    "r1_linked_finding": str,
    "r2_title": str,
    "r2_description": str,
    "r2_effort": str,
    "r2_impact": str,
    "r2_timeline": str,
    "r2_rice": int,
    "r2_linked_finding": str,
    "r3_title": str,
    "r3_description": str,
    "r3_effort": str,
    "r3_impact": str,
    "r3_timeline": str,
    "r3_rice": int,
    "r3_linked_finding": str,
    "r4_title": str,
    "r4_description": str,
    "r4_effort": str,
    "r4_impact": str,
    "r4_timeline": str,
    "r4_rice": int,
    "r4_linked_finding": str,
    "r5_title": str,
    "r5_description": str,
    "r5_effort": str,
    "r5_impact": str,
    "r5_timeline": str,
    "r5_rice": int,
    "r5_linked_finding": str,
    # Calculated fields
    "break_even_timeline": str,
    "team_multiplier": int,
    "confidence_score": float,
    "response_count": int,
    # Findings
    "top_findings": list,
    "radar_insights": str,
    # Time breakdown
    "time_productive": int,
    "time_meetings": int,
    "time_admin": int,
    "time_context_switch": int,
    # Workflow data
    "workflow1_r": str,
    "workflow1_a": str,
    "workflow1_s": str,
    "workflow1_c": str,
    "workflow1_i": str,
    "workflow2_r": str,
    "workflow2_a": str,
    "workflow2_s": str,
    "workflow2_c": str,
    "workflow2_i": str,
    "workflow3_r": str,
    "workflow3_a": str,
    "workflow3_s": str,
    "workflow3_c": str,
    "workflow3_i": str,
    "workflow4_r": str,
    "workflow4_a": str,
    "workflow4_s": str,
    "workflow4_c": str,
    "workflow4_i": str,
    "workflow5_r": str,
    "workflow5_a": str,
    "workflow5_s": str,
    "workflow5_c": str,
    "workflow5_i": str,
    # Findings details
    "f1_issue": str,
    "f1_evidence": str,
    "f1_impact": str,
    "f1_root_cause": str,
    "f1_preview": str,
    "f2_issue": str,
    "f2_evidence": str,
    "f2_impact": str,
    "f2_root_cause": str,
    "f2_preview": str,
    "f3_issue": str,
    "f3_evidence": str,
    "f3_impact": str,
    "f3_root_cause": str,
    "f3_preview": str,
    "f4_issue": str,
    "f4_evidence": str,
    "f4_impact": str,
    "f4_root_cause": str,
    "f4_preview": str,
    "f5_issue": str,
    "f5_evidence": str,
    "f5_impact": str,
    "f5_root_cause": str,
    "f5_preview": str,
    # Efficiency metrics
    "efficiency_planning": int,
    "efficiency_execution": int,
    "efficiency_review": int,
    "efficiency_communication": int,
    "workflow_bottlenecks": str,
    # ROI calculations
    "base_overhead": float,
    "archetype_adjustment": float,
    "weekly_cost": float,
    # Sensitivity analysis
    "sensitivity_25_margin": float,
    "sensitivity_25_cost": float,
    "sensitivity_25_hours": float,
    "sensitivity_50_margin": float,
    "sensitivity_50_cost": float,
    "sensitivity_50_hours": float,
    "sensitivity_75_margin": float,
    "sensitivity_75_cost": float,
    "sensitivity_75_hours": float,
    # 5-year projections
    "conservative_5yr": float,
    "realistic_5yr": float,
    "optimistic_5yr": float,
    # Savings projections
    "savings_month1": float,
    "savings_month3": float,
    "savings_month6": float,
    "savings_month12": float,
    # Implementation
    "critical_path": str,
    "milestone_schedule": str,
    "roadmap_30_days": str,
    "roadmap_60_days": str,
    "roadmap_90_days": str,
    # Success metrics
    "baseline_ontime": float,
    "target_ontime": float,
    "owner_ontime": str,
    "baseline_latency": float,
    "target_latency": float,
    "owner_latency": str,
    "baseline_variance": float,
    "target_variance": float,
    "owner_variance": str,
    "baseline_change": float,
    "target_change": float,
    "owner_change": str,
    # Next steps
    "next_steps": str,
}

# CamelCase to snake_case mapping
CAMEL_TO_SNAKE_MAP = {
    # Basic metadata
    "companyName": "company_name",
    "assessmentDate": "assessment_date",
    "reportId": "report_id",
    "assessmentId": "assessment_id",
    "completionDate": "completion_date",
    "customerEmail": "customer_email",
    # Archetype data
    "archetypePrimary": "archetype_primary",
    "archetypeConfidence": "archetype_confidence",
    "archetypeTagline": "archetype_tagline",
    "archetypeMixPrimary": "archetype_mix_primary",
    "archetypeMixSecondary": "archetype_mix_secondary",
    "archetypeMixTertiary": "archetype_mix_tertiary",
    "archetypeMixQuaternary": "archetype_mix_quaternary",
    "archetypeSecondary": "archetype_secondary",
    "archetypeTertiary": "archetype_tertiary",
    "archetypeQuaternary": "archetype_quaternary",
    # Axis scores
    "axisStructure": "axis_structure",
    "axisCollaboration": "axis_collaboration",
    "axisScope": "axis_scope",
    "axisTempo": "axis_tempo",
    # Metrics
    "overheadPercentage": "overhead_percentage",
    "annualCost": "annual_cost",
    "weeklyCost": "weekly_cost",
    "hoursLostPpw": "hours_lost_ppw",
    # Context data
    "teamSize": "team_size",
    "meetingLoad": "meeting_load",
    "hourlyRate": "hourly_rate",
    # Recommendations
    "r1Title": "r1_title",
    "r1Description": "r1_description",
    "r1Effort": "r1_effort",
    "r1Impact": "r1_impact",
    "r1Timeline": "r1_timeline",
    "r1Rice": "r1_rice",
    "r1LinkedFinding": "r1_linked_finding",
    "r2Title": "r2_title",
    "r2Description": "r2_description",
    "r2Effort": "r2_effort",
    "r2Impact": "r2_impact",
    "r2Timeline": "r2_timeline",
    "r2Rice": "r2_rice",
    "r2LinkedFinding": "r2_linked_finding",
    "r3Title": "r3_title",
    "r3Description": "r3_description",
    "r3Effort": "r3_effort",
    "r3Impact": "r3_impact",
    "r3Timeline": "r3_timeline",
    "r3Rice": "r3_rice",
    "r3LinkedFinding": "r3_linked_finding",
    "r4Title": "r4_title",
    "r4Description": "r4_description",
    "r4Effort": "r4_effort",
    "r4Impact": "r4_impact",
    "r4Timeline": "r4_timeline",
    "r4Rice": "r4_rice",
    "r4LinkedFinding": "r4_linked_finding",
    "r5Title": "r5_title",
    "r5Description": "r5_description",
    "r5Effort": "r5_effort",
    "r5Impact": "r5_impact",
    "r5Timeline": "r5_timeline",
    "r5Rice": "r5_rice",
    "r5LinkedFinding": "r5_linked_finding",
    # Calculated fields
    "breakEvenTimeline": "break_even_timeline",
    "teamMultiplier": "team_multiplier",
    "confidenceScore": "confidence_score",
    "responseCount": "response_count",
    # Findings
    "topFindings": "top_findings",
    "radarInsights": "radar_insights",
    # Time breakdown
    "timeProductive": "time_productive",
    "timeMeetings": "time_meetings",
    "timeAdmin": "time_admin",
    "timeContextSwitch": "time_context_switch",
    # Workflow data
    "workflow1R": "workflow1_r",
    "workflow1A": "workflow1_a",
    "workflow1S": "workflow1_s",
    "workflow1C": "workflow1_c",
    "workflow1I": "workflow1_i",
    "workflow2R": "workflow2_r",
    "workflow2A": "workflow2_a",
    "workflow2S": "workflow2_s",
    "workflow2C": "workflow2_c",
    "workflow2I": "workflow2_i",
    "workflow3R": "workflow3_r",
    "workflow3A": "workflow3_a",
    "workflow3S": "workflow3_s",
    "workflow3C": "workflow3_c",
    "workflow3I": "workflow3_i",
    "workflow4R": "workflow4_r",
    "workflow4A": "workflow4_a",
    "workflow4S": "workflow4_s",
    "workflow4C": "workflow4_c",
    "workflow4I": "workflow4_i",
    "workflow5R": "workflow5_r",
    "workflow5A": "workflow5_a",
    "workflow5S": "workflow5_s",
    "workflow5C": "workflow5_c",
    "workflow5I": "workflow5_i",
    # Findings details
    "f1Issue": "f1_issue",
    "f1Evidence": "f1_evidence",
    "f1Impact": "f1_impact",
    "f1RootCause": "f1_root_cause",
    "f1Preview": "f1_preview",
    "f2Issue": "f2_issue",
    "f2Evidence": "f2_evidence",
    "f2Impact": "f2_impact",
    "f2RootCause": "f2_root_cause",
    "f2Preview": "f2_preview",
    "f3Issue": "f3_issue",
    "f3Evidence": "f3_evidence",
    "f3Impact": "f3_impact",
    "f3RootCause": "f3_root_cause",
    "f3Preview": "f3_preview",
    "f4Issue": "f4_issue",
    "f4Evidence": "f4_evidence",
    "f4Impact": "f4_impact",
    "f4RootCause": "f4_root_cause",
    "f4Preview": "f4_preview",
    "f5Issue": "f5_issue",
    "f5Evidence": "f5_evidence",
    "f5Impact": "f5_impact",
    "f5RootCause": "f5_root_cause",
    "f5Preview": "f5_preview",
    # Efficiency metrics
    "efficiencyPlanning": "efficiency_planning",
    "efficiencyExecution": "efficiency_execution",
    "efficiencyReview": "efficiency_review",
    "efficiencyCommunication": "efficiency_communication",
    "workflowBottlenecks": "workflow_bottlenecks",
    # ROI calculations
    "baseOverhead": "base_overhead",
    "archetypeAdjustment": "archetype_adjustment",
    "weeklyCost": "weekly_cost",
    # Sensitivity analysis
    "sensitivity25Margin": "sensitivity_25_margin",
    "sensitivity25Cost": "sensitivity_25_cost",
    "sensitivity25Hours": "sensitivity_25_hours",
    "sensitivity50Margin": "sensitivity_50_margin",
    "sensitivity50Cost": "sensitivity_50_cost",
    "sensitivity50Hours": "sensitivity_50_hours",
    "sensitivity75Margin": "sensitivity_75_margin",
    "sensitivity75Cost": "sensitivity_75_cost",
    "sensitivity75Hours": "sensitivity_75_hours",
    # 5-year projections
    "conservative5yr": "conservative_5yr",
    "realistic5yr": "realistic_5yr",
    "optimistic5yr": "optimistic_5yr",
    # Savings projections
    "savingsMonth1": "savings_month1",
    "savingsMonth3": "savings_month3",
    "savingsMonth6": "savings_month6",
    "savingsMonth12": "savings_month12",
    # Implementation
    "criticalPath": "critical_path",
    "milestoneSchedule": "milestone_schedule",
    "roadmap30Days": "roadmap_30_days",
    "roadmap60Days": "roadmap_60_days",
    "roadmap90Days": "roadmap_90_days",
    # Success metrics
    "baselineOntime": "baseline_ontime",
    "targetOntime": "target_ontime",
    "ownerOntime": "owner_ontime",
    "baselineLatency": "baseline_latency",
    "targetLatency": "target_latency",
    "ownerLatency": "owner_latency",
    "baselineVariance": "baseline_variance",
    "targetVariance": "target_variance",
    "ownerVariance": "owner_variance",
    "baselineChange": "baseline_change",
    "targetChange": "target_change",
    "ownerChange": "owner_change",
    # Next steps
    "nextSteps": "next_steps",
}


def to_report_fields(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert incoming camelCase payload to snake_case template fields

    Args:
        payload: Dictionary with camelCase keys

    Returns:
        Dictionary with snake_case keys matching template expectations
    """
    normalized = {}

    # Convert camelCase to snake_case
    for camel_key, value in payload.items():
        snake_key = CAMEL_TO_SNAKE_MAP.get(camel_key, camel_key)
        normalized[snake_key] = value

    # Validate that all required template fields are present
    missing_fields = []
    for field_name, field_type in TEMPLATE_FIELDS.items():
        if field_name not in normalized:
            missing_fields.append(field_name)

    if missing_fields:
        logger.warning(f"Missing template fields: {missing_fields}")
        # Add default values for missing fields
        for field_name in missing_fields:
            field_type = TEMPLATE_FIELDS[field_name]
            if field_type == str:
                normalized[field_name] = "—"
            elif field_type in (int, float):
                normalized[field_name] = 0
            elif field_type == list:
                normalized[field_name] = []

    logger.info(f"Normalized {len(normalized)} fields for template rendering")
    return normalized


def validate_template_fields(data: Dict[str, Any]) -> bool:
    """
    Validate that all required template fields are present and correctly typed

    Args:
        data: Dictionary with template field data

    Returns:
        True if validation passes, False otherwise
    """
    missing_fields = []
    type_errors = []

    for field_name, expected_type in TEMPLATE_FIELDS.items():
        if field_name not in data:
            missing_fields.append(field_name)
            continue

        value = data[field_name]

        # Allow int values for float fields (automatic conversion)
        if expected_type == float and isinstance(value, int):
            data[field_name] = float(value)  # Convert int to float
            continue

        if not isinstance(value, expected_type):
            type_errors.append(
                f"{field_name}: expected {expected_type.__name__}, got {type(value).__name__}"
            )

    if missing_fields:
        logger.warning(f"Missing template fields: {missing_fields}")
        # Don't fail validation for missing fields - they have defaults

    if type_errors:
        logger.error(f"Type errors: {type_errors}")
        return False

    logger.info("Template field validation passed")
    return True


def get_template_field_names() -> list:
    """Get list of all template field names"""
    return list(TEMPLATE_FIELDS.keys())


def get_camel_case_mappings() -> Dict[str, str]:
    """Get camelCase to snake_case mapping dictionary"""
    return CAMEL_TO_SNAKE_MAP.copy()
