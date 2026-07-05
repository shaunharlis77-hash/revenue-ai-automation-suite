import { redirect } from "next/navigation";

import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { PageHeader } from "@/components/PageHeader";
import { StatusBadge } from "@/components/StatusBadge";
import { decideReviewItem, getReviewItems, type ReviewItem } from "@/lib/api";

type ReviewQueuePageProps = {
  searchParams?: Promise<Record<string, string | string[] | undefined>>;
};

export default async function ReviewQueuePage({
  searchParams,
}: ReviewQueuePageProps) {
  const params = searchParams ? await searchParams : {};
  const notice = textParam(params.notice);
  const error = textParam(params.error);
  const { items, loadError } = await loadReviewItems();

  return (
    <div className="pageStack">
      <PageHeader
        eyebrow="Admin"
        title="Review Queue"
        description="Approve or reject prepared workflow output before it becomes customer-facing or changes CRM operations."
        badge={<StatusBadge status="review" />}
      />

      {notice ? <div className="notice successNotice">{notice}</div> : null}
      {error ? <div className="notice errorNotice">{error}</div> : null}

      {loadError ? (
        <ErrorState
          message="The review queue could not be loaded. Start the FastAPI backend and refresh this page."
          detail={loadError}
        />
      ) : null}

      {!loadError && items.length === 0 ? (
        <EmptyState
          title="No review items"
          message="No workflow output is waiting for human decision right now. Run the demo seed journey or create a follow-up/proposal workflow to populate this queue."
        />
      ) : null}

      {!loadError && items.length > 0 ? (
        <section className="reviewList" aria-label="Review items">
          {items.map((item) => (
            <ReviewItemCard key={item.review_item_id} item={item} />
          ))}
        </section>
      ) : null}
    </div>
  );
}

async function loadReviewItems() {
  try {
    return { items: await getReviewItems(), loadError: "" };
  } catch (error) {
    return {
      items: [] as ReviewItem[],
      loadError:
        error instanceof Error
          ? error.message
          : "The review queue could not be loaded.",
    };
  }
}

function ReviewItemCard({ item }: { item: ReviewItem }) {
  const isPending = item.status === "pending";

  return (
    <article className="reviewItem">
      <div className="reviewItemHeader">
        <div>
          <h2 className="reviewTitle">{item.title}</h2>
          <p className="reviewMeta">
            {item.company || "Unknown company"} /{" "}
            {item.contact_name || "Unknown contact"}
          </p>
        </div>
        <div className="badgeRow">
          <span className={`miniBadge status-${item.status}`}>{item.status}</span>
          <span className={`miniBadge risk-${riskTone(item.risk_level)}`}>
            {item.risk_level} risk
          </span>
          {isCustomerFacing(item.review_type) ? (
            <span className="miniBadge badge-review">customer-facing review</span>
          ) : null}
          {isCrmReview(item.review_type) ? (
            <span className="miniBadge badge-crm">CRM update review</span>
          ) : null}
        </div>
      </div>

      <dl className="reviewDetails">
        <div>
          <dt>Workflow</dt>
          <dd>{formatLabel(item.workflow_name)}</dd>
        </div>
        <div>
          <dt>Review type</dt>
          <dd>{formatLabel(item.review_type)}</dd>
        </div>
        <div>
          <dt>Priority</dt>
          <dd>{item.priority}</dd>
        </div>
        <div>
          <dt>Created</dt>
          <dd>{formatDate(item.created_at)}</dd>
        </div>
        <div>
          <dt>Assigned to</dt>
          <dd>{item.assigned_to || "Unassigned"}</dd>
        </div>
      </dl>

      <div className="reviewBlock">
        <p className="cardLabel">Review reasons</p>
        <ul className="compactList">
          {item.review_reasons.map((reason) => (
            <li key={reason}>{reason}</li>
          ))}
        </ul>
      </div>

      <div className="reviewBlock">
        <p className="cardLabel">Proposed action</p>
        <p>{item.proposed_action}</p>
      </div>

      {item.proposed_output ? (
        <div className="reviewBlock">
          <p className="cardLabel">Prepared output</p>
          <p>{item.proposed_output}</p>
        </div>
      ) : null}

      {isPending ? (
        <div className="actionRow">
          <form action={approveReviewItem}>
            <input
              name="review_item_id"
              type="hidden"
              value={item.review_item_id}
            />
            <button className="primaryButton" type="submit">
              Approve
            </button>
          </form>
          <form action={rejectReviewItem}>
            <input
              name="review_item_id"
              type="hidden"
              value={item.review_item_id}
            />
            <button className="secondaryButton" type="submit">
              Reject
            </button>
          </form>
        </div>
      ) : (
        <p className="decisionText">
          Decision: {item.decision || item.status}
          {item.decision_reason ? ` / ${item.decision_reason}` : ""}
        </p>
      )}
    </article>
  );
}

async function approveReviewItem(formData: FormData) {
  "use server";

  const reviewItemId = String(formData.get("review_item_id") || "");
  let target = "/review-queue?notice=Review%20item%20approved.";

  try {
    await decideReviewItem(
      reviewItemId,
      "approve",
      "Approved from Review Queue UI.",
    );
  } catch (error) {
    target = `/review-queue?error=${encodeURIComponent(errorMessage(error))}`;
  }

  redirect(target);
}

async function rejectReviewItem(formData: FormData) {
  "use server";

  const reviewItemId = String(formData.get("review_item_id") || "");
  let target = "/review-queue?notice=Review%20item%20rejected.";

  try {
    await decideReviewItem(
      reviewItemId,
      "reject",
      "Rejected from Review Queue UI.",
    );
  } catch (error) {
    target = `/review-queue?error=${encodeURIComponent(errorMessage(error))}`;
  }

  redirect(target);
}

function textParam(value: string | string[] | undefined) {
  return Array.isArray(value) ? value[0] : value;
}

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : "Action failed.";
}

function isCustomerFacing(reviewType: string) {
  return reviewType === "follow_up_draft" || reviewType === "proposal_outline";
}

function isCrmReview(reviewType: string) {
  return reviewType === "crm_update" || reviewType === "deal_stage_change";
}

function riskTone(riskLevel: string) {
  return riskLevel === "critical" || riskLevel === "high" ? "high" : "normal";
}

function formatLabel(value: string) {
  return value.replaceAll("_", " ");
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}
