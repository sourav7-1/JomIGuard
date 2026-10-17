from fastapi import APIRouter

from app.schemas.field_meta import FieldsMetaResponse, get_field_meta_by_doc_type

router = APIRouter(prefix="/meta", tags=["meta"])


@router.get("/fields", response_model=FieldsMetaResponse)
def get_fields_meta():
    """Field metadata for all four supported document types."""
    return get_field_meta_by_doc_type()
