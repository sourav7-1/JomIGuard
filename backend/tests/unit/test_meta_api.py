from app.schemas.extracted import DeedData, HeirCertData, KhatianData, MutationData
from app.schemas.field_meta import (
    DOC_TYPE_FIELDS,
    extract_schema_fields,
)


def test_meta_fields_api(client):
    r = client.get("/meta/fields")
    assert r.status_code == 200
    data = r.json()
    assert "khatian" in data
    assert "deed" in data
    assert "dcr" in data
    assert "heir_cert" in data


def test_every_schema_field_has_metadata_and_vice_versa():
    """Assert every field in the four Pydantic document schemas has corresponding
    metadata in field_meta, and every metadata entry corresponds to a valid schema field."""
    checks = [
        ("khatian", KhatianData),
        ("deed", DeedData),
        ("dcr", MutationData),
        ("heir_cert", HeirCertData),
    ]

    for doc_type, model_cls in checks:
        schema_fields = extract_schema_fields(model_cls)
        meta_fields = {f.path for f in DOC_TYPE_FIELDS[doc_type]}

        missing_in_meta = schema_fields - meta_fields
        extra_in_meta = meta_fields - schema_fields

        assert not missing_in_meta, (
            f"{doc_type} schema fields missing in metadata: {missing_in_meta}"
        )
        assert not extra_in_meta, (
            f"{doc_type} metadata fields not present in schema: {extra_in_meta}"
        )
        assert schema_fields == meta_fields


def test_field_meta_properties():
    """Verify editable, filled_by, and enum_options contract."""
    for _doc_type, fields in DOC_TYPE_FIELDS.items():
        for field in fields:
            # filled_by is either extractor or normalize
            assert field.filled_by in ("extractor", "normalize")

            # editable equals filled_by == extractor, except doc_type discriminator is not editable
            if field.path == "doc_type":
                assert field.editable is False
            else:
                assert field.editable == (field.filled_by == "extractor")

            # kind is one of the allowed kinds
            assert field.kind in (
                "identifier",
                "name",
                "number_text",
                "date_text",
                "enum",
                "text",
                "list",
            )

            # enums have options with value and Bangla label
            if field.kind == "enum":
                assert field.enum_options is not None and len(field.enum_options) > 0
                for opt in field.enum_options:
                    assert opt.value
                    assert opt.label_bn
