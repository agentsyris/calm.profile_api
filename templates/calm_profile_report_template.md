# calm.profile diagnostic report

## executive summary

**${company_name}** · **${assessment_date}** · **${report_id}**

${archetype_primary} archetype detected with ${archetype_confidence}% confidence.

**headline roi:**

- estimated productivity overhead: ${overhead_percentage}%
- projected annual cost impact: ${annual_cost:,}
- break-even timeline: ${break_even_timeline}

**top findings:**
${top_findings}

**methodology overview:**
this assessment analyzes 20 behavioral indicators across six core axes: decision-making, collaboration, cadence, planning horizon, documentation, tooling posture. responses are mapped to established archetypes and calibrated against team context variables including meeting load, team size, and hourly rates.

<div class="page-break"></div>

## scope & methodology

| component          | detail                                                              |
| ------------------ | ------------------------------------------------------------------- |
| interviews         | 12 people (account 3, pm 3, creative 4, ops 2)                      |
| projects observed  | 8 (brand, campaign, web, content)                                   |
| time windows       | calendars + zoom logs: last 90 days                                 |
| systems/logs       | asana, notion, monday; gdrive version logs                          |
| artifacts reviewed | 14 briefs, 11 scopes, 9 estimates                                   |
| scoring rubric     | 1–5 across speed/quality/predictability/efficiency/team health      |
| limits             | self-report ±10%, seasonal skew (q4)                                |
| roi assumptions    | team size ${team_size}, blended rates (see p8), adoption speed (p9) |

**assessment methodology:**

- behavioral indicators: 20 questions across 6 axes
- archetype matching: euclidean distance calculation
- archetype scoring via euclidean distance calculation
- overhead calculation: base rate × archetype adjustment × team multiplier
- roi projection: hours lost per week × 52 weeks × hourly rate × team size

**confidence indicators:**

- high confidence: >80% archetype match
- medium confidence: 60-80% archetype match
- low confidence: <60% archetype match

<div class="page-break"></div>

## workstyle profile

![radar](components/radar.svg)

**axis interpretation:**

- **decision-making**: preference for systematic approaches, frameworks, and organized processes
- **collaboration**: comfort level with team dynamics, communication, and shared decision-making
- **cadence**: preference for steady, methodical work vs rapid iteration and change
- **planning horizon**: tendency toward big-picture thinking vs detail-oriented execution
- **documentation**: approach to knowledge capture and information sharing
- **tooling posture**: comfort with technology adoption and digital workflows

**profile insights:**
${radar_insights}

**key patterns identified:**

- sync bias → f2: meeting bloat
- interrupt-driven → f3: context switching

<div class="page-break"></div>

## workstyle profile (continued)

![time-pie](components/time-pie.svg)

**workflow responsibilities:**

| workflow | responsible | accountable | support | consulted | informed |
| | -- | -- | -- | -- | -- |
| intake | ${workflow1_r} | ${workflow1_a} | ${workflow1_s} | ${workflow1_c} | ${workflow1_i} |
| scoping | ${workflow2_r} | ${workflow2_a} | ${workflow2_s} | ${workflow2_c} | ${workflow2_i} |
| production | ${workflow3_r} | ${workflow3_a} | ${workflow3_s} | ${workflow3_c} | ${workflow3_i} |
| qa | ${workflow4_r} | ${workflow4_a} | ${workflow4_s} | ${workflow4_c} | ${workflow4_i} |
| delivery/invoicing | ${workflow5_r} | ${workflow5_a} | ${workflow5_s} | ${workflow5_c} | ${workflow5_i} |

![handoff-flow](components/handoff-flow.svg)

<div class="page-break"></div>

## findings

### f1: ${f1_issue}

**evidence:** ${f1_evidence}  
**impact:** ${f1_impact}  
**root cause:** ${f1_root_cause}  
**preview:** ${f1_preview}

### f2: ${f2_issue}

**evidence:** ${f2_evidence}  
**impact:** ${f2_impact}  
**root cause:** ${f2_root_cause}  
**preview:** ${f2_preview}

![workflow-heatmap](components/workflow-heatmap.svg)

**process efficiency scores:**

- planning: ${efficiency_planning}/10
- execution: ${efficiency_execution}/10
- review: ${efficiency_review}/10
- communication: ${efficiency_communication}/10

**bottleneck identification:**
${workflow_bottlenecks}

<div class="page-break"></div>

## findings (continued)

### f3: ${f3_issue}

**evidence:** ${f3_evidence}  
**impact:** ${f3_impact}  
**root cause:** ${f3_root_cause}  
**preview:** ${f3_preview}

### f4: ${f4_issue}

**evidence:** ${f4_evidence}  
**impact:** ${f4_impact}  
**root cause:** ${f4_root_cause}  
**preview:** ${f4_preview}

![swimlane](components/swimlane.svg)

<div class="page-break"></div>

## findings (continued)

### f5: ${f5_issue}

**evidence:** ${f5_evidence}  
**impact:** ${f5_impact}  
**root cause:** ${f5_root_cause}  
**preview:** ${f5_preview}

![integration-map](components/integration-map.svg)

**findings ↔ recommendations mapping:**

| finding | issue       | recommendation | solution    |
| ------- | ----------- | -------------- | ----------- |
| f1      | ${f1_issue} | r1             | ${r1_title} |
| f2      | ${f2_issue} | r2             | ${r2_title} |
| f3      | ${f3_issue} | r3             | ${r3_title} |
| f4      | ${f4_issue} | r4             | ${r4_title} |
| f5      | ${f5_issue} | r5             | ${r5_title} |

<div class="page-break"></div>

## roi impact

**current state costs:**

- weekly productivity loss: ${hours_lost_ppw} hours
- annual cost impact: ${annual_cost:,}
- team multiplier effect: ${team_multiplier}x

**projected savings:**

- month 1: ${savings_month1}% improvement
- month 3: ${savings_month3}% improvement
- month 6: ${savings_month6}% improvement
- month 12: ${savings_month12}% improvement

**break-even timeline:**
${break_even_timeline}

**roi formulas:**

- base overhead: ${base_overhead}% adjusted to ${overhead_percentage}% given team factors (archetype: ${archetype_adjustment}, team multiplier: ${team_multiplier})
- weekly cost: ${hours_lost_ppw} hours × ${hourly_rate} × ${team_multiplier} people = ${weekly_cost:,}
- annual cost: ${weekly_cost:,} × 52 weeks = ${annual_cost:,}

**blended rates:** account $95 / pm $85 / creative $125 / ops $80  
**line items:** meetings, review latency, duplicate entry, rework, estimate variance, write-offs  
*formulas:* capacity = (baseline hrs − improved hrs) × volume; blended rate = current ÷ baseline hrs; delta$ = current − improved

<div class="page-break"></div>

## roi impact (continued)

![12-month savings](components/savings-line-12mo.svg)

**sensitivity analysis:**

| implementation success | margin (pp) | $/q | hours released/q |
| - | | | -- |
| 25% | ${sensitivity_25_margin} pp | ${sensitivity_25_cost:,} | ${sensitivity_25_hours} |
| 50% | ${sensitivity_50_margin} pp | ${sensitivity_50_cost:,} | ${sensitivity_50_hours} |
| 75% | ${sensitivity_75_margin} pp | ${sensitivity_75_cost:,} | ${sensitivity_75_hours} |

**adoption scenarios:**

| scenario | team adoption | timeline | 5-yr savings |
| | - | -- | |
| conservative | 25% | 6 months | ${conservative_5yr:,} |
| realistic | 50% | 4 months | ${realistic_5yr:,} |
| optimistic | 75% | 3 months | ${optimistic_5yr:,} |

![5-year cumulative savings](components/savings-line-5yr.svg)

<div class="page-break"></div>

## recommendations

### r1: ${r1_title}

**linked to:** f${r1_linked_finding}  
**description:** ${r1_description}  
**impact:** ${r1_impact}  
**effort:** ${r1_effort}  
**rice score:** ${r1_rice}

### r2: ${r2_title}

**linked to:** f${r2_linked_finding}  
**description:** ${r2_description}  
**impact:** ${r2_impact}  
**effort:** ${r2_effort}  
**rice score:** ${r2_rice}

### r3: ${r3_title}

**linked to:** f${r3_linked_finding}  
**description:** ${r3_description}  
**impact:** ${r3_impact}  
**effort:** ${r3_effort}  
**rice score:** ${r3_rice}

<div class="page-break"></div>

## recommendations (continued)

### r4: ${r4_title}

**linked to:** f${r4_linked_finding}  
**description:** ${r4_description}  
**impact:** ${r4_impact}  
**effort:** ${r4_effort}  
**rice score:** ${r4_rice}

### r5: ${r5_title}

**linked to:** f${r5_linked_finding}  
**description:** ${r5_description}  
**impact:** ${r5_impact}  
**effort:** ${r5_effort}  
**rice score:** ${r5_rice}

![impact matrix](components/impact-matrix.svg)

**critical path:**
${critical_path}

**milestone schedule:**
${milestone_schedule}

<div class="page-break"></div>

## 30/60/90 roadmap

![mini-gantt](components/mini-gantt.svg)

**30-day quick wins:**
${roadmap_30_days}

**60-day foundations:**
${roadmap_60_days}

**90-day optimization:**
${roadmap_90_days}

**success kpis:**

| metric | baseline | target | owner |
| -- | -- | | -- |
| on-time delivery | ${baseline_ontime}% | ${target_ontime}% | ${owner_ontime} |
| latency reduction | ${baseline_latency}% | ${target_latency}% | ${owner_latency} |
| estimate variance | ${baseline_variance} pp | ${target_variance} pp | ${owner_variance} |
| change-order capture | ${baseline_change}% | ${target_change}% | ${owner_change} |

**next steps:**
${next_steps}

_appendix (tool audit, survey cuts, rasic drafts, raw tables) is provided off-doc via qr/link to a shared folder._
