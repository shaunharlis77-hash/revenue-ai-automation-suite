from fastapi import APIRouter, HTTPException

from app.models.review_queue import ReviewDecisionRequest, ReviewItem
from app.services.review_queue import (
    approve_review_item,
    get_review_item,
    list_review_items,
    reject_review_item,
)


router = APIRouter(prefix="/review", tags=["review"])


@router.get("/items")
def list_items() -> list[ReviewItem]:
    return list_review_items()


@router.get("/items/{review_item_id}")
def get_item(review_item_id: str) -> ReviewItem:
    try:
        return get_review_item(review_item_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post("/items/{review_item_id}/approve")
def approve_item(
    review_item_id: str, request: ReviewDecisionRequest
) -> ReviewItem:
    try:
        return approve_review_item(review_item_id, request)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=500, detail=str(error)) from error


@router.post("/items/{review_item_id}/reject")
def reject_item(
    review_item_id: str, request: ReviewDecisionRequest
) -> ReviewItem:
    try:
        return reject_review_item(review_item_id, request)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=500, detail=str(error)) from error
