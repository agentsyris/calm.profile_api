export default function handler(req, res) {
  if (req.method !== 'POST') return res.status(405).json({ error: 'method not allowed' })
  try {
    const { responses = {}, meta = {} } = req.body || {}

    const groups = {
      structure: [0,1,2,3,4],
      collaboration: [5,6,7,8,9],
      scope: [10,11,12,13,14],
      tempo: [15,16,17,18,19]
    }
    const axisScore = (arr) => {
      let c = 0, sum = 0
      arr.forEach(i => {
        if (responses[i] === 'A' || responses[i] === 'B') { c++; sum += (responses[i] === 'A' ? 1 : 0) }
      })
      const avg = c ? sum / c : 0.5
      return Math.round(avg * 100)
    }
    const axes = Object.fromEntries(Object.entries(groups).map(([k,v]) => [k, axisScore(v)]))

    const overhead_index = Math.round((100 - axes.structure) * 0.4 + (100 - axes.tempo) * 0.3 + (100 - axes.collaboration) * 0.2 + (100 - axes.scope) * 0.1)
    const hours_lost_ppw = Math.max(3, Math.round(overhead_index / 6))
    const team_factor = meta.team_size === '2-5' ? 4 : meta.team_size === '6-15' ? 10 : meta.team_size === '16-50' ? 25 : meta.team_size === '50+' ? 55 : 1
    const annual_cost = Math.round(hours_lost_ppw * 52 * 130 * team_factor)

    const inv = (x) => 100 - x
    const raw = {
      architect:   0.45*axes.structure + 0.25*axes.scope + 0.20*inv(axes.tempo) + 0.10*inv(axes.collaboration),
      conductor:   0.40*axes.collaboration + 0.30*axes.tempo + 0.20*axes.structure + 0.10*axes.scope,
      curator:     0.45*axes.scope + 0.25*inv(axes.structure) + 0.20*inv(axes.tempo) + 0.10*inv(axes.collaboration),
      craftsperson:0.40*axes.structure + 0.30*inv(axes.scope) + 0.20*inv(axes.tempo) + 0.10*axes.collaboration
    }
    const total = Object.values(raw).reduce((a,b)=>a+b,0) || 1
    const mix = Object.fromEntries(Object.entries(raw).map(([k,v]) => [k, Math.round((v/total)*100)]))
    const primary = Object.entries(mix).sort((a,b)=>b[1]-a[1])[0][0]

    const copy = {
      architect: {
        strengths: ['repeatable delivery','risk foresight','documentation clarity'],
        quick_wins: ['replace daily live standup with async form + weekly alignment'],
        tool_stack: ['microsoft 365','planner','sharepoint','power automate'],
        tagline: 'systematic builder of scalable operational frameworks'
      },
      conductor: {
        strengths: ['cross-team alignment','momentum management','meeting facilitation'],
        quick_wins: ['introduce decision logs to cut meeting drag'],
        tool_stack: ['slack','asana','loom','linear'],
        tagline: 'real-time orchestrator of team dynamics and collaboration'
      },
      curator: {
        strengths: ['divergent thinking','pattern spotting','creative direction'],
        quick_wins: ['lock scope with a one-pager before exploration'],
        tool_stack: ['notion','figma','miro','zapier'],
        tagline: 'adaptive orchestrator balancing flexibility with coordination'
      },
      craftsperson: {
        strengths: ['precision','execution excellence','quality control'],
        quick_wins: ['batch reviews; set “definition of done” checklists'],
        tool_stack: ['jira','confluence','clickup','airtable'],
        tagline: 'precision specialist focused on execution excellence'
      }
    }[primary]

    return res.json({
      success: true,
      assessment_id: 'cp_' + Math.random().toString(36).slice(2,10),
      archetype: { primary, mix },
      scores: { overhead_index, axes },
      metrics: { hours_lost_ppw, annual_cost },
      recommendations: {
        strengths: copy.strengths,
        quick_wins: copy.quick_wins,
        tool_stack: copy.tool_stack
      },
      tagline: copy.tagline
    })
  } catch (e) {
    return res.status(500).json({ error: 'failed to score assessment' })
  }
}