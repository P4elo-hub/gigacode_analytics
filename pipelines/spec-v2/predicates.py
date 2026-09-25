"""Thin reasons for authored when: ids (codegen). Predicates evaluate via YAML expr."""

from __future__ import annotations

_REASONS = {
    'agent_zakonchil_svoe_vypolnenie': 'Агент закончил своё выполнение',
    'eshche_odno_svoe_uslovie': 'ещё одно своё условие',
    'has_agent_zakonchil_svoe_vypolnenie': 'Агент закончил своё выполнение',
    'has_alignment_svezhii_verdict_pass_ili_pass_with_gaps_sp': 'ALIGNMENT свежий, verdict PASS или PASS WITH GAPS — spec готов',
    'has_feature_context_slug_md_eshche_net': 'Feature-context/{slug}.md ещё нет',
    'has_kontekst_uzhe_est_a_feature_writing_slug_slug_md_esh': 'контекст уже есть, а Feature-writing/{slug}/{slug}.md ещё нет',
    'has_net_otcheta_ili_on_ustarel_korotko_alignment_net_ili': 'Нет отчёта или он устарел Коротко: ALIGNMENT нет или старше SPEC Чуть точнее: сверки с кодом ещё не было, или SPEC новее ALIGNMENT',
    'has_open_gaps_ne_pustye_posle_revyu_bez_pending_apply': 'open_gaps не пустые (после ревью / без pending-apply)',
    'has_otchet_est_no_bez_pass_korotko_alignment_bez_pass_pa': 'Отчёт есть, но без PASS Коротко: ALIGNMENT без PASS / PASS WITH GAPS Чуть точнее: отчёт есть и не stale, но verdict не PASS — нужен повторный аудит',
    'has_resheniya_po_gap_uzhe_est_nuzhno_primenit_v_spec': 'решения по GAP уже есть — нужно применить в SPEC',
    'has_spec_est_i_posle_poslednei_pravki_eshche_ne_bylo_usp': 'SPEC есть, и после последней правки ещё не было успешного check-feature',
    'has_v_alignment_est_critical_major_raskhozhdeniya_otchet': 'в ALIGNMENT есть Critical/Major расхождения, отчёт свежий, лимит 3 итераций ещё не исчерпан',
    'has_v_decisions_est_needs_answer_s_relates_na_gap_open_g': 'в DECISIONS есть needs-answer с Relates на GAP, open_gaps не пустые',
    'routing_state_needs_refresh': 'нет routing-state.json — нужен analyze-routing',
}


def reason_for_predicate(when: str, status) -> str:
    return _REASONS.get(when, "")
