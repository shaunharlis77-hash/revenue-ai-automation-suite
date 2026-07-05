"""First version of Workflow 2: Meeting Capture and CRM Summary.

The service uses deterministic extraction rules only so the workflow stays easy
to test before LLM, CRM, or meeting platform integration is added.
"""

from app.models.meeting_summary import (
    MeetingSummaryRequest,
    MeetingSummaryResponse,
    RecommendedAction,
)
from app.models.workflow_logs import (
    WorkflowRunFailureRequest,
    WorkflowRunStartRequest,
    WorkflowRunSuccessRequest,
)
from app.services.workflow_logs import (
    mark_workflow_failure,
    mark_workflow_success,
    start_workflow_run,
)
from app.services.workflow_steps import (
    log_step_failure,
    log_step_started,
    log_step_success,
)
from app.services.workflow_audit import (
    audit_completed,
    audit_started,
    audit_workflow_failure,
    record_meeting_summary_audit,
)


WORKFLOW_NAME = "meeting_capture_crm_summary"


def normalize(value: str | None) -> str:
    return (value or "").strip().lower()


def contains_any(text: str, keywords: tuple[str, ...]) -> bool:
    normalized = normalize(text)
    return any(keyword in normalized for keyword in keywords)


def clean_text(text: str) -> str:
    return " ".join(text.split())


def clean_action_description(description: str) -> str:
    cleaned = " ".join(description.split())

    replacements = {
        "agreednext": "agreed next",
        "reviewqueue": "review queue",
        "thereview": "the review",
        "Flagmissing": "Flag missing",
        "Createa": "Create a",
        "arep": "a rep",
        "nextsteps": "next steps",
        "aretoo": "are too",
        "actionsto": "actions to",
        "withrevenue": "with revenue",
    }

    for bad, good in replacements.items():
        cleaned = cleaned.replace(bad, good)

    return cleaned


def recommended_action(
    action_type: str,
    description: str,
    due: str,
    automation_status: str,
) -> RecommendedAction:
    return RecommendedAction(
        action_type=action_type,
        description=clean_action_description(description),
        due=due,
        automation_status=automation_status,
    )


def summarize_meeting(meeting: MeetingSummaryRequest) -> MeetingSummaryResponse:
    workflow_run = start_workflow_run(
        WorkflowRunStartRequest(
            workflow_name=WORKFLOW_NAME,
            input_reference=meeting.meeting_id or meeting.deal_id,
        )
    )
    entity_id = meeting.meeting_id or meeting.deal_id or meeting.company
    failed_step = "workflow_started"
    log_step_started(
        workflow_run.workflow_run_id,
        WORKFLOW_NAME,
        "workflow_started",
        1,
        "meeting",
        entity_id,
    )

    try:
        audit_started(workflow_run, "meeting", entity_id)
        failed_step = "input_validated"
        log_step_success(
            workflow_run.workflow_run_id,
            WORKFLOW_NAME,
            "input_validated",
            2,
            "meeting",
            entity_id,
        )
        failed_step = "meeting_summary_created"
        result = _summarize_meeting(meeting)
        log_step_success(
            workflow_run.workflow_run_id,
            WORKFLOW_NAME,
            "meeting_summary_created",
            3,
            "meeting",
            entity_id,
            {"confidence": result.confidence},
        )
        log_step_success(
            workflow_run.workflow_run_id,
            WORKFLOW_NAME,
            "next_steps_extracted",
            4,
            "meeting",
            entity_id,
            {"next_steps": result.next_steps},
        )
        log_step_success(
            workflow_run.workflow_run_id,
            WORKFLOW_NAME,
            "recommended_actions_created",
            5,
            "meeting",
            entity_id,
            {"action_count": len(result.recommended_actions)},
        )
        review_required_actions = [
            action.action_type
            for action in result.recommended_actions
            if action.automation_status == "review_required"
        ]
        log_step_success(
            workflow_run.workflow_run_id,
            WORKFLOW_NAME,
            "review_actions_identified",
            6,
            "meeting",
            entity_id,
            {"review_required_actions": review_required_actions},
        )
        failed_step = "audit_events_written"
        record_meeting_summary_audit(workflow_run, meeting, result)
        log_step_success(
            workflow_run.workflow_run_id,
            WORKFLOW_NAME,
            "audit_events_written",
            7,
            "meeting",
            entity_id,
        )
        mark_workflow_success(
            workflow_run.workflow_run_id,
            WorkflowRunSuccessRequest(
                output_summary=(
                    f"Meeting summary created with {result.confidence} confidence "
                    f"and deal stage recommendation {result.deal_stage_recommendation}."
                ),
                human_review_required=result.human_review_required,
                next_action=next_action_from_meeting_summary(result),
            ),
        )
        audit_completed(
            workflow_run,
            "meeting",
            entity_id,
            result.meeting_id or entity_id,
            result.human_review_required,
        )
        log_step_success(
            workflow_run.workflow_run_id,
            WORKFLOW_NAME,
            "workflow_completed",
            8,
            "meeting",
            entity_id,
        )
        return result
    except Exception as error:
        log_step_failure(
            workflow_run.workflow_run_id,
            WORKFLOW_NAME,
            failed_step,
            error,
            entity_type="meeting",
            entity_id=entity_id,
            failure_reason=str(error),
            retryable=failed_step == "audit_events_written",
            recommended_fix="Check the meeting input, extraction rules, and audit/review persistence path.",
        )
        mark_workflow_failure(
            workflow_run.workflow_run_id,
            WorkflowRunFailureRequest(
                failure_step=failed_step,
                failure_reason=str(error),
                input_reference=meeting.meeting_id or meeting.deal_id,
            ),
        )
        try:
            audit_workflow_failure(
                workflow_run,
                "meeting",
                meeting.meeting_id or meeting.deal_id or meeting.company,
                failed_step,
                str(error),
            )
        except Exception as audit_error:
            log_step_failure(
                workflow_run.workflow_run_id,
                WORKFLOW_NAME,
                "audit_events_written",
                audit_error,
                entity_type="meeting",
                entity_id=entity_id,
                failure_reason="Audit write failed while recording workflow failure.",
                retryable=True,
                recommended_fix="Check audit event persistence after the meeting summary failure.",
                metadata_json={"original_failure_step": failed_step},
            )
        raise


def _summarize_meeting(meeting: MeetingSummaryRequest) -> MeetingSummaryResponse:
    if is_low_quality_transcript(meeting.transcript):
        response = low_quality_response(meeting)
        response.recommended_actions = clean_recommended_actions(response.recommended_actions)
        return response

    transcript = meeting.transcript
    pain_points = detect_pain_points(transcript)
    objections = detect_objections(transcript)
    buying_signals = detect_buying_signals(transcript)
    next_steps = detect_next_steps(transcript)
    follow_up_due = detect_follow_up_due(transcript)
    proposal_needed = detect_proposal_needed(transcript)
    deal_stage = recommend_deal_stage(transcript, pain_points, buying_signals)
    needs_more_info = detect_needs_more_info(transcript, pain_points, next_steps)
    confidence = determine_confidence(transcript, needs_more_info)
    human_review_required = determine_human_review_required(
        transcript=transcript,
        proposal_needed=proposal_needed,
        needs_more_info=needs_more_info,
        deal_stage_recommendation=deal_stage,
    )

    recommended_actions = build_recommended_actions(
        meeting=meeting,
        deal_stage_recommendation=deal_stage,
        proposal_needed=proposal_needed,
        confidence=confidence,
        needs_more_info=needs_more_info,
        follow_up_due=follow_up_due,
        next_steps=next_steps,
    )
    recommended_actions = clean_recommended_actions(recommended_actions)

    return MeetingSummaryResponse(
        meeting_id=meeting.meeting_id,
        crm_note=build_crm_note(meeting, pain_points, objections, buying_signals, next_steps),
        pain_points=pain_points,
        objections=objections,
        buying_signals=buying_signals,
        next_steps=next_steps,
        follow_up_due=follow_up_due,
        deal_stage_recommendation=deal_stage,
        proposal_needed=proposal_needed,
        confidence=confidence,
        human_review_required=human_review_required,
        needs_more_info=needs_more_info,
        recommended_actions=[
            recommended_action(
                action_type=action.action_type,
                description=action.description,
                due=action.due,
                automation_status=action.automation_status,
            )
            for action in recommended_actions
        ],
        reasoning=build_reasoning(
            confidence=confidence,
            human_review_required=human_review_required,
            needs_more_info=needs_more_info,
            proposal_needed=proposal_needed,
            deal_stage_recommendation=deal_stage,
        ),
    )


def is_low_quality_transcript(transcript: str) -> bool:
    normalized = normalize(transcript)
    vague_phrases = ("short call", "need more info", "follow up later")
    return len(normalized.split()) < 14 or contains_any(normalized, vague_phrases)


def clean_recommended_actions(actions: list[RecommendedAction]) -> list[RecommendedAction]:
    return [
        recommended_action(
            action_type=action.action_type,
            description=action.description,
            due=action.due,
            automation_status=action.automation_status,
        )
        for action in actions
    ]


def next_action_from_meeting_summary(result: MeetingSummaryResponse) -> str:
    review_action = next(
        (
            action.description
            for action in result.recommended_actions
            if action.automation_status == "review_required"
        ),
        None,
    )
    if review_action:
        return review_action
    if result.recommended_actions:
        return result.recommended_actions[0].description
    return "Review the meeting summary."


def low_quality_response(meeting: MeetingSummaryRequest) -> MeetingSummaryResponse:
    return MeetingSummaryResponse(
        meeting_id=meeting.meeting_id,
        crm_note=(
            f"Short call with {meeting.contact_name} at {meeting.company}. "
            "Notes are too limited to identify clear pain, budget, timeline, or next steps."
        ),
        pain_points=["Unclear need"],
        objections=["Not enough information"],
        buying_signals=[],
        next_steps=["Ask for pain points, timeline, budget, and next step"],
        follow_up_due="not_set",
        deal_stage_recommendation="needs_qualification",
        proposal_needed=False,
        confidence="low",
        human_review_required=True,
        needs_more_info=True,
        recommended_actions=[
            recommended_action(
                action_type="prepare_crm_note",
                description="Prepare a low-confidence CRM note saying the call notes are too limited.",
                due="now",
                automation_status="auto_allowed",
            ),
            recommended_action(
                action_type="flag_missing_info",
                description="Flag missing information from the meeting summary.",
                due="now",
                automation_status="auto_allowed",
            ),
            recommended_action(
                action_type="create_task",
                description="Create a rep task: Gather missing qualification details.",
                due="not_set",
                automation_status="auto_allowed",
            ),
            recommended_action(
                action_type="schedule_review",
                description="Add the prepared summary and actions to the review queue.",
                due="before_crm_update",
                automation_status="review_required",
            ),
        ],
        reasoning="Transcript is too short and lacks enough detail for a reliable CRM summary.",
    )


def detect_pain_points(transcript: str) -> list[str]:
    checks = [
        (("manual qualification", "qualifying leads manually"), "Manual qualification"),
        (("lead routing", "routing"), "Lead routing"),
        (("slow response", "slow response times"), "Slow response times"),
        (("unclear ownership",), "Unclear ownership"),
        (("crm cleanup",), "CRM cleanup"),
        (("lead handoff",), "Lead handoff quality"),
        (("manager visibility",), "Manager visibility"),
        (("adoption", "change management"), "Sales adoption"),
        (("sdr workload", "sdr queue"), "SDR workload"),
        (("inbound volume",), "Inbound volume"),
        (("implementation effort", "long setup"), "Implementation effort"),
        (("sla risk",), "SLA risk"),
    ]
    return detect_labels(transcript, checks) or ["Unclear need"]


def detect_objections(transcript: str) -> list[str]:
    checks = [
        (("budget unknown",), "Budget unknown"),
        (("timeline unknown",), "Timeline unknown"),
        (("price", "pricing"), "Pricing concern"),
        (("budget is tight",), "Budget is tight"),
        (("long setup",), "Long setup concern"),
        (("implementation plan is clear", "implementation plan must be clear"), "Implementation plan must be clear"),
        (("security", "security review"), "Security review needed"),
        (("adoption", "nervous about adopting"), "Sales team adoption concern"),
        (("manager buy-in",), "Manager buy-in needed"),
    ]
    return detect_labels(transcript, checks)


def detect_buying_signals(transcript: str) -> list[str]:
    checks = [
        (("approved budget", "budget is approved"), "Approved budget"),
        (("budget is planned", "budget planned"), "Planned budget"),
        (("timeline is this month", "clear timeline"), "Clear timeline"),
        (("30 days", "30-day"), "30-day timeline"),
        (("campaign launch",), "Campaign launch deadline"),
        (("before monday", "urgent"), "Urgent deadline"),
        (("technical discovery",), "Technical discovery requested"),
        (("operations review",), "Operations review requested"),
        (("manager review",), "Manager review requested"),
        (("package option",), "Asked for package option"),
        (("hubspot",), "HubSpot context"),
    ]
    return detect_labels(transcript, checks)


def detect_next_steps(transcript: str) -> list[str]:
    checks = [
        (("send workflow outline",), "Send workflow outline"),
        (("schedule technical discovery",), "Schedule technical discovery with revenue operations"),
        (("send a short overview", "sending a short overview"), "Send short overview"),
        (("provide implementation plan today", "send the implementation plan today"), "Send implementation plan today"),
        (("book a security and operations review tomorrow", "book security and operations review tomorrow"), "Book security and operations review tomorrow"),
        (("send a simple package option",), "Send simple package option"),
        (("confirm budget range next week",), "Confirm budget range next week"),
        (("share adoption plan",), "Share adoption plan"),
        (("schedule manager review",), "Schedule manager review"),
    ]
    return detect_labels(transcript, checks) or ["Confirm next step"]


def detect_labels(
    transcript: str, checks: list[tuple[tuple[str, ...], str]]
) -> list[str]:
    labels: list[str] = []
    for keywords, label in checks:
        if contains_any(transcript, keywords) and label not in labels:
            labels.append(label)
    return labels


def detect_follow_up_due(transcript: str) -> str:
    normalized = normalize(transcript)
    if "today" in normalized:
        return "today"
    if "tomorrow" in normalized:
        return "tomorrow"
    if "thursday" in normalized:
        return "Thursday"
    if "next week" in normalized:
        return "next_week"
    return "not_set"


def detect_proposal_needed(transcript: str) -> bool:
    return contains_any(
        transcript,
        (
            "implementation plan",
            "package option",
            "pricing",
            "price",
            "budget is tight",
            "lightweight version",
            "before monday",
        ),
    )


def recommend_deal_stage(
    transcript: str, pain_points: list[str], buying_signals: list[str]
) -> str:
    if contains_any(transcript, ("before monday", "security and operations review")):
        return "solution_review"
    if contains_any(transcript, ("pricing", "price", "package option", "budget is tight")):
        return "qualification"
    if contains_any(transcript, ("general overview", "not sure what workflow")):
        return "nurture"
    has_clear_pain = pain_points != ["Unclear need"]
    has_budget = any("budget" in normalize(signal) for signal in buying_signals)
    has_timeline = any(
        "timeline" in normalize(signal) or "deadline" in normalize(signal)
        for signal in buying_signals
    )
    if has_clear_pain and has_budget and has_timeline:
        return "qualified_discovery"
    return "needs_qualification"


def detect_needs_more_info(
    transcript: str, pain_points: list[str], next_steps: list[str]
) -> bool:
    if pain_points == ["Unclear need"]:
        return True
    if next_steps == ["Confirm next step"]:
        return True
    return contains_any(transcript, ("budget unknown", "timeline unknown", "not sure"))


def determine_confidence(transcript: str, needs_more_info: bool) -> str:
    if needs_more_info:
        return "medium"
    if len(normalize(transcript).split()) >= 25:
        return "high"
    return "medium"


def determine_human_review_required(
    transcript: str,
    proposal_needed: bool,
    needs_more_info: bool,
    deal_stage_recommendation: str,
) -> bool:
    if proposal_needed or needs_more_info:
        return True
    if deal_stage_recommendation not in {"nurture", "needs_qualification"}:
        return True
    return contains_any(
        transcript,
        ("pricing", "security", "implementation", "adoption", "change management"),
    )


def build_crm_note(
    meeting: MeetingSummaryRequest,
    pain_points: list[str],
    objections: list[str],
    buying_signals: list[str],
    next_steps: list[str],
) -> str:
    parts = [
        f"Meeting with {meeting.contact_name} at {meeting.company}.",
        f"Pain points: {', '.join(pain_points)}.",
    ]
    if objections:
        parts.append(f"Objections or risks: {', '.join(objections)}.")
    if buying_signals:
        parts.append(f"Buying signals: {', '.join(buying_signals)}.")
    if next_steps:
        parts.append(f"Next steps: {', '.join(next_steps)}.")
    return " ".join(parts)


def build_recommended_actions(
    meeting: MeetingSummaryRequest,
    deal_stage_recommendation: str,
    proposal_needed: bool,
    confidence: str,
    needs_more_info: bool,
    follow_up_due: str,
    next_steps: list[str],
) -> list[RecommendedAction]:
    actions = [
        recommended_action(
            action_type="prepare_crm_note",
            description="Prepare a CRM note draft from the meeting summary.",
            due="now",
            automation_status="auto_allowed",
        )
    ]

    if needs_more_info:
        actions.append(
            recommended_action(
                action_type="flag_missing_info",
                description="Flag missing information from the meeting summary.",
                due="now",
                automation_status="auto_allowed",
            )
        )

    for next_step in next_steps:
        actions.append(
            recommended_action(
                action_type="create_task",
                description=format_task_description(next_step),
                due=follow_up_due,
                automation_status="auto_allowed",
            )
        )

    if next_steps and next_steps != ["Confirm next step"]:
        actions.append(
            recommended_action(
                action_type="draft_follow_up",
                description=("Prepare a customer follow-up draft from the agreed " "next steps."),
                due=follow_up_due if follow_up_due != "not_set" else "before_customer_send",
                automation_status="review_required",
            )
        )

    if deal_stage_recommendation not in {"nurture", "needs_qualification"}:
        actions.append(
            recommended_action(
                action_type="recommend_deal_stage",
                description=f"Recommend deal stage: {deal_stage_recommendation}.",
                due="before_crm_update",
                automation_status="review_required",
            )
        )

    if proposal_needed:
        actions.append(
            recommended_action(
                action_type="draft_proposal_outline",
                description="Prepare a proposal or package outline for review.",
                due=follow_up_due if follow_up_due != "not_set" else "before_customer_send",
                automation_status="review_required",
            )
        )

    if confidence == "low" or needs_more_info or proposal_needed or deal_stage_recommendation not in {"nurture", "needs_qualification"}:
        actions.append(
            recommended_action(
                action_type="schedule_review",
                description=("Add the prepared summary and actions to the review " "queue."),
                due="before_crm_update",
                automation_status="review_required",
            )
        )

    return actions


def format_task_description(next_step: str) -> str:
    cleaned_step = clean_text(next_step)
    if not cleaned_step:
        cleaned_step = "Confirm next step"
    return f"Create a rep task: {cleaned_step}."


def build_reasoning(
    confidence: str,
    human_review_required: bool,
    needs_more_info: bool,
    proposal_needed: bool,
    deal_stage_recommendation: str,
) -> str:
    review_text = "requires review" if human_review_required else "does not require review"
    if needs_more_info:
        return f"Summary has {confidence} confidence and {review_text} because important information is missing."
    if proposal_needed:
        return f"Summary has {confidence} confidence and {review_text} because proposal or implementation work is involved."
    return f"Summary has {confidence} confidence, recommends {deal_stage_recommendation}, and {review_text}."
